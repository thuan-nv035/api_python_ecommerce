from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class BannerCreate(BaseModel):
    title: str
    subtitle: Optional[str] = None
    img: str
    link: Optional[str] = None
    position: Optional[str] = "home"
    sort_order: Optional[int] = 0
    is_active: Optional[bool] = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class BannerUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    img: Optional[str] = None
    link: Optional[str] = None
    position: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None