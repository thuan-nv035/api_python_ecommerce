from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models.models import Products, CartItem, ProductVariant
from schemas.cart_schema import CartCreate, CartUpdate


cart_route = APIRouter(prefix="/api/cart", tags=["cart"])


def get_current_user_id(request: Request):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    return current_user_id


def cart_item_to_dict(item: CartItem):
    product = item.product
    variant = item.variant

    price = 0

    if variant and variant.price is not None:
        price = variant.price
    elif product and product.price is not None:
        price = product.price

    item_total = price * item.quantity

    return {
        "id": item.id,
        "user_id": item.user_id,
        "product_id": item.product_id,
        "variant_id": item.variant_id,
        "quantity": item.quantity,
        "price": price,
        "item_total": item_total,
        "product": {
            "id": product.id,
            "title": product.title,
            "desc": product.desc,
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
            "img": variant.img,
            "quantity": variant.quantity,
            "sold": variant.sold,
            "available": variant.quantity - variant.sold,
            "is_active": variant.is_active
        } if variant else None
    }


# =========================
# GET CART
# GET /api/cart/
# =========================

@cart_route.get("/")
def get_cart(
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = get_current_user_id(request)

    cart_items = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user_id)
        .order_by(CartItem.id.desc())
        .all()
    )

    data = [cart_item_to_dict(item) for item in cart_items]
    total_price = sum(item["item_total"] for item in data)
    total_quantity = sum(item["quantity"] for item in data)

    return {
        "message": "Lấy giỏ hàng thành công",
        "data": data,
        "total_items": len(data),
        "total_quantity": total_quantity,
        "total_price": total_price
    }


# =========================
# ADD TO CART
# POST /api/cart/add
# =========================

@cart_route.post("/add")
def add_to_cart(
        cart_data: CartCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = get_current_user_id(request)

    product = (
        db.query(Products)
        .filter(Products.id == cart_data.product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    variant = None

    if cart_data.variant_id is not None:
        variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.id == cart_data.variant_id,
                ProductVariant.product_id == cart_data.product_id
            )
            .first()
        )

        if not variant:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy biến thể sản phẩm"
            )

        if not variant.is_active:
            raise HTTPException(
                status_code=400,
                detail="Biến thể sản phẩm này đang bị tắt"
            )

        available = variant.quantity - variant.sold

        if available < cart_data.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Biến thể này chỉ còn {available} sản phẩm"
            )

    existing_item = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == current_user_id,
            CartItem.product_id == cart_data.product_id,
            CartItem.variant_id == cart_data.variant_id
        )
        .first()
    )

    if existing_item:
        new_quantity = existing_item.quantity + cart_data.quantity

        if variant:
            available = variant.quantity - variant.sold

            if available < new_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Biến thể này chỉ còn {available} sản phẩm"
                )

        existing_item.quantity = new_quantity

        db.commit()
        db.refresh(existing_item)

        return {
            "message": "Cập nhật số lượng sản phẩm trong giỏ hàng thành công",
            "data": cart_item_to_dict(existing_item)
        }

    new_item = CartItem(
        user_id=current_user_id,
        product_id=cart_data.product_id,
        variant_id=cart_data.variant_id,
        quantity=cart_data.quantity
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return {
        "message": "Thêm sản phẩm vào giỏ hàng thành công",
        "data": cart_item_to_dict(new_item)
    }


# =========================
# UPDATE CART ITEM
# PUT /api/cart/{cart_item_id}
# =========================

@cart_route.put("/{cart_item_id}")
@cart_route.patch("/{cart_item_id}")
def update_cart_item(
        cart_item_id: int,
        cart_data: CartUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = get_current_user_id(request)

    cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == current_user_id
        )
        .first()
    )

    if not cart_item:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm trong giỏ hàng"
        )

    if cart_item.variant_id:
        variant = (
            db.query(ProductVariant)
            .filter(ProductVariant.id == cart_item.variant_id)
            .first()
        )

        if not variant:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy biến thể sản phẩm"
            )

        available = variant.quantity - variant.sold

        if available < cart_data.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Biến thể này chỉ còn {available} sản phẩm"
            )

    cart_item.quantity = cart_data.quantity

    db.commit()
    db.refresh(cart_item)

    return {
        "message": "Cập nhật giỏ hàng thành công",
        "data": cart_item_to_dict(cart_item)
    }


# =========================
# DELETE CART ITEM
# DELETE /api/cart/{cart_item_id}
# =========================

@cart_route.delete("/{cart_item_id}")
def delete_cart_item(
        cart_item_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = get_current_user_id(request)

    cart_item = (
        db.query(CartItem)
        .filter(
            CartItem.id == cart_item_id,
            CartItem.user_id == current_user_id
        )
        .first()
    )

    if not cart_item:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm trong giỏ hàng"
        )

    db.delete(cart_item)
    db.commit()

    return {
        "message": "Xóa sản phẩm khỏi giỏ hàng thành công",
        "deleted_cart_item_id": cart_item_id
    }


# =========================
# CLEAR CART
# DELETE /api/cart/clear/all
# =========================

@cart_route.delete("/clear/all")
def clear_cart(
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = get_current_user_id(request)

    db.query(CartItem).filter(CartItem.user_id == current_user_id).delete()
    db.commit()

    return {
        "message": "Xóa toàn bộ giỏ hàng thành công"
    }