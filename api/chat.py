import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db
from models.models import User, ChatRoom, ChatMessage
from schemas.chat_schema import (
    ChatRoomCreate,
    ChatMessageCreate,
    ChatRoomStatusUpdate,
    ChatAssignAdmin
)


# User gửi tin nhắn hỗ trợ
# Admin xem danh sách cuộc trò chuyện
# Admin trả lời user
# User xem lại cuộc trò chuyện
# Đánh dấu đã đọc
# Đóng/mở cuộc trò chuyện

chat_route = APIRouter(prefix="/api/chat", tags=["chat"])


def get_current_user(request: Request, db: Session):
    current_user_id = getattr(request.state, "current_user_id", None)

    if current_user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    user = db.query(User).filter(User.id == current_user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy user"
        )

    return user


def is_admin(user: User):
    return getattr(user, "role", "user") == "admin"


def check_admin(user: User):
    if not is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền admin"
        )


def message_to_dict(message: ChatMessage):
    return {
        "id": message.id,
        "room_id": message.room_id,
        "sender_id": message.sender_id,
        "sender_type": message.sender_type,
        "message": message.message,
        "attachments": message.attachments or [],
        "is_read_by_user": message.is_read_by_user,
        "is_read_by_admin": message.is_read_by_admin,
        "created_at": message.created_at,
        "sender": {
            "id": message.sender.id,
            "username": message.sender.username,
            "avatar": message.sender.avatar,
            "role": getattr(message.sender, "role", "user")
        } if message.sender else None
    }


def room_to_dict(room: ChatRoom, include_messages: bool = False):
    data = {
        "id": room.id,
        "user_id": room.user_id,
        "assigned_admin_id": room.assigned_admin_id,
        "subject": room.subject,
        "status": room.status,
        "last_message": room.last_message,
        "last_message_at": room.last_message_at,
        "created_at": room.created_at,
        "updated_at": room.updated_at,
        "user": {
            "id": room.user.id,
            "username": room.user.username,
            "avatar": room.user.avatar
        } if room.user else None,
        "assigned_admin": {
            "id": room.assigned_admin.id,
            "username": room.assigned_admin.username,
            "avatar": room.assigned_admin.avatar
        } if room.assigned_admin else None,
    }

    if include_messages:
        messages = sorted(room.messages, key=lambda item: item.id)

        data["messages"] = [
            message_to_dict(message)
            for message in messages
        ]

    return data


def check_room_owner_or_admin(room: ChatRoom, user: User):
    if room.user_id != user.id and not is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xem cuộc trò chuyện này"
        )


# =========================
# CUSTOMER CREATE CHAT ROOM
# POST /api/chat/rooms
# =========================

@chat_route.post("/rooms")
def create_chat_room(
        chat_data: ChatRoomCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    now = datetime.utcnow()

    new_room = ChatRoom(
        user_id=current_user.id,
        subject=chat_data.subject,
        status="open",
        last_message=chat_data.message,
        last_message_at=now
    )

    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    first_message = ChatMessage(
        room_id=new_room.id,
        sender_id=current_user.id,
        sender_type="user",
        message=chat_data.message,
        attachments=chat_data.attachments or [],
        is_read_by_user=True,
        is_read_by_admin=False
    )

    db.add(first_message)
    db.commit()
    db.refresh(new_room)

    return {
        "message": "Tạo cuộc trò chuyện thành công",
        "data": room_to_dict(new_room, include_messages=True)
    }


# =========================
# CUSTOMER GET MY CHAT ROOMS
# GET /api/chat/my/rooms
# =========================

@chat_route.get("/my/rooms")
def get_my_chat_rooms(
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    rooms = (
        db.query(ChatRoom)
        .filter(ChatRoom.user_id == current_user.id)
        .order_by(ChatRoom.last_message_at.desc().nullslast(), ChatRoom.id.desc())
        .all()
    )

    return {
        "message": "Lấy danh sách chat của tôi thành công",
        "data": [room_to_dict(room) for room in rooms]
    }


# =========================
# GET ROOM DETAIL
# GET /api/chat/rooms/{room_id}
# Customer owner hoặc admin
# =========================

@chat_route.get("/rooms/{room_id}")
def get_chat_room_detail(
        room_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    check_room_owner_or_admin(room, current_user)

    return {
        "message": "Lấy chi tiết cuộc trò chuyện thành công",
        "data": room_to_dict(room, include_messages=True)
    }


# =========================
# CUSTOMER SEND MESSAGE
# POST /api/chat/rooms/{room_id}/messages
# =========================

@chat_route.post("/rooms/{room_id}/messages")
def customer_send_message(
        room_id: int,
        message_data: ChatMessageCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    room = (
        db.query(ChatRoom)
        .filter(
            ChatRoom.id == room_id,
            ChatRoom.user_id == current_user.id
        )
        .first()
    )

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    if room.status == "closed":
        raise HTTPException(
            status_code=400,
            detail="Cuộc trò chuyện đã đóng"
        )

    new_message = ChatMessage(
        room_id=room.id,
        sender_id=current_user.id,
        sender_type="user",
        message=message_data.message,
        attachments=message_data.attachments or [],
        is_read_by_user=True,
        is_read_by_admin=False
    )

    room.last_message = message_data.message
    room.last_message_at = datetime.utcnow()

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "message": "Gửi tin nhắn thành công",
        "data": message_to_dict(new_message)
    }


# =========================
# CUSTOMER MARK ROOM AS READ
# PATCH /api/chat/rooms/{room_id}/read
# =========================

@chat_route.patch("/rooms/{room_id}/read")
def customer_mark_room_as_read(
        room_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)

    room = (
        db.query(ChatRoom)
        .filter(
            ChatRoom.id == room_id,
            ChatRoom.user_id == current_user.id
        )
        .first()
    )

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.sender_type == "admin",
        ChatMessage.is_read_by_user == False
    ).update({
        ChatMessage.is_read_by_user: True
    })

    db.commit()

    return {
        "message": "Đã đánh dấu tin nhắn là đã đọc"
    }


# =========================
# ADMIN GET ALL CHAT ROOMS
# GET /api/chat/admin/rooms
# =========================

@chat_route.get("/admin/rooms")
def admin_get_chat_rooms(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        status: str = Query(None),
        search: str = Query(None)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    query = db.query(ChatRoom)

    if status:
        query = query.filter(ChatRoom.status == status)

    if search:
        query = query.join(User, ChatRoom.user_id == User.id).filter(
            or_(
                User.username.ilike(f"%{search}%"),
                ChatRoom.subject.ilike(f"%{search}%"),
                ChatRoom.last_message.ilike(f"%{search}%")
            )
        )

    total = query.count()

    rooms = (
        query
        .order_by(ChatRoom.last_message_at.desc().nullslast(), ChatRoom.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Admin lấy danh sách chat thành công",
        "data": [room_to_dict(room) for room in rooms],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# ADMIN GET ROOM DETAIL
# GET /api/chat/admin/rooms/{room_id}
# =========================

@chat_route.get("/admin/rooms/{room_id}")
def admin_get_chat_room_detail(
        room_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    return {
        "message": "Admin lấy chi tiết chat thành công",
        "data": room_to_dict(room, include_messages=True)
    }


# =========================
# ADMIN SEND MESSAGE
# POST /api/chat/admin/rooms/{room_id}/messages
# =========================

@chat_route.post("/admin/rooms/{room_id}/messages")
def admin_send_message(
        room_id: int,
        message_data: ChatMessageCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    if room.status == "closed":
        raise HTTPException(
            status_code=400,
            detail="Cuộc trò chuyện đã đóng"
        )

    if room.assigned_admin_id is None:
        room.assigned_admin_id = current_user.id

    new_message = ChatMessage(
        room_id=room.id,
        sender_id=current_user.id,
        sender_type="admin",
        message=message_data.message,
        attachments=message_data.attachments or [],
        is_read_by_user=False,
        is_read_by_admin=True
    )

    room.last_message = message_data.message
    room.last_message_at = datetime.utcnow()
    room.status = "open"

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "message": "Admin gửi tin nhắn thành công",
        "data": message_to_dict(new_message)
    }


# =========================
# ADMIN MARK ROOM AS READ
# PATCH /api/chat/admin/rooms/{room_id}/read
# =========================

@chat_route.patch("/admin/rooms/{room_id}/read")
def admin_mark_room_as_read(
        room_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    db.query(ChatMessage).filter(
        ChatMessage.room_id == room.id,
        ChatMessage.sender_type == "user",
        ChatMessage.is_read_by_admin == False
    ).update({
        ChatMessage.is_read_by_admin: True
    })

    db.commit()

    return {
        "message": "Admin đã đánh dấu tin nhắn là đã đọc"
    }


# =========================
# ADMIN ASSIGN ROOM
# PATCH /api/chat/admin/rooms/{room_id}/assign
# =========================

@chat_route.patch("/admin/rooms/{room_id}/assign")
def admin_assign_room(
        room_id: int,
        assign_data: ChatAssignAdmin,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    admin_id = assign_data.admin_id or current_user.id

    admin = db.query(User).filter(User.id == admin_id).first()

    if not admin or getattr(admin, "role", "user") != "admin":
        raise HTTPException(
            status_code=400,
            detail="Admin không hợp lệ"
        )

    room.assigned_admin_id = admin.id

    db.commit()
    db.refresh(room)

    return {
        "message": "Gán admin cho cuộc trò chuyện thành công",
        "data": room_to_dict(room)
    }


# =========================
# ADMIN UPDATE ROOM STATUS
# PATCH /api/chat/admin/rooms/{room_id}/status
# =========================

@chat_route.patch("/admin/rooms/{room_id}/status")
def admin_update_room_status(
        room_id: int,
        status_data: ChatRoomStatusUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    allowed_status = ["open", "pending", "closed"]

    if status_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái chat không hợp lệ"
        )

    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    room.status = status_data.status

    db.commit()
    db.refresh(room)

    return {
        "message": "Cập nhật trạng thái chat thành công",
        "data": room_to_dict(room)
    }


# =========================
# ADMIN DELETE ROOM
# DELETE /api/chat/admin/rooms/{room_id}
# =========================

@chat_route.delete("/admin/rooms/{room_id}")
def admin_delete_room(
        room_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    check_admin(current_user)

    room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc trò chuyện"
        )

    db.delete(room)
    db.commit()

    return {
        "message": "Xóa cuộc trò chuyện thành công",
        "deleted_room_id": room_id
    }