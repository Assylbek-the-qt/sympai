from models.item import Item
from schemas.item import ItemCreate

# In-memory store — replace with DB session calls when ready.
_store: dict[int, Item] = {}
_next_id = 1


def get_all() -> list[Item]:
    return list(_store.values())


def get_by_id(item_id: int) -> Item | None:
    return _store.get(item_id)


def create(data: ItemCreate) -> Item:
    global _next_id
    item = Item(id=_next_id, **data.model_dump())
    _store[_next_id] = item
    _next_id += 1
    return item


def update(item_id: int, data: ItemCreate) -> Item | None:
    if item_id not in _store:
        return None
    item = Item(id=item_id, **data.model_dump())
    _store[item_id] = item
    return item


def delete(item_id: int) -> bool:
    if item_id not in _store:
        return False
    del _store[item_id]
    return True
