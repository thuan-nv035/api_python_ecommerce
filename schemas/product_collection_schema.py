from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ProductCollectionCreate(BaseModel):
    title: str
    slug: str
    desc: Optional[str] = None
    banner_img: Optional[str] = None
    is_active: Optional[bool] = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class ProductCollectionUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    desc: Optional[str] = None
    banner_img: Optional[str] = None
    is_active: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class CollectionItemCreate(BaseModel):
    product_id: int
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True


class CollectionItemUpdate(BaseModel):
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None