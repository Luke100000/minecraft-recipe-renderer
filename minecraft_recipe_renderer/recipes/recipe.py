from PIL import Image

from minecraft_recipe_renderer import ItemRenderer


class Recipe:
    def __init__(self, recipe: dict):
        pass

    def render(
        self,
        item_renderer: ItemRenderer,
        resolution: int = 1,
        max_variations: int = 1,
        print_name: bool = True,
    ) -> list[Image.Image]:
        raise NotImplementedError
