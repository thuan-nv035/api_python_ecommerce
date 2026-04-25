import os
from uuid import uuid4
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.params import Query


uploads_route = APIRouter(prefix="/api/uploads", tags=["uploads"])

UPLOAD_ROOT = "uploads"

ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image_file(file: UploadFile):
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Chỉ cho phép upload file ảnh: jpg, jpeg, png, webp, gif"
        )

    return ext


def save_upload_file(file: UploadFile, folder: str):
    ext = validate_image_file(file)

    upload_dir = os.path.join(UPLOAD_ROOT, folder)
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, filename)

    contents = file.file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File ảnh không được vượt quá 5MB"
        )

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    return f"/{file_path.replace(os.sep, '/')}"


# =========================
# UPLOAD SINGLE IMAGE
# POST /api/uploads/image
# =========================

@uploads_route.post("/image")
def upload_image(
        file: UploadFile = File(...),
        folder: str = Form("common")
):
    image_url = save_upload_file(file, folder)

    return {
        "message": "Upload ảnh thành công",
        "url": image_url
    }


# =========================
# UPLOAD MULTIPLE IMAGES
# POST /api/uploads/images
# =========================

@uploads_route.post("/images")
def upload_images(
        files: List[UploadFile] = File(...),
        folder: str = Form("common")
):
    image_urls = []

    for file in files:
        image_url = save_upload_file(file, folder)
        image_urls.append(image_url)

    return {
        "message": "Upload nhiều ảnh thành công",
        "urls": image_urls
    }


# =========================
# DELETE IMAGE
# DELETE /api/uploads/delete?path=/uploads/products/abc.jpg
# =========================

@uploads_route.delete("/delete")
def delete_uploaded_file(
        path: str = Query(...)
):
    if not path.startswith("/uploads/"):
        raise HTTPException(
            status_code=400,
            detail="Đường dẫn file không hợp lệ"
        )

    file_path = path.lstrip("/")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy file"
        )

    try:
        os.remove(file_path)

        return {
            "message": "Xóa file thành công",
            "deleted_path": path
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xóa file: {str(e)}"
        )