from typing import Optional
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    slug: str
    desc: Optional[str] = None
    img: Optional[str] = None
    is_active: Optional[bool] = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    desc: Optional[str] = None
    img: Optional[str] = None
    is_active: Optional[bool] = None