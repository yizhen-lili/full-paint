# Module 4：Admin 用戶管理 實作規劃

> 對照規格：`requirements/auth_users.md`（§2管理者操作）、`schema.md`（users）、`api.md`（模組四）
> 撰寫日期：2026-04-19

---

## 一、要建立的檔案

```
backend/
└── admin/
    ├── __init__.py
    ├── router.py          # /admin/users/* endpoints
    ├── service.py         # 業務邏輯
    └── schemas/
        ├── __init__.py
        ├── request.py     # AdminUpdateUserRequest
        └── response.py    # AdminUserResponse、AdminUserListResponse
```

**要修改的現有檔案：**
- `main.py`：加入 `admin_router`
- `docs/module_plans/`：本檔案

**不建立新表**：全部使用現有 `users` 表。

---

## 二、Endpoints 與業務邏輯

### GET /admin/users（admin）

**Query 參數：**

| 參數 | 型別 | 說明 |
|---|---|---|
| search | string（optional） | ILIKE 搜尋 name 或 email |
| role | `admin\|customer`（optional） | 篩選角色 |
| is_active | `true\|false`（optional） | 篩選啟用狀態 |
| page | int（default=1） | 頁碼 |
| page_size | int（default=20, max=100） | 每頁筆數 |

**Response 200：**
```json
{
  "items": [{ "id", "name", "email", "role", "is_active", "is_email_verified", "created_at" }],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**流程：**
1. 組 WHERE 條件（search 用 `OR ilike(name) OR ilike(email)`）
2. COUNT 查總數
3. SELECT + OFFSET/LIMIT 取分頁資料
4. 兩次查詢使用相同 WHERE 條件

---

### GET /admin/users/{id}（admin）

**Response 200：** 單筆 `AdminUserResponse`（同 items 內容，欄位相同）

**找不到 → 404**

---

### PATCH /admin/users/{id}（admin）

**Request：**
```json
{ "name": "string|null", "role": "admin|customer|null", "is_active": "bool|null", "password": "string|null" }
```
全部選填，未傳的欄位不更新（PATCH 語意）。

**驗證與業務規則：**
1. 查詢目標用戶 → 找不到 → **404**
2. `is_active = false` 且 `operator_id == target_id` → **403**（禁止停用自己）
3. `is_active = false` 且 `target.role == 'admin'` → **403**（禁止停用其他 admin）
4. `role` 欄位：可修改任何人（包含其他 admin），Q2 確認無限制
5. `password` 若傳入：格式驗證（≥ 10 碼，英數混合），bcrypt hash 後更新
6. `name` 若傳入：≥ 4 字元
7. 其餘欄位直接 setattr

**Response 200：** 更新後的 `AdminUserResponse`

---

### POST /admin/users/issue-coupons（admin）

**跨模組依賴**：需要 Coupon 模組（尚未實作）。

**本模組只做：** 建立 endpoint 骨架，呼叫 `coupon_service.issue_coupons_to_users(user_ids, coupon_config_id)`，並在 coupon service 建立 stub function（回傳 0）。

**Request：**
```json
{ "user_ids": ["uuid"], "coupon_config_id": "uuid" }
```

**Response 200：**
```json
{ "issued_count": 0 }
```

> Coupon 模組完成後，stub 自動替換為實際邏輯，此 endpoint 不需改動。

---

## 三、新模組目錄：admin/

這個 `admin/` 目錄只放 admin 專屬的後台管理邏輯，不同於已有的 `auth/router.py` 中的 `/admin/auth/*`。

未來其他 admin 功能（商品管理、訂單管理等）也會放在此目錄下各自的 router 中，或以子模組拆分。

---

## 四、待確認事項

**Q1：`PATCH /admin/users/{id}` 的 `is_active=true`（重新啟用）有無限制？**
→ 規格未提，假設無限制，任何 admin 可重新啟用任何帳號。

**Q2：admin 可以修改另一個 admin 的 role（降為 customer）嗎？**
→ 規格說「可將 admin 降為 customer」，無額外限制，假設可以。

**Q3：`POST /admin/users/issue-coupons` 找不到 coupon_config_id 怎麼處理？**
→ Coupon 模組實作時處理，stub 階段直接回 `{ "issued_count": 0 }`。

---

## 五、實作順序

```
GET /admin/users（含分頁）
→ GET /admin/users/{id}
→ 測試 → quality gate → reviewer

PATCH /admin/users/{id}
→ 測試 → quality gate → reviewer

POST /admin/users/issue-coupons（stub）
→ 測試 → quality gate → reviewer
```

---

## 六、測試覆蓋範圍

### GET /admin/users

| 情境 | 預期 |
|---|---|
| 無篩選，有資料 | 200，分頁正確 |
| search 關鍵字有符合 | 200，只回傳符合的 |
| search 無符合 | 200，items=[] |
| role 篩選 | 200，只回傳指定 role |
| is_active 篩選 | 200，只回傳指定狀態 |
| 非 admin 呼叫 | 403 |
| 未登入 | 401 |

### GET /admin/users/{id}

| 情境 | 預期 |
|---|---|
| 存在的 id | 200 |
| 不存在的 id | 404 |
| 非 admin | 403 |

### PATCH /admin/users/{id}

| 情境 | 預期 |
|---|---|
| 修改 name | 200，name 更新 |
| 修改 role | 200，role 更新 |
| 重設密碼（正常） | 200，新密碼可登入 |
| 停用一般用戶（customer） | 200，is_active=false |
| 停用自己 | 403 |
| 停用另一個 admin | 403 |
| 修改另一個 admin 的 role | 200，role 更新（無限制） |
| 目標不存在 | 404 |
| 非 admin | 403 |

### POST /admin/users/issue-coupons（stub）

| 情境 | 預期 |
|---|---|
| 正常呼叫 | 200，issued_count=0 |
| 非 admin | 403 |
