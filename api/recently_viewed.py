from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import RecentlyViewedProduct, Products, User


recently_viewed_route = APIRouter(
    prefix="/api/recently-viewed",
    tags=["recently-viewed"]
)

def recently_viewed_to_dict(item: RecentlyViewedProduct):
    product = item.product

    return {
        "id": item.id,
        "user_id": item.user_id,
        "product_id": item.product_id,
        "viewed_at": item.viewed_at,
        "product": {
            "id": product.id,
            "title": product.title,
            "desc": product.desc,
            "img": product.img,
            "categories": product.categories,
            "size": product.size,
            "color": product.color,
            "price": product.price
        } if product else None
    }


# =========================
# ADD / UPDATE VIEWED PRODUCT
# POST /api/recently-viewed/{product_id}
# =========================

@recently_viewed_route.post("/{product_id}")
def add_recently_viewed_product(
        product_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    current_user = current_user.id

    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    existed_item = (
        db.query(RecentlyViewedProduct)
        .filter(
            RecentlyViewedProduct.user_id == current_user.id,
            RecentlyViewedProduct.product_id == product_id
        )
        .first()
    )

    if existed_item:
        existed_item.viewed_at = datetime.utcnow()

        db.commit()
        db.refresh(existed_item)

        return {
            "message": "Cập nhật sản phẩm đã xem gần đây thành công",
            "data": recently_viewed_to_dict(existed_item)
        }

    new_item = RecentlyViewedProduct(
        user_id=current_user.id,
        product_id=product_id,
        viewed_at=datetime.utcnow()
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "message": "Thêm sản phẩm đã xem gần đây thành công",
        "data": recently_viewed_to_dict(new_item)
    }


# =========================
# GET RECENTLY VIEWED PRODUCTS
# GET /api/recently-viewed/
# =========================

@recently_viewed_route.get("/")
def get_recently_viewed_products(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        limit: int = Query(10, gt=0)
):

    items = (
        db.query(RecentlyViewedProduct)
        .filter(RecentlyViewedProduct.user_id == current_user.id)
        .order_by(RecentlyViewedProduct.viewed_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách sản phẩm đã xem gần đây thành công",
        "data": [recently_viewed_to_dict(item) for item in items],
        "total": len(items)
    }


# =========================
# CLEAR ALL RECENTLY VIEWED
# DELETE /api/recently-viewed/clear/all
# =========================

@recently_viewed_route.delete("/clear/all")
def clear_recently_viewed_products(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    db.query(RecentlyViewedProduct).filter(
        RecentlyViewedProduct.user_id == current_user.id
    ).delete()

    db.commit()

    return {
        "message": "Xóa toàn bộ sản phẩm đã xem gần đây thành công"
    }


# =========================
# DELETE ONE RECENTLY VIEWED PRODUCT
# DELETE /api/recently-viewed/{product_id}
# =========================

@recently_viewed_route.delete("/{product_id}")
def delete_recently_viewed_product(
        product_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    item = (
        db.query(RecentlyViewedProduct)
        .filter(
            RecentlyViewedProduct.user_id == current_user.id,
            RecentlyViewedProduct.product_id == product_id
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Sản phẩm này không có trong danh sách đã xem"
        )

    db.delete(item)
    db.commit()

    return {
        "message": "Xóa sản phẩm đã xem thành công",
        "deleted_product_id": product_id
    }