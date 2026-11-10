from __future__ import annotations

import io
import sys
import types

import pytest

from backend.app.core.config import settings
from backend.app.services import storage


def test_local_private_storage_round_trip_and_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path))

    storage.write_private_object("complaints/sample.jpg", b"private-image", "image/jpeg")
    assert storage.private_object_exists("complaints/sample.jpg") is True
    assert storage.read_private_object("complaints/sample.jpg") == b"private-image"
    assert storage.read_private_object("missing.jpg") is None

    storage.delete_private_object("complaints/sample.jpg")
    assert storage.private_object_exists("complaints/sample.jpg") is False

    with pytest.raises(ValueError):
        storage.write_private_object("../escape.jpg", b"bad", "image/jpeg")
    assert storage.read_private_object("../../etc/passwd") is None


def test_cloudflare_r2_adapter_uses_private_s3_compatible_operations(monkeypatch):
    calls: list[tuple[str, dict]] = []
    objects: dict[str, bytes] = {}

    class FakeBody(io.BytesIO):
        pass

    class FakeClient:
        def put_object(self, **kwargs):
            calls.append(("put", kwargs))
            objects[kwargs["Key"]] = kwargs["Body"]

        def get_object(self, **kwargs):
            calls.append(("get", kwargs))
            if kwargs["Key"] not in objects:
                raise FakeStorageError("NoSuchKey")
            return {"Body": FakeBody(objects[kwargs["Key"]])}

        def head_object(self, **kwargs):
            calls.append(("head", kwargs))
            if kwargs["Key"] not in objects:
                raise FakeStorageError("NotFound")
            return {}

        def delete_object(self, **kwargs):
            calls.append(("delete", kwargs))
            objects.pop(kwargs["Key"], None)

    class FakeStorageError(Exception):
        def __init__(self, code: str):
            super().__init__(code)
            self.response = {"Error": {"Code": code}}

    fake_client = FakeClient()
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = lambda *args, **kwargs: fake_client
    fake_botocore = types.ModuleType("botocore")
    fake_botocore_config = types.ModuleType("botocore.config")
    fake_botocore_config.Config = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.config", fake_botocore_config)

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "cloudflare_r2")
    monkeypatch.setattr(settings, "R2_ACCOUNT_ID", "test-account")
    monkeypatch.setattr(settings, "R2_ENDPOINT_URL", "")
    monkeypatch.setattr(settings, "R2_ACCESS_KEY_ID", "test-access")
    monkeypatch.setattr(settings, "R2_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setattr(settings, "R2_BUCKET", "township-private")

    storage.write_private_object("visitor_photos/abc.jpg", b"visitor-photo", "image/jpeg")
    assert objects["visitor_photos/abc.jpg"] == b"visitor-photo"
    assert storage.read_private_object("visitor_photos/abc.jpg") == b"visitor-photo"
    assert storage.private_object_exists("visitor_photos/abc.jpg") is True
    storage.delete_private_object("visitor_photos/abc.jpg")
    assert storage.private_object_exists("visitor_photos/abc.jpg") is False

    assert [name for name, _ in calls] == ["put", "get", "head", "delete", "head"]
    put = calls[0][1]
    assert put["Bucket"] == "township-private"
    assert put["CacheControl"] == "private, no-store"
    assert put["ContentType"] == "image/jpeg"


def test_r2_missing_object_is_a_normal_not_found(monkeypatch):
    class FakeStorageError(Exception):
        response = {"Error": {"Code": "NoSuchKey"}}

    class FakeClient:
        def get_object(self, **kwargs):
            raise FakeStorageError()

        def head_object(self, **kwargs):
            raise FakeStorageError()

    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = lambda *args, **kwargs: FakeClient()
    fake_botocore = types.ModuleType("botocore")
    fake_botocore_config = types.ModuleType("botocore.config")
    fake_botocore_config.Config = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.config", fake_botocore_config)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "cloudflare_r2")
    monkeypatch.setattr(settings, "R2_ACCOUNT_ID", "test-account")
    monkeypatch.setattr(settings, "R2_ENDPOINT_URL", "")
    monkeypatch.setattr(settings, "R2_ACCESS_KEY_ID", "test-access")
    monkeypatch.setattr(settings, "R2_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setattr(settings, "R2_BUCKET", "township-private")

    assert storage.read_private_object("missing.jpg") is None
    assert storage.private_object_exists("missing.jpg") is False


def test_cloudinary_adapter_stores_authenticated_assets_and_reads_through_private_url(monkeypatch):
    objects: dict[str, bytes] = {}
    recorded: list[tuple[str, dict]] = []

    class FakeCloudinaryError(Exception):
        http_code = 404

    class FakeUploader:
        def upload(self, file, **kwargs):
            payload = file.read()
            public_id = kwargs["public_id"]
            recorded.append(("upload", kwargs))
            objects[public_id] = payload
            return {"public_id": public_id, "secure_url": "https://not-used.example/asset"}

        def destroy(self, public_id, **kwargs):
            recorded.append(("destroy", {"public_id": public_id, **kwargs}))
            return {"result": "ok" if objects.pop(public_id, None) is not None else "not found"}

    class FakeApi:
        def resource(self, public_id, **kwargs):
            recorded.append(("resource", {"public_id": public_id, **kwargs}))
            if public_id not in objects:
                raise FakeCloudinaryError("Not Found")
            return {"public_id": public_id}

    class FakeUtils:
        def private_download_url(self, public_id, fmt, **kwargs):
            recorded.append(("private_download_url", {"public_id": public_id, "format": fmt, **kwargs}))
            return f"https://private.example/{public_id}.{fmt}?signed=1"

    fake_cloudinary = types.ModuleType("cloudinary")
    fake_cloudinary.config = lambda **kwargs: recorded.append(("config", kwargs))
    fake_cloudinary.api = FakeApi()
    fake_cloudinary.uploader = FakeUploader()
    fake_cloudinary.utils = FakeUtils()
    monkeypatch.setitem(sys.modules, "cloudinary", fake_cloudinary)

    class FakeResponse:
        status_code = 200
        content = b"authenticated-image"

        def raise_for_status(self):
            return None

    fetched_urls: list[str] = []

    def fake_get(url, **kwargs):
        fetched_urls.append(url)
        return FakeResponse()

    monkeypatch.setattr(storage.httpx, "get", fake_get)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "cloudinary")
    monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", "township-test")
    monkeypatch.setattr(settings, "CLOUDINARY_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "CLOUDINARY_API_SECRET", "test-api-secret")

    storage.write_private_object("visitor_photos/abc.jpg", b"visitor-photo", "image/jpeg")
    public_id = "township-one-private/visitor_photos/abc"
    assert objects[public_id] == b"visitor-photo"
    assert storage.private_object_exists("visitor_photos/abc.jpg") is True
    assert storage.read_private_object("visitor_photos/abc.jpg") == b"authenticated-image"
    assert fetched_urls and "signed=1" in fetched_urls[0]
    assert storage.delete_private_object("visitor_photos/abc.jpg") is None
    assert storage.private_object_exists("visitor_photos/abc.jpg") is False

    upload_options = next(kwargs for name, kwargs in recorded if name == "upload")
    assert upload_options["type"] == "authenticated"
    assert upload_options["overwrite"] is False
    assert all(name != "upload" or kwargs["type"] == "authenticated" for name, kwargs in recorded)


def test_cloudinary_missing_asset_returns_none_and_false(monkeypatch):
    class MissingAsset(Exception):
        http_code = 404

    class FakeApi:
        def resource(self, public_id, **kwargs):
            raise MissingAsset("Not Found")

    fake_cloudinary = types.ModuleType("cloudinary")
    fake_cloudinary.config = lambda **kwargs: None
    fake_cloudinary.api = FakeApi()
    fake_cloudinary.uploader = types.SimpleNamespace()
    fake_cloudinary.utils = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "cloudinary", fake_cloudinary)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "cloudinary")
    monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", "township-test")
    monkeypatch.setattr(settings, "CLOUDINARY_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "CLOUDINARY_API_SECRET", "test-api-secret")

    assert storage.private_object_exists("missing.jpg") is False


def test_hosted_demo_requires_cloudinary_credentials_and_persistent_secrets():
    from backend.app.core.config import Settings

    valid = Settings(
        APP_ENV="demo",
        DEBUG=False,
        STORAGE_BACKEND="cloudinary",
        DATABASE_URL="postgresql+psycopg://demo:secret@db.example/township",
        SECRET_KEY="S" * 48,
        SIGNING_KEY="-----BEGIN PRIVATE KEY-----demo-----END PRIVATE KEY-----",
        RETENTION_JOB_TOKEN="R" * 48,
        CLOUDINARY_CLOUD_NAME="township-demo",
        CLOUDINARY_API_KEY="demo-key",
        CLOUDINARY_API_SECRET="demo-api-secret",
    )
    valid.validate_production_guards()

    invalid = Settings(
        APP_ENV="demo",
        DEBUG=False,
        STORAGE_BACKEND="cloudinary",
        DATABASE_URL="postgresql+psycopg://demo:secret@db.example/township",
        SECRET_KEY="S" * 48,
        SIGNING_KEY="-----BEGIN PRIVATE KEY-----demo-----END PRIVATE KEY-----",
        RETENTION_JOB_TOKEN="R" * 48,
    )
    with pytest.raises(RuntimeError, match="CLOUDINARY_API_SECRET"):
        invalid.validate_production_guards()
