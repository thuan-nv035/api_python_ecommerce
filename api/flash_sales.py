import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from database import get_db
from models.models import (
    User,
    Products,
    ProductVariant,
    FlashSale,
    FlashSaleItem
)
from schemas.flash_sale_schema import (
    FlashSaleCreate,
    FlashSaleUpdate,
    FlashSaleItemCreate,
    FlashSaleItemUpdate
)


flash_sales_route = APIRouter(prefix="/api/flash-sales", tags=["flash-sales"])


def get_current_user(request: Request, db: Session):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(status_code=401, detail="Bạn chưa đăng nhập")

    user = db.query(User).filter(User.id == current_user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    return user


def check_admin(user: User):
    if getattr(user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền admin")


def flash_sale_item_to_dict(item: FlashSaleItem):
    product = item.product
    variant = item.variant

    original_price = 0

    if variant and variant.price is not None:
        original_price = variant.price
    elif product and product.price is not None:
        original_price = product.price

    discount_percent = 0

    if original_price and original_price > 0:
        discount_percent = round(
            ((original_price - item.sale_price) / original_price) * 100,
            2
        )

    return {
        "id": item.id,
        "flash_sale_id": item.flash_sale_id,
        "product_id": item.product_id,
        "variant_id": item.variant_id,
        "sale_price": item.sale_price,
        "sale_quantity": item.sale_quantity,
        "sold": item.sold,
        "available": item.sale_quantity - item.sold,
        "is_active": item.is_active,
        "original_price": original_price,
        "discount_percent": discount_percent,
        "product": {
            "id": product.id,
            "title": product.title,
            "img": product.img,
            "price": product.price,
            "categories": product.categories
        } if product else None,
        "variant": {
            "id": variant.id,
            "sku": variant.sku,
            "size": variant.size,
            "color": variant.color,
            "price": variant.price,
            "img": variant.img
        } if variant else None
    }


def flash_sale_to_dict(flash_sale: FlashSale):
    return {
        "id": flash_sale.id,
        "title": flash_sale.title,
        "desc": flash_sale.desc,
        "start_at": flash_sale.start_at,
        "end_at": flash_sale.end_at,
        "is_active": flash_sale.is_active,
        "created_at": flash_sale.created_at,
        "updated_at": flash_sale.updated_at,
        "items": [
            flash_sale_item_to_dict(item)
            for item in flash_sale.items
        ]
    }


def is_flash_sale_running(flash_sale: FlashSale):
    now = datetime.now(timezone.utc)

    if not flash_sale.is_active:
        return False

    if now < flash_sale.start_at:
        return False

    if now > flash_sale.end_at:
        return False

    return True


# =========================
# GET ACTIVE FLASH SALES
# GET /api/flash-sales/active
# Public
# =========================

@flash_sales_route.get("/active")
def get_active_flash_sales(
        db: Session = Depends(get_db)
):
    flash_sales = (
        db.query(FlashSale)
        .filter(FlashSale.is_active == True)
        .order_by(FlashSale.id.desc())
        .all()
    )

    active_sales = [
        sale for sale in flash_sales
        if is_flash_sale_running(sale)
    ]

    return {
        "message": "Lấy flash sale đang hoạt động thành công",
        "data": [flash_sale_to_dict(sale) for sale in active_sales]
    }


# =========================
# GET ALL FLASH SALES
# GET /api/flash-sales/
# Admin
# =========================

@flash_sales_route.get("/")
def get_all_flash_sales(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        is_active: bool = Query(None)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    query = db.query(FlashSale)

    if is_active is not None:
        query = query.filter(FlashSale.is_active == is_active)

    total = query.count()

    flash_sales = (
        query
        .order_by(FlashSale.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách flash sale thành công",
        "data": [flash_sale_to_dict(sale) for sale in flash_sales],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET FLASH SALE BY ID
# GET /api/flash-sales/{flash_sale_id}
# Public
# =========================

@flash_sales_route.get("/{flash_sale_id}")
def get_flash_sale_by_id(
        flash_sale_id: int,
        db: Session = Depends(get_db)
):
    flash_sale = (
        db.query(FlashSale)
        .filter(FlashSale.id == flash_sale_id)
        .first()
    )

    if not flash_sale:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy flash sale"
        )

    return {
        "message": "Lấy chi tiết flash sale thành công",
        "data": flash_sale_to_dict(flash_sale)
    }


# =========================
# CREATE FLASH SALE
# POST /api/flash-sales/
# Admin
# =========================

@flash_sales_route.post("/")
def create_flash_sale(
        flash_sale_data: FlashSaleCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    if flash_sale_data.end_at <= flash_sale_data.start_at:
        raise HTTPException(
            status_code=400,
            detail="Thời gian kết thúc phải lớn hơn thời gian bắt đầu"
        )

    new_flash_sale = FlashSale(
        title=flash_sale_data.title,
        desc=flash_sale_data.desc,
        start_at=flash_sale_data.start_at,
        end_at=flash_sale_data.end_at,
        is_active=flash_sale_data.is_active
    )

    db.add(new_flash_sale)
    db.commit()
    db.refresh(new_flash_sale)

    return {
        "message": "Tạo flash sale thành công",
        "data": flash_sale_to_dict(new_flash_sale)
    }


# =========================
# UPDATE FLASH SALE
# PUT /api/flash-sales/{flash_sale_id}
# PATCH /api/flash-sales/{flash_sale_id}
# Admin
# =========================

@flash_sales_route.put("/{flash_sale_id}")
@flash_sales_route.patch("/{flash_sale_id}")
def update_flash_sale(
        flash_sale_id: int,
        flash_sale_data: FlashSaleUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    flash_sale = (
        db.query(FlashSale)
        .filter(FlashSale.id == flash_sale_id)
        .first()
    )

    if not flash_sale:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy flash sale"
        )

    update_data = flash_sale_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    new_start = update_data.get("start_at", flash_sale.start_at)
    new_end = update_data.get("end_at", flash_sale.end_at)

    if new_end <= new_start:
        raise HTTPException(
            status_code=400,
            detail="Thời gian kết thúc phải lớn hơn thời gian bắt đầu"
        )

    for key, value in update_data.items():
        setattr(flash_sale, key, value)

    db.commit()
    db.refresh(flash_sale)

    return {
        "message": "Cập nhật flash sale thành công",
        "data": flash_sale_to_dict(flash_sale)
    }


# =========================
# DELETE FLASH SALE
# DELETE /api/flash-sales/{flash_sale_id}
# Admin
# =========================

@flash_sales_route.delete("/{flash_sale_id}")
def delete_flash_sale(
        flash_sale_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    flash_sale = (
        db.query(FlashSale)
        .filter(FlashSale.id == flash_sale_id)
        .first()
    )

    if not flash_sale:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy flash sale"
        )

    db.delete(flash_sale)
    db.commit()

    return {
        "message": "Xóa flash sale thành công",
        "deleted_flash_sale_id": flash_sale_id
    }


# =========================
# ADD ITEM TO FLASH SALE
# POST /api/flash-sales/{flash_sale_id}/items
# Admin
# =========================

@flash_sales_route.post("/{flash_sale_id}/items")
def add_flash_sale_item(
        flash_sale_id: int,
        item_data: FlashSaleItemCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    flash_sale = (
        db.query(FlashSale)
        .filter(FlashSale.id == flash_sale_id)
        .first()
    )

    if not flash_sale:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy flash sale"
        )

    product = (
        db.query(Products)
        .filter(Products.id == item_data.product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    variant = None

    if item_data.variant_id:
        variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.id == item_data.variant_id,
                ProductVariant.product_id == item_data.product_id
            )
            .first()
        )

        if not variant:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy biến thể sản phẩm"
            )

    existed_item = (
        db.query(FlashSaleItem)
        .filter(
            FlashSaleItem.flash_sale_id == flash_sale_id,
            FlashSaleItem.product_id == item_data.product_id,
            FlashSaleItem.variant_id == item_data.variant_id
        )
        .first()
    )

    if existed_item:
        raise HTTPException(
            status_code=400,
            detail="Sản phẩm này đã có trong flash sale"
        )

    new_item = FlashSaleItem(
        flash_sale_id=flash_sale_id,
        product_id=item_data.product_id,
        variant_id=item_data.variant_id,
        sale_price=item_data.sale_price,
        sale_quantity=item_data.sale_quantity,
        sold=0,
        is_active=item_data.is_active
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "message": "Thêm sản phẩm vào flash sale thành công",
        "data": flash_sale_item_to_dict(new_item)
    }


# =========================
# UPDATE FLASH SALE ITEM
# PATCH /api/flash-sales/items/{item_id}
# Admin
# =========================

@flash_sales_route.patch("/items/{item_id}")
def update_flash_sale_item(
        item_id: int,
        item_data: FlashSaleItemUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    item = (
        db.query(FlashSaleItem)
        .filter(FlashSaleItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm flash sale"
        )

    update_data = item_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "sale_quantity" in update_data:
        if update_data["sale_quantity"] < item.sold:
            raise HTTPException(
                status_code=400,
                detail="Số lượng sale không được nhỏ hơn số lượng đã bán"
            )

    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)

    return {
        "message": "Cập nhật sản phẩm flash sale thành công",
        "data": flash_sale_item_to_dict(item)
    }


# =========================
# DELETE FLASH SALE ITEM
# DELETE /api/flash-sales/items/{item_id}
# Admin
# =========================

@flash_sales_route.delete("/items/{item_id}")
def delete_flash_sale_item(
        item_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    item = (
        db.query(FlashSaleItem)
        .filter(FlashSaleItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm flash sale"
        )

    if item.sold > 0:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa sản phẩm đã bán trong flash sale. Hãy tắt is_active thay vì xóa."
        )

    db.delete(item)
    db.commit()

    return {
        "message": "Xóa sản phẩm khỏi flash sale thành công",
        "deleted_item_id": item_id
    }