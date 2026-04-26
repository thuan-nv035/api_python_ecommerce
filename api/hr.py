import math

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth import get_admin_user
from database import get_db
from models.models import User, Department, Employee
from schemas.hr_schema import (
    DepartmentCreate,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeUpdate
)

hr_route = APIRouter(tags=["hr"])


def department_to_dict(department: Department):
    return {
        "id": department.id,
        "name": department.name,
        "code": department.code,
        "desc": department.desc,
        "manager_id": department.manager_id,
        "is_active": department.is_active,
        "created_at": department.created_at,
        "updated_at": department.updated_at,
        "manager": {
            "id": department.manager.id,
            "username": department.manager.username,
            "avatar": department.manager.avatar,
            "role": getattr(department.manager, "role", "user")
        } if department.manager else None
    }


def employee_to_dict(employee: Employee):
    return {
        "id": employee.id,
        "user_id": employee.user_id,
        "department_id": employee.department_id,
        "employee_code": employee.employee_code,
        "full_name": employee.full_name,
        "phone": employee.phone,
        "email": employee.email,
        "address": employee.address,
        "position": employee.position,
        "salary": employee.salary,
        "hire_date": employee.hire_date,
        "birth_date": employee.birth_date,
        "status": employee.status,
        "note": employee.note,
        "created_at": employee.created_at,
        "updated_at": employee.updated_at,
        "user": {
            "id": employee.user.id,
            "username": employee.user.username,
            "avatar": employee.user.avatar,
            "role": getattr(employee.user, "role", "user")
        } if employee.user else None,
        "department": {
            "id": employee.department.id,
            "name": employee.department.name,
            "code": employee.department.code
        } if employee.department else None
    }


def validate_user_exists(db: Session, user_id: int):
    if user_id is None:
        return

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy user"
        )


def validate_department_exists(db: Session, department_id: int):
    if department_id is None:
        return

    department = db.query(Department).filter(Department.id == department_id).first()

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy phòng ban"
        )


# =====================================================
# DEPARTMENT API
# =====================================================

# =========================
# CREATE DEPARTMENT
# POST /api/departments/
# =========================

@hr_route.post("/api/departments/")
def create_department(
        department_data: DepartmentCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    code = department_data.code.strip().upper()

    existed_department = (
        db.query(Department)
        .filter(Department.code == code)
        .first()
    )

    if existed_department:
        raise HTTPException(
            status_code=400,
            detail="Mã phòng ban đã tồn tại"
        )

    validate_user_exists(db, department_data.manager_id)

    new_department = Department(
        name=department_data.name,
        code=code,
        desc=department_data.desc,
        manager_id=department_data.manager_id,
        is_active=department_data.is_active
    )

    db.add(new_department)
    db.commit()
    db.refresh(new_department)

    return {
        "message": "Tạo phòng ban thành công",
        "data": department_to_dict(new_department)
    }


# =========================
# GET ALL DEPARTMENTS
# GET /api/departments/
# =========================

@hr_route.get("/api/departments/")
def get_all_departments(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        is_active: bool = Query(None)
):
    get_admin_user(request)

    query = db.query(Department)

    if search:
        query = query.filter(
            or_(
                Department.name.ilike(f"%{search}%"),
                Department.code.ilike(f"%{search}%"),
                Department.desc.ilike(f"%{search}%")
            )
        )

    if is_active is not None:
        query = query.filter(Department.is_active == is_active)

    total = query.count()

    departments = (
        query
        .order_by(Department.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách phòng ban thành công",
        "data": [department_to_dict(department) for department in departments],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET ACTIVE DEPARTMENTS
# GET /api/departments/active
# =========================

@hr_route.get("/api/departments/active")
def get_active_departments(
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    departments = (
        db.query(Department)
        .filter(Department.is_active == True)
        .order_by(Department.name.asc())
        .all()
    )

    return {
        "message": "Lấy phòng ban đang hoạt động thành công",
        "data": [department_to_dict(department) for department in departments]
    }


# =========================
# GET DEPARTMENT BY ID
# GET /api/departments/{department_id}
# =========================

@hr_route.get("/api/departments/{department_id}")
def get_department_by_id(
        department_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy phòng ban"
        )

    return {
        "message": "Lấy chi tiết phòng ban thành công",
        "data": department_to_dict(department)
    }


# =========================
# UPDATE DEPARTMENT
# PUT/PATCH /api/departments/{department_id}
# =========================

@hr_route.put("/api/departments/{department_id}")
@hr_route.patch("/api/departments/{department_id}")
def update_department(
        department_id: int,
        department_data: DepartmentUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy phòng ban"
        )

    update_data = department_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "code" in update_data:
        new_code = update_data["code"].strip().upper()

        existed_department = (
            db.query(Department)
            .filter(
                Department.code == new_code,
                Department.id != department_id
            )
            .first()
        )

        if existed_department:
            raise HTTPException(
                status_code=400,
                detail="Mã phòng ban đã tồn tại"
            )

        update_data["code"] = new_code

    if "manager_id" in update_data:
        validate_user_exists(db, update_data["manager_id"])

    for key, value in update_data.items():
        setattr(department, key, value)

    db.commit()
    db.refresh(department)

    return {
        "message": "Cập nhật phòng ban thành công",
        "data": department_to_dict(department)
    }


# =========================
# DELETE DEPARTMENT
# DELETE /api/departments/{department_id}
# =========================

@hr_route.delete("/api/departments/{department_id}")
def delete_department(
        department_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    department = (
        db.query(Department)
        .filter(Department.id == department_id)
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy phòng ban"
        )

    employee_count = (
        db.query(Employee)
        .filter(Employee.department_id == department_id)
        .count()
    )

    if employee_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa phòng ban đang có nhân viên. Hãy tắt is_active thay vì xóa."
        )

    db.delete(department)
    db.commit()

    return {
        "message": "Xóa phòng ban thành công",
        "deleted_department_id": department_id
    }


# =====================================================
# EMPLOYEE API
# =====================================================

# =========================
# CREATE EMPLOYEE
# POST /api/employees/
# =========================

@hr_route.post("/api/employees/")
def create_employee(
        employee_data: EmployeeCreate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    employee_code = employee_data.employee_code.strip().upper()

    existed_employee = (
        db.query(Employee)
        .filter(Employee.employee_code == employee_code)
        .first()
    )

    if existed_employee:
        raise HTTPException(
            status_code=400,
            detail="Mã nhân viên đã tồn tại"
        )

    allowed_status = ["active", "inactive", "resigned"]

    if employee_data.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Trạng thái nhân viên không hợp lệ"
        )

    validate_user_exists(db, employee_data.user_id)
    validate_department_exists(db, employee_data.department_id)

    if employee_data.user_id:
        existed_user_employee = (
            db.query(Employee)
            .filter(Employee.user_id == employee_data.user_id)
            .first()
        )

        if existed_user_employee:
            raise HTTPException(
                status_code=400,
                detail="User này đã được gắn với một nhân viên khác"
            )

    new_employee = Employee(
        user_id=employee_data.user_id,
        department_id=employee_data.department_id,
        employee_code=employee_code,
        full_name=employee_data.full_name,
        phone=employee_data.phone,
        email=employee_data.email,
        address=employee_data.address,
        position=employee_data.position,
        salary=employee_data.salary or 0,
        hire_date=employee_data.hire_date,
        birth_date=employee_data.birth_date,
        status=employee_data.status,
        note=employee_data.note
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return {
        "message": "Tạo nhân viên thành công",
        "data": employee_to_dict(new_employee)
    }


# =========================
# GET ALL EMPLOYEES
# GET /api/employees/
# =========================

@hr_route.get("/api/employees/")
def get_all_employees(
        request: Request,
        db: Session = Depends(get_db),
        page: int = Query(1, gt=0),
        limit: int = Query(20, gt=0),
        search: str = Query(None),
        department_id: int = Query(None),
        status: str = Query(None)
):
    get_admin_user(request)

    query = db.query(Employee)

    if search:
        query = query.filter(
            or_(
                Employee.full_name.ilike(f"%{search}%"),
                Employee.employee_code.ilike(f"%{search}%"),
                Employee.phone.ilike(f"%{search}%"),
                Employee.email.ilike(f"%{search}%"),
                Employee.position.ilike(f"%{search}%")
            )
        )

    if department_id:
        query = query.filter(Employee.department_id == department_id)

    if status:
        query = query.filter(Employee.status == status)

    total = query.count()

    employees = (
        query
        .order_by(Employee.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "message": "Lấy danh sách nhân viên thành công",
        "data": [employee_to_dict(employee) for employee in employees],
        "pagination": {
            "total_records": total,
            "total_pages": math.ceil(total / limit) if total > 0 else 0,
            "current_page": page,
            "limit": limit
        }
    }


# =========================
# GET EMPLOYEE BY ID
# GET /api/employees/{employee_id}
# =========================

@hr_route.get("/api/employees/{employee_id}")
def get_employee_by_id(
        employee_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nhân viên"
        )

    return {
        "message": "Lấy chi tiết nhân viên thành công",
        "data": employee_to_dict(employee)
    }


# =========================
# UPDATE EMPLOYEE
# PUT/PATCH /api/employees/{employee_id}
# =========================

@hr_route.put("/api/employees/{employee_id}")
@hr_route.patch("/api/employees/{employee_id}")
def update_employee(
        employee_id: int,
        employee_data: EmployeeUpdate,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nhân viên"
        )

    update_data = employee_data.dict(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="Không có dữ liệu để cập nhật"
        )

    if "employee_code" in update_data:
        new_code = update_data["employee_code"].strip().upper()

        existed_employee = (
            db.query(Employee)
            .filter(
                Employee.employee_code == new_code,
                Employee.id != employee_id
            )
            .first()
        )

        if existed_employee:
            raise HTTPException(
                status_code=400,
                detail="Mã nhân viên đã tồn tại"
            )

        update_data["employee_code"] = new_code

    if "status" in update_data:
        allowed_status = ["active", "inactive", "resigned"]

        if update_data["status"] not in allowed_status:
            raise HTTPException(
                status_code=400,
                detail="Trạng thái nhân viên không hợp lệ"
            )

    if "user_id" in update_data:
        validate_user_exists(db, update_data["user_id"])

        if update_data["user_id"]:
            existed_user_employee = (
                db.query(Employee)
                .filter(
                    Employee.user_id == update_data["user_id"],
                    Employee.id != employee_id
                )
                .first()
            )

            if existed_user_employee:
                raise HTTPException(
                    status_code=400,
                    detail="User này đã được gắn với một nhân viên khác"
                )

    if "department_id" in update_data:
        validate_department_exists(db, update_data["department_id"])

    for key, value in update_data.items():
        setattr(employee, key, value)

    db.commit()
    db.refresh(employee)

    return {
        "message": "Cập nhật nhân viên thành công",
        "data": employee_to_dict(employee)
    }


# =========================
# DELETE EMPLOYEE
# DELETE /api/employees/{employee_id}
# =========================

@hr_route.delete("/api/employees/{employee_id}")
def delete_employee(
        employee_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    get_admin_user(request)

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy nhân viên"
        )

    db.delete(employee)
    db.commit()

    return {
        "message": "Xóa nhân viên thành công",
        "deleted_employee_id": employee_id
    }