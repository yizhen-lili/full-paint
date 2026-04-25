import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from auth.models import User
from product.models import Product, ProductStatusEnum, ProductTag, Tag

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
TAGS_URL = "/api/v1/admin/tags"

ADMIN_USER = {
    "name": "標籤管理員", "email": "tag_admin@example.com", "password": "adminpass123"
}
CUSTOMER_USER = {
    "name": "一般用戶", "email": "tag_customer@example.com", "password": "custpass123"
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


async def _create_tag(db, name="測試標籤") -> Tag:
    tag = Tag(name=name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


# ── GET /admin/tags ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tags_empty(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    res = await client.get(TAGS_URL)
    assert res.status_code == 200
    assert res.json()["items"] == []


@pytest.mark.asyncio
async def test_list_tags_with_product_count(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    tag = await _create_tag(db)
    product = Product(
        title="商品A", cover_image_url="http://img.test/a.png",
        status=ProductStatusEnum.draft,
    )
    db.add(product)
    await db.flush()
    db.add(ProductTag(product_id=product.id, tag_id=tag.id))
    await db.commit()

    res = await client.get(TAGS_URL)
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["product_count"] == 1


@pytest.mark.asyncio
async def test_list_tags_non_admin(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    assert (await client.get(TAGS_URL)).status_code == 403


@pytest.mark.asyncio
async def test_list_tags_unauthenticated(client: AsyncClient, db):
    assert (await client.get(TAGS_URL)).status_code == 401


# ── POST /admin/tags ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_tag_ok(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    res = await client.post(TAGS_URL, json={"name": "人像"})
    assert res.status_code == 201
    assert res.json()["name"] == "人像"
    assert res.json()["product_count"] == 0


@pytest.mark.asyncio
async def test_create_tag_duplicate(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    await client.post(TAGS_URL, json={"name": "重複"})
    res = await client.post(TAGS_URL, json={"name": "重複"})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_create_tag_non_admin(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    assert (await client.post(TAGS_URL, json={"name": "X"})).status_code == 403


@pytest.mark.asyncio
async def test_create_tag_unauthenticated(client: AsyncClient, db):
    assert (await client.post(TAGS_URL, json={"name": "X"})).status_code == 401


# ── PUT /admin/tags/{id} ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_tag_ok(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    tag = await _create_tag(db)
    res = await client.put(f"{TAGS_URL}/{tag.id}", json={"name": "更新標籤"})
    assert res.status_code == 200
    assert res.json()["name"] == "更新標籤"


@pytest.mark.asyncio
async def test_update_tag_not_found(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    assert (await client.put(f"{TAGS_URL}/{uuid.uuid4()}", json={"name": "X"})).status_code == 404


@pytest.mark.asyncio
async def test_update_tag_duplicate_name(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    t1 = await _create_tag(db, name="標籤一")
    await _create_tag(db, name="標籤二")
    res = await client.put(f"{TAGS_URL}/{t1.id}", json={"name": "標籤二"})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_update_tag_non_admin(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    assert (await client.put(f"{TAGS_URL}/{uuid.uuid4()}", json={"name": "X"})).status_code == 403


@pytest.mark.asyncio
async def test_update_tag_unauthenticated(client: AsyncClient, db):
    assert (await client.put(f"{TAGS_URL}/{uuid.uuid4()}", json={"name": "X"})).status_code == 401


# ── DELETE /admin/tags/{id} ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_tag_ok(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    tag = await _create_tag(db)
    res = await client.delete(f"{TAGS_URL}/{tag.id}")
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_delete_tag_not_found(client: AsyncClient, db):
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    assert (await client.delete(f"{TAGS_URL}/{uuid.uuid4()}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_tag_cascades_product_tags(client: AsyncClient, db):
    """刪除標籤後 product_tags 關聯應自動移除。"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])
    tag = await _create_tag(db)
    product = Product(
        title="商品B", cover_image_url="http://img.test/b.png",
        status=ProductStatusEnum.draft,
    )
    db.add(product)
    await db.flush()
    db.add(ProductTag(product_id=product.id, tag_id=tag.id))
    await db.commit()

    await client.delete(f"{TAGS_URL}/{tag.id}")

    remaining = await db.execute(
        select(ProductTag).where(ProductTag.tag_id == tag.id)
    )
    assert remaining.scalars().all() == []


@pytest.mark.asyncio
async def test_delete_tag_non_admin(client: AsyncClient, db):
    await _make_customer(client, db)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])
    assert (await client.delete(f"{TAGS_URL}/{uuid.uuid4()}")).status_code == 403


@pytest.mark.asyncio
async def test_delete_tag_unauthenticated(client: AsyncClient, db):
    assert (await client.delete(f"{TAGS_URL}/{uuid.uuid4()}")).status_code == 401
