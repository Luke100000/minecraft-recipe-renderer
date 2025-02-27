import hashlib
import json
import zipfile
from pathlib import Path
from typing import Optional, Generator
from urllib.parse import urlparse, quote, unquote, urlunparse

import requests
from git import Repo

from .classes.model import Model, DEFAULT_ITEM_MODEL
from .recipes import RECIPE_REGISTRY
from .recipes.recipe import Recipe
from .utils import to_location


def looks_like_file(url: str) -> bool:
    sanitized = sanitize_url(url)
    return sanitized.endswith(".jar") or sanitized.endswith(".zip")


def parse_git_link(link: str) -> tuple[str, Optional[str]]:
    split = link.split("/tree/")

    if len(split) == 2:
        return split[0], split[1]
    else:
        return split[0], None


def sanitize_url(url):
    parsed = urlparse(url)

    # Only allow public web URLs with ssh, http, or https schemes
    if parsed.scheme not in {"http", "https", "ssh"}:
        raise ValueError("URL scheme must be http, https, or ssh.")

    # Validate domain: ensure it's a public domain (not localhost or private IPs)
    if (
        not parsed.netloc
        or parsed.netloc.startswith("localhost")
        or parsed.netloc.startswith("127.")
        or parsed.netloc.startswith("192.168.")
        or parsed.netloc.startswith("10.")
    ):
        raise ValueError("URL must point to a public web domain.")

    # Sanitize components
    sanitized_netloc = quote(parsed.netloc)
    sanitized_path = quote(unquote(parsed.path))

    # Strip query and fragment
    sanitized_url = urlunparse(
        (parsed.scheme, sanitized_netloc, sanitized_path, "", "", "")
    )

    return sanitized_url


def list_files(
    root: Path, ext: str, namespace: str
) -> Generator[tuple[Path, str], None, None]:
    for path in root.rglob(f"*.{ext}"):
        rel = path.relative_to(root)
        yield path, namespace + ":" + str(rel.parent / rel.stem)


class ResourceManager:
    def __init__(self, cache: Path = Path("cache")):
        self.cache = cache

        self.recipes: dict[str, Recipe] = {}
        self.tags: dict[str, set[str]] = {}
        self.models: dict[str, Model] = {}
        self.lang: dict[str, str] = {}
        self.textures: dict[str, Path] = {}
        self.default_item_colors: dict[str, int] = {}

        self.models["minecraft:builtin/generated"] = DEFAULT_ITEM_MODEL

    def get_model(self, location: str) -> Model:
        namespace, path = location.split(":", 1)

        for variation in (
            f"{namespace}:item/{path}",
            f"{namespace}:item/{path}_00",
            f"{namespace}:block/{path}_inventory",
            f"{namespace}:block/{path}",
        ):
            if variation in self.models:
                return self.models[variation]

    def post_load(self):
        self._post_load_models()
        self._post_load_tags()
        self._post_load_recipe_tag()

    def _post_load_models(self):
        done = False
        while not done:
            done = True
            for name, model in self.models.items():
                if model.parent and not model.resolved:
                    if model.parent in self.models:
                        parent = self.models[model.parent]
                        if not parent.parent or parent.resolved:
                            done = False
                            model.apply_parent(parent)
                    else:
                        print(f"Missing parent model: {model.parent} for {name}")

    def _post_load_tags(self):
        done = False
        while not done:
            done = True
            for tags in self.tags.values():
                for tag in list(tags):
                    if tag.startswith("#"):
                        done = False
                        tags.remove(tag)
                        if tag[1:] in self.tags:
                            tags.update(self.tags[tag[1:]])
                        else:
                            print(f"Missing tag: {tag}")

    def _post_load_recipe_tag(self):
        # Create a pseudo tag with all recipe outputs
        for recipe in self.recipes.values():
            if hasattr(recipe, "result"):
                namespace, path = recipe.result.id.split(":", 1)
                t = namespace + ":recipes"
                if t not in self.tags:
                    self.tags[t] = set()
                self.tags[t].add(recipe.result.id)

    def load_recipe(self, path: Path, name: str):
        try:
            r = json.loads(path.read_text())
            crafting_type = to_location(r["type"])
            if crafting_type in RECIPE_REGISTRY:
                self.recipes[name] = RECIPE_REGISTRY[crafting_type](r)
        except Exception:
            print(f"Error loading recipe: {name}")

    def load_tags(self, path: Path, name: str):
        try:
            tags = json.loads(path.read_text())
            processed_tags = set()
            for tag in tags["values"]:
                if isinstance(tag, str):
                    processed_tags.add(to_location(tag))
                else:
                    processed_tags.add(to_location(tag["id"]))

            if "replace" in tags and tags["replace"] or name not in self.tags:
                self.tags[name] = processed_tags
            else:
                self.tags[name] |= processed_tags
        except Exception:
            print(f"Error loading tags: {name}")

    def load_model(self, path: Path, name: str):
        try:
            self.models[name] = Model(name, json.loads(path.read_text()))
        except Exception:
            print(f"Error loading model: {name}")

    def load_lang(self, path: Path):
        try:
            self.lang.update(json.loads(path.read_text()))
        except Exception:
            print(f"Error loading lang: {path}")

    def register_texture(self, path: Path, name: str):
        self.textures[name] = path

    def load_resources(self, root: Path):
        """
        Load the resource pack.
        :param root: The root of the pack, containing assets, data, ...
        """

        namespaces = set()
        for namespace in root.glob("assets/*/"):
            namespaces.add(namespace.name)
        for namespace in root.glob("data/*/"):
            namespaces.add(namespace.name)

        for namespace in namespaces:
            for path, name in list_files(
                root / f"data/{namespace}/recipe", "json", namespace
            ):
                self.load_recipe(path, name)
            for path, name in list_files(
                root / f"data/{namespace}/recipes", "json", namespace
            ):
                self.load_recipe(path, name)

            for path, name in list_files(
                root / f"data/{namespace}/tags/item", "json", namespace
            ):
                self.load_tags(path, name)

            for path, name in list_files(
                root / f"data/{namespace}/tags/items", "json", namespace
            ):
                self.load_tags(path, name)

            for path, name in list_files(
                root / f"assets/{namespace}/models", "json", namespace
            ):
                self.load_model(path, name)

            for path, name in list_files(
                root / f"assets/{namespace}/lang", "json", namespace
            ):
                self.load_lang(path)

            for path, name in list_files(
                root / f"assets/{namespace}/textures", "png", namespace
            ):
                self.register_texture(path, name)

            colors_path = root / f"assets/{namespace}/default_item_colors.json"
            if colors_path.exists():
                self.default_item_colors.update(json.loads(colors_path.read_text()))

    def scan_resources(self, path: Path):
        """
        Scan for resources in the given path.
        :param path: The path to scan.
        """
        for root in path.glob("**/resources/"):
            self.load_resources(root)

    def load_dependency(self, url: str):
        if looks_like_file(url):
            self.load_zip(url)
        else:
            self.load_repository(url)

    def load_zip(self, url: str):
        """
        Load a jar file from a URL.
        :param url: The URL to the jar file.
        """
        cache_dir = self.cache / (hashlib.sha256(url.encode()).hexdigest())
        if not cache_dir.exists():
            cache_file = self.cache / (
                hashlib.sha256(url.encode()).hexdigest() + ".zip"
            )
            self.cache.mkdir(parents=True, exist_ok=True)
            with cache_file.open("wb") as f:
                response = requests.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    },
                )
                f.write(response.content)

            with zipfile.ZipFile(cache_file, "r") as ref:
                ref.extractall(cache_dir)

            cache_file.unlink()

        self.scan_resources(cache_dir)
        self.load_resources(cache_dir)

    def load_repository(self, url: str):
        repo, tag = parse_git_link(url)
        cache_dir = self.cache / (
            hashlib.sha256((repo + str(tag)).encode()).hexdigest()
        )

        if cache_dir.exists():
            repo = Repo(cache_dir)
            repo.remotes.origin.pull()
            repo.git.checkout(tag)
        else:
            self.cache.mkdir(parents=True, exist_ok=True)
            repo = Repo.clone_from(repo, cache_dir)
            repo.git.checkout(tag)

        self.scan_resources(cache_dir)

    def get_lang(self, location: str) -> str:
        return self.lang.get(
            "item." + location.replace(":", ".").replace("/", "_"),
            location.split(":", 1)[-1].replace("/", " ").replace("_", " ").title(),
        )
