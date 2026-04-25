from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class FlashSaleCreate(BaseModel):
    title: str
    desc: Optional[str] = None
    start_at: datetime
    end_at: datetime
    is_active: Optional[bool] = True


class FlashSaleUpdate(BaseModel):
    title: Optional[str] = None
    desc: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class FlashSaleItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    sale_price: float = Field(..., gt=0)
    sale_quantity: int = Field(..., ge=0)
    is_active: Optional[bool] = True


class FlashSaleItemUpdate(BaseModel):
    sale_price: Optional[float] = Field(None, gt=0)
    sale_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None