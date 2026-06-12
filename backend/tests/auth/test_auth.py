from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from auth.models import EmailVerificationToken, PasswordResetToken, RoleEnum, User
from auth.service import _hash_password, _hash_token, cleanup_unverified_users

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"
VERIFY_URL = "/api/v1/auth/verify-email"
RESEND_URL = "/api/v1/auth/resend-verification"
FORGOT_URL = "/api/v1/auth/forgot-password"
RESET_URL = "/api/v1/auth/reset-password"
ADMIN_LOGIN_URL = "/api/v1/admin/auth/login"

VALID_USER = {"name": "測試用戶", "email": "test@example.com", "password": "testpass123"}
VALID_PASSWORD = "testpass123"


async def _register_and_verify(client: AsyncClient, db, email=None, password=None):
    """Helper：註冊並完成 email 驗證，回傳 user。"""
    payload = {**VALID_USER}
    if email:
        payload["email"] = email
    if password:
        payload["password"] = password

    await client.post(REGISTER_URL, json=payload)

    # Directly update user to verified for test convenience (token is hashed in DB)
    result2 = await db.execute(select(User).where(User.email == payload["email"]))
    user = result2.scalar_one()
    user.is_email_verified = True
    await db.commit()
    return user


# ── Register ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, db):
    res = await client.post(REGISTER_URL, json=VALID_USER)
    assert res.status_code == 201
    assert res.json()["message"] == "驗證信已寄出"

    result = await db.execute(select(User).where(User.email == VALID_USER["email"]))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.role == "customer"
    assert user.is_email_verified is False


@pytest.mark.asyncio
async def test_register_duplicate_verified_email_blocked(client: AsyncClient, db):
    """已驗證的 email 不可重註冊 — 報 409。"""
    await client.post(REGISTER_URL, json=VALID_USER)
    # 手動把 user 標為已驗證
    result = await db.execute(select(User).where(User.email == VALID_USER["email"]))
    user = result.scalar_one()
    user.is_email_verified = True
    await db.commit()

    res = await client.post(REGISTER_URL, json=VALID_USER)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_register_unverified_email_overwrites(client: AsyncClient, db):
    """未驗證 user 重註冊同 email — 應回 201、覆蓋 password、廢舊 token、發新驗證信。

    回歸測試 — 修補「user 註冊但沒驗證 → 卡死無法再註冊」的 bug。
    """
    from auth.models import EmailVerificationToken, TokenTypeEnum

    # 第一次註冊
    res1 = await client.post(REGISTER_URL, json=VALID_USER)
    assert res1.status_code == 201

    result = await db.execute(select(User).where(User.email == VALID_USER["email"]))
    user_before = result.scalar_one()
    assert user_before.is_email_verified is False
    user_id = user_before.id
    old_password_hash = user_before.password_hash

    # 找出第一次發的 token
    tok_result = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.token_type == TokenTypeEnum.signup,
        )
    )
    old_token = tok_result.scalar_one()
    assert old_token.used_at is None

    # 第二次註冊（同 email、不同 name + password；name ≥ 4 字元 schema 限制）
    new_user = {**VALID_USER, "name": "新名字測", "password": "NewPass123"}
    res2 = await client.post(REGISTER_URL, json=new_user)
    assert res2.status_code == 201

    # user 仍是同一個（id 不變）— 沒重建記錄
    await db.refresh(user_before)
    assert user_before.id == user_id
    # 但 name + password 已被覆蓋
    assert user_before.name == "新名字測"
    assert user_before.password_hash != old_password_hash
    # 仍未驗證
    assert user_before.is_email_verified is False

    # 舊 token 被廢掉（used_at 不為 None）
    await db.refresh(old_token)
    assert old_token.used_at is not None

    # 應該有新的 unused token
    unused_tokens = await db.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.token_type == TokenTypeEnum.signup,
            EmailVerificationToken.used_at == None,  # noqa: E711
        )
    )
    assert unused_tokens.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient, db):
    res = await client.post(REGISTER_URL, json={**VALID_USER, "password": "abc123"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_password_no_letter(client: AsyncClient, db):
    res = await client.post(REGISTER_URL, json={**VALID_USER, "password": "1234567890"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_password_no_digit(client: AsyncClient, db):
    res = await client.post(REGISTER_URL, json={**VALID_USER, "password": "abcdefghij"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_register_name_too_short(client: AsyncClient, db):
    res = await client.post(REGISTER_URL, json={**VALID_USER, "name": "ab"})
    assert res.status_code == 422


# ── Login ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_unverified_email(client: AsyncClient, db):
    await client.post(REGISTER_URL, json=VALID_USER)
    res = await client.post(
        LOGIN_URL, json={"email": VALID_USER["email"], "password": VALID_PASSWORD}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db):
    await _register_and_verify(client, db)
    res = await client.post(
        LOGIN_URL, json={"email": VALID_USER["email"], "password": "wrongpass999"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient, db):
    res = await client.post(
        LOGIN_URL, json={"email": "nobody@example.com", "password": VALID_PASSWORD}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db):
    await _register_and_verify(client, db)
    res = await client.post(
        LOGIN_URL, json={"email": VALID_USER["email"], "password": VALID_PASSWORD}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "customer"
    assert data["name"] == VALID_USER["name"]
    assert "access_token" in res.cookies


@pytest.mark.asyncio
async def test_login_disabled_account(client: AsyncClient, db):
    user = await _register_and_verify(client, db)
    user.is_active = False
    await db.commit()

    res = await client.post(
        LOGIN_URL, json={"email": VALID_USER["email"], "password": VALID_PASSWORD}
    )
    assert res.status_code == 403


# ── Verify Email ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_email_signup_success(client: AsyncClient, db):
    await client.post(REGISTER_URL, json=VALID_USER)

    result = await db.execute(
        select(EmailVerificationToken)
        .join(User, User.id == EmailVerificationToken.user_id)
        .where(User.email == VALID_USER["email"])
    )
    token_row = result.scalar_one()

    # We need the plain token - re-create it to simulate the email link
    # For testing: directly set a known token hash
    import secrets

    from auth.service import _hash_token
    plain = secrets.token_urlsafe(32)
    token_row.token = _hash_token(plain)
    await db.commit()

    res = await client.post(VERIFY_URL, json={"token": plain})
    assert res.status_code == 200
    assert res.json()["token_type"] == "signup"

    await db.refresh(token_row)
    result2 = await db.execute(select(User).where(User.email == VALID_USER["email"]))
    user = result2.scalar_one()
    assert user.is_email_verified is True


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient, db):
    res = await client.post(VERIFY_URL, json={"token": "invalidtoken"})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_used_token(client: AsyncClient, db):
    import secrets
    from datetime import datetime
    await client.post(REGISTER_URL, json=VALID_USER)

    result = await db.execute(
        select(EmailVerificationToken)
        .join(User, User.id == EmailVerificationToken.user_id)
        .where(User.email == VALID_USER["email"])
    )
    token_row = result.scalar_one()
    plain = secrets.token_urlsafe(32)
    token_row.token = _hash_token(plain)
    token_row.used_at = datetime.now(UTC)
    await db.commit()

    res = await client.post(VERIFY_URL, json={"token": plain})
    assert res.status_code == 400


# ── Forgot / Reset Password ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_nonexistent_email(client: AsyncClient, db):
    res = await client.post(FORGOT_URL, json={"email": "nobody@example.com"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient, db):
    import secrets
    user = await _register_and_verify(client, db)

    plain = secrets.token_urlsafe(32)
    from datetime import datetime, timedelta
    token = PasswordResetToken(
        user_id=user.id,
        token=_hash_token(plain),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(token)
    await db.commit()

    res = await client.post(RESET_URL, json={"token": plain, "new_password": "newpass12345"})
    assert res.status_code == 200

    login_res = await client.post(
        LOGIN_URL, json={"email": VALID_USER["email"], "password": "newpass12345"}
    )
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient, db):
    res = await client.post(RESET_URL, json={"token": "badtoken", "new_password": "newpass12345"})
    assert res.status_code == 400


# ── Admin Login ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_email_change_expired_token(client: AsyncClient, db):
    import secrets
    from datetime import datetime, timedelta
    user = await _register_and_verify(client, db)
    user.pending_email = "changed@example.com"
    await db.commit()

    plain = secrets.token_urlsafe(32)
    from auth.models import TokenTypeEnum
    token = EmailVerificationToken(
        user_id=user.id,
        token=_hash_token(plain),
        token_type=TokenTypeEnum.email_change,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db.add(token)
    await db.commit()

    res = await client.post(VERIFY_URL, json={"token": plain})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_change_success(client: AsyncClient, db):
    import secrets
    from datetime import datetime, timedelta
    user = await _register_and_verify(client, db)
    user.pending_email = "changed@example.com"
    await db.commit()

    plain = secrets.token_urlsafe(32)
    from auth.models import TokenTypeEnum
    token = EmailVerificationToken(
        user_id=user.id,
        token=_hash_token(plain),
        token_type=TokenTypeEnum.email_change,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(token)
    await db.commit()

    res = await client.post(VERIFY_URL, json={"token": plain})
    assert res.status_code == 200
    assert res.json()["token_type"] == "email_change"

    await db.refresh(user)
    assert user.email == "changed@example.com"
    assert user.pending_email is None


@pytest.mark.asyncio
async def test_verify_email_change_old_email_cannot_login(client: AsyncClient, db):
    import secrets
    from datetime import datetime, timedelta
    user = await _register_and_verify(client, db)
    old_email = user.email
    user.pending_email = "changed2@example.com"
    await db.commit()

    plain = secrets.token_urlsafe(32)
    from auth.models import TokenTypeEnum
    token = EmailVerificationToken(
        user_id=user.id,
        token=_hash_token(plain),
        token_type=TokenTypeEnum.email_change,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(token)
    await db.commit()

    await client.post(VERIFY_URL, json={"token": plain})

    res = await client.post(LOGIN_URL, json={"email": old_email, "password": VALID_PASSWORD})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_verify_email_change_new_email_can_login(client: AsyncClient, db):
    import secrets
    from datetime import datetime, timedelta
    user = await _register_and_verify(client, db)
    user.pending_email = "changed3@example.com"
    await db.commit()

    plain = secrets.token_urlsafe(32)
    from auth.models import TokenTypeEnum
    token = EmailVerificationToken(
        user_id=user.id,
        token=_hash_token(plain),
        token_type=TokenTypeEnum.email_change,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db.add(token)
    await db.commit()

    await client.post(VERIFY_URL, json={"token": plain})

    res = await client.post(
        LOGIN_URL, json={"email": "changed3@example.com", "password": VALID_PASSWORD}
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_verify_email_change_used_token(client: AsyncClient, db):
    import secrets
    from datetime import datetime, timedelta
    user = await _register_and_verify(client, db)
    user.pending_email = "used@example.com"
    await db.commit()

    plain = secrets.token_urlsafe(32)
    from auth.models import TokenTypeEnum
    token = EmailVerificationToken(
        user_id=user.id,
        token=_hash_token(plain),
        token_type=TokenTypeEnum.email_change,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        used_at=datetime.now(UTC),
    )
    db.add(token)
    await db.commit()

    res = await client.post(VERIFY_URL, json={"token": plain})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_admin_login_with_customer_account(client: AsyncClient, db):
    await _register_and_verify(client, db)
    res = await client.post(
        ADMIN_LOGIN_URL, json={"email": VALID_USER["email"], "password": VALID_PASSWORD}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_login_success(client: AsyncClient, db):
    import bcrypt
    admin = User(
        name="Admin",
        email="admin@test.com",
        password_hash=bcrypt.hashpw(b"adminpass123", bcrypt.gensalt()).decode(),
        role="admin",
        is_active=True,
        is_email_verified=True,
    )
    db.add(admin)
    await db.commit()

    res = await client.post(
        ADMIN_LOGIN_URL, json={"email": "admin@test.com", "password": "adminpass123"}
    )
    assert res.status_code == 200
    assert res.json()["role"] == "admin"
    assert "access_token" in res.cookies


# ── Cleanup unverified users ───────────────────────────────────────────────────

async def _make_user(db, email: str, *, verified: bool, age_hours: int, role=RoleEnum.customer):
    user = User(
        name=f"u_{email}",
        email=email,
        password_hash=_hash_password("p4ssw0rd_xyz"),
        role=role,
        is_email_verified=verified,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    # 強制 created_at 為過去時間（service 比對用 created_at）
    user.created_at = datetime.now(UTC) - timedelta(hours=age_hours)
    await db.commit()
    return user


@pytest.mark.asyncio
async def test_cleanup_deletes_old_unverified_customer(db):
    user = await _make_user(db, "stale@test.com", verified=False, age_hours=30)
    user_id = user.id

    deleted = await cleanup_unverified_users(db, grace_hours=25)

    assert deleted == 1
    result = await db.execute(select(User).where(User.id == user_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_cleanup_skips_recent_unverified_customer(db):
    user = await _make_user(db, "fresh@test.com", verified=False, age_hours=10)

    deleted = await cleanup_unverified_users(db, grace_hours=25)

    assert deleted == 0
    result = await db.execute(select(User).where(User.id == user.id))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_cleanup_skips_verified_user(db):
    user = await _make_user(db, "verified@test.com", verified=True, age_hours=100)

    deleted = await cleanup_unverified_users(db, grace_hours=25)

    assert deleted == 0
    result = await db.execute(select(User).where(User.id == user.id))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_cleanup_skips_admin_role(db):
    user = await _make_user(
        db, "stale_admin@test.com", verified=False, age_hours=100, role=RoleEnum.admin
    )

    deleted = await cleanup_unverified_users(db, grace_hours=25)

    assert deleted == 0
    result = await db.execute(select(User).where(User.id == user.id))
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_cleanup_cascades_tokens(db):
    user = await _make_user(db, "with_tokens@test.com", verified=False, age_hours=30)
    db.add(EmailVerificationToken(
        user_id=user.id,
        token="x" * 64,
        token_type="signup",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    ))
    db.add(PasswordResetToken(
        user_id=user.id,
        token="y" * 64,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    ))
    await db.commit()

    deleted = await cleanup_unverified_users(db, grace_hours=25)

    assert deleted == 1
    ev = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.user_id == user.id)
    )
    assert ev.scalar_one_or_none() is None
    pr = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    assert pr.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_register_rolls_back_when_email_fails(
    client: AsyncClient, db, monkeypatch
):
    """RESEND_API_KEY 沒設 / email 寄信失敗 → register 必須 rollback 不留孤兒帳號。

    之前的 bug：silent try/except 吞掉 email 失敗，user 建出來但 is_email_verified=False
    永遠拿不到驗證連結 → 登不進。修法後 email 失敗 = 全部 rollback + 回 503。
    """
    from core.exceptions import ExternalServiceError

    async def _raise(to, subject, html):
        raise ExternalServiceError("test: email infra down")

    monkeypatch.setattr("auth.service._send_email", _raise)

    res = await client.post(
        REGISTER_URL,
        json={"name": "orphan", "email": "orphan@test.com", "password": "abc1234567"},
    )
    assert res.status_code == 503

    # DB 應該完全沒留下這個 user 跟 token（rollback 成功）
    user_row = await db.execute(select(User).where(User.email == "orphan@test.com"))
    assert user_row.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_forgot_password_rolls_back_when_email_fails(
    client: AsyncClient, db, monkeypatch
):
    """forgot-password email 失敗 → 新 reset token 不該入庫，避免 user 以為已寄出。"""
    from core.exceptions import ExternalServiceError

    # 先正常註冊 + 驗證
    user = await _register_and_verify(client, db, email="forgot@test.com")
    user_id = user.id  # 先拿出來，後面 rollback 後 session 狀態可能不穩

    # 接下來 mock email 寄信失敗
    async def _raise(to, subject, html):
        raise ExternalServiceError("test: email infra down")

    monkeypatch.setattr("auth.service._send_email", _raise)

    res = await client.post(FORGOT_URL, json={"email": "forgot@test.com"})
    assert res.status_code == 503

    # DB 應該沒新增 reset token
    pr = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
    )
    assert pr.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_cleanup_frees_email_for_reregistration(client: AsyncClient, db):
    """user 註冊後 25h+ 沒驗證 → cleanup → 同 email 可再次註冊。"""
    email = "reuse@test.com"

    # 第一次註冊
    await client.post(
        REGISTER_URL, json={"name": "first", "email": email, "password": "abc1234567"}
    )

    # 強制讓帳號變舊
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.created_at = datetime.now(UTC) - timedelta(hours=30)
    await db.commit()

    # cleanup 後 email 釋出
    await cleanup_unverified_users(db, grace_hours=25)

    # 同 email 再註冊應該成功
    res = await client.post(
        REGISTER_URL, json={"name": "second", "email": email, "password": "abc1234567"}
    )
    assert res.status_code == 201


# ── Google Sign-in ─────────────────────────────────────────────────────────────
#
# Google ID token verification 是 sync call 到 google-auth lib，會打 Google 公鑰
# endpoint。所有 case 都 monkeypatch verify_oauth2_token 回固定 dict 模擬 Google
# 已驗證的 token，避免測試打外網 / 假 JWT 要簽。

GOOGLE_URL = "/api/v1/auth/google"


def _patch_google_token(monkeypatch, sub: str, email: str, email_verified: bool = True,
                       name: str = "Test User") -> None:
    """共用：mock id_token.verify_oauth2_token 回固定 dict。"""
    payload = {"sub": sub, "email": email, "email_verified": email_verified, "name": name}
    monkeypatch.setattr(
        "google.oauth2.id_token.verify_oauth2_token",
        lambda *args, **kwargs: payload,
    )
    # GOOGLE_CLIENT_ID 必須非空，否則 service 會主動 raise 503
    from core.config import settings as _settings
    monkeypatch.setattr(_settings, "google_client_id", "test-client-id.apps.googleusercontent.com")


@pytest.mark.asyncio
async def test_google_signin_new_user(client: AsyncClient, db, monkeypatch):
    """情境 C：全新 email + 全新 google_sub → 建 user，password=NULL，已驗證。"""
    _patch_google_token(monkeypatch, sub="google-sub-001", email="new@gmail.com", name="新用戶")

    res = await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})
    assert res.status_code == 200
    assert res.json()["name"] == "新用戶"

    u = (await db.execute(select(User).where(User.email == "new@gmail.com"))).scalar_one()
    assert u.google_sub == "google-sub-001"
    assert u.password_hash is None
    assert u.is_email_verified is True
    assert u.role == "customer"


@pytest.mark.asyncio
async def test_google_signin_merges_existing_email(client: AsyncClient, db, monkeypatch):
    """情境 B：既有 email/password 用戶 + 同 email 的 Google 登入 → 隱式合併 google_sub。"""
    # 先建一個 email/password 帳號（即使尚未驗證）— name 必須 ≥4 字元（schema validator）
    register_res = await client.post(
        REGISTER_URL,
        json={"name": "舊有用戶", "email": "merge@test.com", "password": "abc1234567"},
    )
    assert register_res.status_code == 201

    _patch_google_token(monkeypatch, sub="google-sub-002", email="merge@test.com", name="新名字")

    res = await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})
    assert res.status_code == 200

    u = (await db.execute(select(User).where(User.email == "merge@test.com"))).scalar_one()
    assert u.google_sub == "google-sub-002"
    assert u.is_email_verified is True  # Google 認可 → 視同已驗證
    # password_hash 不該被清掉（既有 user 仍可用 email + password 登入）
    assert u.password_hash is not None
    # name 不該被 Google name 覆蓋（保留用戶原註冊資料）
    assert u.name == "舊有用戶"


@pytest.mark.asyncio
async def test_google_signin_existing_google_user(client: AsyncClient, db, monkeypatch):
    """情境 A：已綁 google_sub 的 user 再點 Google → 直接登入，不重複建。"""
    _patch_google_token(monkeypatch, sub="google-sub-003", email="repeat@gmail.com")

    # 第一次：建帳號
    r1 = await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})
    assert r1.status_code == 200

    # 第二次：應該 lookup 到既有 user，不該再建一個
    r2 = await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})
    assert r2.status_code == 200

    rows = (await db.execute(select(User).where(User.email == "repeat@gmail.com"))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_google_signin_invalid_token(client: AsyncClient, db, monkeypatch):
    """ID token verify 失敗（簽章 / audience / 過期）→ 401。"""
    def _raise(*args, **kwargs):
        raise ValueError("Token signature invalid")

    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", _raise)
    from core.config import settings as _settings
    monkeypatch.setattr(_settings, "google_client_id", "test-client-id.apps.googleusercontent.com")

    res = await client.post(GOOGLE_URL, json={"id_token": "tampered.jwt.token"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_google_signin_unverified_email_rejected(client: AsyncClient, db, monkeypatch):
    """Google email_verified=False（罕見）→ 403。"""
    _patch_google_token(
        monkeypatch, sub="google-sub-004", email="unverified@gmail.com", email_verified=False
    )

    res = await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_google_signin_admin_rejected(client: AsyncClient, db, monkeypatch):
    """既有 admin role 用 Google 登入 → 403（admin 仍走 email/password）。"""
    # 先把這個 user 升 admin（name 須 ≥4 字元）
    await client.post(
        REGISTER_URL,
        json={"name": "管理者人", "email": "admin@yiimui.com", "password": "abc1234567"},
    )
    u = (await db.execute(select(User).where(User.email == "admin@yiimui.com"))).scalar_one()
    u.role = RoleEnum.admin
    u.is_email_verified = True
    await db.commit()

    _patch_google_token(monkeypatch, sub="google-sub-005", email="admin@yiimui.com")

    res = await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_login_blocked_for_google_only_user(client: AsyncClient, db, monkeypatch):
    """Google-only 用戶（password_hash=NULL）嘗試 email/password 登入 → 400 引導改用 Google。"""
    _patch_google_token(monkeypatch, sub="google-sub-006", email="googleonly@gmail.com")
    await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})

    # 嘗試用 password 登入
    res = await client.post(
        LOGIN_URL,
        json={"email": "googleonly@gmail.com", "password": "anything1234"},
    )
    assert res.status_code == 400
    assert "Google" in res.json()["detail"]


@pytest.mark.asyncio
async def test_forgot_password_silent_for_google_only_user(client: AsyncClient, db, monkeypatch):
    """Google-only 用戶 forgot-password → 200 但不寄信、不建 reset token。"""
    _patch_google_token(monkeypatch, sub="google-sub-007", email="silentgoogle@gmail.com")
    await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})

    u = (await db.execute(select(User).where(User.email == "silentgoogle@gmail.com"))).scalar_one()
    user_id = u.id

    res = await client.post(FORGOT_URL, json={"email": "silentgoogle@gmail.com"})
    assert res.status_code == 200  # 不洩漏帳號類型

    # 確認 DB 沒新增 reset token
    pr = await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == user_id))
    assert pr.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_register_rejects_google_bound_email(client: AsyncClient, db, monkeypatch):
    """email 已綁 Google 帳號時 register 用此 email → 409，引導用 Google 登入。"""
    _patch_google_token(monkeypatch, sub="google-sub-008", email="googlebound@gmail.com")
    await client.post(GOOGLE_URL, json={"id_token": "fake.jwt.token"})

    res = await client.post(
        REGISTER_URL,
        json={"name": "搶他帳號", "email": "googlebound@gmail.com", "password": "abc1234567"},
    )
    assert res.status_code == 409
    assert "Google" in res.json()["detail"]
