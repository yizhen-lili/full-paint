import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from auth.models import User
from product.models import Product, ProductSeries, ProductStatusEnum

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
SERIES_URL = "/api/v1/admin/series"

ADMIN_USER = {
    "name": "系列管理員", "email": "series_admin@example.com", "password": "adminpass123"
}
CUSTOMER_USER = {
    "name": "一般用戶", "email": "series_customer@example.com", "password": "custpass123"
}


async def _make_admin(client, db):
    await client.post(REGISTER_URL, json=ADMIN_USER)
    result = await db.execute(select(User).where(User.email == ADMIN_USER["email"]))
    user = result.scalar_one()
    user.is_email_verified = True
    user.role = "admin"
    await db.commit()


async def _make_customer(client, db):
    await client.post(REGISTER_URL, json=CUSTOMER_USER)
    result = await db.execute(select(User).where(User.email == CUSTOMER_USER["email"]))
    user = result.scalar_one()
    user.is_email_verified = True
    await db.commit()


async def _login(client, email, password):
    res = await client.post(LOGIN_URL, json={"email": email, "password": password})
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])


async def _create_series(db, name="測試系列", description=None) -> ProductSeries:
    series = ProductSeries(name=name, description=description)
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return series


# ── GET /admin/series ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_series_empty(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    res = await client.get(SERIES_URL)
    assert res.status_code == 200
    assert res.json()["items"] == []


@pytest.mark.asyncio
async def test_list_series_with_product_count(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    series = await _create_series(db)
    db.add(Product(
        title="商品A", cover_image_url="http://img.test/a.png",
        series_id=series.id, status=ProductStatusEnum.draft,
    ))
    await db.commit()

    res = await client.get(SERIES_URL)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["product_count"] == 1


@pytest.mark.asyncio
async def test_list_series_non_admin(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    assert (await client.get(SERIES_URL)).status_code == 403


@pytest.mark.asyncio
async def test_list_series_unauthenticated(client: AsyncClient, db):
    assert (await client.get(SERIES_URL)).status_code == 401


# ── POST /admin/series ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_series_ok(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    res = await client.post(SERIES_URL, json={"name": "春季系列", "description": "春天主題"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "春季系列"
    assert data["product_count"] == 0


@pytest.mark.asyncio
async def test_create_series_duplicate_name(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    await client.post(SERIES_URL, json={"name": "重複系列"})
    res = await client.post(SERIES_URL, json={"name": "重複系列"})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_create_series_non_admin(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    assert (await client.post(SERIES_URL, json={"name": "X"})).status_code == 403


@pytest.mark.asyncio
async def test_create_series_unauthenticated(client: AsyncClient, db):
    assert (await client.post(SERIES_URL, json={"name": "X"})).status_code == 401


# ── PUT /admin/series/{id} ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_series_ok(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    series = await _create_series(db)
    res = await client.put(f"{SERIES_URL}/{series.id}", json={"name": "更新系列"})
    assert res.status_code == 200
    assert res.json()["name"] == "更新系列"


@pytest.mark.asyncio
async def test_update_series_not_found(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    res = await client.put(f"{SERIES_URL}/{uuid.uuid4()}", json={"name": "X"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_series_duplicate_name(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    s1 = await _create_series(db, name="系列一")
    await _create_series(db, name="系列二")
    res = await client.put(f"{SERIES_URL}/{s1.id}", json={"name": "系列二"})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_update_series_non_admin(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    assert (await client.put(f"{SERIES_URL}/{uuid.uuid4()}", json={"name": "X"})).status_code == 403


@pytest.mark.asyncio
async def test_update_series_unauthenticated(client: AsyncClient, db):
    assert (await client.put(f"{SERIES_URL}/{uuid.uuid4()}", json={"name": "X"})).status_code == 401


# ── DELETE /admin/series/{id} ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_series_ok(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    series = await _create_series(db)
    res = await client.delete(f"{SERIES_URL}/{series.id}")
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_delete_series_not_found(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    assert (await client.delete(f"{SERIES_URL}/{uuid.uuid4()}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_series_with_products(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    series = await _create_series(db)
    db.add(Product(
        title="商品B", cover_image_url="http://img.test/b.png",
        series_id=series.id, status=ProductStatusEnum.draft,
    ))
    await db.commit()
    res = await client.delete(f"{SERIES_URL}/{series.id}")
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_delete_series_non_admin(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    assert (await client.delete(f"{SERIES_URL}/{uuid.uuid4()}")).status_code == 403


@pytest.mark.asyncio
async def test_delete_series_unauthenticated(client: AsyncClient, db):
    assert (await client.delete(f"{SERIES_URL}/{uuid.uuid4()}")).status_code == 401
