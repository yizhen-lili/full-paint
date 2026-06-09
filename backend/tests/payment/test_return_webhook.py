"""Module 23 — ECpay ReturnURL webhook（付款成功權威）整合測試。"""
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from sqlalchemy import func, select

from auth.models import User
from orders.models import (
    Order,
    OrderItem,
    OrderStatusEnum,
    PaymentMethodEnum,
    PaymentTransaction,
    PaymentTransactionStatusEnum,
    ProductionProgress,
)
from payment import service

pytestmark = pytest.mark.asyncio


async def _make_order_with_txn(
    db,
    *,
    total=1260,
    order_status=OrderStatusEnum.pending_payment,
    txn_status=PaymentTransactionStatusEnum.created,
    n_items=1,
    custom=False,
):
    user = User(
        name="付款測試",
        email=f"pay_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode(),
        role="customer",
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    await db.flush()

    order = Order(
        order_number=f"PL-TEST-{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        status=order_status,
        subtotal=total,
        shipping_fee=0,
        total=total,
        shipping_type="home",
        shipping_snapshot={"recipient_name": "x", "phone": "0912345678"},
        payment_method=PaymentMethodEnum.ecpay,
        payment_deadline=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(order)
    await db.flush()

    custom_request_id = None
    if custom:
        from custom.models import CustomRequest
        cr = CustomRequest(user_id=user.id, request_type="custom_photo")
        db.add(cr)
        await db.flush()
        custom_request_id = cr.id

    for _ in range(n_items):
        db.add(OrderItem(
            order_id=order.id,
            product_variant_id=None,  # 測試用，不綁真實 variant（避免 FK）
            custom_request_id=custom_request_id,
            product_title_snapshot="油畫模板",
            variant_spec_snapshot={},
            unit_price=total,
            quantity=1,
            fulfilled_qty=0,
            preorder_qty=1,
        ))

    txn = PaymentTransaction(
        order_id=order.id,
        merchant_trade_no=f"PAY{uuid.uuid4().hex[:12].upper()}",
        amount=service.charge_amount(order),  # 與 production 一致：四捨五入整數快照
        status=txn_status,
    )
    db.add(txn)
    await db.commit()
    return user, order, txn


def _signed_return_params(txn, *, rtn_code="1", trade_amt=None):
    params = {
        "MerchantID": "3002607",
        "MerchantTradeNo": txn.merchant_trade_no,
        "RtnCode": rtn_code,
        "RtnMsg": "交易成功",
        "TradeNo": "EC" + uuid.uuid4().hex[:10].upper(),
        "TradeAmt": str(trade_amt if trade_amt is not None else int(txn.amount)),
        "PaymentType": "Credit_CreditCard",
        "PaymentDate": "2026/06/09 12:00:00",
    }
    params["CheckMacValue"] = service.calculate_check_mac_value(params)
    return params


async def _count_progress(db, order_id):
    return (await db.execute(
        select(func.count()).select_from(ProductionProgress)
        .join(OrderItem, ProductionProgress.order_item_id == OrderItem.id)
        .where(OrderItem.order_id == order_id)
    )).scalar()


async def test_success_marks_paid(db):
    _, order, txn = await _make_order_with_txn(db, n_items=2)
    params = _signed_return_params(txn)

    result = await service.process_return_webhook(db, params)

    assert result == "1|OK"
    refreshed = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == OrderStatusEnum.paid
    assert refreshed.paid_at is not None
    txn_r = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == txn.id)
    )).scalar_one()
    assert txn_r.status == PaymentTransactionStatusEnum.paid
    assert txn_r.ecpay_trade_no is not None
    # 每個 order_item 建一筆 production_progress
    assert await _count_progress(db, order.id) == 2


async def test_bad_mac_does_not_mark_paid(db):
    _, order, txn = await _make_order_with_txn(db)
    params = _signed_return_params(txn)
    params["CheckMacValue"] = "DEADBEEF"  # 竄改簽章

    result = await service.process_return_webhook(db, params)

    assert result == "0|CheckMacValueError"
    refreshed = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == OrderStatusEnum.pending_payment


async def test_amount_tamper_rejected(db):
    _, order, txn = await _make_order_with_txn(db, total=1260)
    # 簽章正確但金額被改成 1 元
    params = _signed_return_params(txn, trade_amt=1)

    result = await service.process_return_webhook(db, params)

    assert result == "0|AmountMismatch"
    refreshed = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == OrderStatusEnum.pending_payment


async def test_unknown_trade_no(db):
    _, _, txn = await _make_order_with_txn(db)
    params = _signed_return_params(txn)
    params["MerchantTradeNo"] = "PAYNOTEXIST999"
    params["CheckMacValue"] = service.calculate_check_mac_value(
        {k: v for k, v in params.items() if k != "CheckMacValue"}
    )

    result = await service.process_return_webhook(db, params)
    assert result == "0|OrderNotFound"


async def test_failed_rtn_code_marks_failed(db):
    _, order, txn = await _make_order_with_txn(db)
    params = _signed_return_params(txn, rtn_code="10100058")  # 信用卡失敗碼

    result = await service.process_return_webhook(db, params)

    assert result == "1|OK"  # 已知失敗不需重送
    refreshed = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == OrderStatusEnum.pending_payment
    txn_r = (await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.id == txn.id)
    )).scalar_one()
    assert txn_r.status == PaymentTransactionStatusEnum.failed


async def test_idempotent_double_callback(db):
    _, order, txn = await _make_order_with_txn(db, n_items=1)
    params = _signed_return_params(txn)

    r1 = await service.process_return_webhook(db, params)
    r2 = await service.process_return_webhook(db, params)

    assert r1 == "1|OK"
    assert r2 == "1|OK"
    # production_progress 只建一份（不因重送重複建）
    assert await _count_progress(db, order.id) == 1


async def test_custom_order_notifies_admin(db):
    from notifications.models import AdminNotification
    _, order, txn = await _make_order_with_txn(db, custom=True)
    params = _signed_return_params(txn)

    await service.process_return_webhook(db, params)

    notif = (await db.execute(
        select(AdminNotification).where(AdminNotification.reference_id == order.id)
    )).scalars().all()
    # 客製訂單發 custom_order_paid（不重複發 order_paid）
    assert any(n.type == "custom_order_paid" for n in notif)
    assert not any(n.type == "order_paid" for n in notif)


async def test_regular_order_ecpay_paid_notifies_admin(db):
    """一般訂單經 ECpay 自動付款 → 發 order_paid admin 通知（提醒備貨出貨）。"""
    from notifications.models import AdminNotification
    _, order, txn = await _make_order_with_txn(db, custom=False)
    params = _signed_return_params(txn)

    await service.process_return_webhook(db, params)

    notif = (await db.execute(
        select(AdminNotification).where(AdminNotification.reference_id == order.id)
    )).scalars().all()
    assert any(n.type == "order_paid" and n.requires_action for n in notif)


async def test_race_guard_already_expired_notifies_admin(db):
    """訂單已 payment_expired 時 ReturnURL 進來 → 不標 paid（guard），但發孤兒款項通知。"""
    from notifications.models import AdminNotification
    _, order, txn = await _make_order_with_txn(db, order_status=OrderStatusEnum.payment_expired)
    params = _signed_return_params(txn)

    result = await service.process_return_webhook(db, params)

    assert result == "1|OK"  # 仍回 OK（已記 transaction），但不標 paid
    refreshed = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == OrderStatusEnum.payment_expired
    assert await _count_progress(db, order.id) == 0
    # 顧客付了錢卻無有效訂單 → 必須通知 admin 人工退款
    notif = (await db.execute(
        select(AdminNotification).where(AdminNotification.reference_id == order.id)
    )).scalars().all()
    assert any(n.type == "ecpay_paid_after_close" and n.requires_action for n in notif)


async def test_non_numeric_trade_amt_rejected(db):
    """TradeAmt 非數字 → AmountMismatch，不標 paid。"""
    _, order, txn = await _make_order_with_txn(db)
    params = {
        "MerchantID": "3002607",
        "MerchantTradeNo": txn.merchant_trade_no,
        "RtnCode": "1",
        "TradeAmt": "abc",
    }
    params["CheckMacValue"] = service.calculate_check_mac_value(params)

    result = await service.process_return_webhook(db, params)

    assert result == "0|AmountMismatch"
    refreshed = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == OrderStatusEnum.pending_payment


async def test_fractional_total_charges_rounded_integer(db):
    """order.total 有小數（百分比折扣）→ txn.amount 為四捨五入整數，webhook 用該整數比對。"""
    # total=694.60 → charge_amount 四捨五入 = 695
    _, order, txn = await _make_order_with_txn(db, total=694.60)
    assert int(txn.amount) == 695
    params = _signed_return_params(txn)  # TradeAmt = int(txn.amount) = 695
    assert params["TradeAmt"] == "695"

    result = await service.process_return_webhook(db, params)
    assert result == "1|OK"
    refreshed = (await db.execute(select(Order).where(Order.id == order.id))).scalar_one()
    assert refreshed.status == OrderStatusEnum.paid
