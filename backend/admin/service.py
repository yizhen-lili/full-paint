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
