from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from notifications.models import AdminNotification


async def create_notification(
    db: AsyncSession,
    type: str,
    message: str,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    requires_action: bool = False,
) -> AdminNotification:
    notification = AdminNotification(
        type=type,
        reference_type=reference_type,
        reference_id=reference_id,
        message=message,
        requires_action=requires_action,
    )
    db.add(notification)
    return notification
