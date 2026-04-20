# Module 1：Auth 實作規劃

> 對照規格：`requirements/auth_users.md`、`schema.md`（users / email_verification_tokens / password_reset_tokens）、`api.md`（模組一）
> 撰寫日期：2026-04-19

---

## 一、要建立的檔案

```
backend/
├── auth/
│   ├── __init__.py
│   ├── router.py          # 所有 Auth endpoints
│   ├── service.py         # 業務邏輯（token 生成、驗證、密碼、email）
│   ├── models.py          # User、EmailVerificationToken、PasswordResetToken ORM 模型
│   └── schemas/
│       ├── __init__.py
│       ├── request.py     # RegisterRequest、LoginRequest、VerifyEmailRequest 等
│       └── response.py    # UserResponse、MeResponse
└── scripts/
    └── create_admin.py    # 初次部署建立第一個 admin 帳號的 CLI 腳本
```

> `shipping_profiles` 屬於 Module 2，不在此建立。

---

## 二、DB 模型（models.py）

### User
```
id              UUID, PK
name            VARCHAR, NOT NULL, min 4 UTF-8 chars
email           VARCHAR, NOT NULL, UNIQUE
password_hash   VARCHAR, NOT NULL
gender          ENUM('female','male','other'), nullable
birthday        DATE, nullable
role            ENUM('admin','customer'), NOT NULL, DEFAULT 'customer'
is_active       BOOLEAN, NOT NULL, DEFAULT true
is_email_verified BOOLEAN, NOT NULL, DEFAULT false
pending_email   VARCHAR, nullable
created_at      TIMESTAMP, NOT NULL, DEFAULT now()
updated_at      TIMESTAMP, NOT NULL, DEFAULT now()
```

### EmailVerificationToken
```
id          UUID, PK
user_id     UUID, NOT NULL, FK → users.id
token       VARCHAR, NOT NULL  ← 存 sha256 hash，不存明文
token_type  ENUM('signup','email_change'), NOT NULL
expires_at  TIMESTAMP, NOT NULL  ← created_at + 24h
used_at     TIMESTAMP, nullable  ← 使用後填入，作廢標記
created_at  TIMESTAMP, NOT NULL, DEFAULT now()
```

### PasswordResetToken
```
id          UUID, PK
user_id     UUID, NOT NULL, FK → users.id
token       VARCHAR, NOT NULL  ← 存 sha256 hash
expires_at  TIMESTAMP, NOT NULL  ← created_at + 1h
used_at     TIMESTAMP, nullable
created_at  TIMESTAMP, NOT NULL, DEFAULT now()
```

---

## 三、Endpoints 與業務邏輯

### POST /auth/register（public）

**Request：** `{ name, email, password }`

**驗證：**
1. `name`：UTF-8 字元長度 ≥ 4（`len(name.encode())` 不夠，需用 `len(name)` 計算 Unicode 字元數）
2. `password`：長度 ≥ 10，且同時含英文字母 + 數字（regex `(?=.*[A-Za-z])(?=.*\d)`）
3. `email`：格式驗證（Pydantic EmailStr）
4. email 唯一性：查 `users.email = email` **AND** `users.pending_email = email`，有任一衝突 → 409

**成功流程：**
1. bcrypt hash password
2. INSERT users（role 強制 `customer`，不接受前端傳入）
3. 生成 `secrets.token_urlsafe(32)` plain token → sha256 hash 後存入 `email_verification_tokens`（type=signup, expires_at=now()+24h）
4. 用 Resend 寄驗證信（含 plain token 的連結），失敗只 log，不擋流程
5. Response 201：`{ "message": "驗證信已寄出" }`

---

### POST /auth/login（public）

**Request：** `{ email, password }`

**驗證順序（順序不可換，防止資訊洩漏）：**
1. 查 users by email → 找不到 → **401**（帳號或密碼錯誤，不區分）
2. bcrypt 驗密碼 → 錯 → **401**
3. `is_email_verified = false` → **403**
4. `is_active = false` → **403**
5. 成功：生成 JWT（payload: `{user_id, role, exp}`）→ 設 httpOnly cookie（`access_token`，7天，SameSite=Lax）

**Response 200：** `{ id, name, role: "customer" }`

---

### POST /auth/logout（auth）

清除 `access_token` cookie（set-cookie: max-age=0）

---

### GET /auth/me（auth）

從 cookie 讀 JWT → 驗 → 查 `is_active`（false → 401）→ Response：
`{ id, name, email, pending_email, role, gender, birthday }`

---

### POST /auth/verify-email（public）

**Request：** `{ token: "plain token string" }`

**流程：**
1. sha256(token) → 查 `email_verification_tokens`
2. 找不到 → 400（token 無效）
3. `used_at IS NOT NULL` → 400（已使用）
4. `expires_at < now()` → 400（已過期）
5. 依 `token_type`：
   - **signup**：`users.is_email_verified = true` → 呼叫 `coupon_service.issue_new_user_coupon(user_id)`（Module 11 實作，現在建 stub）
   - **email_change**：`users.email = users.pending_email`，`users.pending_email = null`
6. `email_verification_tokens.used_at = now()`
7. Response 200：`{ token_type: "signup"|"email_change" }`

---

### POST /auth/resend-verification（public）

**Request：** `{ email }`

**流程：**
1. 查 users by email
2. 找不到 / `is_email_verified = true` → **固定回成功**（不洩漏帳號資訊）
3. 找到且未驗證：建新 token（24h），舊 token 自然過期不主動作廢
4. 用 Resend 寄信，失敗只 log
5. Response 200：`{ "message": "驗證信已重新寄出" }`

---

### POST /auth/forgot-password（public）

**Request：** `{ email }`

**流程：**
1. 查 users by email
2. 找到：
   - `UPDATE password_reset_tokens SET used_at=now() WHERE user_id=? AND used_at IS NULL`（作廢所有舊 token）
   - 建新 token（1h），存 hash
   - 用 Resend 寄重設信，失敗只 log
3. **無論 email 是否存在，固定回成功**
4. Response 200：`{ "message": "若帳號存在，重設連結已寄出" }`

---

### POST /auth/reset-password（public）

**Request：** `{ token, new_password }`

**流程：**
1. 驗 `new_password` 格式（≥10碼，英數混合）
2. sha256(token) → 查 `password_reset_tokens`
3. 找不到 / `used_at IS NOT NULL` / `expires_at < now()` → 400
4. bcrypt hash new_password → `users.password_hash = ?`
5. `password_reset_tokens.used_at = now()`
6. Response 200：`{ "message": "密碼已更新" }`

---

### POST /admin/auth/login（public）

**差異：**
- 驗 `role = 'admin'`（不是 admin → 403）
- cookie 有效期 **8 小時**（非 7 天）
- Response：`{ id, name, role: "admin" }`

---

### POST /admin/auth/logout（admin）

同 customer logout，清除 cookie。

---

### POST /admin/auth/forgot-password（public）

流程同 `POST /auth/forgot-password`，email 信中連結導向 `/admin/reset-password`（前端差異，後端 endpoint 相同邏輯）。

---

## 四、Token 安全機制

| 步驟 | 說明 |
|------|------|
| 產生 | `secrets.token_urlsafe(32)`（256-bit 隨機值） |
| 儲存 | `hashlib.sha256(token.encode()).hexdigest()` → 存 DB |
| 驗證 | 收到 plain token → 同樣 hash → 比對 DB |
| 作廢 | 設 `used_at = now()`，查詢時 `used_at IS NULL` 才有效 |

---

## 五、Cookie 設定

```python
response.set_cookie(
    key="access_token",
    value=jwt_token,
    httponly=True,
    samesite="lax",
    secure=True,       # 生產環境（HTTPS）
    max_age=60*60*24*7  # customer: 7天 / admin: 60*60*8（8小時）
)
```

---

## 六、跨模組依賴

| 依賴 | 說明 | 處理方式 |
|------|------|---------|
| Coupon Module（Module 11）| verify-email signup 觸發 new_user 券 | 在 `coupons/service.py` 建 stub function `issue_new_user_coupon(user_id)`，Module 11 實作時填入邏輯 |
| Resend（外部）| 所有 email 發送 | 失敗只 log，不阻斷流程 |

---

## 七、Alembic 遷移

新增 `import auth.models` 至 `migrations/env.py`（已有此機制），執行 `alembic revision --autogenerate -m "create_auth_tables"` 後確認生成的 migration 正確。

---

## 八、測試覆蓋範圍

| 測試情境 | 預期結果 |
|---------|---------|
| 正常註冊 → 驗證信寄出 | 201 |
| 重複 email 註冊 | 409 |
| 登入未驗證帳號 | 403 |
| 登入停用帳號 | 403 |
| 錯誤密碼 | 401 |
| 正常登入 → cookie 設定 | 200 + Set-Cookie |
| verify-email signup → coupon stub 呼叫 | 200 + token_type=signup |
| verify-email 已使用 token | 400 |
| verify-email 過期 token | 400 |
| forgot-password 不存在 email | 200（固定） |
| reset-password 有效 token | 200 |
| reset-password 已用 token | 400 |
| admin login 非 admin 帳號 | 403 |
| admin login 正確 → 8h cookie | 200 |

---

## 九、待確認事項

詳見下方與使用者的確認問題。
