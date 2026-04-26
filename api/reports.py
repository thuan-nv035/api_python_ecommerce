from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.auth import get_admin_user
from database import get_db
from models.models import User, Products, Order, OrderItem, Payment, Review

reports_route = APIRouter(prefix="/api/reports", tags=["reports"])

def parse_date(date_str: Optional[str]):
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Ngày phải có định dạng YYYY-MM-DD"
        )


def apply_date_filter(query, model, start_date: Optional[datetime], end_date: Optional[datetime]):
    if start_date:
        query = query.filter(model.created_at >= start_date)

    if end_date:
        # Cộng thêm 1 ngày để lấy hết dữ liệu của end_date
        query = query.filter(model.created_at < end_date + timedelta(days=1))

    return query


# =========================
# OVERVIEW REPORT
# GET /api/reports/overview
# =========================

@reports_route.get("/overview")
def get_overview_report(
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    total_users = db.query(User).count()
    total_products = db.query(Products).count()
    total_orders = db.query(Order).count()
    total_reviews = db.query(Review).count()

    pending_orders = db.query(Order).filter(Order.status == "pending").count()
    confirmed_orders = db.query(Order).filter(Order.status == "confirmed").count()
    shipping_orders = db.query(Order).filter(Order.status == "shipping").count()
    completed_orders = db.query(Order).filter(Order.status == "completed").count()
    cancelled_orders = db.query(Order).filter(Order.status == "cancelled").count()

    total_revenue = (
        db.query(func.sum(Order.total_price))
        .filter(Order.status.in_(["confirmed", "shipping", "completed"]))
        .scalar()
    ) or 0

    paid_revenue = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.payment_status == "paid")
        .scalar()
    ) or 0

    today = datetime.now().date()

    today_orders = (
        db.query(Order)
        .filter(func.date(Order.created_at) == today)
        .count()
    )

    today_revenue = (
        db.query(func.sum(Order.total_price))
        .filter(
            func.date(Order.created_at) == today,
            Order.status.in_(["confirmed", "shipping", "completed"])
        )
        .scalar()
    ) or 0

    return {
        "message": "Lấy báo cáo tổng quan thành công",
        "data": {
            "total_users": total_users,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_reviews": total_reviews,
            "orders": {
                "pending": pending_orders,
                "confirmed": confirmed_orders,
                "shipping": shipping_orders,
                "completed": completed_orders,
                "cancelled": cancelled_orders
            },
            "revenue": {
                "total_revenue": total_revenue,
                "paid_revenue": paid_revenue,
                "today_revenue": today_revenue
            },
            "today": {
                "orders": today_orders
            }
        }
    }


# =========================
# REVENUE REPORT
# GET /api/reports/revenue?start_date=2026-01-01&end_date=2026-01-31
# =========================

@reports_route.get("/revenue")
def get_revenue_report(
        request: Request,
        db: Session = Depends(get_db),
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None)
):
    get_admin_user(request)

    start = parse_date(start_date)
    end = parse_date(end_date)

    query = (
        db.query(
            func.date(Order.created_at).label("date"),
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_price).label("total_revenue")
        )
        .filter(Order.status.in_(["confirmed", "shipping", "completed"]))
    )

    query = apply_date_filter(query, Order, start, end)

    rows = (
        query
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at).asc())
        .all()
    )

    total_revenue = sum(float(row.total_revenue or 0) for row in rows)
    total_orders = sum(int(row.total_orders or 0) for row in rows)

    data = []

    for row in rows:
        data.append({
            "date": str(row.date),
            "total_orders": int(row.total_orders or 0),
            "total_revenue": float(row.total_revenue or 0)
        })

    return {
        "message": "Lấy báo cáo doanh thu thành công",
        "data": data,
        "summary": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "start_date": start_date,
            "end_date": end_date
        }
    }


# =========================
# TOP PRODUCTS REPORT
# GET /api/reports/top-products?limit=10
# =========================

@reports_route.get("/top-products")
def get_top_products_report(
        request: Request,
        db: Session = Depends(get_db),
        limit: int = Query(10, gt=0),
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None)
):
    get_admin_user(request)

    start = parse_date(start_date)
    end = parse_date(end_date)

    query = (
        db.query(
            OrderItem.product_id,
            OrderItem.product_title,
            func.sum(OrderItem.quantity).label("sold_quantity"),
            func.sum(OrderItem.total_price).label("revenue")
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status.in_(["confirmed", "shipping", "completed"]))
    )

    query = apply_date_filter(query, Order, start, end)

    rows = (
        query
        .group_by(OrderItem.product_id, OrderItem.product_title)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )

    data = []

    for row in rows:
        product = db.query(Products).filter(Products.id == row.product_id).first()

        data.append({
            "product_id": row.product_id,
            "product_title": row.product_title,
            "product_img": product.img if product else None,
            "price": product.price if product else None,
            "sold_quantity": int(row.sold_quantity or 0),
            "revenue": float(row.revenue or 0)
        })

    return {
        "message": "Lấy báo cáo sản phẩm bán chạy thành công",
        "data": data
    }


# =========================
# ORDER STATUS REPORT
# GET /api/reports/order-status
# =========================

@reports_route.get("/order-status")
def get_order_status_report(
        request: Request,
        db: Session = Depends(get_db),
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None)
):
    get_admin_user(request)

    start = parse_date(start_date)
    end = parse_date(end_date)

    query = (
        db.query(
            Order.status,
            func.count(Order.id).label("count")
        )
    )

    query = apply_date_filter(query, Order, start, end)

    rows = (
        query
        .group_by(Order.status)
        .all()
    )

    data = []

    total = 0

    for row in rows:
        count = int(row.count or 0)
        total += count

        data.append({
            "status": row.status,
            "count": count
        })

    return {
        "message": "Lấy báo cáo trạng thái đơn hàng thành công",
        "data": data,
        "total": total
    }