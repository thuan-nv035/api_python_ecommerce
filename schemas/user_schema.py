from pydantic import BaseModel
from typing import Optional
from pydantic import BaseModel
class UserOut(BaseModel):
    id: int
    username: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True # Dòng này cực kỳ quan trọng

class UserCreate(BaseModel):
    username: str
    password: str
    avatar: str = None