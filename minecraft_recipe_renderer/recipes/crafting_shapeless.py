import math
from typing import TYPE_CHECKING

from minecraft_recipe_renderer.recipes import CraftingShapedRecipe
from ..utils import to_ingredient

if TYPE_CHECKING:
    pass


class CraftingShapelessRecipe(CraftingShapedRecipe):
    def __init__(self, recipe: dict):
        super().__init__(recipe)

        self.ingredients = [to_ingredient(i) for i in recipe["ingredients"]]

        size = math.ceil(math.sqrt(len(self.ingredients)))

        for x in range(size):
            self.recipe.append([])
            for y in range(size):
                if x * size + y < len(self.ingredients):
                    self.recipe[x].append(self.ingredients[x * size + y])
                else:
                    self.recipe[x].append(None)
