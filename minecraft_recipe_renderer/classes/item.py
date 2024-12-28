from ..utils import to_location


class Item:
    def __init__(self, item: dict | str):
        if isinstance(item, str):
            self.id = to_location(item)
            self.count = 1
            self.components = []
        else:
            self.id = to_location(item["id"] if "id" in item else item["item"])
            self.count = item.get("count", 1)
            self.components = item.get("components", [])
