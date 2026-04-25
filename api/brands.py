import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models.models import Brand, User, Products
from schemas.brand_schema import BrandCreate, BrandUpdate


brands_route = APIRouter(prefix="/api/brands", tags=["brands"])


def get_current_user(request: Request, db: Session):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    user = db.query(User).filter(User.id == current_user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy user"
        )

    return user


def check_admin(user: User):
    if getattr(user, "role", "user") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )


def brand_to_dict(brand: Brand):
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "desc": brand.desc,
        "logo": brand.logo,
        "is_active": brand.is_active,
        "created_at": brand.created_at,
        "updated_at": brand.updated_at
    }


# =========================
# GET ALL BRANDS
# GET /api/brands/
# Public
# =========================

@brands_route.get("/")
def get_all_brands(
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        is_active: bool = Query(None)
):
    query = db.query(Brand)

    if search:
        query = query.filter(
            or_(
                Brand.name.ilike(f"%{search}%"),
                Brand.slug.ilike(f"%{search}%")
            )
        )

    if is_active is not None:
        query = query.filter(Brand.is_active == is_active)

    total = query.count()

    brands = (
        query
        .order_by(Brand.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách thương hiệu thành công",
        "data": [brand_to_dict(brand) for brand in brands],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET ACTIVE BRANDS
# GET /api/brands/active
# Public
# =========================

@brands_route.get("/active")
def get_active_brands(
        db: Session = Depends(get_db)
):
    brands = (
        db.query(Brand)
        .filter(Brand.is_active == True)
        .order_by(Brand.name.asc())
        .all()
    )

    return {
        "message": "Lấy thương hiệu đang hoạt động thành công",
        "data": [brand_to_dict(brand) for brand in brands]
    }


# =========================
# GET BRAND BY ID
# GET /api/brands/{brand_id}
# Public
# =========================

@brands_route.get("/{brand_id}")
def get_brand_by_id(
        brand_id: int,
        db: Session = Depends(get_db)
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thương hiệu"
        )

    return {
        "message": "Lấy chi tiết thương hiệu thành công",
        "data": brand_to_dict(brand)
    }


# =========================
# CREATE BRAND
# POST /api/brands/
# Admin
# =========================

@brands_route.post("/")
def create_brand(
        brand_data: BrandCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    slug = brand_data.slug.strip().lower()

    existed_brand = (
        db.query(Brand)
        .filter(Brand.slug == slug)
        .first()
    )

    if existed_brand:
        raise HTTPException(
            status_code=400,
            detail="Slug thương hiệu đã tồn tại"
        )

    new_brand = Brand(
        name=brand_data.name,
        slug=slug,
        desc=brand_data.desc,
        logo=brand_data.logo,
        is_active=brand_data.is_active
    )

    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)

    return {
        "message": "Tạo thương hiệu thành công",
        "data": brand_to_dict(new_brand)
    }


# =========================
# UPDATE BRAND
# PUT /api/brands/{brand_id}
# PATCH /api/brands/{brand_id}
# Admin
# =========================

@brands_route.put("/{brand_id}")
@brands_route.patch("/{brand_id}")
def update_brand(
        brand_id: int,
        brand_data: BrandUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    brand = db.query(Brand).filter(Brand.id == brand_id).first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thương hiệu"
        )

    update_data = brand_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "slug" in update_data:
        new_slug = update_data["slug"].strip().lower()

        existed_brand = (
            db.query(Brand)
            .filter(
                Brand.slug == new_slug,
                Brand.id != brand_id
            )
            .first()
        )

        if existed_brand:
            raise HTTPException(
                status_code=400,
                detail="Slug thương hiệu đã tồn tại"
            )

        update_data["slug"] = new_slug

    for key, value in update_data.items():
        setattr(brand, key, value)

    db.commit()
    db.refresh(brand)

    return {
        "message": "Cập nhật thương hiệu thành công",
        "data": brand_to_dict(brand)
    }


# =========================
# DELETE BRAND
# DELETE /api/brands/{brand_id}
# Admin
# =========================

@brands_route.delete("/{brand_id}")
def delete_brand(
        brand_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    brand = db.query(Brand).filter(Brand.id == brand_id).first()

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thương hiệu"
        )

    product_count = (
        db.query(Products)
        .filter(Products.brand_id == brand_id)
        .count()
    )

    if product_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa thương hiệu đang có sản phẩm. Hãy tắt is_active thay vì xóa."
        )

    db.delete(brand)
    db.commit()

    return {
        "message": "Xóa thương hiệu thành công",
        "deleted_brand_id": brand_id
    }