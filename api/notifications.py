from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models.models import Notification, User
from schemas.notification_schema import NotificationCreate


notifications_route = APIRouter(prefix="/api/notifications", tags=["notifications"])

def is_admin(user: User):
    return getattr(user, "role", "user") == "admin"


def notification_to_dict(notification: Notification):
    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "is_read": notification.is_read,
        "related_id": notification.related_id,
        "created_at": notification.created_at,
    }


def create_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        type: str = "system",
        related_id: int = None
):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        related_id=related_id
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


# =========================
# GET MY NOTIFICATIONS
# GET /api/notifications/
# =========================

@notifications_route.get("/")
def get_my_notifications(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.id.desc())
        .all()
    )

    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .count()
    )

    return {
        "message": "Lấy danh sách thông báo thành công",
        "data": [notification_to_dict(item) for item in notifications],
        "unread_count": unread_count
    }


# =========================
# GET UNREAD COUNT
# GET /api/notifications/unread-count
# =========================

@notifications_route.get("/unread-count")
def get_unread_count(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
        .count()
    )

    return {
        "message": "Lấy số thông báo chưa đọc thành công",
        "unread_count": unread_count
    }


# =========================
# ADMIN CREATE NOTIFICATION
# POST /api/notifications/
# =========================

@notifications_route.post("/")
def admin_create_notification(
        notification_data: NotificationCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Chỉ admin mới được tạo thông báo"
        )

    user = db.query(User).filter(User.id == notification_data.user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy user nhận thông báo"
        )

    notification = create_notification(
        db=db,
        user_id=notification_data.user_id,
        title=notification_data.title,
        message=notification_data.message,
        type=notification_data.type,
        related_id=notification_data.related_id
    )

    return {
        "message": "Tạo thông báo thành công",
        "data": notification_to_dict(notification)
    }


# =========================
# MARK ALL AS READ
# PATCH /api/notifications/read-all
# =========================

@notifications_route.patch("/read-all")
def mark_all_as_read(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({
        Notification.is_read: True
    })

    db.commit()

    return {
        "message": "Đã đánh dấu tất cả thông báo là đã đọc"
    }


# =========================
# MARK ONE AS READ
# PATCH /api/notifications/{notification_id}/read
# =========================

@notifications_route.patch("/{notification_id}/read")
def mark_notification_as_read(
        notification_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thông báo"
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return {
        "message": "Đã đánh dấu thông báo là đã đọc",
        "data": notification_to_dict(notification)
    }


# =========================
# DELETE NOTIFICATION
# DELETE /api/notifications/{notification_id}
# =========================

@notifications_route.delete("/{notification_id}")
def delete_notification(
        notification_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):

    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy thông báo"
        )

    db.delete(notification)
    db.commit()

    return {
        "message": "Xóa thông báo thành công",
        "deleted_notification_id": notification_id
    }