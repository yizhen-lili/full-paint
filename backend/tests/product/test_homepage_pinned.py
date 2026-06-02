"""Module 22 — 首頁置頂商品（homepage_order + admin reorder + public list）。

涵蓋 module_plan 22 第九節 + 第十二節合併後的 17 個 case。
"""
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from auth.models import User
from product.models import Product, ProductStatusEnum, ProductVariant
from production.models import ProductionJob

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ADMIN_PINNED_URL = "/api/v1/admin/products/homepage-pinned"
ADMIN_ORDER_URL = "/api/v1/admin/products/homepage-order"
ADMIN_LIST_URL = "/api/v1/admin/products"
PUBLIC_PINNED_URL = "/api/v1/products/homepage-pinned"

ADMIN_USER = {
    "name": "首頁置頂管理員",
    "email": "homepage_pinned_admin@example.com",
    "password": "adminpass123",
}


async def _make_admin(client, db):
    await client.post(REGISTER_URL, json=ADMIN_USER)
    result = await db.execute(select(User).where(User.email == ADMIN_USER["email"]))
    user = result.scalar_one()
    user.is_email_verified = True
    user.role = "admin"
    await db.commit()


async def _login(client, email, password):
    res = await client.post(LOGIN_URL, json={"email": email, "password": password})
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])


async def _create_on_sale_product(db, title="商品", with_variant=True):
    product = Product(
        title=title,
        cover_image_url="http://img.test/cover.png",
        status=ProductStatusEnum.on_sale,
    )
    db.add(product)
    await db.flush()

    if with_variant:
        job = ProductionJob(
            canvas_w_cm=30,
            canvas_h_cm=40,
            difficulty="beginner",
            detail="standard",
            num_colors_used=18,
            approved=True,
            status="completed",
            filled_template_url="http://example.com/filled.png",
        )
        db.add(job)
        await db.flush()

        variant = ProductVariant(
            product_id=product.id,
            production_job_id=job.id,
            price=Decimal("397"),
            price_formula_base=Decimal("397"),
            is_active=True,
        )
        db.add(variant)

    await db.commit()
    await db.refresh(product)
    return product


async def _create_draft_product(db, title="草稿商品"):
    product = Product(
        title=title,
        cover_image_url="http://img.test/cover.png",
        status=ProductStatusEnum.draft,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def _create_off_sale_product(db, title="下架商品"):
    product = Product(
        title=title,
        cover_image_url="http://img.test/cover.png",
        status=ProductStatusEnum.off_sale,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


# ── Admin list pinned ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_pinned_empty(client: AsyncClient, db):
    """空 DB 列 pinned 回 200 + 空 items"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(ADMIN_PINNED_URL)
    assert res.status_code == 200
    assert res.json() == {"items": []}


@pytest.mark.asyncio
async def test_list_pinned_ordered(client: AsyncClient, db):
    """3 筆置頂，依 homepage_order ASC 排"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    p1 = await _create_on_sale_product(db, title="A")
    p2 = await _create_on_sale_product(db, title="B")
    p3 = await _create_on_sale_product(db, title="C")

    # 直接 SQL 設 order，避免依賴 reorder endpoint
    p1.homepage_order = 3
    p2.homepage_order = 1
    p3.homepage_order = 2
    await db.commit()

    res = await client.get(ADMIN_PINNED_URL)
    assert res.status_code == 200
    items = res.json()["items"]
    titles = [item["title"] for item in items]
    assert titles == ["B", "C", "A"]  # order 1, 2, 3
    orders = [item["homepage_order"] for item in items]
    assert orders == [1, 2, 3]


# ── Admin set homepage-order ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_homepage_order_clear_all(client: AsyncClient, db):
    """空陣列 = 把所有 homepage_order set NULL"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    p1 = await _create_on_sale_product(db, title="A")
    p1.homepage_order = 1
    await db.commit()

    res = await client.post(ADMIN_ORDER_URL, json={"product_ids": []})
    assert res.status_code == 200
    assert res.json() == {"items": []}

    await db.refresh(p1)
    assert p1.homepage_order is None


@pytest.mark.asyncio
async def test_set_homepage_order_assigns_sequential(client: AsyncClient, db):
    """3 筆 on_sale → 依序賦值 1/2/3"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    p1 = await _create_on_sale_product(db, title="A")
    p2 = await _create_on_sale_product(db, title="B")
    p3 = await _create_on_sale_product(db, title="C")

    res = await client.post(
        ADMIN_ORDER_URL,
        json={"product_ids": [str(p3.id), str(p1.id), str(p2.id)]},
    )
    assert res.status_code == 200

    await db.refresh(p1)
    await db.refresh(p2)
    await db.refresh(p3)
    assert p3.homepage_order == 1
    assert p1.homepage_order == 2
    assert p2.homepage_order == 3


@pytest.mark.asyncio
async def test_set_homepage_order_rejects_unknown_id(client: AsyncClient, db):
    """含不存在 id → 400"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    p1 = await _create_on_sale_product(db, title="A")
    fake = uuid4()

    res = await client.post(
        ADMIN_ORDER_URL,
        json={"product_ids": [str(p1.id), str(fake)]},
    )
    assert res.status_code == 400
    assert "不存在" in res.json()["detail"]


@pytest.mark.asyncio
async def test_set_homepage_order_rejects_duplicates(client: AsyncClient, db):
    """含重複 id → 422 (Pydantic validation)"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    p1 = await _create_on_sale_product(db, title="A")

    res = await client.post(
        ADMIN_ORDER_URL,
        json={"product_ids": [str(p1.id), str(p1.id)]},
    )
    # Pydantic field_validator → 422
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_set_homepage_order_rejects_over_limit(client: AsyncClient, db):
    """13 筆 → 422 (schema max_length=12)"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    ids = [str(uuid4()) for _ in range(13)]
    res = await client.post(ADMIN_ORDER_URL, json={"product_ids": ids})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_set_homepage_order_accepts_max_12(client: AsyncClient, db):
    """剛好 12 筆 on_sale → 200"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    products = []
    for i in range(12):
        p = await _create_on_sale_product(db, title=f"P{i}")
        products.append(p)

    res = await client.post(
        ADMIN_ORDER_URL,
        json={"product_ids": [str(p.id) for p in products]},
    )
    assert res.status_code == 200
    assert len(res.json()["items"]) == 12


@pytest.mark.asyncio
async def test_set_homepage_order_rejects_draft(client: AsyncClient, db):
    """含 draft → 400"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    p_on_sale = await _create_on_sale_product(db, title="A")
    p_draft = await _create_draft_product(db, title="B-draft")

    res = await client.post(
        ADMIN_ORDER_URL,
        json={"product_ids": [str(p_on_sale.id), str(p_draft.id)]},
    )
    assert res.status_code == 400
    assert "未上架" in res.json()["detail"]


@pytest.mark.asyncio
async def test_set_homepage_order_rejects_off_sale(client: AsyncClient, db):
    """含 off_sale → 400"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    p_on_sale = await _create_on_sale_product(db, title="A")
    p_off = await _create_off_sale_product(db, title="B-off")

    res = await client.post(
        ADMIN_ORDER_URL,
        json={"product_ids": [str(p_on_sale.id), str(p_off.id)]},
    )
    assert res.status_code == 400
    assert "未上架" in res.json()["detail"]


@pytest.mark.asyncio
async def test_set_homepage_order_shrinks_correctly(client: AsyncClient, db):
    """先 5 筆 → 再 2 筆，多餘 3 筆變 NULL"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    products = []
    for i in range(5):
        p = await _create_on_sale_product(db, title=f"P{i}")
        products.append(p)

    # 第一次：5 筆
    await client.post(
        ADMIN_ORDER_URL,
        json={"product_ids": [str(p.id) for p in products]},
    )
    # 第二次：只留前 2 筆
    res = await client.post(
        ADMIN_ORDER_URL,
        json={"product_ids": [str(products[0].id), str(products[1].id)]},
    )
    assert res.status_code == 200

    for p in products:
        await db.refresh(p)
    assert products[0].homepage_order == 1
    assert products[1].homepage_order == 2
    assert products[2].homepage_order is None
    assert products[3].homepage_order is None
    assert products[4].homepage_order is None


# ── Public list homepage-pinned ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_public_pinned_empty(client: AsyncClient, db):
    """無置頂 → 空 items（public 端，無需 auth）"""
    res = await client.get(PUBLIC_PINNED_URL)
    assert res.status_code == 200
    assert res.json() == {"items": []}


@pytest.mark.asyncio
async def test_public_pinned_filters_out_draft(client: AsyncClient, db):
    """直接 SQL 設 draft 商品有 homepage_order；public endpoint 仍不回（status filter）"""
    p_draft = await _create_draft_product(db, title="A-draft")
    # bypass service layer 的 status 驗證，直接 SQL 設置
    p_draft.homepage_order = 1
    await db.commit()

    res = await client.get(PUBLIC_PINNED_URL)
    assert res.status_code == 200
    assert res.json() == {"items": []}


@pytest.mark.asyncio
async def test_public_pinned_filters_out_no_active_variant(client: AsyncClient, db):
    """on_sale + homepage_order 但無 active variant → 不回（zombie 商品）"""
    p = await _create_on_sale_product(db, title="A", with_variant=False)
    p.homepage_order = 1
    await db.commit()

    res = await client.get(PUBLIC_PINNED_URL)
    assert res.status_code == 200
    assert res.json() == {"items": []}


@pytest.mark.asyncio
async def test_public_pinned_returns_ordered(client: AsyncClient, db):
    """正常 happy path：on_sale + variant + homepage_order，依 order ASC 回"""
    p_a = await _create_on_sale_product(db, title="A")
    p_b = await _create_on_sale_product(db, title="B")
    p_c = await _create_on_sale_product(db, title="C")
    p_a.homepage_order = 2
    p_b.homepage_order = 1
    p_c.homepage_order = 3
    await db.commit()

    res = await client.get(PUBLIC_PINNED_URL)
    assert res.status_code == 200
    titles = [item["title"] for item in res.json()["items"]]
    assert titles == ["B", "A", "C"]


# ── Admin list 加 homepage_order 欄位 / exclude_ids ─────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_includes_homepage_order(client: AsyncClient, db):
    """admin list response 每筆都帶 homepage_order 欄位"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    p1 = await _create_on_sale_product(db, title="A")
    p1.homepage_order = 1
    await db.commit()

    res = await client.get(ADMIN_LIST_URL)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    assert all("homepage_order" in item for item in items)
    pinned = next(item for item in items if item["title"] == "A")
    assert pinned["homepage_order"] == 1


@pytest.mark.asyncio
async def test_admin_list_exclude_ids(client: AsyncClient, db):
    """exclude_ids query 把指定 id 從 list 排掉"""
    await _make_admin(client, db)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    await _create_on_sale_product(db, title="Keep")
    p2 = await _create_on_sale_product(db, title="Exclude")

    res = await client.get(
        ADMIN_LIST_URL,
        params={"exclude_ids": str(p2.id)},
    )
    assert res.status_code == 200
    titles = [item["title"] for item in res.json()["items"]]
    assert "Keep" in titles
    assert "Exclude" not in titles


# ── DB-level CheckConstraint ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_db_rejects_zero_homepage_order(client: AsyncClient, db):
    """CheckConstraint: homepage_order >= 1 — 直接 SQL set 0 → IntegrityError"""
    p = await _create_on_sale_product(db, title="A")

    with pytest.raises(IntegrityError):
        await db.execute(
            text(
                "UPDATE products SET homepage_order = 0 WHERE id = :pid"
            ),
            {"pid": str(p.id)},
        )
        await db.commit()
