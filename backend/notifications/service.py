import asyncio
import logging
import uuid as uuidlib
from datetime import UTC, datetime
from html import escape as html_escape
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import BadRequestError, NotFoundError
from notifications.models import AdminNotification, NotificationStatusEnum

logger = logging.getLogger(__name__)


# 商家會額外收 email 通知的 notification 類型（其餘 type 只在 admin 後台通知中心顯示）
EMAIL_TRIGGER_TYPES: set[str] = {
    "new_order",                    # 新訂單成立（等待匯款）
    "payment_submitted",            # 客人提交匯款回填
    "payment_resubmitted",          # 客人重交匯款回填
    "quote_pending",                # 新客製化申請
    "new_message",                  # 客製化 thread 新訊息
    "draft_revision_requested",     # 客人要求修改 draft
    "stock_shortage",               # 庫存不足（critical）
    "production_failed",            # 生產失敗（critical）
    "customer_modified_shipping",   # 客人改地址（出貨前要重新審）
}


async def _send_admin_email(subject: str, message: str, type_: str) -> None:
    """寄通知信給商家（settings.support_email）。Fire-and-forget，失敗不影響主流程。"""
    if not settings.support_email or not settings.resend_api_key:
        return
    try:
        import resend
        resend.api_key = settings.resend_api_key
        admin_url = (settings.admin_url or "").rstrip("/")
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        link_html = (
            f'<p style="margin-top:24px;"><a href="{admin_url}/admin/notifications" '
            'style="background:#2E2823;color:#FCF7E5;padding:10px 20px;'
            'text-decoration:none;border-radius:4px;font-size:13px;">前往後台查看</a></p>'
            if admin_url else ""
        )
        body_html = (
            '<div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;'
            'max-width:560px;margin:0 auto;padding:24px;color:#2E2823;">'
            '<h2 style="font-weight:400;margin:0 0 16px;">易木 YIIMUI 後台通知</h2>'
            f'<p style="font-size:15px;line-height:1.7;margin:0;">{html_escape(message)}</p>'
            f'<p style="font-size:12px;color:#888;margin-top:20px;">類型：{type_}　時間：{ts}</p>'
            f'{link_html}</div>'
        )
        payload: dict = {
            "from": settings.resend_from_email,
            "to": settings.support_email,
            "subject": f"[YIIMUI 後台] {subject}",
            "html": body_html,
        }
        await asyncio.get_running_loop().run_in_executor(
            None, lambda: resend.Emails.send(payload),
        )
    except Exception as e:
        logger.warning("Admin notification email failed (type=%s): %s", type_, e)


async def create_notification(
    db: AsyncSession,
    type: str,
    message: str,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    requires_action: bool = False,
    status: NotificationStatusEnum = NotificationStatusEnum.unhandled,
) -> AdminNotification:
    notification = AdminNotification(
        type=type,
        reference_type=reference_type,
        reference_id=reference_id,
        message=message,
        requires_action=requires_action,
        status=status,
    )
    db.add(notification)
    if type in EMAIL_TRIGGER_TYPES:
        await _send_admin_email(subject=message[:60], message=message, type_=type)
    return notification


async def create_or_update_stock_shortage(
    db: AsyncSession,
    physical_color_id: UUID,
    message: str,
) -> AdminNotification:
    """Dedup rule (§73): at most one ACTIVE stock_shortage per physical_color.
    Race-safe via partial unique index `uq_active_stock_shortage_per_ref` +
    INSERT ... ON CONFLICT DO UPDATE.
    """
    if physical_color_id is None:
        raise ValueError("physical_color_id is required for stock_shortage notification")

    new_id = uuidlib.uuid4()
    stmt = (
        pg_insert(AdminNotification)
        .values(
            id=new_id,
            type="stock_shortage",
            message=message,
            reference_type="physical_color",
            reference_id=physical_color_id,
            requires_action=True,
            status=NotificationStatusEnum.unhandled,
        )
        .on_conflict_do_update(
            index_elements=[
                AdminNotification.reference_type,
                AdminNotification.reference_id,
            ],
            index_where=text(
                "type = 'stock_shortage' "
                "AND status IN ('unhandled', 'in_progress')"
            ),
            set_={
                "message": message,
                "requires_action": True,
                "updated_at": func.now(),
            },
        )
        .returning(AdminNotification)
    )
    result = await db.execute(
        stmt.execution_options(populate_existing=True)
    )
    notification = result.scalar_one()
    await _send_admin_email(subject=message[:60], message=message, type_="stock_shortage")
    return notification


async def create_payment_resubmitted(
    db: AsyncSession,
    order_id: UUID,
    message: str,
) -> AdminNotification:
    """Create payment_resubmitted notification AND mark prior payment_submitted
    notifications for the same order as completed (per admin_notifications.md §73).
    """
    await db.execute(
        update(AdminNotification)
        .where(
            AdminNotification.type == "payment_submitted",
            AdminNotification.reference_type == "order",
            AdminNotification.reference_id == order_id,
            AdminNotification.status != NotificationStatusEnum.completed,
        )
        .values(
            status=NotificationStatusEnum.completed,
            message=AdminNotification.message + "（已被新付款表單取代）",
            updated_at=func.now(),
        )
    )
    return await create_notification(
        db,
        type="payment_resubmitted",
        message=message,
        reference_type="order",
        reference_id=order_id,
        requires_action=True,
    )


# ── Admin endpoints ────────────────────────────────────────────────────────────


async def list_notifications(
    db: AsyncSession,
    status: str | None,
    requires_action: bool | None,
    page: int,
    page_size: int,
) -> dict:
    query = select(AdminNotification)
    if status:
        query = query.where(AdminNotification.status == status)
    if requires_action is not None:
        query = query.where(AdminNotification.requires_action == requires_action)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    rows = (await db.execute(
        query.order_by(AdminNotification.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    return {
        "items": [_serialize(n) for n in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


_VALID_TRANSITIONS = {
    NotificationStatusEnum.in_progress: {NotificationStatusEnum.unhandled},
    NotificationStatusEnum.completed: {
        NotificationStatusEnum.unhandled,
        NotificationStatusEnum.in_progress,
    },
}


async def update_status(
    db: AsyncSession, notification_id: UUID, new_status: str
) -> AdminNotification:
    result = await db.execute(
        select(AdminNotification)
        .where(AdminNotification.id == notification_id)
        .with_for_update()
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        raise NotFoundError("通知不存在")

    target = NotificationStatusEnum(new_status)
    allowed_from = _VALID_TRANSITIONS.get(target)
    if allowed_from is None or notif.status not in allowed_from:
        raise BadRequestError(
            f"無法從 {notif.status} 轉換至 {new_status}",
            code="INVALID_STATUS_TRANSITION",
        )

    notif.status = target
    await db.commit()
    await db.refresh(notif)
    return notif


async def bulk_complete(db: AsyncSession, ids: list[UUID]) -> dict:
    requested = list(set(ids))
    result = await db.execute(
        select(AdminNotification)
        .where(AdminNotification.id.in_(requested))
        .with_for_update()
    )
    rows = list(result.scalars().all())
    found_ids = {n.id for n in rows}

    processed: list[UUID] = []
    skipped: list[UUID] = []
    for notif in rows:
        if notif.status == NotificationStatusEnum.completed:
            skipped.append(notif.id)
            continue
        notif.status = NotificationStatusEnum.completed
        processed.append(notif.id)

    # IDs not found at all also count as skipped
    for rid in requested:
        if rid not in found_ids:
            skipped.append(rid)

    await db.commit()
    return {
        "completed_count": len(processed),
        "processed_ids": processed,
        "skipped_ids": skipped,
    }


def _serialize(n: AdminNotification) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "message": n.message,
        "requires_action": n.requires_action,
        "status": n.status.value if hasattr(n.status, "value") else str(n.status),
        "reference_type": n.reference_type,
        "reference_id": n.reference_id,
        "created_at": n.created_at,
        "updated_at": n.updated_at,
    }
