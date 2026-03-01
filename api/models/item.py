# Placeholder for your DB model.
# Swap this out with SQLAlchemy, Tortoise, Beanie, etc. when you add a DB.
#
# Example with SQLAlchemy:
#
#   from sqlalchemy import Column, Integer, String
#   from database import Base
#
#   class Item(Base):
#       __tablename__ = "items"
#       id = Column(Integer, primary_key=True, index=True)
#       name = Column(String, nullable=False)
#       description = Column(String, default="")


class Item:
    """In-memory stand-in until a real DB is wired up."""

    def __init__(self, id: int, name: str, description: str = ""):
        self.id = id
        self.name = name
        self.description = description
