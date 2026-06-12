"""Module paint_requirements — 顏料準備清單查詢 endpoint 測試。"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import bcrypt
import pytest
from httpx import AsyncClient

from auth.models import User
from color.models import PhysicalColor
from custom.models import (
    CustomRequest,
    CustomRequestStatusEnum,
    CustomRequestTypeEnum,
)
from palette.models import PaletteColorMapping
from product.models import Product, ProductStatusEnum, ProductVariant
from production.models import JobStatusEnum, ProductionJob

ADMIN_EMAIL = "pr_admin@test.com"
ADMIN_PASS = "adminpass123"
URL = "/api/v1/admin/paint-requirements"
SOURCES_URL = "/api/v1/admin/paint-requirements/sources"


async def _make_admin(db):
    a = User(
        name="PRAdmin",
        email=ADMIN_EMAIL,
        password_hash=bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt()).decode(),
        role="admin",
        is_active=True,
        is_email_verified=True,
    )
    db.add(a)
    await db.commit()


async def _login_admin(client: AsyncClient):
    res = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
    )
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])


async def _make_color(db, *, code, name, rgb, stock_ml):
    c = PhysicalColor(
        code=code,
        name=name,
        rgb=rgb,
        stock_ml=Decimal(str(stock_ml)),
        is_active=True,
    )
    db.add(c)
    await db.flush()
    return c


async def _make_finalized_job(
    db, *, w=30, h=40, mappings=None, custom_request_id=None,
) -> ProductionJob:
    """建一筆 finalized job + 對應 mappings；mappings 格式同 test。"""
    job = ProductionJob(
        detail="standard", difficulty="beginner", mode="standard",
        canvas_w_cm=w, canvas_h_cm=h,
        svg_url="https://e.com/x.svg",
        approved=True, status=JobStatusEnum.completed,
        finalized_at=datetime.now(UTC),
        custom_request_id=custom_request_id,
    )
    db.add(job)
    await db.flush()
    for m in mappings or []:
        db.add(PaletteColorMapping(
            production_job_id=job.id,
            template_id=m["template_id"],
            algorithm_rgb=m.get("algorithm_rgb", {"r": 0, "g": 0, "b": 0}),
            physical_color_id=m["physical_color_id"],
            required_ml=Decimal(str(m["required_ml"])),
            output_label=m["output_label"],
        ))
    await db.flush()
    return job


async def _bind_to_product(db, job, *, title="測試畫", status=ProductStatusEnum.on_sale):
    prod = Product(title=title, description="", cover_image_url="x", status=status)
    db.add(prod)
    await db.flush()
    variant = ProductVariant(
        product_id=prod.id, production_job_id=job.id,
        price=Decimal("500"), price_formula_base=Decimal("500"),
        is_active=True,
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return prod, variant


# ── calculate_for_job 行為測試 ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_calculate_happy_path(client: AsyncClient, db):
    """finalized job + qty=2 → 各物理色 × 2、stock 充足。"""
    await _make_admin(db)
    red = await _make_color(db, code="P001", name="紅", rgb=[255, 0, 0], stock_ml=200)
    blue = await _make_color(db, code="P002", name="藍", rgb=[0, 0, 255], stock_ml=200)
    await db.commit()

    job = await _make_finalized_job(
        db,
        mappings=[
            {"template_id": 1, "physical_color_id": red.id,
             "required_ml": 12.5, "output_label": 1},
            {"template_id": 2, "physical_color_id": red.id,
             "required_ml": 7.5, "output_label": 1},  # 同色合併
            {"template_id": 3, "physical_color_id": blue.id,
             "required_ml": 10.0, "output_label": 2},
        ],
    )
    await db.commit()

    await _login_admin(client)
    res = await client.get(URL, params={
        "production_job_id": str(job.id), "quantity": 2,
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["production_job_id"] == str(job.id)
    assert body["quantity"] == 2
    assert len(body["items"]) == 2
    assert body["summary"]["total_colors"] == 2
    assert body["summary"]["short_count"] == 0

    by_code = {i["code"]: i for i in body["items"]}
    assert by_code["P001"]["required_per_unit_ml"] == 20.0
    assert by_code["P001"]["total_required_ml"] == 40.0
    assert by_code["P001"]["stock_ml"] == 200.0
    assert by_code["P001"]["is_short"] is False
    assert by_code["P001"]["output_label"] == 1
    assert by_code["P001"]["hex"] == "#FF0000"
    assert by_code["P002"]["total_required_ml"] == 20.0


@pytest.mark.asyncio
async def test_calculate_with_shortage(client: AsyncClient, db):
    """某色 stock < required → is_short=True + shortage_ml > 0。"""
    await _make_admin(db)
    red = await _make_color(db, code="P001", name="紅", rgb=[255, 0, 0], stock_ml=5)
    await db.commit()

    job = await _make_finalized_job(
        db,
        mappings=[{
            "template_id": 1, "physical_color_id": red.id,
            "required_ml": 10.0, "output_label": 1,
        }],
    )
    await db.commit()

    await _login_admin(client)
    res = await client.get(URL, params={
        "production_job_id": str(job.id), "quantity": 3,
    })
    assert res.status_code == 200
    body = res.json()
    item = body["items"][0]
    assert item["total_required_ml"] == 30.0
    assert item["stock_ml"] == 5.0
    assert item["shortage_ml"] == 25.0
    assert item["is_short"] is True
    assert body["summary"]["short_count"] == 1


@pytest.mark.asyncio
async def test_job_not_finalized_rejected(client: AsyncClient, db):
    """job.finalized_at=None → 400 + code=JOB_NOT_FINALIZED。"""
    await _make_admin(db)
    job = ProductionJob(
        detail="standard", difficulty="beginner", mode="standard",
        canvas_w_cm=30, canvas_h_cm=40,
        svg_url="https://e.com/x.svg",
        approved=True, status=JobStatusEnum.completed,
        finalized_at=None,
    )
    db.add(job)
    await db.commit()

    await _login_admin(client)
    res = await client.get(URL, params={
        "production_job_id": str(job.id), "quantity": 1,
    })
    assert res.status_code == 400
    body = res.json()
    assert body["code"] == "JOB_NOT_FINALIZED"
    assert body["production_job_id"] == str(job.id)


@pytest.mark.asyncio
async def test_job_not_found(client: AsyncClient, db):
    """job 不存在 → 404。"""
    await _make_admin(db)
    await db.commit()
    await _login_admin(client)
    res = await client.get(URL, params={
        "production_job_id": str(uuid.uuid4()), "quantity": 1,
    })
    assert res.status_code == 404


# ── sources endpoint 三類來源測試 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_sources_lists_product_with_variants(client: AsyncClient, db):
    """商品 + variant（綁 completed job）出現在 products tab。"""
    await _make_admin(db)
    job = await _make_finalized_job(db)
    _prod, variant = await _bind_to_product(db, job, title="商品 A")

    await _login_admin(client)
    res = await client.get(SOURCES_URL)
    assert res.status_code == 200, res.text
    body = res.json()
    assert any(p["title"] == "商品 A" for p in body["products"])
    p = next(p for p in body["products"] if p["title"] == "商品 A")
    assert len(p["variants"]) == 1
    v = p["variants"][0]
    assert v["variant_id"] == str(variant.id)
    assert v["production_job_id"] == str(job.id)
    assert v["is_finalized"] is True


@pytest.mark.asyncio
async def test_sources_lists_custom_request(client: AsyncClient, db):
    """有綁 production_job 的客製訂單出現在 custom_requests tab。"""
    await _make_admin(db)
    customer = User(
        name="客戶大白", email="custfan@test.com",
        password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        role="customer", is_active=True, is_email_verified=True,
    )
    db.add(customer)
    await db.flush()
    cr = CustomRequest(
        user_id=customer.id,
        request_type=CustomRequestTypeEnum.custom_photo,
        status=CustomRequestStatusEnum.quote_confirmed,
    )
    db.add(cr)
    await db.flush()
    job = await _make_finalized_job(db, custom_request_id=cr.id)
    await db.commit()

    await _login_admin(client)
    res = await client.get(SOURCES_URL)
    assert res.status_code == 200
    body = res.json()
    assert len(body["custom_requests"]) >= 1
    matched = [c for c in body["custom_requests"] if c["production_job_id"] == str(job.id)]
    assert len(matched) == 1
    c = matched[0]
    assert c["custom_request_id"] == str(cr.id)
    assert c["label"] == "客製 - 客戶大白"
    assert c["is_finalized"] is True


@pytest.mark.asyncio
async def test_sources_lists_standalone_job(client: AsyncClient, db):
    """無 variant 無 custom_request 的 completed job 出現在 standalone_jobs tab。"""
    await _make_admin(db)
    job = await _make_finalized_job(db)  # 沒綁 variant、沒綁 custom_request
    await db.commit()

    await _login_admin(client)
    res = await client.get(SOURCES_URL)
    assert res.status_code == 200
    body = res.json()
    matched = [s for s in body["standalone_jobs"] if s["production_job_id"] == str(job.id)]
    assert len(matched) == 1
    s = matched[0]
    assert s["label"].startswith("試驗任務 #")
    assert s["is_finalized"] is True
    # 不該重複出現在 products / custom_requests
    assert not any(
        v["production_job_id"] == str(job.id)
        for p in body["products"] for v in p["variants"]
    )
    assert not any(
        c["production_job_id"] == str(job.id) for c in body["custom_requests"]
    )
