"""Upload module tests (Module 14 — stub Firebase signed URLs)."""

import bcrypt
import pytest

from auth.models import User

ADMIN_EMAIL = "upload_admin@test.com"
ADMIN_PASS = "adminpass123"
USER_EMAIL = "upload_user@test.com"
USER_PASS = "userpass123"


async def _make_admin(db):
    a = User(
        name="UploadAdmin",
        email=ADMIN_EMAIL,
        password_hash=bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt()).decode(),
        role="admin",
        is_active=True,
        is_email_verified=True,
    )
    db.add(a)
    await db.commit()


async def _make_customer(db):
    u = User(
        name="UploadUser",
        email=USER_EMAIL,
        password_hash=bcrypt.hashpw(USER_PASS.encode(), bcrypt.gensalt()).decode(),
        role="customer",
        is_active=True,
        is_email_verified=True,
    )
    db.add(u)
    await db.commit()


async def _login_admin(client):
    res = await client.post("/api/v1/admin/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASS,
    })
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])


async def _login_user(client):
    res = await client.post("/api/v1/auth/login", json={
        "email": USER_EMAIL, "password": USER_PASS,
    })
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])


@pytest.mark.asyncio
async def test_upload_product_image(client, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        "/api/v1/upload/product-image",
        json={"filename": "cover.jpg", "content_type": "image/jpeg", "size": 524288},
    )
    assert res.status_code == 200
    body = res.json()
    assert "upload_url" in body and "public_url" in body
    assert "expires_at" in body


@pytest.mark.asyncio
async def test_upload_product_image_non_admin(client, db):
    await _make_customer(db)
    await _login_user(client)
    res = await client.post(
        "/api/v1/upload/product-image",
        json={"filename": "cover.jpg", "content_type": "image/jpeg", "size": 524288},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_upload_custom_photo(client, db):
    await _make_customer(db)
    await _login_user(client)
    res = await client.post(
        "/api/v1/upload/custom-photo",
        json={"filename": "photo.jpg", "content_type": "image/jpeg", "size": 1048576},
    )
    assert res.status_code == 200
    body = res.json()
    assert "upload_url" in body and "firebase_path" in body
    assert body["firebase_path"].startswith("custom_photos/")
    assert "expires_at" in body


@pytest.mark.asyncio
async def test_upload_custom_photo_unauth(client, db):
    res = await client.post(
        "/api/v1/upload/custom-photo",
        json={"filename": "photo.jpg", "content_type": "image/jpeg", "size": 1048576},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_upload_case_image(client, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        "/api/v1/upload/case-image",
        json={"filename": "case.png", "content_type": "image/png", "size": 262144},
    )
    assert res.status_code == 200
    body = res.json()
    assert "upload_url" in body and "public_url" in body
    assert "expires_at" in body


@pytest.mark.asyncio
async def test_upload_rejects_oversize(client, db):
    """size > 20MB → 422 schema 守門。"""
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        "/api/v1/upload/product-image",
        json={
            "filename": "big.jpg", "content_type": "image/jpeg",
            "size": 25_000_000,
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_zero_size(client, db):
    """size <= 0 → 422。"""
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(
        "/api/v1/upload/product-image",
        json={"filename": "x.jpg", "content_type": "image/jpeg", "size": 0},
    )
    assert res.status_code == 422
