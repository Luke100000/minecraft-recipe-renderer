import asyncio
import io
import re
from pathlib import Path

from PIL import Image
from cachetools import cached, TTLCache
from fastapi import Query, FastAPI
from fastapi_cache import Coder
from fastapi_cache.decorator import cache
from starlette.requests import Request
from starlette.responses import Response, HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from minecraft_recipe_renderer import ResourceManager, ItemRenderer, Canvas, Item
from minecraft_recipe_renderer.resource_manager import sanitize_url
from minecraft_recipe_renderer.utils import to_location


class BytesCoder(Coder):
    @classmethod
    def encode(cls, value: bytes) -> bytes:
        return value

    @classmethod
    def decode(cls, value: bytes) -> bytes:
        return value


known_dependencies = {
    "1.20.1": "https://piston-data.mojang.com/v1/objects/a7e5a6024bfd3cd614625aa05629adf760020304/client.jar"
}


@cached(
    cache=TTLCache(maxsize=8, ttl=21600), key=lambda dependencies: str(dependencies)
)
def load_manager(dependencies: list[str]) -> ResourceManager:
    manager = ResourceManager(Path("cache/mcr/"))
    for dep in dependencies:
        manager.load_dependency(dep)
    manager.post_load()
    return manager


def encode_image(texture: Image.Image) -> bytes:
    buffer = io.BytesIO()
    texture.save(buffer, format="PNG")
    return buffer.getvalue()


def render_item(location: str, dependencies: list[str], resolution: int) -> bytes:
    # Load resources
    manager = load_manager(dependencies)
    renderer = ItemRenderer(manager)

    model = manager.get_model(location)
    if not model:
        raise ValueError(f"Unknown item model: {location}")

    texture = renderer.render(model, resolution)

    return encode_image(texture)


@cache(expire=21600, coder=BytesCoder())
async def cached_render_item(
    locations: str, dependencies: list[str], resolution: int
) -> bytes:
    return await asyncio.to_thread(render_item, locations, dependencies, resolution)


def render_atlas(
    locations: str,
    dependencies: list[str],
    resolution: int,
    row_size: int,
    background: str,
) -> bytes:
    # Load resources
    manager = load_manager(dependencies)
    renderer = ItemRenderer(manager)

    # Convert and filter
    locations = [
        (
            sorted(manager.tags.get(location[1:], []))
            if (location.startswith("#") or location.startswith("_"))
            else [location]
        )
        for location in [to_location(location) for location in locations.split(";")]
    ]
    locations = [
        location
        for sublist in locations
        for location in sublist
        if manager.get_model(location)
    ]

    if len(locations) == 0:
        raise ValueError(f"Not a single model found: {locations}")

    # Create atlas canvas
    cols = min(row_size, len(locations))
    rows = (len(locations) + row_size - 1) // row_size
    border = 6 if background == "fancy" else 0
    margin = 0 if background == "none" else 1
    canvas = Canvas(
        cols * (16 + margin * 2) + border * 2,
        rows * (16 + margin * 2) + border * 2,
        resolution // 16,
    )

    if background == "fancy":
        canvas.box("menu", 0, 0, canvas.width, canvas.height)

    # Render slots
    for i, location in enumerate(locations):
        x = (i % cols) * (16 + margin * 2) + border
        y = (i // cols) * (16 + margin * 2) + border
        model = manager.get_model(location)
        if model:
            if background != "none":
                canvas.box("slot", x, y, 16 + margin * 2, 16 + margin * 2)
            canvas.item(renderer, Item(location), x + margin, y + margin)

    return encode_image(canvas.image)


@cache(expire=21600, coder=BytesCoder())
async def cached_render_atlas(
    locations: str,
    dependencies: list[str],
    resolution: int,
    row_size: int,
    background: str,
) -> bytes:
    return await asyncio.to_thread(
        render_atlas, locations, dependencies, resolution, row_size, background
    )


def render_recipes(
    locations: str,
    dependencies: list[str],
    resolution: int,
    row_width: int,
    animated: bool,
    max_variations: int = 10,
) -> bytes:
    # Load resources
    manager = load_manager(dependencies)
    renderer = ItemRenderer(manager)

    locations = [to_location(location) for location in locations.split(";")]
    filtered_locations = []
    for name in manager.recipes.keys():
        for location in locations:
            if re.match(location, name):
                filtered_locations.append(name)
                break

    if not filtered_locations:
        raise ValueError("No recipe matched.")

    # Sort for consistent results
    filtered_locations = sorted(filtered_locations)

    # Render recipes
    x = 0
    y = 0
    w = 0
    h = 0
    last_h = 0
    images = []
    for location in filtered_locations:
        recipe = manager.recipes[location]
        image = recipe.render(
            renderer,
            resolution // 16,
            max_variations=max_variations if animated else 1,
            print_name=len(filtered_locations) > 1,
        )

        if not image:
            image.append(Image.new("RGBA", (16, 16), color=(0, 0, 0, 0)))

        size = image[0].size
        if x + size[0] > row_width and x > 0:
            x = 0
            y += last_h
            last_h = 0
            if y > (2048 if animated else 8192):
                break

        images.append((image, x, y))

        w = max(w, x + size[0])
        h = max(h, y + size[1])
        last_h = max(last_h, size[1])

        x += size[0]

    if len(images) == 1:
        atlases = [i[0][0] for i in images]
    else:
        atlases = []
        max_variations = max([len(recipe[0]) for recipe in images])
        for variation in range(max_variations):
            atlas = Image.new(
                "RGBA",
                (w, h),
                color=(0, 0, 0, 0),
            )
            for image, x, y in images:
                atlas.paste(image[variation % len(image)], (x, y))
            atlases.append(atlas)

    if animated:
        buffer = io.BytesIO()
        atlases[0].save(
            buffer,
            format="GIF",
            save_all=True,
            append_images=atlases[1:],
            duration=1000,
            loop=0,
        )
        return buffer.getvalue()
    else:
        return encode_image(atlases[0])


@cache(expire=21600, coder=BytesCoder())
async def cached_render_recipes(
    locations: str,
    dependencies: list[str],
    resolution: int,
    row_width: int,
    animated: bool,
) -> bytes:
    return await asyncio.to_thread(
        render_recipes, locations, dependencies, resolution, row_width, animated
    )


def parse_dependencies(minecraft_version: str, dependencies: str) -> list[str]:
    return [
        sanitize_url(known_dependencies[d] if d in known_dependencies else d.strip())
        for d in (dependencies.split(";") + [minecraft_version])
        if d.strip()
    ]


def setup(app: FastAPI):
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    async def get_index(request: Request, page: str = "recipes"):
        if page not in ["recipes", "atlas", "item"]:
            return Response(status_code=404)
        return templates.TemplateResponse(request=request, name=f"{page}.html")

    @app.get(
        "/item",
        responses={200: {"content": {"image/png": {}}}},
    )
    async def get_item(
        location: str = Query(
            title="Resource Location",
            description="The resource location of the item or tag to render. "
            "It can be a list of locations separated by semicolons. ",
            examples=[
                "minecraft:iron_ingot",
                "minecraft:iron_ingot;minecraft:gold_ingot",
                "minecraft:iron_ingot;#minecraft:ingots",
            ],
            min_length=1,
        ),
        minecraft_version: str = Query(
            default="1.20.1",
            title="Minecraft Version",
            description="The version of Minecraft to use as the primary dependency.",
        ),
        dependencies: str = Query(
            default="",
            title="Dependencies",
            description="A semicolon separated list of dependencies, given as repository or JAR URLs.",
        ),
        resolution: int = Query(
            default=16,
            ge=16,
            le=256,
            title="Resolution",
            description="The resolution of the image, a multiple of 16.",
        ),
        _c: int = Query(
            default=0,
            title="Cache Breaker",
            description="This flag is ignored and can be used to break caches.",
        ),
    ) -> Response:
        if resolution % 16 != 0:
            raise ValueError("Resolution must be a multiple of 16.")

        try:
            parsed_dependencies = parse_dependencies(minecraft_version, dependencies)

            result = await cached_render_item(location, parsed_dependencies, resolution)
        except ValueError as e:
            return Response(status_code=422, content=str(e))

        return Response(
            content=result,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=21600, immutable"},
        )

    @app.get(
        "/atlas",
        responses={200: {"content": {"image/png": {}}}},
    )
    async def get_atlas(
        locations: str = Query(
            title="Resource Locations",
            description="A comma separated list of resource locations and tags to render. ",
            examples=[
                "minecraft:iron_ingot;minecraft:gold_ingot",
                "minecraft:iron_ingot;#minecraft:ingots",
            ],
            min_length=1,
        ),
        minecraft_version: str = Query(
            default="1.20.1",
            title="Minecraft Version",
            description="The version of Minecraft to use as the primary dependency.",
        ),
        dependencies: str = Query(
            default="",
            title="Dependencies",
            description="A semicolon separated list of dependencies, given as repository or JAR URLs.",
        ),
        resolution: int = Query(
            default=16,
            ge=16,
            le=256,
            title="Resolution",
            description="The resolution of the image, a multiple of 16.",
        ),
        row_size: int = Query(
            default=8,
            ge=1,
            title="Items per row",
            description="The number of items to display per row before wrapping.",
        ),
        background: str = Query(
            default="none",
            title="Background Style",
            description="The style of the background, can be 'none', 'simple', or 'fancy'.",
        ),
        _c: int = Query(
            default=0,
            title="Cache Breaker",
            description="This flag is ignored and can be used to break caches.",
        ),
    ) -> Response:
        if resolution % 16 != 0:
            raise ValueError("Resolution must be a multiple of 16.")

        try:
            parsed_dependencies = parse_dependencies(minecraft_version, dependencies)

            result = await cached_render_atlas(
                locations, parsed_dependencies, resolution, row_size, background
            )
        except ValueError as e:
            return Response(status_code=422, content=str(e))

        return Response(
            content=result,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=21600, immutable"},
        )

    @app.get(
        "/recipes",
        responses={200: {"content": {"image/png": {}}}},
    )
    async def get_recipes(
        locations: str = Query(
            title="Resource Locations",
            description="A comma separated list of recipes. "
            "Recipes can contain regex patterns.",
            examples=[
                "minecraft:iron_ingot;minecraft:gold_ingot",
                "minecraft:.*_ingot",
            ],
            min_length=1,
        ),
        minecraft_version: str = Query(
            default="1.20.1",
            title="Minecraft Version",
            description="The version of Minecraft to use as the primary dependency.",
        ),
        dependencies: str = Query(
            default="",
            title="Dependencies",
            description="A semicolon separated list of dependencies, given as repository or JAR URLs.",
        ),
        resolution: int = Query(
            default=16,
            ge=16,
            le=128,
            title="Resolution",
            description="The resolution of the image, a multiple of 16.",
        ),
        row_width: int = Query(
            default=1024,
            ge=512,
            le=4096,
            title="Pixels per row",
            description="The number of pixels to display per row before wrapping.",
        ),
        animated: bool = Query(
            default=False,
            title="Animated GIF",
            description="Animate the recipe if it has multiple variations.",
        ),
        _c: int = Query(
            default=0,
            title="Cache Breaker",
            description="This flag is ignored and can be used to break caches.",
        ),
    ) -> Response:
        if resolution % 16 != 0:
            raise ValueError("Resolution must be a multiple of 16.")

        try:
            parsed_dependencies = parse_dependencies(minecraft_version, dependencies)

            result = await cached_render_recipes(
                locations, parsed_dependencies, resolution, row_width, animated
            )
        except ValueError as e:
            return Response(status_code=422, content=str(e))

        return Response(
            content=result,
            media_type="image/gif" if animated else "image/png",
            headers={"Cache-Control": "public, max-age=21600, immutable"},
        )
