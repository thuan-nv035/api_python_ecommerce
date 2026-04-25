from typing import Optional
from pydantic import BaseModel, Field


class InventoryCreate(BaseModel):
    product_id: int
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: int = Field(..., ge=0)


class InventoryUpdate(BaseModel):
    size: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)


class InventoryAdjust(BaseModel):
    quantity: int