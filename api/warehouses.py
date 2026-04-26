import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth import get_admin_user
from database import get_db
from models.models import User, Warehouse
from schemas.warehouse_schema import WarehouseCreate, WarehouseUpdate

warehouses_route = APIRouter(prefix="/api/warehouses", tags=["warehouses"])

def warehouse_to_dict(warehouse: Warehouse):
    return {
        "id": warehouse.id,
        "name": warehouse.name,
        "code": warehouse.code,
        "phone": warehouse.phone,
        "address": warehouse.address,
        "province": warehouse.province,
        "district": warehouse.district,
        "ward": warehouse.ward,
        "manager_id": warehouse.manager_id,
        "is_active": warehouse.is_active,
        "note": warehouse.note,
        "created_at": warehouse.created_at,
        "updated_at": warehouse.updated_at,
        "manager": {
            "id": warehouse.manager.id,
            "username": warehouse.manager.username,
            "avatar": warehouse.manager.avatar,
            "role": getattr(warehouse.manager, "role", "user")
        } if warehouse.manager else None
    }


# =========================
# CREATE WAREHOUSE
# POST /api/warehouses/
# =========================

@warehouses_route.post("/")
def create_warehouse(
        warehouse_data: WarehouseCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    code = warehouse_data.code.strip().upper()

    existed_warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.code == code)
        .first()
    )

    if existed_warehouse:
        raise HTTPException(
            status_code=400,
            detail="Mã kho đã tồn tại"
        )

    if warehouse_data.manager_id:
        manager = db.query(User).filter(User.id == warehouse_data.manager_id).first()

        if not manager:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy người quản lý kho"
            )

    new_warehouse = Warehouse(
        name=warehouse_data.name,
        code=code,
        phone=warehouse_data.phone,
        address=warehouse_data.address,
        province=warehouse_data.province,
        district=warehouse_data.district,
        ward=warehouse_data.ward,
        manager_id=warehouse_data.manager_id,
        is_active=warehouse_data.is_active,
        note=warehouse_data.note
    )

    db.add(new_warehouse)
    db.commit()
    db.refresh(new_warehouse)

    return {
        "message": "Tạo kho hàng thành công",
        "data": warehouse_to_dict(new_warehouse)
    }


# =========================
# GET ALL WAREHOUSES
# GET /api/warehouses/
# =========================

@warehouses_route.get("/")
def get_all_warehouses(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        is_active: bool = Query(None)
):
    get_admin_user(request)

    query = db.query(Warehouse)

    if search:
        query = query.filter(
            or_(
                Warehouse.name.ilike(f"%{search}%"),
                Warehouse.code.ilike(f"%{search}%"),
                Warehouse.phone.ilike(f"%{search}%"),
                Warehouse.address.ilike(f"%{search}%"),
                Warehouse.province.ilike(f"%{search}%"),
                Warehouse.district.ilike(f"%{search}%")
            )
        )

    if is_active is not None:
        query = query.filter(Warehouse.is_active == is_active)

    total = query.count()

    warehouses = (
        query
        .order_by(Warehouse.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách kho hàng thành công",
        "data": [warehouse_to_dict(warehouse) for warehouse in warehouses],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET ACTIVE WAREHOUSES
# GET /api/warehouses/active
# =========================

@warehouses_route.get("/active")
def get_active_warehouses(
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    warehouses = (
        db.query(Warehouse)
        .filter(Warehouse.is_active == True)
        .order_by(Warehouse.name.asc())
        .all()
    )

    return {
        "message": "Lấy kho đang hoạt động thành công",
        "data": [warehouse_to_dict(warehouse) for warehouse in warehouses]
    }


# =========================
# GET WAREHOUSE BY ID
# GET /api/warehouses/{warehouse_id}
# =========================

@warehouses_route.get("/{warehouse_id}")
def get_warehouse_by_id(
        warehouse_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy kho hàng"
        )

    return {
        "message": "Lấy chi tiết kho hàng thành công",
        "data": warehouse_to_dict(warehouse)
    }


# =========================
# UPDATE WAREHOUSE
# PUT/PATCH /api/warehouses/{warehouse_id}
# =========================

@warehouses_route.put("/{warehouse_id}")
@warehouses_route.patch("/{warehouse_id}")
def update_warehouse(
        warehouse_id: int,
        warehouse_data: WarehouseUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy kho hàng"
        )

    update_data = warehouse_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "code" in update_data:
        new_code = update_data["code"].strip().upper()

        existed_warehouse = (
            db.query(Warehouse)
            .filter(
                Warehouse.code == new_code,
                Warehouse.id != warehouse_id
            )
            .first()
        )

        if existed_warehouse:
            raise HTTPException(
                status_code=400,
                detail="Mã kho đã tồn tại"
            )

        update_data["code"] = new_code

    if "manager_id" in update_data and update_data["manager_id"]:
        manager = db.query(User).filter(User.id == update_data["manager_id"]).first()

        if not manager:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy người quản lý kho"
            )

    for key, value in update_data.items():
        setattr(warehouse, key, value)

    db.commit()
    db.refresh(warehouse)

    return {
        "message": "Cập nhật kho hàng thành công",
        "data": warehouse_to_dict(warehouse)
    }


# =========================
# DELETE WAREHOUSE
# DELETE /api/warehouses/{warehouse_id}
# =========================

@warehouses_route.delete("/{warehouse_id}")
def delete_warehouse(
        warehouse_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy kho hàng"
        )

    db.delete(warehouse)
    db.commit()

    return {
        "message": "Xóa kho hàng thành công",
        "deleted_warehouse_id": warehouse_id
    }