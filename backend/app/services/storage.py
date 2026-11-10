"""Private image storage with local, Cloudinary Free and optional Cloudflare R2 adapters.

All uploaded images are decoded and re-encoded before storage. Object keys are
never exposed as public URLs; Cloudinary assets use authenticated delivery,
and reads remain behind the application's signed, short-lived application routes
and authorization checks.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import os
import posixpath
import time
import uuid
from pathlib import Path, PurePosixPath

import httpx
from fastapi import HTTPException, status
from PIL import Image

from backend.app.core.config import settings

ALLOWED_MIME_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_DIMENSION = 4000


def _backend() -> str:
    return str(settings.STORAGE_BACKEND).strip().lower()


def _normalise_key(storage_key: str) -> str:
    """Validate a relative object key; reject traversal and absolute backend keys."""
    raw = (storage_key or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or "\x00" in raw:
        raise ValueError("Invalid storage key.")
    normalised = posixpath.normpath(raw)
    if normalised in ("", ".", "..") or normalised.startswith("../"):
        raise ValueError("Invalid storage key.")
    parts = PurePosixPath(normalised).parts
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Invalid storage key.")
    return normalised


def get_storage_path(storage_key: str) -> str:
    """Return a safe local path for a relative key (used by local operations/tests)."""
    key = _normalise_key(storage_key)
    base = Path(settings.STORAGE_DIR).resolve()
    path = (base / Path(*PurePosixPath(key).parts)).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise ValueError("Storage key escapes the configured storage directory.") from exc
    return str(path)


def _legacy_local_path(storage_key: str) -> str | None:
    """Accept old local keys (absolute or relative) only when they remain inside STORAGE_DIR."""
    raw = (storage_key or "").strip()
    if not raw:
        return None
    try:
        base = Path(settings.STORAGE_DIR).resolve()
        path = Path(raw).resolve()
        path.relative_to(base)
        return str(path)
    except (ValueError, OSError):
        return None


def _cloudinary_components():
    """Configure and return Cloudinary SDK components on first use."""
    cloud_name = settings.CLOUDINARY_CLOUD_NAME.strip()
    api_key = settings.CLOUDINARY_API_KEY.strip()
    api_secret = settings.CLOUDINARY_API_SECRET.strip()
    if not all((cloud_name, api_key, api_secret)):
        raise RuntimeError(
            "Cloudinary storage is selected but CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET are not fully configured."
        )

    try:
        import cloudinary
        from cloudinary import api, uploader, utils
    except ImportError as exc:  # pragma: no cover - deployment configuration failure
        raise RuntimeError("Install cloudinary to use Cloudinary private image storage.") from exc

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    return api, uploader, utils


def _cloudinary_public_id(storage_key: str) -> str:
    """Map an opaque app key into a fixed private Cloudinary namespace."""
    key = _normalise_key(storage_key)
    stem = posixpath.splitext(key)[0]
    return f"township-one-private/{stem}"


def _cloudinary_format(storage_key: str) -> str:
    suffix = PurePosixPath(_normalise_key(storage_key)).suffix.lower().lstrip(".")
    formats = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp"}
    if suffix not in formats:
        raise ValueError("Unsupported Cloudinary image format.")
    return formats[suffix]


def _is_cloudinary_not_found(exc: Exception) -> bool:
    return getattr(exc, "http_code", None) == 404 or "not found" in str(exc).lower()


def _r2_client():
    """Create an S3-compatible Cloudflare R2 client lazily."""
    account_id = settings.R2_ACCOUNT_ID.strip()
    endpoint = settings.R2_ENDPOINT_URL.strip() or (
        f"https://{account_id}.r2.cloudflarestorage.com" if account_id else ""
    )
    if not all(
        (endpoint, settings.R2_ACCESS_KEY_ID.strip(), settings.R2_SECRET_ACCESS_KEY.strip(), settings.R2_BUCKET.strip())
    ):
        raise RuntimeError(
            "Cloudflare R2 storage is selected but R2_ACCOUNT_ID/R2_ENDPOINT_URL, "
            "R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET are not fully configured."
        )

    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:  # pragma: no cover - deployment configuration failure
        raise RuntimeError("Install boto3 to use Cloudflare R2 storage.") from exc

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name="auto",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def write_private_object(storage_key: str, data: bytes, content_type: str) -> None:
    """Persist bytes privately using the configured storage adapter."""
    key = _normalise_key(storage_key)
    if _backend() == "cloudinary":
        _, uploader, _ = _cloudinary_components()
        public_id = _cloudinary_public_id(key)
        result = uploader.upload(
            io.BytesIO(data),
            resource_type="image",
            type="authenticated",
            public_id=public_id,
            overwrite=False,
            unique_filename=False,
            use_filename=False,
            invalidate=False,
        )
        if result.get("public_id") != public_id:
            raise RuntimeError("Cloudinary did not confirm the expected private object key.")
        return

    if _backend() == "cloudflare_r2":
        _r2_client().put_object(
            Bucket=settings.R2_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="private, no-store",
        )
        return

    if _backend() != "local":
        raise RuntimeError(f"Unsupported STORAGE_BACKEND: {_backend()!r}.")
    target = Path(get_storage_path(key))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def read_private_object(storage_key: str) -> bytes | None:
    """Read a private object. Returns None for a missing/invalid key."""
    if _backend() == "cloudinary":
        try:
            key = _normalise_key(storage_key)
            _, _, utils = _cloudinary_components()
            download_url = utils.private_download_url(
                _cloudinary_public_id(key),
                _cloudinary_format(key),
                resource_type="image",
                type="authenticated",
                expires_at=int(time.time()) + 60,
            )
            response = httpx.get(download_url, timeout=20.0, follow_redirects=True)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.content
        except Exception as exc:
            if _is_cloudinary_not_found(exc):
                return None
            if isinstance(exc, (ValueError, HTTPException)):
                return None
            raise

    if _backend() == "cloudflare_r2":
        try:
            key = _normalise_key(storage_key)
            response = _r2_client().get_object(Bucket=settings.R2_BUCKET, Key=key)
            body = response["Body"]
            try:
                return body.read()
            finally:
                body.close()
        except Exception as exc:
            error = getattr(exc, "response", {}).get("Error", {})
            code = str(error.get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise

    if _backend() != "local":
        raise RuntimeError(f"Unsupported STORAGE_BACKEND: {_backend()!r}.")
    legacy_path = _legacy_local_path(storage_key)
    try:
        target = Path(legacy_path or get_storage_path(storage_key))
        return target.read_bytes() if target.is_file() else None
    except (OSError, ValueError):
        return None


def delete_private_object(storage_key: str) -> None:
    """Delete an object; deletion is idempotent for already-missing objects."""
    if _backend() == "cloudinary":
        key = _normalise_key(storage_key)
        _, uploader, _ = _cloudinary_components()
        result = uploader.destroy(
            _cloudinary_public_id(key),
            resource_type="image",
            type="authenticated",
            invalidate=False,
        )
        if result.get("result") not in {"ok", "not found"}:
            raise RuntimeError("Cloudinary did not confirm private object deletion.")
        return

    if _backend() == "cloudflare_r2":
        key = _normalise_key(storage_key)
        _r2_client().delete_object(Bucket=settings.R2_BUCKET, Key=key)
        return

    if _backend() != "local":
        raise RuntimeError(f"Unsupported STORAGE_BACKEND: {_backend()!r}.")
    legacy_path = _legacy_local_path(storage_key)
    target = Path(legacy_path or get_storage_path(storage_key))
    target.unlink(missing_ok=True)


def private_object_exists(storage_key: str) -> bool:
    """Check an object without making its bucket or filesystem public."""
    if _backend() == "cloudinary":
        try:
            key = _normalise_key(storage_key)
            api, _, _ = _cloudinary_components()
            api.resource(
                _cloudinary_public_id(key),
                resource_type="image",
                type="authenticated",
            )
            return True
        except Exception as exc:
            if _is_cloudinary_not_found(exc) or isinstance(exc, ValueError):
                return False
            raise

    if _backend() == "cloudflare_r2":
        key = _normalise_key(storage_key)
        try:
            _r2_client().head_object(Bucket=settings.R2_BUCKET, Key=key)
            return True
        except Exception as exc:
            error = getattr(exc, "response", {}).get("Error", {})
            if str(error.get("Code", "")) in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    if _backend() != "local":
        raise RuntimeError(f"Unsupported STORAGE_BACKEND: {_backend()!r}.")
    legacy_path = _legacy_local_path(storage_key)
    try:
        target = Path(legacy_path or get_storage_path(storage_key))
        return target.is_file()
    except ValueError:
        return False


def save_complaint_photo(file_bytes: bytes, original_filename: str) -> tuple[str, str, int, str]:
    """Validate, strip metadata, re-encode and store a resident complaint image."""
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File size exceeds the 5 MB maximum limit.",
        )

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.verify()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid image file format. Only valid JPEG, PNG, and WebP are accepted.",
        ) from exc

    image = Image.open(io.BytesIO(file_bytes))
    format_name = image.format
    if not format_name:
        raise HTTPException(status_code=422, detail="Unable to determine image format.")
    mime_type = Image.MIME.get(format_name)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported image format '{format_name}'. Only JPEG, PNG, and WebP are allowed.",
        )

    width, height = image.size
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(
            status_code=422,
            detail=f"Image dimensions ({width}x{height}) exceed maximum allowed {MAX_DIMENSION}x{MAX_DIMENSION}.",
        )

    # Construct a fresh pixel-only image so EXIF/GPS and other metadata are not copied.
    clean_image = Image.frombytes(image.mode, image.size, image.tobytes())
    save_format = ALLOWED_MIME_TYPES[mime_type]
    if save_format == "JPEG" and clean_image.mode not in ("RGB", "L"):
        clean_image = clean_image.convert("RGB")
    elif save_format in ("PNG", "WEBP") and clean_image.mode not in ("RGB", "RGBA", "L", "LA"):
        clean_image = clean_image.convert("RGBA")

    output_buffer = io.BytesIO()
    clean_image.save(output_buffer, format=save_format)
    clean_bytes = output_buffer.getvalue()
    file_sha256 = hashlib.sha256(clean_bytes).hexdigest()
    extension = ".jpg" if mime_type == "image/jpeg" else (".png" if mime_type == "image/png" else ".webp")
    storage_key = f"{uuid.uuid4().hex}{extension}"
    write_private_object(storage_key, clean_bytes, mime_type)
    return storage_key, mime_type, len(clean_bytes), file_sha256


def generate_signed_photo_url(storage_key: str, expires_seconds: int = 300) -> str:
    """Create an HMAC-SHA256 signed URL valid for no more than five minutes."""
    expiry_timestamp = int(time.time()) + min(max(int(expires_seconds), 1), 300)
    data_to_sign = f"{storage_key}:{expiry_timestamp}".encode()
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), data_to_sign, hashlib.sha256).hexdigest()
    return f"{settings.API_PREFIX}/complaints/photos/{storage_key}?exp={expiry_timestamp}&sig={signature}"


def verify_signed_photo_token(storage_key: str, exp: int, sig: str) -> bool:
    """Validate the expiry timestamp and HMAC signature using constant-time comparison."""
    now = int(time.time())
    if now > exp:
        return False
    data_to_sign = f"{storage_key}:{exp}".encode()
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), data_to_sign, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)
