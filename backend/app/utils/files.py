import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException

from app.config import settings

DOCUMENT_EXTENSIONS = {"pdf", "docx", "pptx"}
VIDEO_EXTENSIONS = {"mp4", "mov"}
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | VIDEO_EXTENSIONS

ALLOWED_CONTENT_TYPES = {
    "pdf": {"application/pdf"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    "mp4": {"video/mp4"},
    "mov": {"video/quicktime"},
}


def validate_upload_file(upload_file: UploadFile, allowed_extensions: set[str] | None = None) -> str:
    """Validate an upload before any bytes are written and return its extension."""
    filename = upload_file.filename or ""
    extension = get_file_type(filename)
    accepted = allowed_extensions or ALLOWED_EXTENSIONS
    if extension not in accepted:
        allowed = ", ".join(f".{item}" for item in sorted(accepted))
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Allowed: {allowed}")

    content_type = (upload_file.content_type or "").lower()
    if content_type and content_type != "application/octet-stream":
        allowed_mime_types = ALLOWED_CONTENT_TYPES.get(extension, set())
        if allowed_mime_types and content_type not in allowed_mime_types:
            raise HTTPException(
                status_code=415,
                detail=f"File content type '{content_type}' does not match .{extension}",
            )
    return extension


def get_upload_path(project_id: str, filename: str) -> Path:
    """Return an absolute path for storing an uploaded file."""
    safe_name = Path(filename).name  # strip any path traversal
    dest_dir = Path(settings.UPLOAD_DIR) / project_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / f"{uuid.uuid4()}_{safe_name}"


async def save_upload_file(upload_file: UploadFile, project_id: str) -> str:
    """Save an UploadFile to disk, return the storage path string."""
    validate_upload_file(upload_file)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    dest_path = get_upload_path(project_id, upload_file.filename or "upload")

    size = 0
    with open(dest_path, "wb") as buffer:
        while chunk := await upload_file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)
            if size > max_bytes:
                buffer.close()
                os.unlink(dest_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
                )
            buffer.write(chunk)

    return str(dest_path)


def get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext if ext else "unknown"
