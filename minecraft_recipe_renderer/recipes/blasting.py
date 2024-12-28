from minecraft_recipe_renderer.recipes.smelting import SmeltingRecipe


class BlastingRecipe(SmeltingRecipe):
    def get_name(self) -> str:
        return "Blast Furnace"
