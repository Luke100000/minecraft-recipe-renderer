from minecraft_recipe_renderer import ResourceManager, ItemRenderer

manager = ResourceManager()
manager.load_zip(
    "https://piston-data.mojang.com/v1/objects/a7e5a6024bfd3cd614625aa05629adf760020304/client.jar"
)
manager.load_repository("https://github.com/Luke100000/ImmersiveMachinery")
manager.load_repository("https://github.com/Luke100000/ImmersiveAircraft")
manager.post_load()
renderer = ItemRenderer(manager)

recipe = manager.recipes["immersive_machinery:bamboo_bee"]
recipe.render(item_renderer=renderer, resolution=2)[0].save("iron_drill.png")
