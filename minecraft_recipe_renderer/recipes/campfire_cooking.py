from minecraft_recipe_renderer.recipes.smelting import SmeltingRecipe


class CampfireCookingRecipe(SmeltingRecipe):
    def get_name(self) -> str:
        return "Campfire"
