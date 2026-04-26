# Hàng tăng do nhập hàng
# Hàng giảm do bán hàng
# Hàng tăng do khách hoàn hàng
# Hàng thay đổi do admin chỉnh kho

import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from api.auth import get_admin_user, get_current_user
from database import get_db
from models.models import (
    User,
    Products,
    ProductVariant,
    Warehouse,
    Inventory,
    StockMovement
)
from schemas.stock_movement_schema import StockAdjustCreate


stock_movements_route = APIRouter(
    prefix="/api/stock-movements",
    tags=["stock-movements"]
)

def stock_movement_to_dict(movement: StockMovement):
    return {
        "id": movement.id,
        "warehouse_id": movement.warehouse_id,
        "product_id": movement.product_id,
        "variant_id": movement.variant_id,
        "movement_type": movement.movement_type,
        "quantity": movement.quantity,
        "before_quantity": movement.before_quantity,
        "after_quantity": movement.after_quantity,
        "reference_type": movement.reference_type,
        "reference_id": movement.reference_id,
        "note": movement.note,
        "created_by_id": movement.created_by_id,
        "created_at": movement.created_at,
        "warehouse": {
            "id": movement.warehouse.id,
            "name": movement.warehouse.name,
            "code": movement.warehouse.code
        } if movement.warehouse else None,
        "product": {
            "id": movement.product.id,
            "title": movement.product.title,
            "img": movement.product.img,
            "price": movement.product.price
        } if movement.product else None,
        "variant": {
            "id": movement.variant.id,
            "sku": movement.variant.sku,
            "size": movement.variant.size,
            "color": movement.variant.color,
            "price": movement.variant.price
        } if movement.variant else None,
        "created_by": {
            "id": movement.created_by.id,
            "username": movement.created_by.username,
            "role": getattr(movement.created_by, "role", "user")
        } if movement.created_by else None
    }


def get_or_create_inventory(
        db: Session,
        warehouse_id: int,
        product_id: int,
        variant_id: int = None
):
    inventory = (
        db.query(Inventory)
        .filter(
            Inventory.warehouse_id == warehouse_id,
            Inventory.product_id == product_id,
            Inventory.variant_id == variant_id
        )
        .first()
    )

    if inventory:
        return inventory

    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    variant = None

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
                detail="Không tìm thấy biến thể sản phẩm"
            )

    inventory = Inventory(
        warehouse_id=warehouse_id,
        product_id=product_id,
        variant_id=variant_id,
        size=variant.size if variant else None,
        color=variant.color if variant else None,
        quantity=0,
        sold=0
    )

    db.add(inventory)
    db.flush()

    return inventory


def create_stock_movement(
        db: Session,
        warehouse_id: int,
        product_id: int,
        variant_id: int,
        movement_type: str,
        quantity: int,
        reference_type: str = None,
        reference_id: int = None,
        note: str = None,
        created_by_id: int = None
):
    allowed_types = [
        "import",
        "export",
        "adjust",
        "return",
        "transfer"
    ]

    if movement_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Loại biến động kho không hợp lệ"
        )

    if warehouse_id:
        warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

        if not warehouse:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy kho hàng"
            )

    inventory = get_or_create_inventory(
        db=db,
        warehouse_id=warehouse_id,
        product_id=product_id,
        variant_id=variant_id
    )

    before_quantity = inventory.quantity
    after_quantity = before_quantity + quantity

    if after_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Tồn kho không đủ để xuất hoặc điều chỉnh giảm"
        )

    inventory.quantity = after_quantity

    movement = StockMovement(
        warehouse_id=warehouse_id,
        product_id=product_id,
        variant_id=variant_id,
        movement_type=movement_type,
        quantity=quantity,
        before_quantity=before_quantity,
        after_quantity=after_quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        created_by_id=created_by_id
    )

    db.add(movement)
    db.flush()

    return movement


# =========================
# GET ALL STOCK MOVEMENTS
# GET /api/stock-movements/
# =========================

@stock_movements_route.get("/")
def get_all_stock_movements(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        warehouse_id: int = Query(None),
        product_id: int = Query(None),
        variant_id: int = Query(None),
        movement_type: str = Query(None),
        reference_type: str = Query(None),
        reference_id: int = Query(None)
):
    get_admin_user(request)

    query = db.query(StockMovement)

    if warehouse_id:
        query = query.filter(StockMovement.warehouse_id == warehouse_id)

    if product_id:
        query = query.filter(StockMovement.product_id == product_id)

    if variant_id:
        query = query.filter(StockMovement.variant_id == variant_id)

    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)

    if reference_type:
        query = query.filter(StockMovement.reference_type == reference_type)

    if reference_id:
        query = query.filter(StockMovement.reference_id == reference_id)

    total = query.count()

    movements = (
        query
        .order_by(StockMovement.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy lịch sử biến động kho thành công",
        "data": [stock_movement_to_dict(item) for item in movements],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET MOVEMENTS BY PRODUCT
# GET /api/stock-movements/product/{product_id}
# =========================

@stock_movements_route.get("/product/{product_id}")
def get_stock_movements_by_product(
        product_id: int,
        request: Request,
        db: Session = Depends(get_db),
        variant_id: int = Query(None),
        warehouse_id: int = Query(None)
):
    get_admin_user(request)

    query = db.query(StockMovement).filter(
        StockMovement.product_id == product_id
    )

    if variant_id:
        query = query.filter(StockMovement.variant_id == variant_id)

    if warehouse_id:
        query = query.filter(StockMovement.warehouse_id == warehouse_id)

    movements = (
        query
        .order_by(StockMovement.id.desc())
        .all()
    )

    return {
        "message": "Lấy lịch sử kho theo sản phẩm thành công",
        "data": [stock_movement_to_dict(item) for item in movements]
    }


# =========================
# MANUAL STOCK ADJUST
# POST /api/stock-movements/adjust
# Admin chỉnh kho thủ công
# =========================

@stock_movements_route.post("/adjust")
def adjust_stock(
        adjust_data: StockAdjustCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    get_admin_user(request)

    if adjust_data.quantity == 0:
        raise HTTPException(
            status_code=400,
            detail="Số lượng điều chỉnh không được bằng 0"
        )

    movement = create_stock_movement(
        db=db,
        warehouse_id=adjust_data.warehouse_id,
        product_id=adjust_data.product_id,
        variant_id=adjust_data.variant_id,
        movement_type="adjust",
        quantity=adjust_data.quantity,
        reference_type="manual_adjust",
        reference_id=None,
        note=adjust_data.note,
        created_by_id=current_user.id
    )

    db.commit()
    db.refresh(movement)

    return {
        "message": "Điều chỉnh tồn kho thành công",
        "data": stock_movement_to_dict(movement)
    }


# =========================
# GET INVENTORY BY WAREHOUSE
# GET /api/stock-movements/inventory
# =========================

@stock_movements_route.get("/inventory")
def get_inventory_summary(
        request: Request,
        db: Session = Depends(get_db),
        warehouse_id: int = Query(None),
        product_id: int = Query(None),
        variant_id: int = Query(None)
):
    get_admin_user(request)

    query = db.query(Inventory)

    if warehouse_id:
        query = query.filter(Inventory.warehouse_id == warehouse_id)

    if product_id:
        query = query.filter(Inventory.product_id == product_id)

    if variant_id:
        query = query.filter(Inventory.variant_id == variant_id)

    inventories = query.order_by(Inventory.id.desc()).all()

    data = []

    for item in inventories:
        data.append({
            "id": item.id,
            "warehouse_id": item.warehouse_id,
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "size": item.size,
            "color": item.color,
            "quantity": item.quantity,
            "sold": item.sold,
            "available": item.quantity - item.sold,
            "warehouse": {
                "id": item.warehouse.id,
                "name": item.warehouse.name,
                "code": item.warehouse.code
            } if item.warehouse else None,
            "product": {
                "id": item.product.id,
                "title": item.product.title,
                "img": item.product.img,
                "price": item.product.price
            } if item.product else None,
            "variant": {
                "id": item.variant.id,
                "sku": item.variant.sku,
                "size": item.variant.size,
                "color": item.variant.color,
                "price": item.variant.price
            } if item.variant else None
        })

    return {
        "message": "Lấy tồn kho thành công",
        "data": data
    }