from minecraft_recipe_renderer.recipes import SmeltingRecipe


class SmokingRecipe(SmeltingRecipe):
    def get_name(self) -> str:
        return "Smoker"
