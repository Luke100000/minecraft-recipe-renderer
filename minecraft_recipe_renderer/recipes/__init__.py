from .crafting_shaped import CraftingShapedRecipe, Recipe

RECIPE_REGISTRY: dict[str, type[Recipe]] = {
    "minecraft:crafting_shaped": CraftingShapedRecipe,
}
