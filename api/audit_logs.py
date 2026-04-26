import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth import get_admin_user, get_current_user
from database import get_db
from models.models import User, AuditLog
from schemas.audit_log_schema import AuditLogCreate


audit_logs_route = APIRouter(
    prefix="/api/audit-logs",
    tags=["audit-logs"]
)

def parse_date(date_str):
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Ngày phải có định dạng YYYY-MM-DD"
        )


def audit_log_to_dict(log: AuditLog):
    return {
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "module": log.module,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "old_data": log.old_data,
        "new_data": log.new_data,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "note": log.note,
        "created_at": log.created_at,
        "user": {
            "id": log.user.id,
            "username": log.user.username,
            "avatar": log.user.avatar,
            "role": getattr(log.user, "role", "user")
        } if log.user else None
    }


def create_audit_log(
        db: Session,
        user_id: int = None,
        action: str = None,
        module: str = None,
        resource_type: str = None,
        resource_id: int = None,
        old_data=None,
        new_data=None,
        ip_address: str = None,
        user_agent: str = None,
        note: str = None
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        old_data=old_data,
        new_data=new_data,
        ip_address=ip_address,
        user_agent=user_agent,
        note=note
    )

    db.add(log)
    db.flush()

    return log


def get_request_ip(request: Request):
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return None


def get_request_user_agent(request: Request):
    return request.headers.get("user-agent")


# =========================
# CREATE AUDIT LOG MANUAL
# POST /api/audit-logs/
# Admin
# =========================

@audit_logs_route.post("/")
def create_manual_audit_log(
        data: AuditLogCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    get_admin_user(request)

    log = AuditLog(
        user_id=data.user_id or current_user.id,
        action=data.action,
        module=data.module,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        old_data=data.old_data,
        new_data=data.new_data,
        ip_address=data.ip_address or get_request_ip(request),
        user_agent=data.user_agent or get_request_user_agent(request),
        note=data.note
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "message": "Tạo audit log thành công",
        "data": audit_log_to_dict(log)
    }


# =========================
# GET ALL AUDIT LOGS
# GET /api/audit-logs/
# Admin
# =========================

@audit_logs_route.get("/")
def get_all_audit_logs(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),

        search: str = Query(None),
        user_id: int = Query(None),

        action: str = Query(None),
        module: str = Query(None),

        resource_type: str = Query(None),
        resource_id: int = Query(None),

        start_date: str = Query(None),
        end_date: str = Query(None)
):
    get_admin_user(request)

    query = db.query(AuditLog)

    if search:
        query = query.filter(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.module.ilike(f"%{search}%"),
                AuditLog.resource_type.ilike(f"%{search}%"),
                AuditLog.note.ilike(f"%{search}%"),
                AuditLog.ip_address.ilike(f"%{search}%")
            )
        )

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if action:
        query = query.filter(AuditLog.action == action)

    if module:
        query = query.filter(AuditLog.module == module)

    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)

    start = parse_date(start_date)
    end = parse_date(end_date)

    if start:
        query = query.filter(AuditLog.created_at >= start)

    if end:
        query = query.filter(AuditLog.created_at < end + timedelta(days=1))

    total = query.count()

    logs = (
        query
        .order_by(AuditLog.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách audit log thành công",
        "data": [audit_log_to_dict(log) for log in logs],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        },
        "filters": {
            "search": search,
            "user_id": user_id,
            "action": action,
            "module": module,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "start_date": start_date,
            "end_date": end_date
        }
    }


# =========================
# GET AUDIT LOG BY ID
# GET /api/audit-logs/{log_id}
# Admin
# =========================

@audit_logs_route.get("/{log_id}")
def get_audit_log_by_id(
        log_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()

    if not log:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy audit log"
        )

    return {
        "message": "Lấy chi tiết audit log thành công",
        "data": audit_log_to_dict(log)
    }


# =========================
# DELETE AUDIT LOG
# DELETE /api/audit-logs/{log_id}
# Admin
# =========================

@audit_logs_route.delete("/{log_id}")
def delete_audit_log(
        log_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()

    if not log:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy audit log"
        )

    db.delete(log)
    db.commit()

    return {
        "message": "Xóa audit log thành công",
        "deleted_log_id": log_id
    }