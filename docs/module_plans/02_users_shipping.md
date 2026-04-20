# Module 2+3：用戶資料 + 收件資料 實作規劃

> 對照規格：`requirements/auth_users.md`（§2用戶操作、§5收件資料）、`schema.md`（shipping_profiles）、`api.md`（模組二、模組三）
> 撰寫日期：2026-04-19

---

## 一、要建立的檔案

```
backend/
├── users/
│   ├── __init__.py
│   ├── models.py          # ShippingProfile ORM 模型
│   ├── service.py         # 業務邏輯
│   ├── router.py          # 所有 /users/* endpoints
│   └── schemas/
│       ├── __init__.py
│       ├── request.py     # UpdateProfileRequest、ChangePasswordRequest 等
│       └── response.py    # UserProfileResponse、ShippingProfileResponse
├── tests/
│   └── users/
│       ├── __init__.py
│       └── test_users.py
└── migrations/versions/
    └── xxxx_create_shipping_profiles.py   # Alembic autogenerate
```

**要修改的現有檔案：**
- `main.py`：加入 `users_router`
- `scripts/reset_test_db.py`：加 `import users.models`
- `scripts/drop_test_db.py`：加 `import users.models`

---

## 二、DB 模型（models.py）

### ShippingProfile（新表）

```
id              UUID, PK
user_id         UUID, NOT NULL, FK → users.id
shipping_type   ENUM('home','seven_eleven','family_mart'), NOT NULL
recipient_name  VARCHAR, NOT NULL
phone           VARCHAR, NOT NULL
email           VARCHAR, nullable          ← 物流通知 email，null 時出貨用帳號 email
city            VARCHAR, nullable          ← 宅配必填
district        VARCHAR, nullable          ← 宅配必填
address_detail  VARCHAR, nullable          ← 宅配必填
store_id        VARCHAR, nullable          ← 超商必填
store_name      VARCHAR, nullable          ← 超商必填
is_default      BOOLEAN, NOT NULL, DEFAULT false
created_at      TIMESTAMP, NOT NULL, DEFAULT now()
```

### users 表（不異動欄位，已存在）

---

## 三、Endpoints 與業務邏輯

### PATCH /users/me（auth）

**Request：** `{ name?, gender?, birthday? }`（全部選填，未傳的欄位不更新）

**驗證：**
- `name`：若傳入，≥ 4 個 Unicode 字元
- `gender`：若傳入，只能是 `female | male | other | null`（null = 清除）
- `birthday`：若傳入，`date` 格式或 `null`（null = 清除）

**流程：**
1. 用 `body.model_dump(exclude_unset=True)` 取得只有使用者明確傳入的欄位
2. `setattr(user, key, value)` 逐欄更新
3. `db.commit()`

**Response 200：** 更新後的完整用戶資料（`UserProfileResponse`）

---

### POST /users/me/change-password（auth）

**Request：** `{ old_password, new_password }`

**驗證：**
- `new_password`：≥ 10 碼，含字母 + 數字

**流程：**
1. `bcrypt.checkpw(old_password, user.password_hash)` → 失敗 → **400**（舊密碼錯誤）
2. `bcrypt.hashpw(new_password)` → 更新 `user.password_hash`
3. `db.commit()`

**Response 204：** 無 body

---

### POST /users/me/request-email-change（auth）

**Request：** `{ new_email }`

**驗證：**
- `new_email`：EmailStr 格式
- `new_email == user.email` → **400**（新 Email 不能與目前 Email 相同）
- 查 `users.email = new_email OR users.pending_email = new_email`（排除自己）→ 有衝突 → **409**

**流程：**
1. 同 email 檢查 → 400
2. 衝突檢查 → 409
3. 作廢舊 token：`UPDATE email_verification_tokens SET used_at=now() WHERE user_id=? AND token_type='email_change' AND used_at IS NULL`
4. `user.pending_email = new_email`
5. 建 `email_verification_tokens`（type=email_change, expires_at=now()+24h）
6. 寄驗證信（失敗只 log，不阻斷）
7. `db.commit()`

**Response 200：** `{ "message": "驗證信已寄出" }`

> 驗證完成流程（點連結後呼叫 `POST /auth/verify-email`）已在 auth 模組實作，不重複。

---

### GET /users/me/shipping-profiles（auth）

**Response 200：** `ShippingProfileResponse[]`（依 is_default DESC, created_at ASC 排序）

---

### POST /users/me/shipping-profiles（auth）

**前置檢查：** 查該用戶現有筆數 ≥ 10 → **400**（已達上限）

**Request：**
```json
{
  "shipping_type": "home|seven_eleven|family_mart",
  "recipient_name": "string",
  "phone": "string（09xxxxxxxx，台灣手機格式）",
  "email": "string|null",
  "city": "string|null",
  "district": "string|null",
  "address_detail": "string|null",
  "store_id": "string|null",
  "store_name": "string|null",
  "is_default": false
}
```

**跨欄位驗證（Pydantic model_validator）：**
- `shipping_type = home` → city、district、address_detail 必填
- `shipping_type = seven_eleven | family_mart` → store_id、store_name 必填

**流程：**
1. 若 `is_default = true`：`UPDATE shipping_profiles SET is_default=false WHERE user_id=?`
2. INSERT 新 profile
3. `db.commit()`

**Response 201：** 建立後的 `ShippingProfileResponse`

---

### PUT /users/me/shipping-profiles/{id}（auth）

**Request：** 同 POST（全欄位覆寫）

**流程：**
1. 查詢 `id AND user_id = current_user.id` → 找不到 → **404**
2. 若新資料 `is_default = true`：先清除其他 profile 的 is_default
3. 覆寫所有欄位
4. `db.commit()`

**Response 200：** 更新後的 `ShippingProfileResponse`

---

### DELETE /users/me/shipping-profiles/{id}（auth）

**流程：**
1. 查詢 `id AND user_id = current_user.id` → 找不到 → **404**
2. DELETE

**Response 204：** 無 body

---

### PATCH /users/me/shipping-profiles/{id}/set-default（auth）

**流程：**
1. 查詢 `id AND user_id = current_user.id` → 找不到 → **404**
2. `UPDATE shipping_profiles SET is_default=false WHERE user_id=?`（清除所有）
3. `UPDATE shipping_profiles SET is_default=true WHERE id=?`
4. `db.commit()`

**Response 200：** 更新後的 `ShippingProfileResponse`

---

## 四、跨欄位驗證規則（Pydantic）

| shipping_type | 必填 | 應為 null |
|---|---|---|
| home | city, district, address_detail | store_id, store_name |
| seven_eleven / family_mart | store_id, store_name | city, district, address_detail |

在 `ShippingProfileRequest` 的 `@model_validator(mode="after")` 實作，驗證失敗回 422。

---

## 五、實作順序（每個 endpoint 獨立循環）

```
PATCH /users/me
→ 測試 → quality gate → reviewer
→ POST /users/me/change-password
→ 測試 → quality gate → reviewer
→ POST /users/me/request-email-change
→ 測試 → quality gate → reviewer
→ GET /users/me/shipping-profiles
→ POST /users/me/shipping-profiles
→ 測試 → quality gate → reviewer
→ PUT /users/me/shipping-profiles/{id}
→ DELETE /users/me/shipping-profiles/{id}
→ PATCH /users/me/shipping-profiles/{id}/set-default
→ 測試 → quality gate → reviewer
```

> shipping-profiles 的 GET+POST+PUT+DELETE+set-default 可合併為同一輪測試。

---

## 六、測試覆蓋範圍

### 模組二 — 用戶資料

| 測試情境 | 預期結果 |
|---------|---------|
| 修改 name（正常） | 200，name 更新 |
| 修改 name 太短（< 4 字） | 422 |
| 只傳 gender，name 不動 | 200，只 gender 變 |
| gender 傳 null → 清除 | 200，gender = null |
| 未登入呼叫 PATCH /users/me | 401 |
| 換密碼（正常） | 204 |
| 換密碼舊密碼錯誤 | 400 |
| 換密碼新密碼格式不合 | 422 |
| 申請換 email（正常） | 200 |
| 申請換 email 已被使用 | 409 |
| 申請換 email 與自己 pending_email 相同 | 409 |

### 模組三 — 收件資料

| 測試情境 | 預期結果 |
|---------|---------|
| 新增宅配資料（正常） | 201 |
| 新增超商資料（正常） | 201 |
| 宅配缺少 city | 422 |
| 超商缺少 store_id | 422 |
| 新增時 is_default=true → 自動取消舊預設 | 201，舊 is_default=false |
| 列出（有多筆） | 200，預設排第一 |
| 修改（正常） | 200 |
| 修改不屬於自己的 profile | 404 |
| 刪除（正常） | 204 |
| 刪除不存在的 profile | 404 |
| set-default（正常） | 200，其他 is_default=false |
| set-default 不屬於自己 | 404 |

---

## 七、Alembic 遷移

新增 `import users.models` 至 `migrations/env.py`，執行：

```bash
alembic revision --autogenerate -m "create_shipping_profiles"
```

確認生成的 migration 包含：
- `shipping_profiles` 建表
- `shipping_type` ENUM 建立

---

## 八、待確認事項（已確認）

| 問題 | 結論 |
|---|---|
| PATCH /users/me 未傳欄位行為 | 不更新，用 exclude_unset=True |
| change-password 成功回傳 | 204 無 body |
| change-password 後 JWT 失效 | 不主動失效，舊 cookie 自然過期 |
| request-email-change 成功回傳 | 200 `{ message: "驗證信已寄出" }` |
| request-email-change 重複申請 | 先 `UPDATE email_verification_tokens SET used_at=now() WHERE user_id=? AND token_type='email_change' AND used_at IS NULL`，再覆蓋 pending_email、建新 token |
| request-email-change 申請自己現有的 email | 400（「新 Email 不能與目前 Email 相同」） |
| POST shipping-profiles 成功回傳 | 201 + 物件 |
| 刪除預設收件資料後 | 不自動指定新預設，之後無預設 |
| phone 格式驗證 | 驗台灣手機格式：09 開頭，共 10 碼（regex: `^09\d{8}$`） |
| 收件資料筆數上限 | 10 筆，超過回 400 |
