import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth import get_admin_user, get_current_user
from api.stock_movements import create_stock_movement
from database import get_db
from models.models import (
    User,
    Supplier,
    Warehouse,
    Products,
    ProductVariant,
    Inventory,
    PurchaseOrder,
    PurchaseOrderItem
)
from schemas.purchase_order_schema import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
    PurchaseOrderReceive
)

purchase_orders_route = APIRouter(
    prefix="/api/purchase-orders",
    tags=["purchase-orders"]
)

# Admin tạo đơn nhập hàng
# → Chọn supplier
# → Chọn warehouse
# → Thêm sản phẩm / biến thể
# → Submit đơn nhập
# → Nhận hàng
# → Tự tăng tồn kho

def generate_purchase_order_code():
    return f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


def purchase_order_item_to_dict(item: PurchaseOrderItem):
    product = item.product
    variant = item.variant

    return {
        "id": item.id,
        "purchase_order_id": item.purchase_order_id,
        "product_id": item.product_id,
        "variant_id": item.variant_id,
        "quantity": item.quantity,
        "received_quantity": item.received_quantity,
        "remaining_quantity": item.quantity - item.received_quantity,
        "unit_cost": item.unit_cost,
        "total_cost": item.total_cost,
        "note": item.note,
        "created_at": item.created_at,
        "product": {
            "id": product.id,
            "title": product.title,
            "img": product.img,
            "price": product.price
        } if product else None,
        "variant": {
            "id": variant.id,
            "sku": variant.sku,
            "size": variant.size,
            "color": variant.color,
            "price": variant.price,
            "quantity": variant.quantity,
            "sold": variant.sold
        } if variant else None
    }


def purchase_order_to_dict(po: PurchaseOrder):
    return {
        "id": po.id,
        "code": po.code,
        "supplier_id": po.supplier_id,
        "warehouse_id": po.warehouse_id,
        "status": po.status,
        "order_date": po.order_date,
        "expected_date": po.expected_date,
        "subtotal": po.subtotal,
        "tax_amount": po.tax_amount,
        "shipping_fee": po.shipping_fee,
        "discount_amount": po.discount_amount,
        "total_amount": po.total_amount,
        "note": po.note,
        "created_by_id": po.created_by_id,
        "confirmed_by_id": po.confirmed_by_id,
        "received_at": po.received_at,
        "cancelled_at": po.cancelled_at,
        "created_at": po.created_at,
        "updated_at": po.updated_at,
        "supplier": {
            "id": po.supplier.id,
            "name": po.supplier.name,
            "code": po.supplier.code,
            "phone": po.supplier.phone
        } if po.supplier else None,
        "warehouse": {
            "id": po.warehouse.id,
            "name": po.warehouse.name,
            "code": po.warehouse.code
        } if po.warehouse else None,
        "items": [
            purchase_order_item_to_dict(item)
            for item in po.items
        ]
    }


def recalculate_purchase_order(po: PurchaseOrder):
    subtotal = 0

    for item in po.items:
        item.total_cost = item.quantity * item.unit_cost
        subtotal += item.total_cost

    po.subtotal = subtotal
    po.total_amount = (
        subtotal
        + (po.tax_amount or 0)
        + (po.shipping_fee or 0)
        - (po.discount_amount or 0)
    )

    if po.total_amount < 0:
        po.total_amount = 0


def increase_stock_from_purchase_item(
        db: Session,
        item: PurchaseOrderItem,
        quantity: int
):
    if item.variant_id:
        variant = (
            db.query(ProductVariant)
            .filter(ProductVariant.id == item.variant_id)
            .first()
        )

        if not variant:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy biến thể id {item.variant_id}"
            )

        variant.quantity += quantity

    else:
        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.product_id == item.product_id,
                Inventory.size == None,
                Inventory.color == None
            )
            .first()
        )

        if inventory:
            inventory.quantity += quantity
        else:
            inventory = Inventory(
                product_id=item.product_id,
                size=None,
                color=None,
                quantity=quantity,
                sold=0
            )
            db.add(inventory)


def validate_supplier_and_warehouse(
        db: Session,
        supplier_id: int,
        warehouse_id: int
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nhà cung cấp"
        )

    if supplier.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Nhà cung cấp đang không hoạt động"
        )

    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

    if not warehouse:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy kho hàng"
        )

    if not warehouse.is_active:
        raise HTTPException(
            status_code=400,
            detail="Kho hàng đang không hoạt động"
        )


def validate_product_and_variant(
        db: Session,
        product_id: int,
        variant_id: int = None
):
    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy sản phẩm id {product_id}"
        )

    if variant_id:
        variant = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.id == variant_id,
                ProductVariant.product_id == product_id
            )
            .first()
        )

        if not variant:
            raise HTTPException(
                status_code=404,
                detail=f"Không tìm thấy biến thể id {variant_id} của sản phẩm id {product_id}"
            )


# =========================
# CREATE PURCHASE ORDER
# POST /api/purchase-orders/
# =========================

@purchase_orders_route.post("/")
def create_purchase_order(
        po_data: PurchaseOrderCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    get_admin_user(request)

    if not po_data.items:
        raise HTTPException(
            status_code=400,
            detail="Đơn nhập hàng phải có ít nhất một sản phẩm"
        )

    validate_supplier_and_warehouse(
        db=db,
        supplier_id=po_data.supplier_id,
        warehouse_id=po_data.warehouse_id
    )

    code = po_data.code.strip().upper() if po_data.code else generate_purchase_order_code()

    existed_po = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.code == code)
        .first()
    )

    if existed_po:
        raise HTTPException(
            status_code=400,
            detail="Mã đơn nhập hàng đã tồn tại"
        )

    new_po = PurchaseOrder(
        code=code,
        supplier_id=po_data.supplier_id,
        warehouse_id=po_data.warehouse_id,
        status="draft",
        expected_date=po_data.expected_date,
        tax_amount=po_data.tax_amount or 0,
        shipping_fee=po_data.shipping_fee or 0,
        discount_amount=po_data.discount_amount or 0,
        note=po_data.note,
        created_by_id=current_user.id
    )

    db.add(new_po)
    db.commit()
    db.refresh(new_po)

    for item_data in po_data.items:
        validate_product_and_variant(
            db=db,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id
        )

        item = PurchaseOrderItem(
            purchase_order_id=new_po.id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            quantity=item_data.quantity,
            received_quantity=0,
            unit_cost=item_data.unit_cost,
            total_cost=item_data.quantity * item_data.unit_cost,
            note=item_data.note
        )

        db.add(item)

    db.commit()
    db.refresh(new_po)

    recalculate_purchase_order(new_po)

    db.commit()
    db.refresh(new_po)

    return {
        "message": "Tạo đơn nhập hàng thành công",
        "data": purchase_order_to_dict(new_po)
    }


# =========================
# GET ALL PURCHASE ORDERS
# GET /api/purchase-orders/
# =========================

@purchase_orders_route.get("/")
def get_all_purchase_orders(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        status: str = Query(None),
        supplier_id: int = Query(None),
        warehouse_id: int = Query(None),
):
    get_admin_user(request)

    query = db.query(PurchaseOrder)

    if search:
        query = query.filter(
            or_(
                PurchaseOrder.code.ilike(f"%{search}%"),
                PurchaseOrder.note.ilike(f"%{search}%")
            )
        )

    if status:
        query = query.filter(PurchaseOrder.status == status)

    if supplier_id:
        query = query.filter(PurchaseOrder.supplier_id == supplier_id)

    if warehouse_id:
        query = query.filter(PurchaseOrder.warehouse_id == warehouse_id)

    total = query.count()

    purchase_orders = (
        query
        .order_by(PurchaseOrder.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách đơn nhập hàng thành công",
        "data": [purchase_order_to_dict(po) for po in purchase_orders],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET PURCHASE ORDER BY ID
# GET /api/purchase-orders/{po_id}
# =========================

@purchase_orders_route.get("/{po_id}")
def get_purchase_order_by_id(
        po_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn nhập hàng"
        )

    return {
        "message": "Lấy chi tiết đơn nhập hàng thành công",
        "data": purchase_order_to_dict(po)
    }


# =========================
# UPDATE PURCHASE ORDER
# PATCH /api/purchase-orders/{po_id}
# Chỉ sửa khi còn draft
# =========================

@purchase_orders_route.patch("/{po_id}")
@purchase_orders_route.put("/{po_id}")
def update_purchase_order(
        po_id: int,
        po_data: PurchaseOrderUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn nhập hàng"
        )

    if po.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể sửa đơn nhập hàng khi còn draft"
        )

    update_data = po_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    new_supplier_id = update_data.get("supplier_id", po.supplier_id)
    new_warehouse_id = update_data.get("warehouse_id", po.warehouse_id)

    validate_supplier_and_warehouse(
        db=db,
        supplier_id=new_supplier_id,
        warehouse_id=new_warehouse_id
    )

    for key, value in update_data.items():
        setattr(po, key, value)

    recalculate_purchase_order(po)

    db.commit()
    db.refresh(po)

    return {
        "message": "Cập nhật đơn nhập hàng thành công",
        "data": purchase_order_to_dict(po)
    }


# =========================
# SUBMIT PURCHASE ORDER
# PATCH /api/purchase-orders/{po_id}/submit
# draft -> pending
# =========================

@purchase_orders_route.patch("/{po_id}/submit")
def submit_purchase_order(
        po_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    get_admin_user(request)

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn nhập hàng"
        )

    if po.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể submit đơn đang draft"
        )

    if not po.items:
        raise HTTPException(
            status_code=400,
            detail="Đơn nhập hàng chưa có sản phẩm"
        )

    po.status = "pending"
    po.confirmed_by_id = current_user.id

    db.commit()
    db.refresh(po)

    return {
        "message": "Submit đơn nhập hàng thành công",
        "data": purchase_order_to_dict(po)
    }


# =========================
# RECEIVE PURCHASE ORDER
# PATCH /api/purchase-orders/{po_id}/receive
# Nhận hàng và tăng tồn kho
# =========================

@purchase_orders_route.patch("/{po_id}/receive")
def receive_purchase_order(
        po_id: int,
        receive_data: PurchaseOrderReceive,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    get_admin_user(request)

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn nhập hàng"
        )

    if po.status not in ["pending", "partial_received"]:
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể nhận hàng khi đơn đang pending hoặc partial_received"
        )

    if receive_data.items:
        for receive_item in receive_data.items:
            item = (
                db.query(PurchaseOrderItem)
                .filter(
                    PurchaseOrderItem.id == receive_item.item_id,
                    PurchaseOrderItem.purchase_order_id == po.id
                )
                .first()
            )

            if not item:
                raise HTTPException(
                    status_code=404,
                    detail=f"Không tìm thấy item id {receive_item.item_id}"
                )

            remaining = item.quantity - item.received_quantity

            if receive_item.received_quantity > remaining:
                raise HTTPException(
                    status_code=400,
                    detail=f"Số lượng nhận vượt quá số lượng còn lại của item id {item.id}"
                )

            item.received_quantity += receive_item.received_quantity

            create_stock_movement(
                db=db,
                warehouse_id=po.warehouse_id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                movement_type="import",
                quantity=receive_item.received_quantity,
                reference_type="purchase_order",
                reference_id=po.id,
                note=f"Nhập hàng từ đơn {po.code}",
                created_by_id=current_user.id
            )

    else:
        # Nếu không truyền items thì nhận toàn bộ số lượng còn lại
        for item in po.items:
            remaining = item.quantity - item.received_quantity

            if remaining > 0:
                item.received_quantity += remaining

                increase_stock_from_purchase_item(
                    db=db,
                    item=item,
                    quantity=remaining
                )

    all_received = all(
        item.received_quantity >= item.quantity
        for item in po.items
    )

    po.status = "received" if all_received else "partial_received"

    if po.status == "received":
        po.received_at = datetime.utcnow()

    if receive_data.note:
        po.note = receive_data.note

    db.commit()
    db.refresh(po)

    return {
        "message": "Nhận hàng thành công",
        "data": purchase_order_to_dict(po)
    }


# =========================
# CANCEL PURCHASE ORDER
# PATCH /api/purchase-orders/{po_id}/cancel
# =========================

@purchase_orders_route.patch("/{po_id}/cancel")
def cancel_purchase_order(
        po_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn nhập hàng"
        )

    if po.status in ["received", "partial_received"]:
        raise HTTPException(
            status_code=400,
            detail="Không thể hủy đơn đã nhận hàng"
        )

    if po.status == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="Đơn nhập hàng đã bị hủy trước đó"
        )

    po.status = "cancelled"
    po.cancelled_at = datetime.utcnow()

    db.commit()
    db.refresh(po)

    return {
        "message": "Hủy đơn nhập hàng thành công",
        "data": purchase_order_to_dict(po)
    }


# =========================
# DELETE PURCHASE ORDER
# DELETE /api/purchase-orders/{po_id}
# Chỉ xóa khi draft
# =========================

@purchase_orders_route.delete("/{po_id}")
def delete_purchase_order(
        po_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    if not po:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy đơn nhập hàng"
        )

    if po.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Chỉ có thể xóa đơn nhập hàng khi còn draft"
        )

    db.delete(po)
    db.commit()

    return {
        "message": "Xóa đơn nhập hàng thành công",
        "deleted_purchase_order_id": po_id
    }