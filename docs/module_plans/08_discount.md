# Module 08：折扣系統（Discount System）實作規劃

> 對照規格：`requirements/admin_discount.md`、`schema.md`（coupon_configs / promo_codes / user_coupons）、`api.md`（模組十六）、`EVENT_MATRIX.md`（E02, E40, E19, E23/E24/E25, E42, E43, E44）
> 撰寫日期：2026-04-23

> **⚠️ Orders 模組建立時必須補做：**
> `user_coupons.used_in_order_id` 和 `source_order_id` 目前為純 UUID（無 FK），
> orders 表建立後需在 orders migration 補上：
> `op.create_foreign_key(None, 'user_coupons', 'orders', ['used_in_order_id'], ['id'])`
> `op.create_foreign_key(None, 'user_coupons', 'orders', ['source_order_id'], ['id'])`

---

## 1. 要建立的檔案清單

```
backend/
├── discount/
│   ├── __init__.py
│   ├── models.py          # CouponConfig, PromoCode, UserCoupon ORM
│   ├── router.py          # Admin + Customer endpoints
│   ├── service.py         # 業務邏輯（含供其他模組呼叫的函式）
│   └── schemas/
│       ├── __init__.py
│       ├── request.py     # 所有 Request schema
│       └── response.py    # 所有 Response schema
├── tests/
│   └── discount/
│       ├── __init__.py
│       └── test_discount.py
```

---

## 2. DB 模型

### CouponConfig

| 欄位 | SQLAlchemy 型別 | 限制 | 說明 |
|------|----------------|------|------|
| id | UUID | PK, default=uuid4 | 主鍵 |
| coupon_type | Enum('new_user','spend_reward','returning_loyal','manual','auto_checkout') | NOT NULL | 券類型 |
| discount_type | Enum('percentage','fixed') | NOT NULL | 折扣方式 |
| discount_value | Numeric(10,2) | NOT NULL | 折扣值 |
| min_purchase | Numeric(10,2) | nullable | 最低消費門檻 |
| is_active | Boolean | NOT NULL, DEFAULT True | 是否啟用 |
| params | JSONB | NOT NULL, DEFAULT {} | 類型專屬參數 |
| updated_at | DateTime(tz=True) | NOT NULL, DEFAULT now(), onupdate=now() | 最後修改時間 |

**索引**：`UNIQUE INDEX ON coupon_configs (coupon_type) WHERE coupon_type != 'auto_checkout'`

### PromoCode

| 欄位 | SQLAlchemy 型別 | 限制 | 說明 |
|------|----------------|------|------|
| id | UUID | PK, default=uuid4 | 主鍵 |
| code | String | NOT NULL, UNIQUE | 促銷碼 |
| discount_type | Enum('percentage','fixed') | NOT NULL | 折扣方式 |
| discount_value | Numeric(10,2) | NOT NULL | 折扣值 |
| min_purchase | Numeric(10,2) | nullable | 最低消費門檻 |
| start_at | DateTime(tz=True) | nullable | 活動開始時間 |
| end_at | DateTime(tz=True) | nullable | 活動結束時間 |
| max_total_uses | Integer | nullable | 總使用上限（null=無限） |
| max_per_user | Integer | NOT NULL, DEFAULT 1 | 每人使用上限 |
| total_used | Integer | NOT NULL, DEFAULT 0 | 已使用次數（原子遞增） |
| is_active | Boolean | NOT NULL, DEFAULT True | 是否啟用 |
| created_at | DateTime(tz=True) | NOT NULL, DEFAULT now() | 建立時間 |
| updated_at | DateTime(tz=True) | NOT NULL, DEFAULT now(), onupdate=now() | 最後修改時間 |

### UserCoupon

| 欄位 | SQLAlchemy 型別 | 限制 | 說明 |
|------|----------------|------|------|
| id | UUID | PK, default=uuid4 | 主鍵 |
| user_id | UUID | NOT NULL, FK → users.id | 所屬用戶 |
| coupon_config_id | UUID | nullable, FK → coupon_configs.id | 對應設定（public_code 為 null） |
| promo_code_id | UUID | nullable, FK → promo_codes.id | 對應促銷碼（非 public_code 為 null） |
| discount_type | Enum('percentage','fixed') | NOT NULL | 折扣方式快照 |
| discount_value | Numeric(10,2) | NOT NULL | 折扣值快照 |
| min_purchase | Numeric(10,2) | nullable | 最低消費門檻快照 |
| expires_at | DateTime(tz=True) | nullable | 到期時間 |
| is_used | Boolean | NOT NULL, DEFAULT False | 是否已使用 |
| used_at | DateTime(tz=True) | nullable | 使用時間 |
| used_in_order_id | UUID | nullable, FK → orders.id | 使用於哪筆訂單 |
| source_order_id | UUID | nullable, FK → orders.id | 觸發來源訂單（spend_reward/returning_loyal） |
| created_at | DateTime(tz=True) | NOT NULL, DEFAULT now() | 發放時間 |

**CHECK constraint**：`coupon_config_id IS NOT NULL OR promo_code_id IS NOT NULL`

**索引**：
- `(user_id, is_used)` — 可用券查詢
- `source_order_id` — 退款撤銷回饋券
- `used_in_order_id` — 退款回補已用券

---

## 3. Endpoints 與業務邏輯

### 3.1 GET /api/v1/users/me/coupons
**權限**：auth（客戶）
**業務邏輯**：
- 查詢 `user_coupons WHERE user_id = current_user.id`
- 分成三類回傳：
  - `available`：`is_used=false AND (expires_at IS NULL OR expires_at > now())`
  - `used`：`is_used=true`
  - `expired`：`is_used=false AND expires_at < now()`
- 每筆附上 `coupon_type`（從 coupon_config_id 或 promo_code_id 反查）

**Response 200**：
```json
{
  "available": [{"id": "uuid", "coupon_type": "new_user", "discount_type": "percentage", "discount_value": 10, "min_purchase": 300, "expires_at": "datetime"}],
  "used": [...],
  "expired": [...]
}
```

---

### 3.2 POST /api/v1/promo-codes/validate
**權限**：auth（客戶）
**Request**：`{ "code": "SALE2026", "subtotal": 794 }`
**業務邏輯**：
1. 查 `promo_codes WHERE code = ?`，不存在 → 400
2. `is_active=false` → 400
3. 時間範圍：`start_at` 或 `end_at` 有值時檢查 now() 是否在範圍內 → 400（過期或未開始）
4. `max_total_uses IS NOT NULL AND total_used >= max_total_uses` → 400「促銷碼已達使用上限」
5. 該用戶對此 promo_code 的 user_coupons 記錄數（含已用）>= `max_per_user` → 400「超過每人使用上限」
6. `subtotal < min_purchase`（若 min_purchase 不為 null）→ 400「未達最低消費門檻」
7. 全部通過 → 200 回傳折扣資訊（**不實際扣減，僅驗證**）

**Response 200**：`{ "valid": true, "discount_type": "fixed", "discount_value": 100 }`
**Response 400**：各種失敗原因

---

### 3.3 GET /api/v1/admin/coupon-configs
**權限**：admin
**業務邏輯**：列出所有 coupon_configs，依 coupon_type 排序
**Response 200**：`{ "items": [...] }`

---

### 3.4 GET /api/v1/admin/coupon-configs/{id}/usage-stats
**權限**：admin
**業務邏輯**：
- `total_issued`：COUNT user_coupons WHERE coupon_config_id = ?
- `total_used`：COUNT user_coupons WHERE coupon_config_id = ? AND is_used=true
- `total_discount_amount`：SUM discount_value WHERE is_used=true（percentage 型需乘以實際訂單金額，但 user_coupons 只快照 discount_value，非實際折扣額，故直接 SUM discount_value 作為參考）
- `usage_by_month`：依 created_at GROUP BY month，統計 issued 和 used

---

### 3.5 PATCH /api/v1/admin/coupon-configs/{id}
**權限**：admin｜更新非 auto_checkout 類型設定
**Request**：`{ "is_active": true, "discount_type": "percentage", "discount_value": 10, "min_purchase": 300, "params": {...} }`
**業務邏輯**：
- 若 coupon_type = auto_checkout → 400「請使用 DELETE 後重建」
- 驗證 params 結構符合 coupon_type
- UPDATE 欄位，updated_at 自動更新

---

### 3.6 POST /api/v1/admin/coupon-configs/auto-checkout
**權限**：admin
**Request**：`{ "discount_type": "fixed", "discount_value": 50, "min_purchase": 500, "params": { "trigger_threshold": 500, "start_at": "2026-05-01", "end_at": "2026-05-31" } }`
**業務邏輯**：
- INSERT coupon_configs WITH coupon_type='auto_checkout'
- auto_checkout 可有多筆，不受部分唯一索引限制
- 驗證 params 中 trigger_threshold 必填

---

### 3.7 DELETE /api/v1/admin/coupon-configs/{id}
**權限**：admin
**業務邏輯**：
- 查 coupon_type，若非 auto_checkout → 400「僅允許刪除 auto_checkout 類型」
- DELETE

---

### 3.8 GET /api/v1/admin/promo-codes
**權限**：admin
**Response 200**：`{ "items": [{ 所有欄位 }] }`

---

### 3.9 POST /api/v1/admin/promo-codes
**權限**：admin
**Request**：`{ "code": "SALE2026", "discount_type": "fixed", "discount_value": 100, "min_purchase": 500, "start_at": null, "end_at": null, "max_total_uses": 100, "max_per_user": 1 }`
**業務邏輯**：
- code UNIQUE 檢查 → 409 若重複
- INSERT

---

### 3.10 PUT /api/v1/admin/promo-codes/{id}
**權限**：admin
**業務邏輯**：
- 若 total_used > 0 仍可編輯（管理員責任）
- code 若更改需 UNIQUE 檢查

---

### 3.11 DELETE /api/v1/admin/promo-codes/{id}
**權限**：admin
**業務邏輯**：
- 若 total_used > 0 → 400「促銷碼已有使用記錄，無法刪除」

---

### 3.12 GET /api/v1/admin/user-coupons
**權限**：admin
**Query**：`?user_id=uuid&coupon_type=&is_used=true|false`
**業務邏輯**：列出符合條件的 user_coupons，JOIN coupon_configs 和 promo_codes 取得 coupon_type

---

### 3.13 POST /api/v1/admin/users/issue-coupons
**權限**：admin
**Request**：`{ "user_ids": ["uuid"], "coupon_config_id": "uuid" }`
**業務邏輯**（E43）：
- 查 coupon_config，不存在 → 404
- coupon_type 需為 manual
- 批量 INSERT user_coupons，快照當時參數
- expires_at 從 manual coupon 的 params.expires_at 取（若有）
- 一次最多 100 個用戶（防止逾時）

---

## 4. 供其他模組呼叫的 Service 函式

這些函式**不對應 HTTP endpoint**，由其他模組直接呼叫：

### `issue_new_user_coupon(db, user_id)` → 用於 E02
- 查 coupon_configs WHERE coupon_type='new_user' AND is_active=true
- 不存在或未啟用 → 靜默 return（不 raise）
- INSERT user_coupons（快照當時參數，expires_at = now() + valid_days）

### `issue_reward_coupon(db, user_id, order_id, order_total)` → 用於 E40
- 偽碼邏輯（優先序：returning_loyal > spend_reward）：
  ```
  has_prior_orders = COUNT(orders WHERE user_id=? AND status=completed AND id!=order_id) > 0
  returning_loyal_config = 查 coupon_configs WHERE coupon_type='returning_loyal' AND is_active=true
  spend_reward_config = 查 coupon_configs WHERE coupon_type='spend_reward' AND is_active=true
  
  if has_prior_orders AND returning_loyal_config AND order_total >= returning_loyal_config.params['trigger_threshold']:
      INSERT user_coupons(coupon_config_id=returning_loyal, source_order_id=order_id)
  elif spend_reward_config AND order_total >= spend_reward_config.params['trigger_threshold']:
      INSERT user_coupons(coupon_config_id=spend_reward, source_order_id=order_id)
  ```

### `calculate_discount(db, user_id, subtotal, user_coupon_id=None, promo_code=None)` → 用於 E44 / checkout preview
- 依優先序決定折扣：
  1. promo_code 有值 → 驗證並計算（**不** 實際扣減 total_used）
  2. user_coupon_id 有值 → 查 user_coupons 驗證可用性，計算折扣
  3. 都無 → 查 auto_checkout（符合條件者取折扣金額最高）
- 回傳：`{ discount_amount, discount_source, user_coupon_id, promo_code_id, auto_checkout_config_id }`

### `apply_discount(db, order_id, user_id, subtotal, user_coupon_id=None, promo_code=None)` → 用於 E19（實際下單）
- 執行 calculate_discount 邏輯，**同時在同一 transaction 內**：
  - promo_code：原子遞增 total_used，INSERT user_coupons(is_used=true)
  - user_coupon：UPDATE is_used=true, used_at=now(), used_in_order_id=order_id
  - auto_checkout：記錄 orders.auto_checkout_config_id，不建 user_coupon
- 回傳 `{ discount_amount, discount_source, user_coupon_id, auto_checkout_config_id }`

### `revert_coupon(db, order_id)` → 用於 E23/E24/E25/E42（取消/退款回補）
- 查 user_coupons WHERE used_in_order_id=order_id
- 若有：
  - is_used=false, used_at=null, used_in_order_id=null
  - 若 promo_code_id IS NOT NULL：原子遞減 promo_codes.total_used -= 1

### `revoke_reward_coupons(db, order_id, refund_amount=None, order_total=None)` → 用於 E42（退款撤銷回饋券）
- 查 user_coupons WHERE source_order_id=order_id AND is_used=false
- 全額退款（refund_amount IS NULL 或 refund_amount == order_total）→ expires_at = now()
- 部分退款：計算 remaining = order_total - refund_amount
  - 需知道發券時的 trigger_threshold（從 coupon_config_id 查）
  - remaining < trigger_threshold → expires_at = now()
  - remaining >= trigger_threshold → 不撤銷

---

## 5. EVENT_MATRIX 對照

| Event | 說明 | 本模組副作用 | 實作位置 |
|-------|------|------------|---------|
| E02 | Email 驗證完成 | 發 new_user 券 | `auth/service.py` 呼叫 `discount.service.issue_new_user_coupon` |
| E40 | 訂單完成 | 發 spend_reward / returning_loyal | `orders/service.py` 呼叫 `discount.service.issue_reward_coupon` |
| E19 | 結帳送出訂單 | 套用/扣減折扣 | `orders/service.py` 呼叫 `discount.service.apply_discount` |
| E23 | 付款逾期 | 回補折扣券 | Celery task 呼叫 `discount.service.revert_coupon` |
| E24 | 客戶主動取消 | 回補折扣券 | `orders/service.py` 呼叫 `discount.service.revert_coupon` |
| E25 | 管理員取消 | 回補折扣券 | `orders/service.py` 呼叫 `discount.service.revert_coupon` |
| E42 | 退款完成 | 回補券 + 撤銷回饋券 | `orders/service.py` 呼叫 `revert_coupon` + `revoke_reward_coupons` |
| E43 | 管理員手動發券 | INSERT user_coupons | endpoint 3.13 |
| E44 | 結帳套用折扣 | 驗證並套用 | `discount.service.apply_discount` |

---

## 6. 測試覆蓋範圍

| Case 描述 | 預期狀態碼 | 測試函數名稱 |
|----------|-----------|------------|
| **GET /users/me/coupons** | | |
| 用戶無券 | 200（空列表） | `test_list_coupons_empty` |
| 用戶有可用券、已用券、過期券 | 200（三類分開） | `test_list_coupons_categorized` |
| 未登入 | 401 | `test_list_coupons_unauthenticated` |
| **POST /promo-codes/validate** | | |
| 有效 public_code | 200 | `test_validate_promo_code_success` |
| 代碼不存在 | 400 | `test_validate_promo_code_not_found` |
| 已停用 | 400 | `test_validate_promo_code_inactive` |
| 超過 max_total_uses | 400 | `test_validate_promo_code_usage_limit` |
| 超過 max_per_user | 400 | `test_validate_promo_code_per_user_limit` |
| 未達 min_purchase | 400 | `test_validate_promo_code_below_min_purchase` |
| 時間範圍外 | 400 | `test_validate_promo_code_expired` |
| 未登入 | 401 | `test_validate_promo_code_unauthenticated` |
| **GET /admin/coupon-configs** | | |
| 列出所有設定 | 200 | `test_list_coupon_configs` |
| **GET /admin/coupon-configs/{id}/usage-stats** | | |
| 有使用記錄 | 200 | `test_coupon_config_usage_stats` |
| 無記錄 | 200（全零） | `test_coupon_config_usage_stats_empty` |
| **PATCH /admin/coupon-configs/{id}** | | |
| 更新 new_user 設定 | 200 | `test_patch_coupon_config_success` |
| 嘗試更新 auto_checkout 類型 | 400 | `test_patch_auto_checkout_blocked` |
| **POST /admin/coupon-configs/auto-checkout** | | |
| 新增 auto_checkout | 201 | `test_create_auto_checkout` |
| 缺少 trigger_threshold | 422 | `test_create_auto_checkout_missing_threshold` |
| **DELETE /admin/coupon-configs/{id}** | | |
| 刪除 auto_checkout | 204 | `test_delete_auto_checkout` |
| 嘗試刪除非 auto_checkout | 400 | `test_delete_non_auto_checkout_blocked` |
| **POST /admin/promo-codes** | | |
| 新增促銷碼 | 201 | `test_create_promo_code` |
| code 重複 | 409 | `test_create_promo_code_duplicate` |
| **PUT /admin/promo-codes/{id}** | | |
| 更新促銷碼 | 200 | `test_update_promo_code` |
| **DELETE /admin/promo-codes/{id}** | | |
| 無使用記錄可刪 | 204 | `test_delete_promo_code` |
| 有使用記錄不可刪 | 400 | `test_delete_promo_code_has_usage` |
| **GET /admin/user-coupons** | | |
| 篩選 user_id | 200 | `test_list_user_coupons_by_user` |
| 篩選 is_used | 200 | `test_list_user_coupons_by_used` |
| **POST /admin/users/issue-coupons** | | |
| 批量發放 manual 券 | 200 | `test_issue_manual_coupons` |
| coupon_type 非 manual | 400 | `test_issue_non_manual_coupon_blocked` |
| **Service 函式（邏輯測試）** | | |
| issue_new_user_coupon：新用戶快照正確 | — | `test_issue_new_user_coupon` |
| issue_new_user_coupon：未啟用時靜默跳過 | — | `test_issue_new_user_coupon_inactive` |
| issue_reward_coupon：returning_loyal 優先 | — | `test_issue_reward_returning_loyal` |
| issue_reward_coupon：首購只發 spend_reward | — | `test_issue_reward_spend_reward_first_order` |
| issue_reward_coupon：未達門檻不發 | — | `test_issue_reward_below_threshold` |
| calculate_discount：promo_code 優先 | — | `test_calculate_discount_promo_priority` |
| calculate_discount：user_coupon 優先於 auto_checkout | — | `test_calculate_discount_user_coupon_priority` |
| calculate_discount：auto_checkout 取最高折扣 | — | `test_calculate_discount_best_auto_checkout` |
| apply_discount：promo_code 原子遞增 total_used | — | `test_apply_discount_promo_code_increments` |
| revert_coupon：user_coupon 回補 | — | `test_revert_coupon_user_coupon` |
| revert_coupon：promo_code 原子遞減 total_used | — | `test_revert_coupon_promo_code_decrements` |
| revoke_reward_coupons：全額退款撤銷未用券 | — | `test_revoke_reward_full_refund` |
| revoke_reward_coupons：部分退款超門檻不撤銷 | — | `test_revoke_reward_partial_above_threshold` |
| revoke_reward_coupons：部分退款低於門檻撤銷 | — | `test_revoke_reward_partial_below_threshold` |
| revoke_reward_coupons：已使用的回饋券不撤銷 | — | `test_revoke_reward_already_used_not_revoked` |
