"""Module 15 — print_batch tests."""

import uuid
from decimal import Decimal
from unittest.mock import patch

import bcrypt
import pytest
from sqlalchemy import select

from auth.models import User
from print_batch.service import (
    NO_WASTE_THRESHOLD,
    billing,
    inch_per_unit,
)
from product.models import (
    Product,
    ProductStatusEnum,
    ProductVariant,
)
from production.models import ProductionJob

ADMIN_EMAIL = "print_admin@test.com"
ADMIN_PASS = "adminpass123"
URL = "/api/v1/admin/print-batches"


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_admin(db):
    a = User(
        name="PrintAdmin",
        email=ADMIN_EMAIL,
        password_hash=bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt()).decode(),
        role="admin",
        is_active=True,
        is_email_verified=True,
    )
    db.add(a)
    await db.commit()
    return a


async def _make_customer(db, email="cust@test.com"):
    u = User(
        name="cust",
        email=email,
        password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        role="customer",
        is_active=True,
        is_email_verified=True,
    )
    db.add(u)
    await db.commit()
    return u


async def _login_admin(client):
    res = await client.post("/api/v1/admin/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASS,
    })
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])


async def _make_job(db, *, w=30, h=40, svg_url="https://example.com/x.svg"):
    job = ProductionJob(
        detail="standard", difficulty="beginner", mode="standard",
        canvas_w_cm=w, canvas_h_cm=h, svg_url=svg_url,
        approved=True, status="completed",
    )
    db.add(job)
    await db.flush()
    return job


async def _make_product_with_variant(db, job_id, *, title="畫"):
    p = Product(
        title=title, description="", cover_image_url="x",
        status=ProductStatusEnum.on_sale,
    )
    db.add(p)
    await db.flush()
    v = ProductVariant(
        product_id=p.id, production_job_id=job_id,
        price=500, price_formula_base=500, is_active=True,
    )
    db.add(v)
    await db.flush()
    return p, v


# ── Pure pricing ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inch_per_unit():
    """30×40 含留白 → (40 × 50) / 900 = 2.2222 才。"""
    assert abs(float(inch_per_unit(30, 40)) - 2.2222) < 0.001


@pytest.mark.asyncio
async def test_total_billing_below_floor():
    """16 才 → 列印 max(560, 200)=560，裁切 max(80, 100)=100，總 660。"""
    bill = billing(Decimal("16"))
    assert bill["billable_inch_count"] == Decimal("16")
    assert bill["print_cost"] == Decimal("560")
    assert bill["cut_cost"] == Decimal("100")
    assert bill["total_cost"] == Decimal("660")


@pytest.mark.asyncio
async def test_total_billing_above_floor():
    """30 才 → 列印 1050，裁切 150，總 1200。"""
    bill = billing(Decimal("30"))
    assert bill["print_cost"] == Decimal("1050")
    assert bill["cut_cost"] == Decimal("150")
    assert bill["total_cost"] == Decimal("1200")


@pytest.mark.asyncio
async def test_total_billing_ceil_partial():
    """47.3 才 → 整單 ceil 為 48 才。"""
    bill = billing(Decimal("47.3"))
    assert bill["billable_inch_count"] == Decimal("48")


# ── Endpoints ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_only_unauthenticated(client, db):
    res = await client.get(URL)
    assert res.status_code == 401
    res = await client.post(f"{URL}/preview", json={"required": []})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_only_customer_blocked(client, db):
    await _make_customer(db)
    res = await client.post("/api/v1/auth/login", json={
        "email": "cust@test.com", "password": "x",
    })
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])
    res = await client.get(URL)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_candidates_filter_on_sale_active(client, db):
    """候選池：approved=true + status=completed 全列（不要求商品上架）。

    包含：
      A. 在架上商品 → label = product.title
      B. draft 商品（未上架）→ 仍列出（為了囤庫存）
      C. variant inactive → 仍列出（同上）
      D. 客製訂單 job（無 product 綁定）→ label = 「客製 - {user.name}」
      E. approved=False → 排除
      F. status≠completed → 排除
    """
    from custom.models import (
        CustomRequest,
        CustomRequestStatusEnum,
        CustomRequestTypeEnum,
    )

    await _make_admin(db)
    job_a = await _make_job(db, w=30, h=40)  # 上架商品
    job_b = await _make_job(db, w=50, h=50)  # 草稿商品
    job_c = await _make_job(db, w=60, h=60)  # variant inactive
    job_d = await _make_job(db, w=20, h=20)  # 客製
    job_e = ProductionJob(
        detail="standard", difficulty="beginner", mode="standard",
        canvas_w_cm=10, canvas_h_cm=10, svg_url="https://example.com/e.svg",
        approved=False, status="completed",
    )
    db.add(job_e)
    job_f = ProductionJob(
        detail="standard", difficulty="beginner", mode="standard",
        canvas_w_cm=15, canvas_h_cm=15, svg_url="https://example.com/f.svg",
        approved=True, status="processing",
    )
    db.add(job_f)
    await db.flush()

    p_a = Product(title="架上", description="", cover_image_url="x",
                  status=ProductStatusEnum.on_sale)
    db.add(p_a)
    await db.flush()
    db.add(ProductVariant(product_id=p_a.id, production_job_id=job_a.id,
                          price=500, price_formula_base=500, is_active=True))

    p_b = Product(title="草稿", description="", cover_image_url="x",
                  status=ProductStatusEnum.draft)
    db.add(p_b)
    await db.flush()
    db.add(ProductVariant(product_id=p_b.id, production_job_id=job_b.id,
                          price=500, price_formula_base=500, is_active=True))

    p_c = Product(title="架上但變體停用", description="", cover_image_url="x",
                  status=ProductStatusEnum.on_sale)
    db.add(p_c)
    await db.flush()
    db.add(ProductVariant(product_id=p_c.id, production_job_id=job_c.id,
                          price=500, price_formula_base=500, is_active=False))

    customer = await _make_customer(db, email="custom_buyer@test.com")
    cr = CustomRequest(
        user_id=customer.id,
        request_type=CustomRequestTypeEnum.custom_photo,
        status=CustomRequestStatusEnum.quote_confirmed,
    )
    db.add(cr)
    await db.flush()
    job_d.custom_request_id = cr.id
    db.add(job_d)
    await db.commit()

    await _login_admin(client)
    res = await client.get(f"{URL}/candidates")
    assert res.status_code == 200
    items = res.json()["items"]
    titles = [i["product_title"] for i in items]
    by_title = {i["product_title"]: i for i in items}
    # A/B/C/D 都要列出（放寬後不要求 on_sale + active）
    assert "架上" in titles
    assert "草稿" in titles
    assert "架上但變體停用" in titles
    # 商品類型統一 kind=product
    assert by_title["架上"]["kind"] == "product"
    assert by_title["草稿"]["kind"] == "product"
    assert by_title["架上但變體停用"]["kind"] == "product"
    # preview_url 欄位存在（值依 filled_template_url 而定，可為 None）
    assert "preview_url" in by_title["架上"]
    # 客製 label + kind=custom
    custom_label = f"客製 - {customer.name}"
    assert custom_label in titles
    assert by_title[custom_label]["kind"] == "custom"
    # E/F 不該出現（approved=False / status!=completed）
    job_ids_in_pool = {i["production_job_id"] for i in items}
    assert str(job_e.id) not in job_ids_in_pool
    assert str(job_f.id) not in job_ids_in_pool


@pytest.mark.asyncio
async def test_preview_required_only(client, db):
    """純必印 16 才 → 660 元 + 候選 suggestions。"""
    await _make_admin(db)
    j1 = await _make_job(db, w=30, h=40)
    j2 = await _make_job(db, w=50, h=60)
    await _make_product_with_variant(db, j1.id, title="A")
    await _make_product_with_variant(db, j2.id, title="B")
    await db.commit()

    await _login_admin(client)
    res = await client.post(f"{URL}/preview", json={
        "required": [
            {"production_job_id": str(j1.id), "quantity": 3},
            {"production_job_id": str(j2.id), "quantity": 2},
        ],
    })
    assert res.status_code == 200
    body = res.json()
    # 3 × 2.222 + 2 × 4.667 = 15.999... → ceil 16
    assert body["billable_inch_count"] == 16.0
    assert body["cost_breakdown"]["print_cost"] == 560.0
    assert body["cost_breakdown"]["cut_cost"] == 100.0
    assert body["cost_breakdown"]["total_cost"] == 660.0
    assert body["waste_inch"] == 4.0  # 20 - 16
    assert len(body["suggestions"]) > 0


@pytest.mark.asyncio
async def test_preview_no_waste_when_above_threshold(client, db):
    """整單 30 才已超過 20，不需補單建議。"""
    await _make_admin(db)
    j = await _make_job(db, w=50, h=60)  # 4.67 才/張
    await _make_product_with_variant(db, j.id)
    await db.commit()

    await _login_admin(client)
    res = await client.post(f"{URL}/preview", json={
        "required": [{"production_job_id": str(j.id), "quantity": 7}],  # 32.67 才
    })
    body = res.json()
    assert body["waste_inch"] == 0.0
    assert body["suggestions"] == []


@pytest.mark.asyncio
async def test_preview_required_empty_rejected(client, db):
    await _make_admin(db)
    await _login_admin(client)
    res = await client.post(f"{URL}/preview", json={"required": []})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_preview_unknown_job_404(client, db):
    await _make_admin(db)
    await _login_admin(client)
    fake = str(uuid.uuid4())
    res = await client.post(f"{URL}/preview", json={
        "required": [{"production_job_id": fake, "quantity": 1}],
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_batch_draft(client, db):
    """POST /admin/print-batches → 建 draft，不產 PDF。"""
    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    await _make_product_with_variant(db, j.id)
    await db.commit()

    await _login_admin(client)
    res = await client.post(URL, json={
        "required": [{"production_job_id": str(j.id), "quantity": 5}],
        "admin_notes": "test",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "draft"
    assert body["pdf_url"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


@pytest.mark.asyncio
async def test_finalize_creates_pdf(client, db):
    """Finalize → status=finalized + pdf_url 填值。"""
    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    await _make_product_with_variant(db, j.id)
    await db.commit()

    await _login_admin(client)
    create_res = await client.post(URL, json={
        "required": [{"production_job_id": str(j.id), "quantity": 5}],
    })
    batch_id = create_res.json()["id"]

    # Mock _generate_pdf 避免實際呼叫 Firebase；用 https URL 模擬上傳成功
    # (stub.firebase 會被 _resolve_pdf_url 過濾為 None — 那是上傳失敗的 fallback)
    with patch("print_batch.service._generate_pdf") as mock_pdf:
        mock_pdf.return_value = "https://example.com/uploaded/batch.pdf"
        res = await client.post(f"{URL}/{batch_id}/finalize")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "finalized"
    assert body["pdf_url"] == "https://example.com/uploaded/batch.pdf"


@pytest.mark.asyncio
async def test_finalize_stub_url_filtered_to_none(client, db):
    """上傳失敗 fallback 的 stub URL 不可漏到前端（會 404）→ pdf_url=null。"""
    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    await _make_product_with_variant(db, j.id)
    await db.commit()

    await _login_admin(client)
    create_res = await client.post(URL, json={
        "required": [{"production_job_id": str(j.id), "quantity": 5}],
    })
    batch_id = create_res.json()["id"]
    with patch("print_batch.service._generate_pdf") as mock_pdf:
        mock_pdf.return_value = "https://stub.firebase/print_batch/abc/batch.pdf"
        res = await client.post(f"{URL}/{batch_id}/finalize")
    assert res.status_code == 200
    # stub URL 被 _resolve_pdf_url 過濾掉，前端拿不到壞連結
    assert res.json()["pdf_url"] is None
    # 但 batch 狀態仍是 finalized（admin 可看到結果，PDF 失敗不阻擋流程）
    assert res.json()["status"] == "finalized"


@pytest.mark.asyncio
async def test_finalize_already_finalized_rejected(client, db):
    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    await _make_product_with_variant(db, j.id)
    await db.commit()

    await _login_admin(client)
    create_res = await client.post(URL, json={
        "required": [{"production_job_id": str(j.id), "quantity": 5}],
    })
    batch_id = create_res.json()["id"]
    with patch("print_batch.service._generate_pdf") as mock_pdf:
        mock_pdf.return_value = "https://stub/x.pdf"
        await client.post(f"{URL}/{batch_id}/finalize")
        res = await client.post(f"{URL}/{batch_id}/finalize")
    assert res.status_code == 400
    assert res.json().get("code") == "ALREADY_FINALIZED"


@pytest.mark.asyncio
async def test_finalize_svg_not_ready_rejected(client, db):
    """svg_url 為 null → 拒絕 finalize 並回 SVG_NOT_READY。"""
    await _make_admin(db)
    j = await _make_job(db, w=30, h=40, svg_url=None)
    await _make_product_with_variant(db, j.id)
    await db.commit()

    await _login_admin(client)
    create_res = await client.post(URL, json={
        "required": [{"production_job_id": str(j.id), "quantity": 1}],
    })
    batch_id = create_res.json()["id"]
    res = await client.post(f"{URL}/{batch_id}/finalize")
    assert res.status_code == 400
    assert res.json().get("code") == "SVG_NOT_READY"


@pytest.mark.asyncio
async def test_finalize_does_not_touch_production_progress(client, db):
    """Finalize 後 production_progress 不被修改。"""
    from orders.models import (
        Order,
        OrderItem,
        OrderStatusEnum,
        ProductionProgress,
        ProductionProgressStatusEnum,
    )
    await _make_admin(db)
    user = await _make_customer(db)
    j = await _make_job(db, w=30, h=40)
    await _make_product_with_variant(db, j.id)

    order = Order(
        order_number=f"PL-{uuid.uuid4().hex[:8]}",
        user_id=user.id, status=OrderStatusEnum.paid,
        subtotal=100, discount_amount=0, shipping_fee=0, total=100,
        shipping_type="home", shipping_snapshot={},
    )
    db.add(order)
    await db.flush()
    item = OrderItem(
        order_id=order.id, production_job_id=j.id,
        product_title_snapshot="x", variant_spec_snapshot={},
        unit_price=100, quantity=1, fulfilled_qty=1, preorder_qty=0,
        is_returned=False,
    )
    db.add(item)
    await db.flush()
    progress = ProductionProgress(order_item_id=item.id)
    db.add(progress)
    await db.commit()

    await _login_admin(client)
    create_res = await client.post(URL, json={
        "required": [{
            "production_job_id": str(j.id),
            "quantity": 1,
            "source_type": "order_item",
            "source_order_item_id": str(item.id),
        }],
    })
    batch_id = create_res.json()["id"]
    with patch("print_batch.service._generate_pdf") as mock_pdf:
        mock_pdf.return_value = "https://stub/x.pdf"
        await client.post(f"{URL}/{batch_id}/finalize")

    # progress 保持 pending（finalize 不動它）
    refreshed = (await db.execute(
        select(ProductionProgress).where(ProductionProgress.id == progress.id)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert refreshed.status == ProductionProgressStatusEnum.pending


@pytest.mark.asyncio
async def test_list_batches_pagination(client, db):
    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    await _make_product_with_variant(db, j.id)
    await db.commit()

    await _login_admin(client)
    for _ in range(3):
        await client.post(URL, json={
            "required": [{"production_job_id": str(j.id), "quantity": 1}],
        })
    res = await client.get(f"{URL}?page=1&page_size=2")
    body = res.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_get_batch_detail(client, db):
    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    await _make_product_with_variant(db, j.id)
    await db.commit()

    await _login_admin(client)
    create_res = await client.post(URL, json={
        "required": [{"production_job_id": str(j.id), "quantity": 1}],
    })
    batch_id = create_res.json()["id"]
    res = await client.get(f"{URL}/{batch_id}")
    assert res.status_code == 200
    assert res.json()["id"] == batch_id


@pytest.mark.asyncio
async def test_no_waste_threshold_constant():
    """門檻常數 = 20 才（裁切 100/5）。"""
    assert NO_WASTE_THRESHOLD == Decimal("20")


# ── Non-integer canvas dimension regression ───────────────────────────────────


@pytest.mark.asyncio
async def test_non_integer_canvas_cm_round_trips_through_endpoints(client, db):
    """Numeric(6,1) 的 canvas_w_cm=30.5 / h=40.5 不可在 response 觸發 500。"""
    await _make_admin(db)
    j = await _make_job(db, w=Decimal("30.5"), h=Decimal("40.5"))
    await _make_product_with_variant(db, j.id, title="小數尺寸")
    await db.commit()

    await _login_admin(client)

    cand_res = await client.get(f"{URL}/candidates")
    assert cand_res.status_code == 200
    cand_items = cand_res.json()["items"]
    assert any(
        it["canvas_w_cm"] == 30.5 and it["canvas_h_cm"] == 40.5
        for it in cand_items
    )

    create_res = await client.post(URL, json={
        "required": [{"production_job_id": str(j.id), "quantity": 1}],
    })
    assert create_res.status_code == 201
    body = create_res.json()
    assert body["items"][0]["canvas_w_cm"] == 30.5
    assert body["items"][0]["canvas_h_cm"] == 40.5

    detail_res = await client.get(f"{URL}/{body['id']}")
    assert detail_res.status_code == 200
    assert detail_res.json()["items"][0]["canvas_w_cm"] == 30.5


# ── PDF generation path ───────────────────────────────────────────────────────


class _MockHttpResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _MockHttpClient:
    """模擬 httpx.AsyncClient，避免真實對外請求。"""

    def __init__(self, svg_text: str):
        self._svg_text = svg_text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url):
        return _MockHttpResponse(self._svg_text)


@pytest.mark.asyncio
async def test_generate_pdf_with_parseable_svg_returns_url(db):
    """_generate_pdf 在 SVG 可解析時走完拼版流程，回傳 stub URL。"""
    from print_batch.models import PrintBatchItem, PrintBatchItemSourceEnum
    from print_batch.service import _generate_pdf

    j = await _make_job(db, w=30, h=40, svg_url="https://example.com/ok.svg")
    await db.commit()

    item = PrintBatchItem(
        print_batch_id=uuid.uuid4(),
        source_type=PrintBatchItemSourceEnum.standalone,
        production_job_id=j.id,
        quantity=2,
        inch_per_unit=Decimal("2.2222"),
        canvas_w_cm=Decimal("30.0"),
        canvas_h_cm=Decimal("40.0"),
    )

    valid_svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="30mm" height="40mm" viewBox="0 0 30 40">'
        '<rect width="30" height="40" fill="none" stroke="black"/>'
        '</svg>'
    )

    def mock_client_factory(*args, **kwargs):
        return _MockHttpClient(valid_svg)

    with patch("print_batch.service.httpx.AsyncClient", mock_client_factory):
        url = await _generate_pdf([(item, j)])

    assert isinstance(url, str)
    assert url.startswith("https://stub.firebase/print_batch/")
    assert url.endswith("/batch.pdf")


@pytest.mark.asyncio
async def test_generate_pdf_falls_back_on_unparseable_svg(db):
    """svglib + cairosvg 皆失敗時走佔位框 fallback，仍回傳 URL 不爆。"""
    from print_batch.models import PrintBatchItem, PrintBatchItemSourceEnum
    from print_batch.service import _generate_pdf

    j = await _make_job(db, w=20, h=30, svg_url="https://example.com/broken.svg")
    await db.commit()

    item = PrintBatchItem(
        print_batch_id=uuid.uuid4(),
        source_type=PrintBatchItemSourceEnum.standalone,
        production_job_id=j.id,
        quantity=1,
        inch_per_unit=Decimal("1.0"),
        canvas_w_cm=Decimal("20.0"),
        canvas_h_cm=Decimal("30.0"),
    )

    def mock_client_factory(*args, **kwargs):
        return _MockHttpClient("not a valid svg")

    with patch("print_batch.service.httpx.AsyncClient", mock_client_factory):
        url = await _generate_pdf([(item, j)])

    assert isinstance(url, str)
    assert url.startswith("https://stub.firebase/print_batch/")


@pytest.mark.asyncio
async def test_render_svg_falls_back_to_cairosvg_when_svglib_fails(db):
    """svglib 失敗時走 cairosvg → PNG，回傳 png_bytes 不為 None。"""
    import cairosvg

    from print_batch.service import _render_svg_with_fallbacks

    valid_svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="20mm" height="30mm" viewBox="0 0 20 30">'
        '<rect width="20" height="30" fill="white" stroke="black"/>'
        '</svg>'
    )

    def mock_client_factory(*args, **kwargs):
        return _MockHttpClient(valid_svg)

    cairo_calls = []
    original_svg2png = cairosvg.svg2png

    def spy_svg2png(**kwargs):
        cairo_calls.append(kwargs)
        return original_svg2png(**kwargs)

    def force_svglib_fail(*_args, **_kwargs):
        raise RuntimeError("forced svglib failure for test")

    with (
        patch("print_batch.service.httpx.AsyncClient", mock_client_factory),
        patch("print_batch.service.svg2rlg", force_svglib_fail),
        patch("print_batch.service.cairosvg.svg2png", spy_svg2png),
    ):
        drawing, png_bytes = await _render_svg_with_fallbacks(
            "https://example.com/x.svg", w_cm=20.0, h_cm=30.0,
        )

    assert drawing is None
    assert png_bytes is not None and len(png_bytes) > 0
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(cairo_calls) == 1
    assert cairo_calls[0]["output_width"] == int(20.0 * 118)
    assert cairo_calls[0]["output_height"] == int(30.0 * 118)


@pytest.mark.asyncio
async def test_render_svg_returns_none_none_on_total_failure(db):
    """svglib + cairosvg 皆失敗 → (None, None) 讓上層走佔位框。"""
    from print_batch.service import _render_svg_with_fallbacks

    def mock_client_factory(*args, **kwargs):
        return _MockHttpClient("totally not svg")

    with patch("print_batch.service.httpx.AsyncClient", mock_client_factory):
        drawing, png_bytes = await _render_svg_with_fallbacks(
            "https://example.com/junk.svg", w_cm=10.0, h_cm=10.0,
        )

    assert drawing is None
    assert png_bytes is None


@pytest.mark.asyncio
async def test_render_svg_when_cairosvg_unavailable_returns_none_none(db):
    """libcairo 缺失情境（cairosvg=None）→ Layer 2 跳過，回 (None, None)。"""
    from print_batch.service import _render_svg_with_fallbacks

    valid_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        '<rect width="10" height="10" fill="white"/></svg>'
    )

    def mock_client_factory(*args, **kwargs):
        return _MockHttpClient(valid_svg)

    def force_svglib_fail(*_args, **_kwargs):
        raise RuntimeError("forced svglib failure")

    with (
        patch("print_batch.service.httpx.AsyncClient", mock_client_factory),
        patch("print_batch.service.svg2rlg", force_svglib_fail),
        patch("print_batch.service.cairosvg", None),
    ):
        drawing, png_bytes = await _render_svg_with_fallbacks(
            "https://example.com/x.svg", w_cm=10.0, h_cm=10.0,
        )

    assert drawing is None
    assert png_bytes is None


@pytest.mark.asyncio
async def test_render_svg_when_svglib_unavailable_uses_cairosvg(db):
    """svglib=None 情境（極端部署）→ 直接走 cairosvg。"""
    import cairosvg

    from print_batch.service import _render_svg_with_fallbacks

    valid_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
        '<rect width="10" height="10" fill="white"/></svg>'
    )

    def mock_client_factory(*args, **kwargs):
        return _MockHttpClient(valid_svg)

    cairo_calls = []
    original_svg2png = cairosvg.svg2png

    def spy_svg2png(**kwargs):
        cairo_calls.append(kwargs)
        return original_svg2png(**kwargs)

    with (
        patch("print_batch.service.httpx.AsyncClient", mock_client_factory),
        patch("print_batch.service.svg2rlg", None),
        patch("print_batch.service.cairosvg.svg2png", spy_svg2png),
    ):
        drawing, png_bytes = await _render_svg_with_fallbacks(
            "https://example.com/x.svg", w_cm=10.0, h_cm=10.0,
        )

    assert drawing is None
    assert png_bytes is not None


# ── Delete print_batch (Module 22 — cascade orphan + 訂單守則) ────────────────


async def _make_batch_with_item(
    db, job, *, source_type="standalone", source_order_item_id=None,
    pdf_url=None, status="draft",
):
    """快速建一個 batch + 一個 item。回 (batch, item)。"""
    from print_batch.models import (
        PrintBatch, PrintBatchItem, PrintBatchItemSourceEnum, PrintBatchStatusEnum,
    )

    batch = PrintBatch(
        status=PrintBatchStatusEnum(status),
        total_inch_count=Decimal("2.2222"),
        billable_inch_count=Decimal("3"),
        print_cost=Decimal("200"),
        cut_cost=Decimal("100"),
        total_cost=Decimal("300"),
        pdf_url=pdf_url,
    )
    db.add(batch)
    await db.flush()
    item = PrintBatchItem(
        print_batch_id=batch.id,
        source_type=PrintBatchItemSourceEnum(source_type),
        source_order_item_id=source_order_item_id,
        production_job_id=job.id,
        quantity=1,
        inch_per_unit=Decimal("2.2222"),
        canvas_w_cm=Decimal("30.0"),
        canvas_h_cm=Decimal("40.0"),
    )
    db.add(item)
    await db.commit()
    return batch, item


async def _make_paid_order_with_item(db, user, job):
    """建一筆 paid Order + OrderItem 綁 job，給 print_batch_item.source_order_item_id 用。"""
    from orders.models import (
        Order, OrderItem, OrderStatusEnum, ShippingTypeEnum,
    )

    order = Order(
        user_id=user.id,
        order_number=f"ORD-PB-{uuid.uuid4().hex[:6]}",
        status=OrderStatusEnum.paid,
        subtotal=100, total=100,
        shipping_type=ShippingTypeEnum.home,
        shipping_snapshot={"recipient": "T", "phone": "0900", "address": "T"},
    )
    db.add(order)
    await db.flush()
    oi = OrderItem(
        order_id=order.id,
        production_job_id=job.id,
        product_title_snapshot="T",
        variant_spec_snapshot={"size": "30x40"},
        unit_price=100, quantity=1,
    )
    db.add(oi)
    await db.commit()
    return order, oi


@pytest.mark.asyncio
async def test_delete_draft_batch_succeeds(client, db):
    """draft batch 可刪、items 同時 CASCADE 消失。"""
    from print_batch.models import PrintBatch, PrintBatchItem

    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    batch, item = await _make_batch_with_item(db, j, status="draft")
    batch_id = batch.id
    item_id = item.id

    await _login_admin(client)
    res = await client.delete(f"{URL}/{batch_id}")
    assert res.status_code == 204

    # 清 session cache（DB CASCADE 刪掉 row 但 session 還持有 stale 物件）
    db.expire_all()
    # batch + item 都不見
    assert (await db.execute(
        select(PrintBatch).where(PrintBatch.id == batch_id)
    )).scalar_one_or_none() is None
    assert (await db.execute(
        select(PrintBatchItem).where(PrintBatchItem.id == item_id)
    )).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_finalized_batch_succeeds_and_cleans_pdf(client, db):
    """finalized + 帶 pdf_url（gs://）也可刪、_delete_firebase_pdf 被呼叫。"""
    from print_batch.models import PrintBatch

    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    batch, _item = await _make_batch_with_item(
        db, j, status="finalized", pdf_url="gs://test-bucket/print_batches/x/y.pdf",
    )

    await _login_admin(client)
    with patch("print_batch.service._delete_firebase_pdf") as mock_del:
        res = await client.delete(f"{URL}/{batch.id}")
        assert res.status_code == 204
        mock_del.assert_called_once_with("gs://test-bucket/print_batches/x/y.pdf")

    assert await db.get(PrintBatch, batch.id) is None


@pytest.mark.asyncio
async def test_delete_batch_blocked_by_order_item(client, db):
    """item 來源是 order_item → 400 + code=BATCH_BLOCKED_BY_ORDER + references。"""
    from print_batch.models import PrintBatch

    await _make_admin(db)
    customer = await _make_customer(db)
    j = await _make_job(db, w=30, h=40)
    _order, oi = await _make_paid_order_with_item(db, customer, j)
    batch, _item = await _make_batch_with_item(
        db, j, source_type="order_item", source_order_item_id=oi.id,
    )

    await _login_admin(client)
    res = await client.delete(f"{URL}/{batch.id}")
    assert res.status_code == 400
    body = res.json()
    assert body["code"] == "BATCH_BLOCKED_BY_ORDER"
    assert len(body["references"]) == 1
    g = body["references"][0]
    assert g["type"] == "order_item"
    assert g["cascadeable"] is False
    assert "ORD-PB-" in g["items"][0]["display"]

    # batch 還在
    assert await db.get(PrintBatch, batch.id) is not None


@pytest.mark.asyncio
async def test_batch_delete_partial(client, db):
    """batch-delete 三筆（draft / finalized / order）→ 2 成功 1 失敗。"""
    from print_batch.models import PrintBatch

    await _make_admin(db)
    customer = await _make_customer(db)
    j1 = await _make_job(db, w=30, h=40, svg_url="https://e.com/1.svg")
    j2 = await _make_job(db, w=20, h=30, svg_url="https://e.com/2.svg")
    j3 = await _make_job(db, w=10, h=20, svg_url="https://e.com/3.svg")

    b1, _ = await _make_batch_with_item(db, j1, status="draft")
    b2, _ = await _make_batch_with_item(db, j2, status="finalized")
    _order, oi = await _make_paid_order_with_item(db, customer, j3)
    b3, _ = await _make_batch_with_item(
        db, j3, source_type="order_item", source_order_item_id=oi.id,
    )

    await _login_admin(client)
    res = await client.post(
        f"{URL}/batch-delete",
        json={"batch_ids": [str(b1.id), str(b2.id), str(b3.id)]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["success"] == 2
    assert body["failed"] == 1

    by_id = {r["batch_id"]: r for r in body["results"]}
    assert by_id[str(b1.id)]["ok"] is True
    assert by_id[str(b2.id)]["ok"] is True
    assert by_id[str(b3.id)]["ok"] is False
    assert by_id[str(b3.id)]["references"] is not None
    assert by_id[str(b3.id)]["references"][0]["type"] == "order_item"

    # b1 / b2 沒了；b3 還在
    assert await db.get(PrintBatch, b1.id) is None
    assert await db.get(PrintBatch, b2.id) is None
    assert await db.get(PrintBatch, b3.id) is not None


@pytest.mark.asyncio
async def test_cascade_orphan_batch_removed(client, db):
    """production_job cascade delete 後，孤兒 batch（item count = 0）自動刪。"""
    from production.models import ProductionJob
    from print_batch.models import PrintBatch
    from product.models import Product, ProductStatusEnum, ProductVariant

    await _make_admin(db)
    j = await _make_job(db, w=30, h=40)
    # variant 引用同個 job → cascade=true 才會走到 _cascade_delete_refs
    p = Product(title="P", description="", cover_image_url="x",
                status=ProductStatusEnum.on_sale)
    db.add(p)
    await db.flush()
    db.add(ProductVariant(product_id=p.id, production_job_id=j.id,
                          price=100, price_formula_base=100))
    batch, _item = await _make_batch_with_item(db, j, status="draft")
    await db.commit()

    await _login_admin(client)
    with patch("production.service.get_bucket"):
        res = await client.delete(
            f"/api/v1/admin/production/jobs/{j.id}?cascade=true",
        )
    assert res.status_code == 204
    # batch 與 job 都消失（job 被刪 → cascade 刪 print_batch_item → batch 變空孤兒 → 連帶刪）
    assert await db.get(PrintBatch, batch.id) is None
    assert await db.get(ProductionJob, j.id) is None


@pytest.mark.asyncio
async def test_cascade_keeps_batch_when_other_items_remain(client, db):
    """同 batch 內還有其他 job 的 item → cascade 刪 job 後 batch 保留。"""
    from production.models import ProductionJob
    from print_batch.models import PrintBatch, PrintBatchItem, PrintBatchItemSourceEnum
    from product.models import Product, ProductStatusEnum, ProductVariant

    await _make_admin(db)
    j1 = await _make_job(db, w=30, h=40)
    j2 = await _make_job(db, w=20, h=30)
    p = Product(title="P", description="", cover_image_url="x",
                status=ProductStatusEnum.on_sale)
    db.add(p)
    await db.flush()
    db.add(ProductVariant(product_id=p.id, production_job_id=j1.id,
                          price=100, price_formula_base=100))

    # batch 包兩個 items：j1 + j2
    batch, _item1 = await _make_batch_with_item(db, j1, status="draft")
    db.add(PrintBatchItem(
        print_batch_id=batch.id,
        source_type=PrintBatchItemSourceEnum.standalone,
        production_job_id=j2.id,
        quantity=1,
        inch_per_unit=Decimal("1.5"),
        canvas_w_cm=Decimal("20.0"),
        canvas_h_cm=Decimal("30.0"),
    ))
    await db.commit()

    await _login_admin(client)
    with patch("production.service.get_bucket"):
        res = await client.delete(
            f"/api/v1/admin/production/jobs/{j1.id}?cascade=true",
        )
    assert res.status_code == 204

    # j1 被刪，batch 還在（仍含 j2 的 item）
    assert await db.get(ProductionJob, j1.id) is None
    assert await db.get(PrintBatch, batch.id) is not None
    remaining = (await db.execute(
        select(PrintBatchItem).where(PrintBatchItem.print_batch_id == batch.id)
    )).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].production_job_id == j2.id
