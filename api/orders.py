from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.coupons import validate_coupon
from database import get_db
from models.models import Products, CartItem, Order, OrderItem, CouponUsage, ProductVariant
from schemas.order_schema import CheckoutSchema, UpdateOrderStatusSchema
from models.models import Inventory

orders_route = APIRouter(prefix="/api/orders", tags=["orders"])


def order_to_dict(order: Order):
    return {
        "id": order.id,
        "user_id": order.user_id,
        "full_name": order.full_name,
        "phone": order.phone,
        "address": order.address,
        "note": order.note,
        "total_price": order.total_price,
        "payment_method": order.payment_method,
        "status": order.status,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "quantity": item.quantity,
                "price": item.price,
                "total_price": item.total_price,
                "product_title": item.product_title,
                "product_img": item.product_img,
                "variant_sku": item.variant_sku,
                "variant_size": item.variant_size,
                "variant_color": item.variant_color,
            }
            for item in order.items
        ]
    }


# =========================
# CHECKOUT
# POST /api/orders/checkout
# =========================

@orders_route.post("/checkout")
def checkout(
        checkout_data: CheckoutSchema,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    cart_items = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user_id)
        .all()
    )

    if not cart_items:
        raise HTTPException(
            status_code=400,
            detail="Giỏ hàng đang trống"
        )

    total_price = 0

    for cart_item in cart_items:
        product = db.query(Products).filter(Products.id == cart_item.product_id).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Sản phẩm id {cart_item.product_id} không tồn tại"
            )

        inventory = (
            db.query(Inventory)
            .filter(Inventory.product_id == cart_item.product_id)
            .first()
        )

        if inventory:
            available = inventory.quantity - inventory.sold

            if available < cart_item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm {product.title} không đủ tồn kho"
                )
        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Sản phẩm id {cart_item.product_id} không tồn tại"
            )

        if cart_item.variant_id:
            variant = (
                db.query(ProductVariant)
                .filter(
                    ProductVariant.id == cart_item.variant_id,
                    ProductVariant.product_id == cart_item.product_id
                )
                .first()
            )

            if not variant:
                raise HTTPException(
                    status_code=404,
                    detail=f"Biến thể của sản phẩm {product.title} không tồn tại"
                )

            if not variant.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Biến thể của sản phẩm {product.title} đang bị tắt"
                )

            available = variant.quantity - variant.sold

            if available < cart_item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Sản phẩm {product.title} - {variant.size}/{variant.color} chỉ còn {available}"
                )

            item_price = variant.price if variant.price is not None else product.price or 0

        else:
            item_price = product.price or 0

        total_price += item_price * cart_item.quantity

    subtotal = total_price
    discount_amount = 0
    coupon_code = None
    coupon = None

    if checkout_data.coupon_code:
        coupon_result = validate_coupon(
            db=db,
            user_id=current_user_id,
            code=checkout_data.coupon_code,
            order_total=subtotal
        )

        coupon = coupon_result["coupon"]
        discount_amount = coupon_result["discount_amount"]
        coupon_code = coupon.code
        total_price = coupon_result["final_total"]

    new_order = Order(
        user_id=current_user_id,
        full_name=checkout_data.full_name,
        phone=checkout_data.phone,
        address=checkout_data.address,
        note=checkout_data.note,
        payment_method=checkout_data.payment_method,
        status="pending",
        total_price=total_price,
        subtotal = subtotal,
        discount_amount = discount_amount,
        coupon_code = coupon_code,
    )

    if coupon:
        coupon_usage = CouponUsage(
            coupon_id=coupon.id,
            user_id=current_user_id,
            order_id=new_order.id
        )

        coupon.used_count = (coupon.used_count or 0) + 1

        db.add(coupon_usage)

    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    for cart_item in cart_items:
        product = db.query(Products).filter(Products.id == cart_item.product_id).first()

        variant = None

        if cart_item.variant_id:
            variant = (
                db.query(ProductVariant)
                .filter(ProductVariant.id == cart_item.variant_id)
                .first()
            )

        if variant:
            item_price = variant.price if variant.price is not None else product.price or 0
            product_img = variant.img if variant.img else product.img

            variant.sold += cart_item.quantity

            variant_sku = variant.sku
            variant_size = variant.size
            variant_color = variant.color

        else:
            item_price = product.price or 0
            product_img = product.img

            variant_sku = None
            variant_size = None
            variant_color = None

        item_total = item_price * cart_item.quantity
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            variant_id=cart_item.variant_id,
            quantity=cart_item.quantity,
            price=item_price,
            total_price=item_total,
            product_title=product.title,
            product_img=product_img,
            variant_sku=variant_sku,
            variant_size=variant_size,
            variant_color=variant_color
        )

        db.add(order_item)

    # Xóa giỏ hàng sau khi checkout
    for cart_item in cart_items:
        db.delete(cart_item)

    db.commit()
    db.refresh(new_order)

    return {
        "message": "Đặt hàng thành công",
        "data": order_to_dict(new_order)
    }


# =========================
# GET MY ORDERS
# GET /api/orders/
# =========================

@orders_route.get("/")
def get_my_orders(
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    orders = (
        db.query(Order)
        .filter(Order.user_id == current_user_id)
        .order_by(Order.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách đơn hàng thành công",
        "data": [order_to_dict(order) for order in orders]
    }


# =========================
# GET ORDER BY ID
# GET /api/orders/{order_id}
# =========================

@orders_route.get("/{order_id}")
def get_order_by_id(
        order_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.user_id == current_user_id
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng"
        )

    return {
        "message": "Lấy chi tiết đơn hàng thành công",
        "data": order_to_dict(order)
    }


# =========================
# CANCEL ORDER
# PATCH /api/orders/{order_id}/cancel
# =========================

@orders_route.patch("/{order_id}/cancel")
def cancel_order(
        order_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.user_id == current_user_id
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng"
        )

    if order.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail="Không thể hủy đơn hàng ở trạng thái hiện tại"
        )

    order.status = "cancelled"

    db.commit()
    db.refresh(order)

    return {
        "message": "Hủy đơn hàng thành công",
        "data": order_to_dict(order)
    }


# =========================
# UPDATE ORDER STATUS
# PATCH /api/orders/{order_id}/status
# =========================

@orders_route.patch("/{order_id}/status")
def update_order_status(
        order_id: int,
        status_data: UpdateOrderStatusSchema,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    allowed_status = [
        "pending",
        "confirmed",
        "shipping",
        "completed",
        "cancelled"
    ]

    if status_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái đơn hàng không hợp lệ"
        )

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn hàng"
        )

    order.status = status_data.status

    db.commit()
    db.refresh(order)

    return {
        "message": "Cập nhật trạng thái đơn hàng thành công",
        "data": order_to_dict(order)
    }