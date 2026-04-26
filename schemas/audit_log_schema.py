from typing import Optional, Any
from pydantic import BaseModel


class AuditLogCreate(BaseModel):
    user_id: Optional[int] = None

    action: str
    module: str

    resource_type: Optional[str] = None
    resource_id: Optional[int] = None

    old_data: Optional[Any] = None
    new_data: Optional[Any] = None

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    note: Optional[str] = None