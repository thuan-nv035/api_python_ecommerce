from typing import Optional
from pydantic import BaseModel, Field


class StockAdjustCreate(BaseModel):
    warehouse_id: Optional[int] = None
    product_id: int
    variant_id: Optional[int] = None

    quantity: int = Field(...)

    note: Optional[str] = None


class StockMovementFilter(BaseModel):
    pass