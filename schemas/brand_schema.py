from typing import Optional
from pydantic import BaseModel


class BrandCreate(BaseModel):
    name: str
    slug: str
    desc: Optional[str] = None
    logo: Optional[str] = None
    is_active: Optional[bool] = True


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    desc: Optional[str] = None
    logo: Optional[str] = None
    is_active: Optional[bool] = None