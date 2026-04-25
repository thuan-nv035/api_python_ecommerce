from typing import Optional, List
from pydantic import BaseModel, Field


class ProductVariantCreate(BaseModel):
    product_id: int
    sku: Optional[str] = None

    size: Optional[str] = None
    color: Optional[str] = None

    price: Optional[float] = None
    img: Optional[List[str]] = []

    quantity: int = Field(..., ge=0)
    is_active: Optional[bool] = True


class ProductVariantUpdate(BaseModel):
    sku: Optional[str] = None

    size: Optional[str] = None
    color: Optional[str] = None

    price: Optional[float] = None
    img: Optional[List[str]] = None

    quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class VariantStockAdjust(BaseModel):
    quantity: int