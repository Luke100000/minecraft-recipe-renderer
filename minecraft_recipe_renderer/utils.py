def to_location(item: str | dict):
    if isinstance(item, str):
        parts = item.split(":", 1)
        if len(parts) == 1:
            if parts[0].startswith("#"):
                return "#minecraft:" + parts[0][1:]
            return "minecraft:" + parts[0]
        else:
            return item
    elif "tag" in item:
        return to_location(f"#{item['tag']}")
    else:
        return to_location(item["item"])


def to_ingredient(ingredient: str | dict | list[dict | str]):
    if isinstance(ingredient, list):
        return [to_location(i) for i in ingredient]
    else:
        return [to_location(ingredient)]


def to_path(location: str) -> str:
    return location.split(":", 1)[-1]
