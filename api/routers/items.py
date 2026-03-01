from fastapi import APIRouter, HTTPException

from schemas.item import ItemCreate, ItemOut
from services import item as item_service
from utils.responses import not_found

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemOut])
def list_items():
    return item_service.get_all()


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int):
    item = item_service.get_by_id(item_id)
    if not item:
        raise not_found("Item")
    return item


@router.post("", response_model=ItemOut, status_code=201)
def create_item(data: ItemCreate):
    return item_service.create(data)


@router.put("/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemCreate):
    item = item_service.update(item_id, data)
    if not item:
        raise not_found("Item")
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int):
    if not item_service.delete(item_id):
        raise not_found("Item")
