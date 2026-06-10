import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from core.celery_app import celery_app
from core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="orders.check_payment_expired")
def check_payment_expired():
    """E23: 每 5 分鐘掃描逾期未付款訂單，更新狀態並回補庫存+折扣券。"""
    asyncio.run(_check_payment_expired_async())


async def _check_payment_expired_async():
    from datetime import UTC, datetime

    from auth.models import User
    from orders.models import Order, OrderStatusEnum
    from orders.service import _send_email, expire_pending_order

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with AsyncSession(bind=engine, expire_on_commit=False) as db:
        now = datetime.now(UTC)
        result = await db.execute(
            select(Order).where(
                Order.status == OrderStatusEnum.pending_payment,
                Order.payment_deadline < now,
            )
        )
        orders = result.scalars().all()

        for order in orders:
            try:
                locked_result = await db.execute(
                    select(Order)
                    .where(
                        Order.id == order.id,
                        Order.status == OrderStatusEnum.pending_payment,
                    )
                    .with_for_update(skip_locked=True)
                )
                locked_order = locked_result.scalar_one_or_none()
                if locked_order is None:
                    continue

                # 標 payment_expired + 釋放庫存/折扣券、客製退回 quote_sent、
                # ECpay 取號未繳交易標 expired（與 reorder 主動過期共用同一邏輯）
                await expire_pending_order(db, locked_order)

                user_result = await db.execute(
                    select(User).where(User.id == locked_order.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    await _send_email(
                        to=user.email,
                        subject=f"【易木 YIIMUI】訂單付款逾期 {locked_order.order_number}",
                        html=(
                            f"<p>您的訂單 {locked_order.order_number}"
                            " 已超過付款期限，訂單已取消。</p>"
                            "<p>如有需要請重新下單。</p>"
                        ),
                    )
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to expire order {order.id}: {e}")
                await db.rollback()

    await engine.dispose()


# Celery Beat schedule
celery_app.conf.beat_schedule = {
    **getattr(celery_app.conf, "beat_schedule", {}),
    "check-payment-expired-every-5-min": {
        "task": "orders.check_payment_expired",
        "schedule": 300,  # 5 minutes
    },
}
