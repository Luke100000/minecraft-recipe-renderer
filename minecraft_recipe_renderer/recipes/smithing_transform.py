from typing import TYPE_CHECKING

from PIL import Image

from .recipe import Recipe
from ..classes import Canvas
from ..classes.item import Item
from ..utils import to_ingredient

if TYPE_CHECKING:
    from .. import ItemRenderer


class SmithingTransformRecipe(Recipe):
    def __init__(self, recipe: dict):
        super().__init__(recipe)

        self.template = to_ingredient(recipe["template"])
        self.base = to_ingredient(recipe["base"])
        self.addition = to_ingredient(recipe["addition"])
        self.result = Item(recipe["result"])

    def render(
        self,
        item_renderer: "ItemRenderer",
        resolution: int = 1,
        max_variations: int = 1,
        print_name: bool = True,
    ) -> list[Image.Image]:
        images = []
        for variation in range(
            min(max_variations, len(self.template), len(self.base), len(self.addition))
        ):
            canvas = Canvas(125, 46, resolution)
            canvas.box("menu", 0, 0, canvas.width, canvas.height)

            # Arrow
            canvas.texture("arrow", 68, 20)

            # Text
            if print_name:
                name = item_renderer.resource_manager.get_lang(self.result.id)
            else:
                name = "Smithing Table"
            canvas.text(name, 7, 6)

            # Ingredients
            item = Item(self.template[variation % len(self.template)])
            canvas.slot(item_renderer, item, 7, 18)

            item = Item(self.base[variation % len(self.base)])
            canvas.slot(item_renderer, item, 25, 18)

            item = Item(self.addition[variation % len(self.addition)])
            canvas.slot(item_renderer, item, 43, 18)

            # Result
            canvas.slot(item_renderer, self.result, 98, 18)

            images.append(canvas.image)

        return images
