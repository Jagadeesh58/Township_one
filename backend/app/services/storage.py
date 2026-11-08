"""
Township One — Private Media Storage Engine.

Enforces zero-static exposure:
- Files are saved outside the web root in STORAGE_DIR.
- Validates real MIME types using Pillow.
- Re-encodes uploaded images to strip GPS coordinates and EXIF metadata.
- Validates 5 MB size limit and 4000x4000 dimension limit.
- Generates time-bounded HMAC signed access URLs (expires in <= 5 minutes).
"""

import os
import io
import time
import hmac
import hashlib
import uuid
from PIL import Image, ImageOps
from fastapi import HTTPException, status
from backend.app.core.config import settings

ALLOWED_MIME_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP"
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION = 4000


def get_storage_path(storage_key: str) -> str:
    """Returns absolute path on disk ensuring no directory traversal."""
    safe_name = os.path.basename(storage_key)
    return os.path.join(settings.STORAGE_DIR, safe_name)


def save_complaint_photo(file_bytes: bytes, original_filename: str) -> tuple[str, str, int, str]:
    """
    Validates, strips EXIF, re-encodes, and writes image to private storage.
    Returns: (storage_key, content_type, file_size, file_sha256)
    """
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File size exceeds the 5 MB maximum limit."
        )

    # Validate image using Pillow
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.verify()  # Verifies file integrity
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid image file format. Only valid JPEG, PNG, and WebP are accepted."
        )

    # Re-open for transformation (verify() destroys image state)
    image = Image.open(io.BytesIO(file_bytes))
    format_name = image.format
    if not format_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to determine image format."
        )

    mime_type = Image.MIME.get(format_name)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported image format '{format_name}'. Only JPEG, PNG, and WebP are allowed."
        )

    width, height = image.size
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Image dimensions ({width}x{height}) exceed maximum allowed {MAX_DIMENSION}x{MAX_DIMENSION}."
        )

    # Strip EXIF and re-encode to clean bytes buffer
    output_buffer = io.BytesIO()
    clean_image = Image.new(image.mode, image.size)
    clean_image.putdata(list(image.getdata()))

    save_format = ALLOWED_MIME_TYPES[mime_type]
    clean_image.save(output_buffer, format=save_format)
    clean_bytes = output_buffer.getvalue()

    file_sha256 = hashlib.sha256(clean_bytes).hexdigest()
    ext = ".jpg" if mime_type == "image/jpeg" else (".png" if mime_type == "image/png" else ".webp")
    storage_key = f"{uuid.uuid4().hex}{ext}"

    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    target_path = get_storage_path(storage_key)
    with open(target_path, "wb") as f:
        f.write(clean_bytes)

    return storage_key, mime_type, len(clean_bytes), file_sha256


def generate_signed_photo_url(storage_key: str, expires_seconds: int = 300) -> str:
    """Generates an HMAC-SHA256 signed URL valid for <= 5 minutes."""
    expiry_timestamp = int(time.time()) + expires_seconds
    data_to_sign = f"{storage_key}:{expiry_timestamp}".encode("utf-8")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), data_to_sign, hashlib.sha256).hexdigest()
    return f"{settings.API_PREFIX}/complaints/photos/{storage_key}?exp={expiry_timestamp}&sig={signature}"


def verify_signed_photo_token(storage_key: str, exp: int, sig: str) -> bool:
    """Validates the expiry timestamp and HMAC signature."""
    now = int(time.time())
    if now > exp:
        return False
    data_to_sign = f"{storage_key}:{exp}".encode("utf-8")
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), data_to_sign, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, sig)
