from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageEnhance
from cachetools import cached, LRUCache

from .classes.model import Model, Element
from .utils import to_location, to_path

if TYPE_CHECKING:
    from .resource_manager import ResourceManager

default_image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))

face_identifiers = ["north", "south", "down", "up", "west", "east"]


faces = [
    [2, 3, 0, 1],  # north
    [7, 6, 5, 4],  # south
    [1, 0, 4, 5],  # down
    [3, 2, 6, 7],  # up
    [3, 7, 4, 0],  # left
    [6, 2, 1, 5],  # right
]

# Especially entity based items cannot be rendered correctly, so use a list of overrides
# TODO: Better solution
overrides = {
    "minecraft:item/conduit": "conduit",
}

root = Path(__file__)


@cache
def load_override_texture(name: str):
    return Image.open(root.parent / "assets/overrides" / (name + ".png")).convert(
        "RGBA"
    )


def rotate(vertices, rotation_angles):
    # Rotate around the Z, Y, and X axes
    angles = np.radians(rotation_angles)
    rotation_matrix_z = np.array(
        [
            [np.cos(angles[2]), -np.sin(angles[2]), 0],
            [np.sin(angles[2]), np.cos(angles[2]), 0],
            [0, 0, 1],
        ]
    )
    rotation_matrix_y = np.array(
        [
            [np.cos(angles[1]), 0, np.sin(angles[1])],
            [0, 1, 0],
            [-np.sin(angles[1]), 0, np.cos(angles[1])],
        ]
    )
    rotation_matrix_x = np.array(
        [
            [1, 0, 0],
            [0, np.cos(angles[0]), -np.sin(angles[0])],
            [0, np.sin(angles[0]), np.cos(angles[0])],
        ]
    )
    rotation_matrix = rotation_matrix_x @ rotation_matrix_y @ rotation_matrix_z
    return np.dot(vertices, rotation_matrix.T)


@cached(cache=LRUCache(maxsize=128))
def load_texture(texture: str):
    return Image.open(texture).convert("RGBA")


class ItemRenderer:
    """
    An absolute catastrophic implementation of Minecraft's item model rendering.
    Probably broken and unstable, but it works for the 3 models I need.
    """

    def __init__(self, resource_manager: "ResourceManager"):
        self.resource_manager = resource_manager

    def get_texture(self, texture_location: str) -> Image.Image:
        if (
            texture_location not in self.resource_manager.textures
            and texture_location != "minecraft:item/missing_texture"
        ):
            print("Missing texture", texture_location)
        return (
            load_texture(self.resource_manager.textures[texture_location])
            if texture_location in self.resource_manager.textures
            else default_image
        )

    def render(self, model: Model, resolution: int):
        if model.location in overrides:
            return load_override_texture(overrides[model.location]).resize(
                (resolution, resolution), Image.Resampling.NEAREST
            )
        elif model.elements:
            canvas = Image.new("RGBA", (resolution, resolution), color=(0, 0, 0, 0))
            depth = np.zeros((resolution, resolution), dtype=float)

            for element in model.elements:
                self.render_element(model, element, canvas, depth)

            return canvas
        else:
            texture1 = self.get_texture(model.textures.get("layer0", "missing"))

            # Default color
            item_location = model.location.replace(":item/", ":")
            if item_location in self.resource_manager.default_item_colors:
                img_array = np.array(texture1, dtype=np.float32)
                packed_color = self.resource_manager.default_item_colors[item_location]
                color = (
                    np.array(
                        [
                            (packed_color >> 16) & 0xFF,
                            (packed_color >> 8) & 0xFF,
                            packed_color & 0xFF,
                        ],
                        dtype=np.float32,
                    )
                    / 255.0
                )
                img_array[..., :3] *= color
                img_array = np.clip(img_array, 0, 255).astype(np.uint8)
                texture1 = Image.fromarray(img_array, "RGBA")

            if "layer1" in model.textures:
                texture2 = self.get_texture(model.textures["layer1"])
                texture = Image.new("RGBA", texture1.size)
                texture.paste(texture1, (0, 0), texture1)
                texture.paste(texture2, (0, 0), texture2)
            else:
                texture = texture1
            return texture.resize((resolution, resolution), Image.Resampling.NEAREST)

    def render_element(
        self,
        model: Model,
        element: Element,
        canvas: Image.Image,
        depth: np.ndarray,
    ):
        from_pos = np.asarray(element.from_pos)
        to_pos = np.asarray(element.to_pos)
        cuboid_vertices = np.array(
            [
                [from_pos[0], from_pos[1], from_pos[2]],
                [to_pos[0], from_pos[1], from_pos[2]],
                [to_pos[0], to_pos[1], from_pos[2]],
                [from_pos[0], to_pos[1], from_pos[2]],
                [from_pos[0], from_pos[1], to_pos[2]],
                [to_pos[0], from_pos[1], to_pos[2]],
                [to_pos[0], to_pos[1], to_pos[2]],
                [from_pos[0], to_pos[1], to_pos[2]],
            ],
            dtype=float,
        )

        # Apply rotation
        cuboid_vertices -= np.asarray(element.rotation.origin, dtype=float)
        cuboid_vertices = rotate(
            cuboid_vertices,
            [
                element.rotation.angle if element.rotation.axis == "x" else 0,
                element.rotation.angle if element.rotation.axis == "y" else 0,
                element.rotation.angle if element.rotation.axis == "z" else 0,
            ],
        )
        cuboid_vertices += element.rotation.origin
        cuboid_vertices -= 8

        # Apply the transformations
        cuboid_vertices = rotate(cuboid_vertices, model.display.rotation)
        cuboid_vertices *= model.display.scale
        cuboid_vertices *= 1 + 12 / canvas.size[0]
        cuboid_vertices += model.display.translation

        # OpenGL coordinate system
        cuboid_vertices[:, 1] = -cuboid_vertices[:, 1]

        def find_coeffs(pa, pb) -> np.ndarray:
            matrix = []
            for p1, p2 in zip(pa, pb):
                matrix.append(
                    [p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]]
                )
                matrix.append(
                    [0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]]
                )

            A = np.matrix(matrix, dtype=float)
            B = np.array(pb).reshape(8)

            res = np.dot(np.linalg.inv(A.T * A) * A.T, B)
            return np.array(res).reshape(8)

        # Draw each face of the cuboid with corresponding texture
        for i, (face_identifier, face_indices) in enumerate(
            zip(face_identifiers, faces)
        ):
            if face_identifier in element.faces:
                face = element.faces[face_identifier]
            else:
                continue

            # Resolve texture key
            texture_location = face.texture
            for _ in range(100):
                if texture_location.startswith("#"):
                    texture_location = model.textures.get(
                        to_path(texture_location), "unknown"
                    )
                else:
                    break
            texture_location = to_location(texture_location)

            # Load texture
            texture = self.get_texture(texture_location)

            # Transform to image space
            face_vertices = cuboid_vertices[face_indices]
            depth_vertices = face_vertices[:, 2]
            face_vertices = (
                face_vertices[:, :2] * (canvas.size[0] - 8) / 16 + canvas.size[0] / 2
            )
            face_polygon = np.asarray([(float(x), float(y)) for x, y in face_vertices])

            # Backface culling
            if (face_polygon[1, 0] - face_polygon[0, 0]) * (
                face_polygon[2, 1] - face_polygon[0, 1]
            ) - (face_polygon[1, 1] - face_polygon[0, 1]) * (
                face_polygon[2, 0] - face_polygon[0, 0]
            ) < 0:
                continue

            sane_uv = (
                min(face.uv[0], face.uv[2]),
                min(face.uv[1], face.uv[3]),
                max(face.uv[0], face.uv[2]),
                max(face.uv[1], face.uv[3]),
            )

            src = np.array(
                [
                    [0, 0],
                    [sane_uv[2] - sane_uv[0], 0],
                    [sane_uv[2] - sane_uv[0], sane_uv[3] - sane_uv[1]],
                    [0, sane_uv[3] - sane_uv[1]],
                ]
            )

            src = np.roll(src, face.rotation // 90, axis=0)

            try:
                coeffs = find_coeffs(face_polygon, src)
            except np.linalg.LinAlgError:
                continue

            # Transform texture
            cropped_texture = texture.crop(sane_uv)

            if face.uv[0] > face.uv[2]:
                cropped_texture = cropped_texture.transpose(
                    Image.Transpose.FLIP_LEFT_RIGHT
                )
            if face.uv[1] > face.uv[3]:
                cropped_texture = cropped_texture.transpose(
                    Image.Transpose.FLIP_TOP_BOTTOM
                )

            texture = cropped_texture.transform(
                canvas.size,
                Image.Transform.PERSPECTIVE,
                coeffs.tolist(),
                Image.Resampling.NEAREST,
            )

            # Depth mask
            new_depth = np.zeros(cropped_texture.size, dtype=float)
            for y in range(cropped_texture.size[1]):
                for x in range(cropped_texture.size[0]):
                    u = x / (cropped_texture.size[0] - 0)
                    v = y / (cropped_texture.size[1] - 0)
                    top_color = (1 - u) * depth_vertices[0] + u * depth_vertices[1]
                    bottom_color = (1 - u) * depth_vertices[3] + u * depth_vertices[2]
                    new_depth[x, y] = (1 - v) * top_color + v * bottom_color

            new_depth = 100 + np.asarray(
                Image.fromarray(new_depth.T).transform(
                    canvas.size,
                    Image.Transform.PERSPECTIVE,
                    coeffs.tolist(),
                    Image.Resampling.NEAREST,
                )
            )

            # Depth mask
            mask = new_depth > depth

            # Apply mask
            alpha = np.array(texture.getchannel("A"))
            mask *= alpha > 0
            new_alpha = (alpha * mask).astype(np.uint8)
            texture.putalpha(Image.fromarray(new_alpha))

            # Light
            if model.gui_light == "side":
                enhancer = ImageEnhance.Brightness(texture)
                if i == 0 or i == 1:
                    texture = enhancer.enhance(0.61)
                elif i == 2 or i == 3:
                    texture = enhancer.enhance(0.985)
                else:
                    texture = enhancer.enhance(0.8)

            # Paste face texture
            canvas.paste(texture, mask=texture)

            # Set new depth
            np.maximum(depth, new_depth * mask, out=depth)
