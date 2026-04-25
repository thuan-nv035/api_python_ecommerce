import json
import os
import shutil
from typing import Optional, List
from uuid import uuid4

from fastapi import UploadFile, HTTPException

UPLOAD_DIR = "uploads/products"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload_files(files: Optional[List[UploadFile]]):
    image_paths = []

    if not files:
        return image_paths

    for file in files:
        if not file.filename:
            continue

        ext = os.path.splitext(file.filename)[1]
        filename = f"{uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image_paths.append(f"/{file_path.replace(os.sep, '/')}")

    return image_paths


def parse_json_field(value: Optional[str]):
    if not value:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="categories phải là JSON hợp lệ"
        )
