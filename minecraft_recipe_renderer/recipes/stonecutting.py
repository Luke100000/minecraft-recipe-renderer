from typing import TYPE_CHECKING

from PIL import Image

from .recipe import Recipe
from ..classes import Canvas
from ..classes.item import Item
from ..utils import to_ingredient

if TYPE_CHECKING:
    from .. import ItemRenderer


class StonecuttingRecipe(Recipe):
    def __init__(self, recipe: dict):
        super().__init__(recipe)

        self.ingredient = to_ingredient(recipe["ingredient"])
        self.result = Item(recipe["result"])

    def render(
        self,
        item_renderer: "ItemRenderer",
        resolution: int = 1,
        max_variations: int = 1,
        print_name: bool = True,
    ) -> list[Image.Image]:
        images = []
        for variation in range(min(max_variations, len(self.ingredient))):
            canvas = Canvas(86, 43, resolution)
            canvas.box("menu", 0, 0, canvas.width, canvas.height)

            # Arrow
            canvas.texture("arrow", 32, 20)

            # Text
            canvas.text("Stone Cutting", 7, 6)

            # Ingredients
            item = Item(self.ingredient[variation])
            canvas.slot(item_renderer, item, 7, 18)

            # Result
            canvas.slot(item_renderer, self.result, 61, 18)

            images.append(canvas.image)

        return images
