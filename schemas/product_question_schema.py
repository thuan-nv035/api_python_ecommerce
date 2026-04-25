from typing import Optional
from pydantic import BaseModel


class ProductQuestionCreate(BaseModel):
    product_id: int
    question: str
    is_public: Optional[bool] = True


class ProductQuestionUpdate(BaseModel):
    question: Optional[str] = None
    is_public: Optional[bool] = None


class ProductQuestionAnswer(BaseModel):
    answer: str
    status: Optional[str] = "answered"
    is_public: Optional[bool] = True