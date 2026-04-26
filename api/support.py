import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from api.auth import get_current_user, get_admin_user
from database import get_db
from models.models import SupportTicket, User, Order
from schemas.support_schema import SupportTicketCreate, SupportTicketStatusUpdate


support_route = APIRouter(prefix="/api/support", tags=["support"])


def get_current_user_optional(request: Request, db: Session):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        return None

    return db.query(User).filter(User.id == current_user_id).first()

def ticket_to_dict(ticket: SupportTicket):
    return {
        "id": ticket.id,
        "user_id": ticket.user_id,
        "order_id": ticket.order_id,
        "full_name": ticket.full_name,
        "email": ticket.email,
        "phone": ticket.phone,
        "subject": ticket.subject,
        "message": ticket.message,
        "status": ticket.status,
        "admin_reply": ticket.admin_reply,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "user": {
            "id": ticket.user.id,
            "username": ticket.user.username,
            "avatar": ticket.user.avatar,
        } if ticket.user else None
    }


# =========================
# CREATE SUPPORT TICKET
# POST /api/support/
# User đăng nhập hoặc khách đều có thể gửi
# =========================

@support_route.post("/")
def create_support_ticket(
        ticket_data: SupportTicketCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user_optional(request, db)

    if ticket_data.order_id:
        order = db.query(Order).filter(Order.id == ticket_data.order_id).first()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy đơn hàng"
            )

        if current_user and order.user_id != current_user.id and getattr(current_user, "role", "user") != "admin":
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền gửi hỗ trợ cho đơn hàng này"
            )

    new_ticket = SupportTicket(
        user_id=current_user.id if current_user else None,
        order_id=ticket_data.order_id,
        full_name=ticket_data.full_name,
        email=ticket_data.email,
        phone=ticket_data.phone,
        subject=ticket_data.subject,
        message=ticket_data.message,
        status="pending"
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return {
        "message": "Gửi yêu cầu hỗ trợ thành công",
        "data": ticket_to_dict(new_ticket)
    }


# =========================
# GET MY SUPPORT TICKETS
# GET /api/support/my
# =========================

@support_route.get("/my")
def get_my_support_tickets(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    tickets = (
        db.query(SupportTicket)
        .filter(SupportTicket.user_id == current_user.id)
        .order_by(SupportTicket.id.desc())
        .all()
    )

    return {
        "message": "Lấy yêu cầu hỗ trợ của tôi thành công",
        "data": [ticket_to_dict(ticket) for ticket in tickets]
    }


# =========================
# GET ALL SUPPORT TICKETS
# GET /api/support/
# Admin
# =========================

@support_route.get("/")
def get_all_support_tickets(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        status: str = Query(None)
):
    get_admin_user(request)

    query = db.query(SupportTicket)

    if status:
        query = query.filter(SupportTicket.status == status)

    total = query.count()

    tickets = (
        query
        .order_by(SupportTicket.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách yêu cầu hỗ trợ thành công",
        "data": [ticket_to_dict(ticket) for ticket in tickets],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET SUPPORT TICKET BY ID
# GET /api/support/{ticket_id}
# Admin hoặc owner
# =========================

@support_route.get("/{ticket_id}")
def get_support_ticket_by_id(
        ticket_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy yêu cầu hỗ trợ"
        )

    is_owner = ticket.user_id == current_user.id
    is_admin = getattr(current_user, "role", "user") == "admin"

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem yêu cầu này"
        )

    return {
        "message": "Lấy chi tiết yêu cầu hỗ trợ thành công",
        "data": ticket_to_dict(ticket)
    }


# =========================
# UPDATE SUPPORT STATUS
# PATCH /api/support/{ticket_id}/status
# Admin
# =========================

@support_route.patch("/{ticket_id}/status")
def update_support_ticket_status(
        ticket_id: int,
        status_data: SupportTicketStatusUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    allowed_status = [
        "pending",
        "processing",
        "resolved",
        "rejected"
    ]

    if status_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái hỗ trợ không hợp lệ"
        )

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy yêu cầu hỗ trợ"
        )

    ticket.status = status_data.status

    if status_data.admin_reply is not None:
        ticket.admin_reply = status_data.admin_reply

    db.commit()
    db.refresh(ticket)

    return {
        "message": "Cập nhật yêu cầu hỗ trợ thành công",
        "data": ticket_to_dict(ticket)
    }


# =========================
# DELETE SUPPORT TICKET
# DELETE /api/support/{ticket_id}
# Admin hoặc owner
# =========================

@support_route.delete("/{ticket_id}")
def delete_support_ticket(
        ticket_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy yêu cầu hỗ trợ"
        )

    is_owner = ticket.user_id == current_user.id
    is_admin = getattr(current_user, "role", "user") == "admin"

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xóa yêu cầu này"
        )

    db.delete(ticket)
    db.commit()

    return {
        "message": "Xóa yêu cầu hỗ trợ thành công",
        "deleted_ticket_id": ticket_id
    }