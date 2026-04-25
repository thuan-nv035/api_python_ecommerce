from pydantic import BaseModel


class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str