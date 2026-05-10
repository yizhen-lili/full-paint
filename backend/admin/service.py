import logging
from uuid import UUID

import bcrypt as _bcrypt
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from auth.models import RoleEnum, User
from core.exceptions import ForbiddenError, NotFoundError


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


async def list_users(
    db: AsyncSession,
    search: str | None,
    role: str | None,
    is_active: bool | None,
    is_email_verified: bool | None,
    page: int,
    page_size: int,
) -> tuple[list[User], int]:
    conditions = []
    if search:
        pattern = f"%{search}%"
        conditions.append(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
    if role:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active == is_active)
    if is_email_verified is not None:
        conditions.append(User.is_email_verified == is_email_verified)

    base_query = select(User)
    if conditions:
        for c in conditions:
            base_query = base_query.where(c)

    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar()

    offset = (page - 1) * page_size
    result = await db.execute(base_query.offset(offset).limit(page_size))
    users = list(result.scalars().all())
    return users, total


async def get_user(db: AsyncSession, user_id: UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("用戶不存在")
    return user


async def update_user(
    db: AsyncSession,
    operator: User,
    target_id: UUID,
    fields: dict,
) -> User:
    result = await db.execute(select(User).where(User.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("用戶不存在")

    if fields.get("is_active") is False:
        if target.id == operator.id:
            raise ForbiddenError("不可停用自己的帳號")
        if target.role == RoleEnum.admin:
            raise ForbiddenError("不可停用其他管理員帳號")

    if "password" in fields:
        target.password_hash = _hash_password(fields.pop("password"))

    for key, value in fields.items():
        setattr(target, key, value)

    await db.commit()
    await db.refresh(target)
    return target


# ── 客服救援動作 ──────────────────────────────────────────────────────────────


async def admin_resend_verification(db: AsyncSession, target_id: UUID) -> None:
    """Admin 替未驗證 user 重寄驗證信（救援被卡住的 user）。

    使用情境：
    - User 註冊時 Resend 還沒設好，永遠收不到驗證信
    - User 註冊 email 打錯（admin 改 email 後重寄）
    - 系統信進垃圾信、user 找不到
    """
    result = await db.execute(select(User).where(User.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("用戶不存在")
    if target.is_email_verified:
        raise ForbiddenError("此帳號已驗證，無需重寄")

    # reuse auth.service 既有 resend_verification 邏輯（會自動廢舊 token + 發新 token）
    from auth.service import resend_verification
    await resend_verification(db, target.email)


async def admin_force_verify_email(db: AsyncSession, target_id: UUID) -> User:
    """Admin 強制把未驗證 user 標為已驗證（跳過 email 驗證流程）。

    使用情境：
    - user 永遠收不到信（垃圾信箱無解、email 公司擋）
    - 線下確認 user 身分後手動放行
    - 廢掉所有未用的 signup token（避免舊連結還能用）

    使用情境少，每次操作都 audit log（之後可加）。
    """
    from auth.models import EmailVerificationToken, TokenTypeEnum
    from datetime import UTC, datetime
    from sqlalchemy import update as sa_update

    result = await db.execute(select(User).where(User.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundError("用戶不存在")
    if target.is_email_verified:
        raise ForbiddenError("此帳號已驗證")

    target.is_email_verified = True
    # 廢掉所有未使用的 signup tokens
    await db.execute(
        sa_update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == target.id,
            EmailVerificationToken.token_type == TokenTypeEnum.signup,
            EmailVerificationToken.used_at == None,  # noqa: E711
        )
        .values(used_at=datetime.now(UTC))
    )
    await db.commit()
    await db.refresh(target)
    return target
