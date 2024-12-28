from functools import cache
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import requests
from PIL import Image, ImageDraw, ImageFont

from .item import Item

if TYPE_CHECKING:
    from ..item_renderer import ItemRenderer

root = Path(__file__)


@cache
def get_font(
    font_url: str = "https://www.minecraft.net/etc.clientlibs/minecraftnet/clientlibs/clientlib-site/resources/fonts/Minecraft-Seven_v2.woff2",
    font_cache_path: Path = Path("cache/font.woff2"),
    size: int = 10,
):
    if not font_cache_path.exists():
        font_cache_path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(
            font_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        )
        with font_cache_path.open("wb") as f:
            f.write(response.content)

    return ImageFont.truetype(font_cache_path, size)


@cache
def load_texture(name: str):
    return Image.open(root.parent.parent / "assets" / (name + ".png"))


class Canvas:
    def __init__(self, width: int, height: int, resolution: int = 1):
        self.width = width
        self.height = height
        self.resolution = resolution

        self.image = Image.new(
            "RGBA", (width * resolution, height * resolution), color=(0, 0, 0, 0)
        )
        self.image_draw = ImageDraw.Draw(self.image)
        self.image_draw.fontmode = "1"

        self.text_color = (63, 63, 63)

    def slot(
        self,
        item_renderer: "ItemRenderer",
        item: Optional[Item],
        x: int,
        y: int,
        margin: int = 1,
    ):
        self.box("slot", x, y, 16 + margin * 2, 16 + margin * 2)
        if item:
            self.item(item_renderer, item, x + margin, y + margin)

    def item(self, item_renderer: "ItemRenderer", item: Item, x: int, y: int):
        model = item_renderer.resource_manager.get_model(item.id)
        if model:
            texture = item_renderer.render(model, 16 * self.resolution)
            self.draw(
                self.image,
                texture,
                (0, 0, texture.width, texture.height),
                (x, y),
                None,
                False,
            )

    def text(self, text: str, x: int, y: int):
        self.image_draw.text(
            (x * self.resolution, y * self.resolution),
            text,
            font=get_font(size=self.resolution * 10),
            fill=self.text_color,
        )

    def box(self, texture: str, x: int, y: int, width: int, height: int):
        tex = load_texture(texture)
        self.draw(self.image, tex, (0, 0, 8, 8), (x, y))
        self.draw(self.image, tex, (16, 0, 24, 8), (x + width - 8, y))
        self.draw(self.image, tex, (16, 16, 24, 24), (x + width - 8, y + height - 8))
        self.draw(self.image, tex, (0, 16, 8, 24), (x, y + height - 8))

        self.draw(
            self.image,
            tex,
            (7, 7, 16, 16),
            (x + 8, y + 8),
            (width - 16, height - 16),
        )

        self.draw(
            self.image,
            tex,
            (7, 0, 16, 8),
            (x + 8, y),
            (width - 16, 8),
        )

        self.draw(
            self.image,
            tex,
            (7, 16, 16, 24),
            (x + 8, y + height - 8),
            (width - 16, 8),
        )

        self.draw(
            self.image,
            tex,
            (0, 7, 8, 16),
            (x, y + 8),
            (8, height - 16),
        )

        self.draw(
            self.image,
            tex,
            (16, 7, 24, 16),
            (x + width - 8, y + 8),
            (8, height - 16),
        )

    def texture(self, texture: str, x: int, y: int):
        tex = load_texture(texture)
        self.draw(
            self.image,
            tex,
            (0, 0, tex.width, tex.height),
            (x, y),
        )

    def draw(
        self,
        base: Image.Image,
        texture: Image.Image,
        viewport: tuple[int, int, int, int],
        position: tuple[int, int],
        scale: Optional[tuple[int, int]] = None,
        apply_resolution: bool = True,
    ):
        cropped_texture = texture.crop(viewport)
        if scale:
            cropped_texture = cropped_texture.resize(scale, Image.Resampling.NEAREST)

        if apply_resolution:
            cropped_texture = cropped_texture.resize(
                (
                    cropped_texture.width * self.resolution,
                    cropped_texture.height * self.resolution,
                ),
                Image.Resampling.NEAREST,
            )

        base.paste(
            cropped_texture,
            (position[0] * self.resolution, position[1] * self.resolution),
            mask=cropped_texture,
        )
