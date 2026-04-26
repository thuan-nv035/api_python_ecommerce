import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth import get_admin_user, get_current_user
from database import get_db
from models.models import (
    User,
    Role,
    Permission,
    RolePermission,
    UserRole
)
from schemas.rbac_schema import (
    RoleCreate,
    RoleUpdate,
    PermissionCreate,
    PermissionUpdate,
    AssignPermissionsToRole,
    AssignRolesToUser
)


rbac_route = APIRouter(tags=["rbac"])

def get_user_permission_codes(db: Session, user_id: int):
    rows = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(
            UserRole.user_id == user_id,
            Role.is_active == True,
            Permission.is_active == True
        )
        .all()
    )

    return [row[0] for row in rows]


def has_permission(db: Session, user: User, permission_code: str):
    # Giữ tương thích với hệ thống cũ
    if getattr(user, "role", "user") == "admin":
        return True

    permission_codes = get_user_permission_codes(db, user.id)

    return permission_code in permission_codes

def role_to_dict(role: Role):
    return {
        "id": role.id,
        "name": role.name,
        "code": role.code,
        "desc": role.desc,
        "is_active": role.is_active,
        "created_at": role.created_at,
        "updated_at": role.updated_at,
    }


def permission_to_dict(permission: Permission):
    return {
        "id": permission.id,
        "name": permission.name,
        "code": permission.code,
        "module": permission.module,
        "desc": permission.desc,
        "is_active": permission.is_active,
        "created_at": permission.created_at,
        "updated_at": permission.updated_at,
    }


def user_role_to_dict(user_role: UserRole):
    role = user_role.role

    return {
        "id": user_role.id,
        "user_id": user_role.user_id,
        "role_id": user_role.role_id,
        "created_at": user_role.created_at,
        "role": role_to_dict(role) if role else None
    }


def role_permission_to_dict(role_permission: RolePermission):
    permission = role_permission.permission

    return {
        "id": role_permission.id,
        "role_id": role_permission.role_id,
        "permission_id": role_permission.permission_id,
        "created_at": role_permission.created_at,
        "permission": permission_to_dict(permission) if permission else None
    }


# =====================================================
# PERMISSION API
# =====================================================

# =========================
# CREATE PERMISSION
# POST /api/permissions/
# =========================

@rbac_route.post("/api/permissions/")
def create_permission(
        data: PermissionCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    code = data.code.strip().lower()

    existed_permission = (
        db.query(Permission)
        .filter(Permission.code == code)
        .first()
    )

    if existed_permission:
        raise HTTPException(
            status_code=400,
            detail="Mã quyền đã tồn tại"
        )

    permission = Permission(
        name=data.name,
        code=code,
        module=data.module,
        desc=data.desc,
        is_active=data.is_active
    )

    db.add(permission)
    db.commit()
    db.refresh(permission)

    return {
        "message": "Tạo quyền thành công",
        "data": permission_to_dict(permission)
    }


# =========================
# GET PERMISSIONS
# GET /api/permissions/
# =========================

@rbac_route.get("/api/permissions/")
def get_permissions(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        module: str = Query(None),
        is_active: bool = Query(None)
):
    get_admin_user(request)

    query = db.query(Permission)

    if search:
        query = query.filter(
            or_(
                Permission.name.ilike(f"%{search}%"),
                Permission.code.ilike(f"%{search}%"),
                Permission.module.ilike(f"%{search}%")
            )
        )

    if module:
        query = query.filter(Permission.module == module)

    if is_active is not None:
        query = query.filter(Permission.is_active == is_active)

    total = query.count()

    permissions = (
        query
        .order_by(Permission.module.asc(), Permission.code.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách quyền thành công",
        "data": [permission_to_dict(permission) for permission in permissions],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# UPDATE PERMISSION
# PUT/PATCH /api/permissions/{permission_id}
# =========================

@rbac_route.put("/api/permissions/{permission_id}")
@rbac_route.patch("/api/permissions/{permission_id}")
def update_permission(
        permission_id: int,
        data: PermissionUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy quyền"
        )

    update_data = data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "code" in update_data:
        new_code = update_data["code"].strip().lower()

        existed_permission = (
            db.query(Permission)
            .filter(
                Permission.code == new_code,
                Permission.id != permission_id
            )
            .first()
        )

        if existed_permission:
            raise HTTPException(
                status_code=400,
                detail="Mã quyền đã tồn tại"
            )

        update_data["code"] = new_code

    for key, value in update_data.items():
        setattr(permission, key, value)

    db.commit()
    db.refresh(permission)

    return {
        "message": "Cập nhật quyền thành công",
        "data": permission_to_dict(permission)
    }


# =========================
# DELETE PERMISSION
# DELETE /api/permissions/{permission_id}
# =========================

@rbac_route.delete("/api/permissions/{permission_id}")
def delete_permission(
        permission_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy quyền"
        )

    role_permission_count = (
        db.query(RolePermission)
        .filter(RolePermission.permission_id == permission_id)
        .count()
    )

    if role_permission_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa quyền đang được gán cho role. Hãy tắt is_active thay vì xóa."
        )

    db.delete(permission)
    db.commit()

    return {
        "message": "Xóa quyền thành công",
        "deleted_permission_id": permission_id
    }


# =====================================================
# ROLE API
# =====================================================

# =========================
# CREATE ROLE
# POST /api/roles/
# =========================

@rbac_route.post("/api/roles/")
def create_role(
        data: RoleCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    code = data.code.strip().lower()

    existed_role = (
        db.query(Role)
        .filter(Role.code == code)
        .first()
    )

    if existed_role:
        raise HTTPException(
            status_code=400,
            detail="Mã role đã tồn tại"
        )

    role = Role(
        name=data.name,
        code=code,
        desc=data.desc,
        is_active=data.is_active
    )

    db.add(role)
    db.commit()
    db.refresh(role)

    return {
        "message": "Tạo role thành công",
        "data": role_to_dict(role)
    }


# =========================
# GET ROLES
# GET /api/roles/
# =========================

@rbac_route.get("/api/roles/")
def get_roles(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        is_active: bool = Query(None)
):
    get_admin_user(request)

    query = db.query(Role)

    if search:
        query = query.filter(
            or_(
                Role.name.ilike(f"%{search}%"),
                Role.code.ilike(f"%{search}%")
            )
        )

    if is_active is not None:
        query = query.filter(Role.is_active == is_active)

    total = query.count()

    roles = (
        query
        .order_by(Role.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách role thành công",
        "data": [role_to_dict(role) for role in roles],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET ROLE DETAIL
# GET /api/roles/{role_id}
# =========================

@rbac_route.get("/api/roles/{role_id}")
def get_role_by_id(
        role_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy role"
        )

    role_permissions = (
        db.query(RolePermission)
        .filter(RolePermission.role_id == role_id)
        .all()
    )

    data = role_to_dict(role)
    data["permissions"] = [
        role_permission_to_dict(item)["permission"]
        for item in role_permissions
    ]

    return {
        "message": "Lấy chi tiết role thành công",
        "data": data
    }


# =========================
# UPDATE ROLE
# PUT/PATCH /api/roles/{role_id}
# =========================

@rbac_route.put("/api/roles/{role_id}")
@rbac_route.patch("/api/roles/{role_id}")
def update_role(
        role_id: int,
        data: RoleUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy role"
        )

    update_data = data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "code" in update_data:
        new_code = update_data["code"].strip().lower()

        existed_role = (
            db.query(Role)
            .filter(
                Role.code == new_code,
                Role.id != role_id
            )
            .first()
        )

        if existed_role:
            raise HTTPException(
                status_code=400,
                detail="Mã role đã tồn tại"
            )

        update_data["code"] = new_code

    for key, value in update_data.items():
        setattr(role, key, value)

    db.commit()
    db.refresh(role)

    return {
        "message": "Cập nhật role thành công",
        "data": role_to_dict(role)
    }


# =========================
# DELETE ROLE
# DELETE /api/roles/{role_id}
# =========================

@rbac_route.delete("/api/roles/{role_id}")
def delete_role(
        role_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy role"
        )

    user_role_count = (
        db.query(UserRole)
        .filter(UserRole.role_id == role_id)
        .count()
    )

    if user_role_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa role đang được gán cho user. Hãy tắt is_active thay vì xóa."
        )

    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

    db.delete(role)
    db.commit()

    return {
        "message": "Xóa role thành công",
        "deleted_role_id": role_id
    }


# =====================================================
# ROLE PERMISSION API
# =====================================================

# =========================
# ASSIGN PERMISSIONS TO ROLE
# POST /api/roles/{role_id}/permissions
# =========================

@rbac_route.post("/api/roles/{role_id}/permissions")
def assign_permissions_to_role(
        role_id: int,
        data: AssignPermissionsToRole,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy role"
        )

    for permission_id in data.permission_ids:
        permission = db.query(Permission).filter(Permission.id == permission_id).first()

        if not permission:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy permission id {permission_id}"
            )

        existed = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id
            )
            .first()
        )

        if not existed:
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission_id
            )
            db.add(role_permission)

    db.commit()

    role_permissions = (
        db.query(RolePermission)
        .filter(RolePermission.role_id == role_id)
        .all()
    )

    return {
        "message": "Gán quyền cho role thành công",
        "data": [
            role_permission_to_dict(item)
            for item in role_permissions
        ]
    }


# =========================
# GET ROLE PERMISSIONS
# GET /api/roles/{role_id}/permissions
# =========================

@rbac_route.get("/api/roles/{role_id}/permissions")
def get_role_permissions(
        role_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    role = db.query(Role).filter(Role.id == role_id).first()

    if not role:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy role"
        )

    role_permissions = (
        db.query(RolePermission)
        .filter(RolePermission.role_id == role_id)
        .all()
    )

    return {
        "message": "Lấy quyền của role thành công",
        "data": [
            role_permission_to_dict(item)
            for item in role_permissions
        ]
    }


# =========================
# REMOVE PERMISSION FROM ROLE
# DELETE /api/roles/{role_id}/permissions/{permission_id}
# =========================

@rbac_route.delete("/api/roles/{role_id}/permissions/{permission_id}")
def remove_permission_from_role(
        role_id: int,
        permission_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    role_permission = (
        db.query(RolePermission)
        .filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id
        )
        .first()
    )

    if not role_permission:
        raise HTTPException(
            status_code=404,
            detail="Role chưa có quyền này"
        )

    db.delete(role_permission)
    db.commit()

    return {
        "message": "Gỡ quyền khỏi role thành công",
        "role_id": role_id,
        "permission_id": permission_id
    }


# =====================================================
# USER ROLE API
# =====================================================

# =========================
# ASSIGN ROLES TO USER
# POST /api/users/{user_id}/roles
# =========================

@rbac_route.post("/api/users/{user_id}/roles")
def assign_roles_to_user(
        user_id: int,
        data: AssignRolesToUser,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy user"
        )

    for role_id in data.role_ids:
        role = db.query(Role).filter(Role.id == role_id).first()

        if not role:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy role id {role_id}"
            )

        existed = (
            db.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
            .first()
        )

        if not existed:
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id
            )
            db.add(user_role)

    db.commit()

    user_roles = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id)
        .all()
    )

    return {
        "message": "Gán role cho user thành công",
        "data": [
            user_role_to_dict(item)
            for item in user_roles
        ]
    }


# =========================
# GET USER ROLES
# GET /api/users/{user_id}/roles
# =========================

@rbac_route.get("/api/users/{user_id}/roles")
def get_user_roles(
        user_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy user"
        )

    user_roles = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id)
        .all()
    )

    return {
        "message": "Lấy role của user thành công",
        "data": [
            user_role_to_dict(item)
            for item in user_roles
        ]
    }


# =========================
# REMOVE ROLE FROM USER
# DELETE /api/users/{user_id}/roles/{role_id}
# =========================

@rbac_route.delete("/api/users/{user_id}/roles/{role_id}")
def remove_role_from_user(
        user_id: int,
        role_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    user_role = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        .first()
    )

    if not user_role:
        raise HTTPException(
            status_code=404,
            detail="User chưa có role này"
        )

    db.delete(user_role)
    db.commit()

    return {
        "message": "Gỡ role khỏi user thành công",
        "user_id": user_id,
        "role_id": role_id
    }


# =========================
# GET MY PERMISSIONS
# GET /api/me/permissions
# =========================

@rbac_route.get("/api/me/permissions")
def get_my_permissions(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    permission_codes = get_user_permission_codes(db, current_user.id)

    return {
        "message": "Lấy quyền của tôi thành công",
        "data": {
            "user_id": current_user.id,
            "username": current_user.username,
            "legacy_role": getattr(current_user, "role", "user"),
            "permissions": permission_codes,
            "is_admin": getattr(current_user, "role", "user") == "admin" or "system.admin" in permission_codes
        }
    }