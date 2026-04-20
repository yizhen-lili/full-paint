import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from auth.models import User

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
USERS_URL = "/api/v1/admin/users"
ISSUE_COUPONS_URL = "/api/v1/admin/users/issue-coupons"

ADMIN_USER = {"name": "管理員帳號", "email": "admin@example.com", "password": "adminpass123"}
CUSTOMER_USER = {"name": "一般用戶", "email": "customer@example.com", "password": "custpass123"}
ADMIN2_USER = {"name": "管理員二號", "email": "admin2@example.com", "password": "admin2pass123"}


async def _make_user(client: AsyncClient, db, payload: dict, role: str = "customer") -> User:
    await client.post(REGISTER_URL, json=payload)
    result = await db.execute(select(User).where(User.email == payload["email"]))
    user = result.scalar_one()
    user.is_email_verified = True
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, email: str, password: str):
    res = await client.post(LOGIN_URL, json={"email": email, "password": password})
    if "access_token" in res.cookies:
        client.cookies.set("access_token", res.cookies["access_token"])
    return res


# ── GET /admin/users ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_users_no_filter(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(USERS_URL)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_users_search_match(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(USERS_URL, params={"search": "一般"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == CUSTOMER_USER["email"]


@pytest.mark.asyncio
async def test_list_users_search_no_match(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(USERS_URL, params={"search": "不存在的關鍵字xyz"})
    assert res.status_code == 200
    assert res.json()["items"] == []
    assert res.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_users_role_filter(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(USERS_URL, params={"role": "customer"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["role"] == "customer"


@pytest.mark.asyncio
async def test_list_users_is_active_filter(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    customer.is_active = False
    await db.commit()
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(USERS_URL, params={"is_active": "false"})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["is_active"] is False


@pytest.mark.asyncio
async def test_list_users_pagination(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    for i in range(3):
        payload = {"name": f"用戶{i:04d}", "email": f"u{i}@ex.com", "password": "testpass123"}
        await _make_user(client, db, payload)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(USERS_URL, params={"page": 1, "page_size": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_list_users_non_admin_forbidden(client: AsyncClient, db):
    await _make_user(client, db, CUSTOMER_USER)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])

    res = await client.get(USERS_URL)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client: AsyncClient, db):
    res = await client.get(USERS_URL)
    assert res.status_code == 401


# ── GET /admin/users/{id} ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_exists(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(f"{USERS_URL}/{customer.id}")
    assert res.status_code == 200
    assert res.json()["email"] == CUSTOMER_USER["email"]


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.get(f"{USERS_URL}/{uuid.uuid4()}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_get_user_non_admin_forbidden(client: AsyncClient, db):
    admin = await _make_user(client, db, ADMIN_USER, role="admin")
    await _make_user(client, db, CUSTOMER_USER)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])

    res = await client.get(f"{USERS_URL}/{admin.id}")
    assert res.status_code == 403


# ── PATCH /admin/users/{id} ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_user_name(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{customer.id}", json={"name": "新名字測試"})
    assert res.status_code == 200
    assert res.json()["name"] == "新名字測試"


@pytest.mark.asyncio
async def test_update_user_role(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{customer.id}", json={"role": "admin"})
    assert res.status_code == 200
    assert res.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_update_user_reset_password(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    new_pw = "newPassword99"
    res = await client.patch(f"{USERS_URL}/{customer.id}", json={"password": new_pw})
    assert res.status_code == 200

    client.cookies.clear()
    login_res = await _login(client, CUSTOMER_USER["email"], new_pw)
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_update_user_deactivate_customer(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{customer.id}", json={"is_active": False})
    assert res.status_code == 200
    assert res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_cannot_deactivate_self(client: AsyncClient, db):
    admin = await _make_user(client, db, ADMIN_USER, role="admin")
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{admin.id}", json={"is_active": False})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_update_user_cannot_deactivate_other_admin(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    admin2 = await _make_user(client, db, ADMIN2_USER, role="admin")
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{admin2.id}", json={"is_active": False})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_update_user_can_change_other_admin_role(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    admin2 = await _make_user(client, db, ADMIN2_USER, role="admin")
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{admin2.id}", json={"role": "customer"})
    assert res.status_code == 200
    assert res.json()["role"] == "customer"


@pytest.mark.asyncio
async def test_update_user_not_found(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{uuid.uuid4()}", json={"name": "名字名字"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_user_non_admin_forbidden(client: AsyncClient, db):
    admin = await _make_user(client, db, ADMIN_USER, role="admin")
    await _make_user(client, db, CUSTOMER_USER)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])

    res = await client.patch(f"{USERS_URL}/{admin.id}", json={"name": "名字名字"})
    assert res.status_code == 403


# ── PATCH /admin/users/{id} — validator errors ───────────────────────────────

@pytest.mark.asyncio
async def test_update_user_name_null_ignored(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{customer.id}", json={"name": None})
    assert res.status_code == 200
    assert res.json()["name"] == CUSTOMER_USER["name"]


@pytest.mark.asyncio
async def test_update_user_name_too_short(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{customer.id}", json={"name": "短"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_user_password_too_short(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{customer.id}", json={"password": "short1"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_user_password_no_digits(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    customer = await _make_user(client, db, CUSTOMER_USER)
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.patch(f"{USERS_URL}/{customer.id}", json={"password": "onlyletters!!"})
    assert res.status_code == 422


# ── POST /admin/users/issue-coupons ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_issue_coupons_stub_admin(client: AsyncClient, db):
    await _make_user(client, db, ADMIN_USER, role="admin")
    await _login(client, ADMIN_USER["email"], ADMIN_USER["password"])

    res = await client.post(ISSUE_COUPONS_URL, json={
        "user_ids": [str(uuid.uuid4())],
        "coupon_config_id": str(uuid.uuid4()),
    })
    assert res.status_code == 200
    assert res.json() == {"issued_count": 0}


@pytest.mark.asyncio
async def test_issue_coupons_stub_non_admin_forbidden(client: AsyncClient, db):
    await _make_user(client, db, CUSTOMER_USER)
    await _login(client, CUSTOMER_USER["email"], CUSTOMER_USER["password"])

    res = await client.post(ISSUE_COUPONS_URL, json={
        "user_ids": [str(uuid.uuid4())],
        "coupon_config_id": str(uuid.uuid4()),
    })
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_issue_coupons_stub_unauthenticated(client: AsyncClient, db):
    res = await client.post(ISSUE_COUPONS_URL, json={
        "user_ids": [str(uuid.uuid4())],
        "coupon_config_id": str(uuid.uuid4()),
    })
    assert res.status_code == 401
