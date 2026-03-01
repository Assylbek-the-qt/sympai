from pydantic import BaseModel


class ItemCreate(BaseModel):
    name: str
    description: str = ""


class ItemOut(ItemCreate):
    id: int

    class Config:
        from_attributes = True
