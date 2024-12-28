from ..utils import to_location


class Display:
    def __init__(self, display: dict):
        self.rotation = display.get("rotation", [30, 225, 0])
        self.translation = display.get("translation", [0, 0, 0])
        self.scale = display.get("scale", [0.625, 0.625, 0.625])


class Rotation:
    def __init__(self, rotation: dict):
        self.origin = rotation.get("origin", [8, 8, 8])
        self.axis = rotation.get("axis", "y")
        self.angle = rotation.get("angle", 0)


class Face:
    def __init__(self, face: dict):
        self.uv = face.get("uv", [0, 0, 16, 16])
        self.texture = to_location(face.get("texture", ""))
        self.rotation = face.get("rotation", 0)


class Element:
    def __init__(self, element: dict):
        self.from_pos = element.get("from", [0, 0, 0])
        self.to_pos = element.get("to", [16, 16, 16])
        self.rotation = Rotation(element.get("rotation", {}))
        self.faces = {k: Face(v) for k, v in element.get("faces", {}).items()}


DEFAULT_DISPLAY = Display({})


class Model:
    def __init__(self, model: dict):
        self.resolved = False
        self.parent = to_location(model["parent"]) if "parent" in model else None
        self.display = (
            Display(model.get("display", {})["gui"])
            if "gui" in model.get("display", {})
            else DEFAULT_DISPLAY
        )
        self.textures = {
            k: to_location(v) for k, v in model.get("textures", {}).items()
        }
        self.gui_light = model.get("gui_light", "")
        self.elements = [Element(e) for e in model.get("elements", [])]

    def apply_parent(self, parent: "Model"):
        self.resolved = True
        for k, v in parent.textures.items():
            if k not in self.textures:
                self.textures[k] = v
        if not self.elements:
            self.elements = parent.elements
        if self.display == DEFAULT_DISPLAY:
            self.display = parent.display
        if not self.gui_light:
            self.gui_light = parent.gui_light


DEFAULT_ITEM_MODEL = Model({"textures": {"layer0": "item/missing_texture"}})
