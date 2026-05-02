"""部署啟動時 idempotent 建 initial admin user。

從 env var 讀 credentials：
  INITIAL_ADMIN_EMAIL
  INITIAL_ADMIN_PASSWORD

行為：
- 兩個 env var 都沒設 → skip（log info）
- 該 email 的 user 已存在 → skip（idempotent，不更新密碼）
- 否則建 admin user：role=admin, is_active=True, is_email_verified=True

部署後可以把這兩個 env vars 從 Railway 刪除（user 已建好，重啟不重複跑）。
"""
from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import auth.models  # noqa: F401
from auth.models import User
from core.config import settings


def _hash_password(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def init_admin() -> None:
    email = os.environ.get("INITIAL_ADMIN_EMAIL", "").strip()
    password = os.environ.get("INITIAL_ADMIN_PASSWORD", "").strip()

    if not email or not password:
        print("[init_admin] INITIAL_ADMIN_EMAIL/PASSWORD not set, skipping", flush=True)
        return

    engine = create_async_engine(settings.database_url)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            existing = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if existing is not None:
                print(
                    f"[init_admin] user {email} already exists "
                    f"(role={existing.role}), skipping",
                    flush=True,
                )
                return

            user = User(
                name="Admin",
                email=email,
                password_hash=_hash_password(password),
                role="admin",
                is_active=True,
                is_email_verified=True,
            )
            session.add(user)
            await session.commit()
            print(f"[init_admin] created admin user: {email}", flush=True)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(init_admin()) or 0)
