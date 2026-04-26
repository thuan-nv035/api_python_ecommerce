import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.audit_logs import create_audit_log, get_request_ip, get_request_user_agent
from api.auth import get_admin_user, get_current_user
from database import get_db
from models.models import User, Supplier
from schemas.supplier_schema import SupplierCreate, SupplierUpdate

suppliers_route = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

def supplier_to_dict(supplier: Supplier):
    return {
        "id": supplier.id,
        "name": supplier.name,
        "code": supplier.code,
        "phone": supplier.phone,
        "email": supplier.email,
        "address": supplier.address,
        "tax_code": supplier.tax_code,
        "contact_person": supplier.contact_person,
        "status": supplier.status,
        "note": supplier.note,
        "created_at": supplier.created_at,
        "updated_at": supplier.updated_at,
    }


# =========================
# CREATE SUPPLIER
# POST /api/suppliers/
# Admin
# =========================

@suppliers_route.post("/")
def create_supplier(
        supplier_data: SupplierCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user:User = Depends(get_current_user)
):
    get_admin_user(request)

    code = supplier_data.code.strip().upper()

    existed_supplier = (
        db.query(Supplier)
        .filter(Supplier.code == code)
        .first()
    )

    if existed_supplier:
        raise HTTPException(
            status_code=400,
            detail="Mã nhà cung cấp đã tồn tại"
        )

    allowed_status = ["active", "inactive"]

    if supplier_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái nhà cung cấp không hợp lệ"
        )

    new_supplier = Supplier(
        name=supplier_data.name,
        code=code,
        phone=supplier_data.phone,
        email=supplier_data.email,
        address=supplier_data.address,
        tax_code=supplier_data.tax_code,
        contact_person=supplier_data.contact_person,
        status=supplier_data.status,
        note=supplier_data.note
    )

    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="create",
        module="suppliers",
        resource_type="Supplier",
        resource_id=new_supplier.id,
        old_data=None,
        new_data=supplier_to_dict(new_supplier),
        ip_address=get_request_ip(request),
        user_agent=get_request_user_agent(request),
        note=f"Tạo nhà cung cấp {new_supplier.code}"
    )

    db.commit()

    return {
        "message": "Tạo nhà cung cấp thành công",
        "data": supplier_to_dict(new_supplier)
    }


# =========================
# GET ALL SUPPLIERS
# GET /api/suppliers/
# Admin
# =========================

@suppliers_route.get("/")
def get_all_suppliers(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        status: str = Query(None)
):
    get_admin_user(request)

    query = db.query(Supplier)

    if search:
        query = query.filter(
            or_(
                Supplier.name.ilike(f"%{search}%"),
                Supplier.code.ilike(f"%{search}%"),
                Supplier.phone.ilike(f"%{search}%"),
                Supplier.email.ilike(f"%{search}%"),
                Supplier.contact_person.ilike(f"%{search}%")
            )
        )

    if status:
        query = query.filter(Supplier.status == status)

    total = query.count()

    suppliers = (
        query
        .order_by(Supplier.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách nhà cung cấp thành công",
        "data": [supplier_to_dict(supplier) for supplier in suppliers],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET ACTIVE SUPPLIERS
# GET /api/suppliers/active
# Admin
# =========================

@suppliers_route.get("/active")
def get_active_suppliers(
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    suppliers = (
        db.query(Supplier)
        .filter(Supplier.status == "active")
        .order_by(Supplier.name.asc())
        .all()
    )

    return {
        "message": "Lấy nhà cung cấp đang hoạt động thành công",
        "data": [supplier_to_dict(supplier) for supplier in suppliers]
    }


# =========================
# GET SUPPLIER BY ID
# GET /api/suppliers/{supplier_id}
# Admin
# =========================

@suppliers_route.get("/{supplier_id}")
def get_supplier_by_id(
        supplier_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nhà cung cấp"
        )

    return {
        "message": "Lấy chi tiết nhà cung cấp thành công",
        "data": supplier_to_dict(supplier)
    }


# =========================
# UPDATE SUPPLIER
# PUT/PATCH /api/suppliers/{supplier_id}
# Admin
# =========================

@suppliers_route.put("/{supplier_id}")
@suppliers_route.patch("/{supplier_id}")
def update_supplier(
        supplier_id: int,
        supplier_data: SupplierUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nhà cung cấp"
        )

    update_data = supplier_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "code" in update_data:
        new_code = update_data["code"].strip().upper()

        existed_supplier = (
            db.query(Supplier)
            .filter(
                Supplier.code == new_code,
                Supplier.id != supplier_id
            )
            .first()
        )

        if existed_supplier:
            raise HTTPException(
                status_code=400,
                detail="Mã nhà cung cấp đã tồn tại"
            )

        update_data["code"] = new_code

    if "status" in update_data:
        allowed_status = ["active", "inactive"]

        if update_data["status"] not in allowed_status:
            raise HTTPException(
                status_code=400,
                detail="Trạng thái nhà cung cấp không hợp lệ"
            )

    for key, value in update_data.items():
        setattr(supplier, key, value)

    db.commit()
    db.refresh(supplier)

    return {
        "message": "Cập nhật nhà cung cấp thành công",
        "data": supplier_to_dict(supplier)
    }


# =========================
# DELETE SUPPLIER
# DELETE /api/suppliers/{supplier_id}
# Admin
# =========================

@suppliers_route.delete("/{supplier_id}")
def delete_supplier(
        supplier_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nhà cung cấp"
        )

    db.delete(supplier)
    db.commit()

    return {
        "message": "Xóa nhà cung cấp thành công",
        "deleted_supplier_id": supplier_id
    }