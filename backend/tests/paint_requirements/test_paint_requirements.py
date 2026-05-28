"""Module paint_requirements — 顏料準備清單查詢 endpoint 測試。"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import bcrypt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from auth.models import User
from color.models import PhysicalColor
from palette.models import PaletteColorMapping
from product.models import Product, ProductStatusEnum, ProductVariant
from production.models import JobStatusEnum, ProductionJob

ADMIN_EMAIL = "pr_admin@test.com"
ADMIN_PASS = "adminpass123"
URL = "/api/v1/admin/paint-requirements"


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


async def _make_finalized_job_with_variant(
    db, *, w=30, h=40, mappings=None,
) -> tuple[ProductionJob, ProductVariant]:
    """建一筆 finalized job + 對應 mappings + 綁到一個 product variant。

    mappings 格式：[{"template_id": 1, "physical_color_id": UUID, "required_ml": float,
                    "output_label": 1, "algorithm_rgb": [...]}, ...]
    """
    job = ProductionJob(
        detail="standard", difficulty="beginner", mode="standard",
        canvas_w_cm=w, canvas_h_cm=h,
        svg_url="https://e.com/x.svg",
        approved=True, status=JobStatusEnum.completed,
        finalized_at=datetime.now(UTC),
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

    prod = Product(
        title="測試畫", description="", cover_image_url="x",
        status=ProductStatusEnum.on_sale,
    )
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
    return job, variant


@pytest.mark.asyncio
async def test_calculate_happy_path(client: AsyncClient, db):
    """finalized variant + qty=2 → 各物理色 × 2、stock 充足。"""
    await _make_admin(db)
    red = await _make_color(db, code="P001", name="紅",
                            rgb=[255, 0, 0], stock_ml=200)
    blue = await _make_color(db, code="P002", name="藍",
                             rgb=[0, 0, 255], stock_ml=200)
    await db.commit()

    _job, variant = await _make_finalized_job_with_variant(
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

    await _login_admin(client)
    res = await client.get(URL, params={"variant_id": str(variant.id), "quantity": 2})
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["variant_id"] == str(variant.id)
    assert body["quantity"] == 2
    # 兩種物理色（紅、藍）
    assert len(body["items"]) == 2
    assert body["summary"]["total_colors"] == 2
    assert body["summary"]["short_count"] == 0

    by_code = {i["code"]: i for i in body["items"]}
    # 紅色：12.5 + 7.5 = 20.0/件 × 2 = 40.0 總；stock=200 充足
    assert by_code["P001"]["required_per_unit_ml"] == 20.0
    assert by_code["P001"]["total_required_ml"] == 40.0
    assert by_code["P001"]["stock_ml"] == 200.0
    assert by_code["P001"]["is_short"] is False
    assert by_code["P001"]["shortage_ml"] == 0.0
    assert by_code["P001"]["output_label"] == 1
    assert by_code["P001"]["hex"] == "#FF0000"

    # 藍：10.0/件 × 2 = 20.0
    assert by_code["P002"]["total_required_ml"] == 20.0
    assert by_code["P002"]["hex"] == "#0000FF"


@pytest.mark.asyncio
async def test_calculate_with_shortage(client: AsyncClient, db):
    """某色 stock < required → is_short=True + shortage_ml > 0。"""
    await _make_admin(db)
    red = await _make_color(db, code="P001", name="紅",
                            rgb=[255, 0, 0], stock_ml=5)  # 庫存只有 5ml
    await db.commit()

    _job, variant = await _make_finalized_job_with_variant(
        db,
        mappings=[
            {"template_id": 1, "physical_color_id": red.id,
             "required_ml": 10.0, "output_label": 1},
        ],
    )

    await _login_admin(client)
    res = await client.get(URL, params={"variant_id": str(variant.id), "quantity": 3})
    assert res.status_code == 200
    body = res.json()
    item = body["items"][0]
    # 10 × 3 = 30 總需，stock 5 → 缺 25ml
    assert item["total_required_ml"] == 30.0
    assert item["stock_ml"] == 5.0
    assert item["shortage_ml"] == 25.0
    assert item["is_short"] is True
    assert body["summary"]["short_count"] == 1


@pytest.mark.asyncio
async def test_variant_not_finalized_rejected(client: AsyncClient, db):
    """job.finalized_at=None → 400 + code=VARIANT_NOT_FINALIZED。"""
    await _make_admin(db)
    # 直接造一個 unfinalized job + variant，不走 _make_finalized_job_with_variant
    job = ProductionJob(
        detail="standard", difficulty="beginner", mode="standard",
        canvas_w_cm=30, canvas_h_cm=40,
        svg_url="https://e.com/x.svg",
        approved=True, status=JobStatusEnum.completed,
        finalized_at=None,  # ← 關鍵
    )
    db.add(job)
    await db.flush()
    prod = Product(title="未對應", description="", cover_image_url="x",
                   status=ProductStatusEnum.draft)
    db.add(prod)
    await db.flush()
    variant = ProductVariant(
        product_id=prod.id, production_job_id=job.id,
        price=Decimal("500"), price_formula_base=Decimal("500"),
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)

    await _login_admin(client)
    res = await client.get(URL, params={"variant_id": str(variant.id), "quantity": 1})
    assert res.status_code == 400
    body = res.json()
    assert body["code"] == "VARIANT_NOT_FINALIZED"
    assert body["variant_id"] == str(variant.id)
    assert body["production_job_id"] == str(job.id)


@pytest.mark.asyncio
async def test_variant_not_found(client: AsyncClient, db):
    """variant 不存在 → 404。"""
    await _make_admin(db)
    await db.commit()
    await _login_admin(client)

    fake_id = uuid.uuid4()
    res = await client.get(URL, params={"variant_id": str(fake_id), "quantity": 1})
    assert res.status_code == 404
