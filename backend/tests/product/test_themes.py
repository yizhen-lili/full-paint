"""Module 16 — themes (主題) tests."""
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from auth.models import User
from product.models import ProductSeries

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
THEMES_URL = "/api/v1/admin/themes"
SERIES_URL = "/api/v1/admin/series"

ADMIN_USER = {
    "name": "主題管理員",
    "email": "themes_admin@example.com",
    "password": "adminpass123",
}
CUSTOMER_USER = {
    "name": "一般用戶",
    "email": "themes_customer@example.com",
    "password": "custpass123",
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


# ── Create / list / order ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_create_theme(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.post(THEMES_URL, json={
        "name": "萌寵",
        "description": "可愛動物主題",
        "cover_image_url": "https://example.com/pets.jpg",
        "sort_order": 10,
    })
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "萌寵"
    assert body["sort_order"] == 10
    assert body["series_count"] == 0


@pytest.mark.asyncio
async def test_admin_create_theme_duplicate_name_409(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    await client.post(THEMES_URL, json={"name": "風景", "sort_order": 0})
    res = await client.post(THEMES_URL, json={"name": "風景", "sort_order": 0})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_list_themes_sort_order(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    await client.post(THEMES_URL, json={"name": "B", "sort_order": 20})
    await client.post(THEMES_URL, json={"name": "A", "sort_order": 10})
    await client.post(THEMES_URL, json={"name": "C", "sort_order": 30})

    res = await client.get(THEMES_URL)
    items = res.json()["items"]
    assert [i["name"] for i in items] == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_list_themes_series_count(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    create_res = await client.post(THEMES_URL, json={"name": "風景"})
    theme_id = create_res.json()["id"]

    db.add(ProductSeries(name="山系列", theme_id=theme_id))
    db.add(ProductSeries(name="海系列", theme_id=theme_id))
    db.add(ProductSeries(name="無歸屬系列"))
    await db.commit()

    res = await client.get(THEMES_URL)
    items = {i["name"]: i["series_count"] for i in res.json()["items"]}
    assert items["風景"] == 2


# ── Update / delete ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_theme(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    create_res = await client.post(THEMES_URL, json={"name": "原名"})
    theme_id = create_res.json()["id"]
    res = await client.put(f"{THEMES_URL}/{theme_id}", json={
        "name": "新名",
        "description": "改了",
        "sort_order": 5,
    })
    assert res.status_code == 200
    assert res.json()["name"] == "新名"
    assert res.json()["description"] == "改了"


@pytest.mark.asyncio
async def test_delete_theme_no_series(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    create_res = await client.post(THEMES_URL, json={"name": "可丟"})
    theme_id = create_res.json()["id"]
    res = await client.delete(f"{THEMES_URL}/{theme_id}")
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_delete_theme_with_series_sets_null(client: AsyncClient, db):
    """刪主題時系列的 theme_id 應該變 NULL（ON DELETE SET NULL），系列不被刪。"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    create_res = await client.post(THEMES_URL, json={"name": "萌寵"})
    theme_id = create_res.json()["id"]

    s = ProductSeries(name="貓咪", theme_id=theme_id)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    series_id = s.id

    res = await client.delete(f"{THEMES_URL}/{theme_id}")
    assert res.status_code == 204

    refreshed = (await db.execute(
        select(ProductSeries).where(ProductSeries.id == series_id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert refreshed is not None
    assert refreshed.theme_id is None


# ── Auth guards ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_themes_customer_403(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    res = await client.get(THEMES_URL)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_themes_unauth_401(client: AsyncClient, db):
    res = await client.get(THEMES_URL)
    assert res.status_code == 401


# ── Series-with-theme integration ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_series_with_theme(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    theme_res = await client.post(THEMES_URL, json={"name": "萌寵"})
    theme_id = theme_res.json()["id"]

    res = await client.post(SERIES_URL, json={
        "name": "貓咪系列",
        "description": None,
        "theme_id": theme_id,
    })
    assert res.status_code == 201
    body = res.json()
    assert body["theme_id"] == theme_id
    assert body["theme_name"] == "萌寵"

    list_res = await client.get(SERIES_URL)
    items = list_res.json()["items"]
    assert any(s["theme_name"] == "萌寵" for s in items)


@pytest.mark.asyncio
async def test_list_series_filter_by_theme(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    t1 = await client.post(THEMES_URL, json={"name": "A"})
    t2 = await client.post(THEMES_URL, json={"name": "B"})
    await client.post(SERIES_URL, json={"name": "S-A1", "theme_id": t1.json()["id"]})
    await client.post(SERIES_URL, json={"name": "S-A2", "theme_id": t1.json()["id"]})
    await client.post(SERIES_URL, json={"name": "S-B1", "theme_id": t2.json()["id"]})

    res = await client.get(f"{SERIES_URL}?theme_id={t1.json()['id']}")
    names = {s["name"] for s in res.json()["items"]}
    assert names == {"S-A1", "S-A2"}


@pytest.mark.asyncio
async def test_create_series_with_invalid_theme_404(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    fake = str(uuid.uuid4())
    res = await client.post(SERIES_URL, json={
        "name": "孤兒系列",
        "theme_id": fake,
    })
    assert res.status_code == 404
