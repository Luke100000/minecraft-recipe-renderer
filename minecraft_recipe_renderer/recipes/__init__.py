from .blasting import BlastingRecipe
from .campfire_cooking import CampfireCookingRecipe
from .crafting_shaped import CraftingShapedRecipe, Recipe
from .crafting_shapeless import CraftingShapelessRecipe
from .smelting import SmeltingRecipe
from .smithing_transform import SmithingTransformRecipe
from .smoking import SmokingRecipe
from .stonecutting import StonecuttingRecipe

RECIPE_REGISTRY: dict[str, type[Recipe]] = {
    "minecraft:blasting": BlastingRecipe,
    "minecraft:campfire_cooking": CampfireCookingRecipe,
    "minecraft:smelting": SmeltingRecipe,
    "minecraft:smoking": SmokingRecipe,
    "minecraft:crafting_shaped": CraftingShapedRecipe,
    "minecraft:crafting_shapeless": CraftingShapelessRecipe,
    "minecraft:smithing_transform": SmithingTransformRecipe,
    "minecraft:stonecutting": StonecuttingRecipe,
}
