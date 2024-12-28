from typing import TYPE_CHECKING

from PIL import Image

from .recipe import Recipe
from ..classes import Canvas
from ..classes.item import Item
from ..utils import to_ingredient

if TYPE_CHECKING:
    from .. import ItemRenderer


class SmeltingRecipe(Recipe):
    def __init__(self, recipe: dict):
        super().__init__(recipe)

        self.category = recipe.get("category", "misc")
        self.group = recipe.get("group", None)

        self.cookingTime = recipe.get("cookingtime", 200)
        self.experience = recipe.get("experience", 0)

        self.ingredient = to_ingredient(recipe["ingredient"])
        self.result = Item(recipe["result"])

    def get_name(self) -> str:
        return "Furnace"

    def render(
        self,
        item_renderer: "ItemRenderer",
        resolution: int = 1,
        max_variations: int = 1,
        print_name: bool = True,
    ) -> list[Image.Image]:
        images = []
        for variation in range(min(max_variations, len(self.ingredient))):
            canvas = Canvas(94, 69, resolution)
            canvas.box("menu", 0, 0, canvas.width, canvas.height)

            # Arrow
            canvas.texture("arrow", 34, 29)
            canvas.texture("burn", 7, 36)

            # Text
            canvas.text(self.get_name(), 7, 6)

            # Cooking time
            canvas.text(f"{self.cookingTime} ticks", 7, 55)

            # Ingredients
            item = Item(self.ingredient[variation])
            canvas.slot(item_renderer, item, 7, 18)

            # Result
            canvas.slot(item_renderer, self.result, 63, 24, 4)

            images.append(canvas.image)

        return images
