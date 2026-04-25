import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from database import get_db
from models.models import Products, ProductVariant, User
from schemas.product_variant_schema import (
    ProductVariantCreate,
    ProductVariantUpdate,
    VariantStockAdjust
)


product_variants_route = APIRouter(
    prefix="/api/product-variants",
    tags=["product-variants"]
)


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


def variant_to_dict(variant: ProductVariant):
    product = variant.product

    return {
        "id": variant.id,
        "product_id": variant.product_id,
        "sku": variant.sku,
        "size": variant.size,
        "color": variant.color,
        "price": variant.price,
        "img": variant.img,
        "quantity": variant.quantity,
        "sold": variant.sold,
        "available": variant.quantity - variant.sold,
        "is_active": variant.is_active,
        "created_at": variant.created_at,
        "updated_at": variant.updated_at,
        "product": {
            "id": product.id,
            "title": product.title,
            "price": product.price,
            "img": product.img
        } if product else None
    }


# =========================
# GET ALL VARIANTS
# GET /api/product-variants/
# Public
# =========================

@product_variants_route.get("/")
def get_all_variants(
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        product_id: int = Query(None),
        size: str = Query(None),
        color: str = Query(None),
        is_active: bool = Query(None)
):
    query = db.query(ProductVariant)

    if product_id is not None:
        query = query.filter(ProductVariant.product_id == product_id)

    if size:
        query = query.filter(ProductVariant.size == size)

    if color:
        query = query.filter(ProductVariant.color == color)

    if is_active is not None:
        query = query.filter(ProductVariant.is_active == is_active)

    total = query.count()

    variants = (
        query
        .order_by(ProductVariant.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách biến thể sản phẩm thành công",
        "data": [variant_to_dict(variant) for variant in variants],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET VARIANTS BY PRODUCT
# GET /api/product-variants/product/{product_id}
# Public
# =========================

@product_variants_route.get("/product/{product_id}")
def get_variants_by_product(
        product_id: int,
        db: Session = Depends(get_db)
):
    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    variants = (
        db.query(ProductVariant)
        .filter(ProductVariant.product_id == product_id)
        .order_by(ProductVariant.id.desc())
        .all()
    )

    total_quantity = sum(item.quantity for item in variants)
    total_sold = sum(item.sold for item in variants)

    return {
        "message": "Lấy biến thể theo sản phẩm thành công",
        "data": [variant_to_dict(variant) for variant in variants],
        "summary": {
            "total_quantity": total_quantity,
            "total_sold": total_sold,
            "available": total_quantity - total_sold
        }
    }


# =========================
# GET VARIANT BY ID
# GET /api/product-variants/{variant_id}
# Public
# =========================

@product_variants_route.get("/{variant_id}")
def get_variant_by_id(
        variant_id: int,
        db: Session = Depends(get_db)
):
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == variant_id)
        .first()
    )

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy biến thể sản phẩm"
        )

    return {
        "message": "Lấy chi tiết biến thể thành công",
        "data": variant_to_dict(variant)
    }


# =========================
# CREATE VARIANT
# POST /api/product-variants/
# Admin
# =========================

@product_variants_route.post("/")
def create_variant(
        variant_data: ProductVariantCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    product = (
        db.query(Products)
        .filter(Products.id == variant_data.product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    existed_variant = (
        db.query(ProductVariant)
        .filter(
            ProductVariant.product_id == variant_data.product_id,
            ProductVariant.size == variant_data.size,
            ProductVariant.color == variant_data.color
        )
        .first()
    )

    if existed_variant:
        raise HTTPException(
            status_code=400,
            detail="Biến thể size/color này đã tồn tại"
        )

    if variant_data.sku:
        existed_sku = (
            db.query(ProductVariant)
            .filter(ProductVariant.sku == variant_data.sku)
            .first()
        )

        if existed_sku:
            raise HTTPException(
                status_code=400,
                detail="SKU đã tồn tại"
            )

    new_variant = ProductVariant(
        product_id=variant_data.product_id,
        sku=variant_data.sku,
        size=variant_data.size,
        color=variant_data.color,
        price=variant_data.price,
        img=variant_data.img or [],
        quantity=variant_data.quantity,
        sold=0,
        is_active=variant_data.is_active
    )

    db.add(new_variant)
    db.commit()
    db.refresh(new_variant)

    return {
        "message": "Tạo biến thể sản phẩm thành công",
        "data": variant_to_dict(new_variant)
    }


# =========================
# UPDATE VARIANT
# PUT /api/product-variants/{variant_id}
# PATCH /api/product-variants/{variant_id}
# Admin
# =========================

@product_variants_route.put("/{variant_id}")
@product_variants_route.patch("/{variant_id}")
def update_variant(
        variant_id: int,
        variant_data: ProductVariantUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == variant_id)
        .first()
    )

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy biến thể sản phẩm"
        )

    update_data = variant_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "sku" in update_data and update_data["sku"]:
        existed_sku = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.sku == update_data["sku"],
                ProductVariant.id != variant_id
            )
            .first()
        )

        if existed_sku:
            raise HTTPException(
                status_code=400,
                detail="SKU đã tồn tại"
            )

    if "size" in update_data or "color" in update_data:
        new_size = update_data.get("size", variant.size)
        new_color = update_data.get("color", variant.color)

        existed_variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.product_id == variant.product_id,
                ProductVariant.size == new_size,
                ProductVariant.color == new_color,
                ProductVariant.id != variant_id
            )
            .first()
        )

        if existed_variant:
            raise HTTPException(
                status_code=400,
                detail="Biến thể size/color này đã tồn tại"
            )

    for key, value in update_data.items():
        setattr(variant, key, value)

    db.commit()
    db.refresh(variant)

    return {
        "message": "Cập nhật biến thể thành công",
        "data": variant_to_dict(variant)
    }


# =========================
# ADD STOCK
# PATCH /api/product-variants/{variant_id}/add-stock
# Admin
# =========================

@product_variants_route.patch("/{variant_id}/add-stock")
def add_variant_stock(
        variant_id: int,
        stock_data: VariantStockAdjust,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    if stock_data.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Số lượng nhập thêm phải lớn hơn 0"
        )

    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == variant_id)
        .first()
    )

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy biến thể sản phẩm"
        )

    variant.quantity += stock_data.quantity

    db.commit()
    db.refresh(variant)

    return {
        "message": "Nhập thêm tồn kho biến thể thành công",
        "data": variant_to_dict(variant)
    }


# =========================
# DELETE VARIANT
# DELETE /api/product-variants/{variant_id}
# Admin
# =========================

@product_variants_route.delete("/{variant_id}")
def delete_variant(
        variant_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == variant_id)
        .first()
    )

    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy biến thể sản phẩm"
        )

    if variant.sold > 0:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa biến thể đã có lượt bán. Hãy tắt is_active thay vì xóa."
        )

    db.delete(variant)
    db.commit()

    return {
        "message": "Xóa biến thể sản phẩm thành công",
        "deleted_variant_id": variant_id
    }