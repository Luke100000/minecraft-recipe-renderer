from typing import TYPE_CHECKING

from PIL import Image

from .recipe import Recipe
from ..classes import Canvas
from ..classes.item import Item
from ..utils import to_ingredient

if TYPE_CHECKING:
    from .. import ItemRenderer, ResourceManager


def load_pattern_recipe(pattern: list, key: dict):
    keys = {k: to_ingredient(v) for k, v in key.items()}

    width = max(len(row) for row in pattern)
    height = len(pattern)

    recipe = []
    for x in range(height):
        recipe.append([])
        for y in range(width):
            i = pattern[x][y] if x < len(pattern) and y < len(pattern[x]) else " "
            recipe[x].append(keys.get(i, None))

    return recipe


class CraftingShapedRecipe(Recipe):
    def __init__(self, recipe: dict):
        super().__init__(recipe)

        self.category = recipe.get("category", "misc")
        self.group = recipe.get("group", None)
        self.show_notification = recipe.get("show_notification", True)

        self.recipe = load_pattern_recipe(recipe["pattern"], recipe["key"]) if "pattern" in recipe else []
        self.result = Item(recipe["result"])

    def _expand_ingredients(self, resource_manager: "ResourceManager"):
        expanded = []
        for row in self.recipe:
            expanded.append([])
            for ingredients in row:
                expanded[-1].append([])
                if ingredients:
                    for i in ingredients:
                        if i.startswith("#"):
                            if i[1:] in resource_manager.tags:
                                for item in resource_manager.tags[i[1:]]:
                                    expanded[-1][-1].append(item)
                            else:
                                print("Unknown tag:", i)
                        else:
                            expanded[-1][-1].append(i)
        return expanded

    def render(
        self,
        item_renderer: "ItemRenderer",
        resolution: int = 1,
        max_variations: int = 1,
        print_name: bool = True,
    ) -> list[Image.Image]:
        size = max(len(self.recipe), len(self.recipe[0]))
        ox = (size - len(self.recipe[0])) // 2
        oy = (size - len(self.recipe)) // 2

        # Flatten ingredient tags into items
        ingredients = self._expand_ingredients(item_renderer.resource_manager)

        variations = 0
        for row in ingredients:
            for ingredient in row:
                if ingredient:
                    variations = max(variations, len(ingredient))

        images = []
        for variation in range(min(max_variations, variations)):
            canvas = Canvas(72 + size * 18, 26 + 18 * size, resolution)
            canvas.box("menu", 0, 0, canvas.width, canvas.height)

            # Arrow
            canvas.texture("arrow", 12 + 18 * size, 18 + (size - 1) * 9)

            # Text
            if print_name:
                name = item_renderer.resource_manager.get_lang(self.result.id)
            else:
                name = "Crafting"
            canvas.text(name, 7, 6)

            # Ingredients
            for x in range(size):
                for y in range(size):
                    ingredient = (
                        ingredients[y - oy][x - ox]
                        if 0 <= y - oy < len(ingredients)
                        and 0 <= x - ox < len(ingredients[y - oy])
                        else None
                    )
                    item = (
                        Item(ingredient[variation % len(ingredient)])
                        if ingredient
                        else None
                    )
                    canvas.slot(
                        item_renderer,
                        item,
                        7 + x * 18,
                        18 + y * 18,
                    )

            # Result
            canvas.slot(
                item_renderer,
                self.result,
                41 + 18 * size,
                14 + (size - 1) * 9,
                4,
            )

            images.append(canvas.image)

        return images
