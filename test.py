from minecraft_recipe_renderer import ResourceManager, ItemRenderer

manager = ResourceManager()
manager.load_zip(
    "https://piston-data.mojang.com/v1/objects/a7e5a6024bfd3cd614625aa05629adf760020304/client.jar"
)
manager.load_repository("https://github.com/Luke100000/ImmersiveMachinery")
manager.load_repository("https://github.com/Luke100000/ImmersiveAircraft")
manager.post_load()
renderer = ItemRenderer(manager)

renderer.render(manager.get_model("minecraft:heart_of_the_sea"), resolution=32).show()

# recipe = manager.recipes["minecraft:heart_of_the_sea"]
# recipe.render(item_renderer=renderer, resolution=2)[0].show()
