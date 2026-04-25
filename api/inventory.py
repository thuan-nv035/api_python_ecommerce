from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models.models import Products, Inventory
from schemas.inventory_schema import InventoryCreate, InventoryUpdate, InventoryAdjust


inventory_route = APIRouter(prefix="/api/inventory", tags=["inventory"])


def get_current_user_id(request: Request):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    return current_user_id


def inventory_to_dict(item: Inventory):
    return {
        "id": item.id,
        "product_id": item.product_id,
        "size": item.size,
        "color": item.color,
        "quantity": item.quantity,
        "sold": item.sold,
        "available": item.quantity - item.sold,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "product": {
            "id": item.product.id,
            "title": item.product.title,
            "img": item.product.img,
            "price": item.product.price
        } if item.product else None
    }


# =========================
# CREATE INVENTORY
# POST /api/inventory/
# =========================

@inventory_route.post("/")
def create_inventory(
        inventory_data: InventoryCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_current_user_id(request)

    product = db.query(Products).filter(Products.id == inventory_data.product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    existed_inventory = (
        db.query(Inventory)
        .filter(
            Inventory.product_id == inventory_data.product_id,
            Inventory.size == inventory_data.size,
            Inventory.color == inventory_data.color
        )
        .first()
    )

    if existed_inventory:
        raise HTTPException(
            status_code=400,
            detail="Tồn kho cho size/color này đã tồn tại"
        )

    new_inventory = Inventory(
        product_id=inventory_data.product_id,
        size=inventory_data.size,
        color=inventory_data.color,
        quantity=inventory_data.quantity,
        sold=0
    )

    db.add(new_inventory)
    db.commit()
    db.refresh(new_inventory)

    return {
        "message": "Tạo tồn kho thành công",
        "data": inventory_to_dict(new_inventory)
    }


# =========================
# GET ALL INVENTORY
# GET /api/inventory/
# =========================

@inventory_route.get("/")
def get_all_inventory(
        db: Session = Depends(get_db)
):
    inventory_items = (
        db.query(Inventory)
        .order_by(Inventory.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách tồn kho thành công",
        "data": [inventory_to_dict(item) for item in inventory_items]
    }


# =========================
# GET INVENTORY BY PRODUCT
# GET /api/inventory/product/{product_id}
# =========================

@inventory_route.get("/product/{product_id}")
def get_inventory_by_product(
        product_id: int,
        db: Session = Depends(get_db)
):
    product = db.query(Products).filter(Products.id == product_id).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy sản phẩm"
        )

    inventory_items = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .all()
    )

    total_quantity = sum(item.quantity for item in inventory_items)
    total_sold = sum(item.sold for item in inventory_items)

    return {
        "message": "Lấy tồn kho theo sản phẩm thành công",
        "data": [inventory_to_dict(item) for item in inventory_items],
        "summary": {
            "total_quantity": total_quantity,
            "total_sold": total_sold,
            "available": total_quantity - total_sold
        }
    }


# =========================
# UPDATE INVENTORY
# PUT /api/inventory/{inventory_id}
# =========================

@inventory_route.put("/{inventory_id}")
def update_inventory(
        inventory_id: int,
        inventory_data: InventoryUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_current_user_id(request)

    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tồn kho"
        )

    update_data = inventory_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    for key, value in update_data.items():
        setattr(inventory, key, value)

    db.commit()
    db.refresh(inventory)

    return {
        "message": "Cập nhật tồn kho thành công",
        "data": inventory_to_dict(inventory)
    }


# =========================
# ADD STOCK
# PATCH /api/inventory/{inventory_id}/add
# =========================

@inventory_route.patch("/{inventory_id}/add")
def add_stock(
        inventory_id: int,
        data: InventoryAdjust,
        request: Request,
        db: Session = Depends(get_db)
):
    get_current_user_id(request)

    if data.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Số lượng nhập thêm phải lớn hơn 0"
        )

    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tồn kho"
        )

    inventory.quantity += data.quantity

    db.commit()
    db.refresh(inventory)

    return {
        "message": "Nhập thêm kho thành công",
        "data": inventory_to_dict(inventory)
    }


# =========================
# DELETE INVENTORY
# DELETE /api/inventory/{inventory_id}
# =========================

@inventory_route.delete("/{inventory_id}")
def delete_inventory(
        inventory_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_current_user_id(request)

    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()

    if not inventory:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy tồn kho"
        )

    db.delete(inventory)
    db.commit()

    return {
        "message": "Xóa tồn kho thành công",
        "deleted_inventory_id": inventory_id
    }