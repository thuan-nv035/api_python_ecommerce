from pydantic import BaseModel


class UpdateOrderStatusSchema(BaseModel):
    status: str


class UpdateUserRoleSchema(BaseModel):
    role: str