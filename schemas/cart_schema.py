from typing import Optional

from pydantic import BaseModel, Field


class CartCreate(BaseModel):
    product_id: int
    quantity: int = 1
    variant_id: Optional[int] = None

class CartUpdate(BaseModel):
    quantity: int = Field(..., gt=0)