from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import Wishlist, Products, User

wishlist_route = APIRouter(prefix="/api/wishlist", tags=["wishlist"])

def wishlist_to_dict(item: Wishlist):
    product = item.product

    return {
        "id": item.id,
        "user_id": item.user_id,
        "product_id": item.product_id,
        "created_at": item.created_at,
        "product": {
            "id": product.id,
            "title": product.title,
            "desc": product.desc,
            "img": product.img,
            "categories": product.categories,
            "size": product.size,
            "color": product.color,
            "price": product.price,
        } if product else None
    }


# =========================
# GET MY WISHLIST
# GET /api/wishlist/
# =========================

@wishlist_route.get("/")
def get_my_wishlist(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    wishlist_items = (
        db.query(Wishlist)
        .filter(Wishlist.user_id == current_user_id)
        .order_by(Wishlist.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách yêu thích thành công",
        "data": [wishlist_to_dict(item) for item in wishlist_items],
        "total": len(wishlist_items)
    }


# =========================
# ADD TO WISHLIST
# POST /api/wishlist/{product_id}
# =========================

@wishlist_route.post("/{product_id}")
def add_to_wishlist(
        product_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    existed_item = (
        db.query(Wishlist)
        .filter(
            Wishlist.user_id == current_user_id,
            Wishlist.product_id == product_id
        )
        .first()
    )

    if existed_item:
        raise HTTPException(
            status_code=400,
            detail="Sản phẩm đã có trong danh sách yêu thích"
        )

    new_item = Wishlist(
        user_id=current_user_id,
        product_id=product_id
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "message": "Thêm sản phẩm vào yêu thích thành công",
        "data": wishlist_to_dict(new_item)
    }


# =========================
# CHECK PRODUCT IN WISHLIST
# GET /api/wishlist/check/{product_id}
# =========================

@wishlist_route.get("/check/{product_id}")
def check_product_in_wishlist(
        product_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    existed_item = (
        db.query(Wishlist)
        .filter(
            Wishlist.user_id == current_user_id,
            Wishlist.product_id == product_id
        )
        .first()
    )

    return {
        "message": "Kiểm tra sản phẩm yêu thích thành công",
        "is_liked": existed_item is not None
    }


# =========================
# REMOVE FROM WISHLIST
# DELETE /api/wishlist/{product_id}
# =========================

@wishlist_route.delete("/{product_id}")
def remove_from_wishlist(
        product_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    wishlist_item = (
        db.query(Wishlist)
        .filter(
            Wishlist.user_id == current_user_id,
            Wishlist.product_id == product_id
        )
        .first()
    )

    if not wishlist_item:
        raise HTTPException(
            status_code=404,
            detail="Sản phẩm không có trong danh sách yêu thích"
        )

    db.delete(wishlist_item)
    db.commit()

    return {
        "message": "Xóa sản phẩm khỏi danh sách yêu thích thành công",
        "deleted_product_id": product_id
    }