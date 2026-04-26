from typing import Optional, List
from pydantic import BaseModel


class RoleCreate(BaseModel):
    name: str
    code: str
    desc: Optional[str] = None
    is_active: Optional[bool] = True


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    desc: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionCreate(BaseModel):
    name: str
    code: str
    module: Optional[str] = None
    desc: Optional[str] = None
    is_active: Optional[bool] = True


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    module: Optional[str] = None
    desc: Optional[str] = None
    is_active: Optional[bool] = None


class AssignPermissionsToRole(BaseModel):
    permission_ids: List[int]


class AssignRolesToUser(BaseModel):
    role_ids: List[int]