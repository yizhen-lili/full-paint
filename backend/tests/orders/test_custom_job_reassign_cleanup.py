"""重做製作（重新指派）+ 取消/退款訂單清理 測試。"""
import uuid

import bcrypt
import pytest
from sqlalchemy import select

from auth.models import User
from custom.models import CustomRequest
from orders import service
from orders.models import (
    Order,
    OrderItem,
    OrderStatusEnum,
    PaymentMethodEnum,
    ProductionProgress,
)
from production.models import JobStatusEnum, ProductionJob

pytestmark = pytest.mark.asyncio


async def _make_user(db):
    u = User(
        name="客製測試", email=f"cj_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        role="customer", is_active=True, is_email_verified=True,
    )
    db.add(u)
    await db.flush()
    return u


async def _make_job(db, custom_request_id, status=JobStatusEnum.completed):
    job = ProductionJob(
        detail="standard", difficulty="beginner",
        canvas_w_cm=20.0, canvas_h_cm=20.0,
        status=status, custom_request_id=custom_request_id,
    )
    db.add(job)
    await db.flush()
    return job


async def _make_custom_order(
    db, *, order_status=OrderStatusEnum.processing, photo="custom_photos/x.jpg"
):
    user = await _make_user(db)
    cr = CustomRequest(user_id=user.id, request_type="custom_photo", photo_url=photo)
    db.add(cr)
    await db.flush()
    job = await _make_job(db, cr.id)
    cr.quoted_production_job_id = job.id

    order = Order(
        order_number=f"PL-CJ-{uuid.uuid4().hex[:8]}",
        user_id=user.id, status=order_status,
        subtotal=1000, shipping_fee=0, total=1000,
        shipping_type="home",
        shipping_snapshot={"recipient_name": "x", "phone": "0912345678"},
        payment_method=PaymentMethodEnum.bank_transfer,
    )
    db.add(order)
    await db.flush()
    item = OrderItem(
        order_id=order.id, product_variant_id=None,
        custom_request_id=cr.id, production_job_id=job.id,
        product_title_snapshot="客製油畫", variant_spec_snapshot={},
        unit_price=1000, quantity=1, fulfilled_qty=0, preorder_qty=1,
    )
    db.add(item)
    await db.flush()
    db.add(ProductionProgress(order_item_id=item.id))
    await db.commit()
    return user, cr, job, order, item


# ── Feature A：重新指派 ──────────────────────────────────────────────────────

async def test_reassign_repoints_order_item_and_custom_request(db):
    _, cr, old_job, order, item = await _make_custom_order(db)
    new_job = await _make_job(db, cr.id)
    await db.commit()

    await service.reassign_production_job(db, order.id, item.id, new_job.id)

    item_r = (await db.execute(select(OrderItem).where(OrderItem.id == item.id))).scalar_one()
    cr_r = (await db.execute(select(CustomRequest).where(CustomRequest.id == cr.id))).scalar_one()
    assert item_r.production_job_id == new_job.id
    assert cr_r.quoted_production_job_id == new_job.id
    # production_progress 綁 order_item，不受重新指派影響（仍在）
    prog = (await db.execute(
        select(ProductionProgress).where(ProductionProgress.order_item_id == item.id)
    )).scalars().all()
    assert len(prog) == 1


async def test_reassign_rejects_job_of_other_request(db):
    from core.exceptions import BadRequestError
    _, cr, old_job, order, item = await _make_custom_order(db)
    # 另一個 custom_request 的 job
    other_cr = CustomRequest(user_id=(await _make_user(db)).id, request_type="custom_photo")
    db.add(other_cr)
    await db.flush()
    other_job = await _make_job(db, other_cr.id)
    await db.commit()

    with pytest.raises(BadRequestError, match="不屬於"):
        await service.reassign_production_job(db, order.id, item.id, other_job.id)


async def test_reassign_rejects_shipped_order(db):
    """已出貨訂單不可重做製作（保護已交付的製作檔）。"""
    from core.exceptions import BadRequestError
    _, cr, old_job, order, item = await _make_custom_order(db, order_status=OrderStatusEnum.shipped)
    new_job = await _make_job(db, cr.id)
    await db.commit()

    with pytest.raises(BadRequestError, match="出貨前"):
        await service.reassign_production_job(db, order.id, item.id, new_job.id)


async def test_reassign_rejects_non_completed_job(db):
    from core.exceptions import BadRequestError
    _, cr, old_job, order, item = await _make_custom_order(db)
    pending_job = await _make_job(db, cr.id, status=JobStatusEnum.pending)
    await db.commit()

    with pytest.raises(BadRequestError, match="completed"):
        await service.reassign_production_job(db, order.id, item.id, pending_job.id)


# ── Feature B：取消/退款清理 ─────────────────────────────────────────────────

async def test_cleanup_deletes_job_and_photo_keeps_order_item(db):
    _, cr, job, order, item = await _make_custom_order(db, order_status=OrderStatusEnum.cancelled)

    result = await service.cleanup_custom_order_assets(db, order.id)

    # order_item 保留，但 production_job_id 解除
    item_r = (await db.execute(select(OrderItem).where(OrderItem.id == item.id))).scalar_one()
    assert item_r is not None
    assert item_r.production_job_id is None
    # job 被刪
    job_r = (await db.execute(
        select(ProductionJob).where(ProductionJob.id == job.id)
    )).scalar_one_or_none()
    assert job_r is None
    # 照片清掉
    cr_r = (await db.execute(select(CustomRequest).where(CustomRequest.id == cr.id))).scalar_one()
    assert cr_r.photo_url is None
    assert result["deleted_jobs"] == 1
    assert result["deleted_photos"] == 1


async def test_cleanup_rejects_active_order(db):
    from core.exceptions import BadRequestError
    _, cr, job, order, item = await _make_custom_order(db, order_status=OrderStatusEnum.paid)

    with pytest.raises(BadRequestError, match="取消"):
        await service.cleanup_custom_order_assets(db, order.id)


async def test_cleanup_allowed_for_refunded(db):
    _, cr, job, order, item = await _make_custom_order(db, order_status=OrderStatusEnum.refunded)
    result = await service.cleanup_custom_order_assets(db, order.id)
    assert result["deleted_jobs"] == 1


async def test_cleanup_allowed_for_payment_expired(db):
    _, cr, job, order, item = await _make_custom_order(
        db, order_status=OrderStatusEnum.payment_expired
    )
    result = await service.cleanup_custom_order_assets(db, order.id)
    assert result["deleted_jobs"] == 1
    assert result["deleted_photos"] == 1


async def test_reassign_rejects_non_custom_item(db):
    """非客製 order_item（custom_request_id 為 None）不可重新指派。"""
    from core.exceptions import BadRequestError
    user = await _make_user(db)
    cr = CustomRequest(user_id=user.id, request_type="custom_photo")
    db.add(cr)
    await db.flush()
    job = await _make_job(db, cr.id)
    order = Order(
        order_number=f"PL-NC-{uuid.uuid4().hex[:8]}", user_id=user.id,
        status=OrderStatusEnum.paid, subtotal=500, shipping_fee=0, total=500,
        shipping_type="home", shipping_snapshot={"recipient_name": "x", "phone": "0912345678"},
        payment_method=PaymentMethodEnum.bank_transfer,
    )
    db.add(order)
    await db.flush()
    # 一般 variant item（custom_request_id=None）
    plain = OrderItem(
        order_id=order.id, product_variant_id=None, custom_request_id=None,
        product_title_snapshot="一般商品", variant_spec_snapshot={},
        unit_price=500, quantity=1, fulfilled_qty=1, preorder_qty=0,
    )
    db.add(plain)
    await db.commit()

    with pytest.raises(BadRequestError, match="客製"):
        await service.reassign_production_job(db, order.id, plain.id, job.id)


async def test_cleanup_skips_job_still_referenced_by_variant(db):
    """job 同時被商品規格引用 → cleanup 略過該 job（不刪），但照片仍清、order_item 保留。"""
    from product.models import Product, ProductVariant
    _, cr, job, order, item = await _make_custom_order(db, order_status=OrderStatusEnum.cancelled)
    product = Product(title="上架商品", cover_image_url="x")
    db.add(product)
    await db.flush()
    variant = ProductVariant(
        product_id=product.id, production_job_id=job.id,
        price=1000, price_formula_base=500,
    )
    db.add(variant)
    await db.commit()

    result = await service.cleanup_custom_order_assets(db, order.id)

    # job 仍被 variant 引用 → 略過不刪
    job_r = (await db.execute(
        select(ProductionJob).where(ProductionJob.id == job.id)
    )).scalar_one_or_none()
    assert job_r is not None
    assert result["deleted_jobs"] == 0
    assert len(result["skipped_jobs"]) == 1
    # 但照片仍清、order_item 仍在且已解除連結
    cr_r = (await db.execute(select(CustomRequest).where(CustomRequest.id == cr.id))).scalar_one()
    assert cr_r.photo_url is None
    item_r = (await db.execute(select(OrderItem).where(OrderItem.id == item.id))).scalar_one()
    assert item_r.production_job_id is None


def test_delete_custom_photo_rejects_non_custom_prefix(monkeypatch):
    """安全：photo_url 指向非 custom_photos/ 路徑時拒刪（防任意檔案刪除）。"""
    from custom import service as cs

    deleted: list[str] = []

    class _FakeBlob:
        def __init__(self, path): self.path = path
        def delete(self): deleted.append(self.path)

    class _FakeBucket:
        name = "mybucket"
        def blob(self, path): return _FakeBlob(path)

    monkeypatch.setattr("core.firebase.get_bucket", lambda: _FakeBucket())

    # 惡意：指向 products/ → 拒刪
    cs.delete_custom_photo("https://storage.googleapis.com/mybucket/products/featured/banner.jpg")
    assert deleted == []
    # 合法 custom_photos/ → 刪
    cs.delete_custom_photo("https://storage.googleapis.com/mybucket/custom_photos/abc.jpg")
    assert deleted == ["custom_photos/abc.jpg"]
