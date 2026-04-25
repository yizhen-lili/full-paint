# Module 09 — Orders（購物車 + 訂單系統）

---

## 1. 要建立的檔案

```
backend/
├── notifications/
│   ├── __init__.py
│   ├── models.py          # AdminNotification model
│   └── service.py         # create_notification() helper（供其他模組呼叫）
├── orders/
│   ├── __init__.py
│   ├── models.py          # CartItem, Order, OrderItem, Shipment, ProductionProgress, PaymentSubmission, SystemSetting
│   ├── router.py          # 所有 endpoints
│   ├── service.py         # 業務邏輯
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── request.py
│   │   └── response.py
│   └── tasks.py           # Celery tasks（E23 payment_expired）
├── migrations/versions/
│   └── c3d4e5f6a7b8_create_order_tables.py
└── tests/orders/
    ├── __init__.py
    └── test_orders.py
```

---

## 2. DB 模型

### admin_notifications（notifications/models.py）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK | 主鍵 |
| type | VARCHAR | NOT NULL | 通知類型（payment_submitted, order_cancelled, custom_order_paid, ...） |
| reference_type | VARCHAR | nullable | 關聯對象類型（order, custom_request, physical_color） |
| reference_id | UUID | nullable | 關聯對象 ID |
| message | TEXT | NOT NULL | 通知內容 |
| requires_action | BOOLEAN | NOT NULL, DEFAULT false | 是否需要管理員處理 |
| is_completed | BOOLEAN | NOT NULL, DEFAULT false | 是否已完成/已讀 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() |

### cart_items（orders/models.py）

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK |
| user_id | UUID | NOT NULL, FK → users.id |
| product_variant_id | UUID | NOT NULL, FK → product_variants.id |
| quantity | INTEGER | NOT NULL, DEFAULT 1 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() |

### orders

| 欄位 | 型別 | 限制 | 說明 |
|------|------|------|------|
| id | UUID | PK |
| order_number | VARCHAR | NOT NULL, UNIQUE | PL-YYYYMMDD-XXXXXX（PostgreSQL SEQUENCE） |
| user_id | UUID | NOT NULL, FK → users.id |
| status | ENUM(10 values) | NOT NULL, DEFAULT 'pending_payment' |
| subtotal | NUMERIC(10,2) | NOT NULL |
| discount_amount | NUMERIC(10,2) | NOT NULL, DEFAULT 0 |
| discount_source | ENUM('coupon','auto_checkout') | nullable |
| auto_checkout_config_id | UUID | nullable, FK → coupon_configs.id |
| shipping_fee | NUMERIC(10,2) | NOT NULL, DEFAULT 0 |
| total | NUMERIC(10,2) | NOT NULL |
| user_coupon_id | UUID | nullable, FK → user_coupons.id |
| shipping_type | ENUM('home','seven_eleven','family_mart') | NOT NULL |
| shipping_preference | ENUM('together','separate') | nullable |
| shipping_snapshot | JSONB | NOT NULL |
| payment_deadline | TIMESTAMP | nullable |
| paid_at | TIMESTAMP | nullable |
| completed_at | TIMESTAMP | nullable |
| cancel_reason_code | ENUM('payment_expired','customer_cancelled','admin_cancelled') | nullable |
| cancel_reason_note | TEXT | nullable |
| refund_amount | NUMERIC(10,2) | nullable |
| refunded_at | TIMESTAMP | nullable |
| refund_confirmed_at | TIMESTAMP | nullable |
| customer_notes | TEXT | nullable |
| admin_notes | TEXT | nullable |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now(), onupdate=now() |

### order_items

| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK |
| order_id | UUID | NOT NULL, FK → orders.id |
| product_variant_id | UUID | nullable, FK → product_variants.id |
| custom_request_id | UUID | nullable, FK → custom_requests.id（custom_requests 尚未建立，暫用 plain UUID）⚠️ |
| production_job_id | UUID | nullable, FK → production_jobs.id |
| product_title_snapshot | VARCHAR | NOT NULL |
| variant_spec_snapshot | JSONB | NOT NULL |
| unit_price | NUMERIC(10,2) | NOT NULL |
| quantity | INTEGER | NOT NULL |
| fulfilled_qty | INTEGER | NOT NULL, DEFAULT 0 |
| preorder_qty | INTEGER | NOT NULL, DEFAULT 0 |
| is_returned | BOOLEAN | NOT NULL, DEFAULT false |

### shipments

| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK |
| order_id | UUID | NOT NULL, FK → orders.id |
| shipment_type | ENUM('fulfilled','preorder') | NOT NULL |
| status | ENUM('pending','shipped','delivered') | NOT NULL, DEFAULT 'pending' |
| tracking_number | VARCHAR | nullable |
| ecpay_logistics_id | VARCHAR | nullable |
| shipped_at | TIMESTAMP | nullable |
| delivered_at | TIMESTAMP | nullable |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() |

### production_progress

| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK |
| order_item_id | UUID | NOT NULL, FK → order_items.id |
| status | ENUM('pending','in_production','manufacturing','packaging','ready_to_ship','shipped') | NOT NULL, DEFAULT 'pending' |
| notes | TEXT | nullable |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now(), onupdate=now() |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() |

### payment_submissions

| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK |
| order_id | UUID | NOT NULL, FK → orders.id |
| is_flagged | BOOLEAN | NOT NULL, DEFAULT false |
| transfer_amount | NUMERIC(10,2) | NOT NULL |
| transfer_date | DATE | NOT NULL |
| transfer_time | TIME | NOT NULL |
| account_last5 | VARCHAR(5) | NOT NULL |
| notes | TEXT | nullable |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() |

### system_settings（簡化 key/value）

| 欄位 | 型別 | 限制 |
|------|------|------|
| key | VARCHAR | PK |
| value | TEXT | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() |

---

## 3. Migration

- 建立 order_number sequence：`CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1`
- 建立 admin_notifications, cart_items, orders, order_items, shipments, production_progress, payment_submissions, system_settings 資料表
- **補上折扣模組延遲的 FK**：
  - `ALTER TABLE user_coupons ADD CONSTRAINT fk_user_coupons_order FOREIGN KEY (used_in_order_id) REFERENCES orders(id)`
  - `ALTER TABLE user_coupons ADD CONSTRAINT fk_user_coupons_source_order FOREIGN KEY (source_order_id) REFERENCES orders(id)`
- 插入預設 system_settings：bank_account_number, bank_name, bank_account_name, payment_absolute_deadline_hours=48

---

## 4. Endpoints 與業務流程

### 模組一：購物車

#### GET /cart（auth）
- 查 cart_items WHERE user_id=me，JOIN product_variants + products
- 回傳每筆：variant 規格、單價、庫存預算（fulfilled_units = min(quantity, stock_可用)、preorder_units）
- is_active = variant.is_active

#### POST /cart/items（auth）
- 驗證 variant.is_active；409 若已下架
- 若 user 已有此 variant → quantity += 新數量
- 否則 INSERT

#### PATCH /cart/items/{id}（auth）
- 驗證 cart_item.user_id == me，否則 404
- UPDATE quantity；quantity <= 0 則刪除

#### DELETE /cart/items/{id}（auth）
- 驗證 owner，DELETE

#### POST /cart/checkout-preview（auth）
- 計算 subtotal = Σ(variant.price × quantity)
- 計算庫存拆單（fulfilled/preorder）
- 計算折扣（呼叫 discount.service.calculate_discount）
- 計算運費：home=120, 7-11/family=70；免運條件：subtotal≥800 OR 總 qty≥3
- 回傳預覽（不扣庫存）

### 模組二：客戶下單（E19）

#### POST /orders（auth）
業務流程（同一 transaction）：
1. 驗證 cart 非空，所有 variant.is_active；否則 409
2. SELECT FOR UPDATE 鎖定 physical_colors（通過 palette_color_mappings → order_items 的 required_ml 計算庫存）
3. 計算 subtotal、庫存拆單（fulfilled_qty/preorder_qty）
4. 呼叫 discount.service.apply_discount（含 promo_code / user_coupon / auto_checkout）
5. 計算運費、total
6. 生成 order_number（`SELECT TO_CHAR(now(), 'PL-YYYYMMDD-') || LPAD(nextval('order_number_seq')::text, 6, '0')`）
7. INSERT orders（status=pending_payment, payment_deadline=now+24h）
8. INSERT order_items（每個 cart_item 一筆，帶快照）
9. 扣減 stock_ml（fulfilled_qty × required_ml）
10. DELETE cart_items
11. Email 客戶（訂單確認 + 付款帳號 + 期限）
12. 回傳 order_id, order_number, total, payment_deadline, payment_info（從 system_settings 讀）

#### GET /orders（auth）
- 分頁、可過濾 status
- 回傳訂單列表

#### GET /orders/{id}（auth）
- 驗證 order.user_id == me；否則 404
- 含 items、shipments、production_progress
- can_cancel = status == 'pending_payment'
- can_confirm_received = status == 'shipped'

#### POST /orders/{id}/payment-submission（auth）
- 驗證 order 屬於 me，status == 'pending_payment'；否則 400
- INSERT payment_submissions
- CREATE admin_notification(type='payment_submitted', reference_id=order.id)
- ⚠️ SSE push 暫不實作（notifications 模組）

#### POST /orders/{id}/confirm-received（auth，E38）
- 驗證 order 屬於 me，status == 'shipped'；否則 400
- SELECT FOR UPDATE 鎖定 order；再次確認 status
- UPDATE 所有該訂單 shipments.status = 'delivered'，delivered_at = now()
- UPDATE order.status = 'completed'，completed_at = now()
- 呼叫 discount.service.issue_reward_coupon（E40）
- CREATE admin_notification(type='order_completed_by_customer')

#### POST /orders/{id}/cancel（auth，E24）
- 驗證 order 屬於 me，status == 'pending_payment'；否則 400
- SELECT FOR UPDATE 鎖定 order
- UPDATE order.status = 'cancelled'，cancel_reason_code = 'customer_cancelled'
- 呼叫 _revert_order_effects（回補庫存 + 折扣券，見下）
- CREATE admin_notification(type='order_cancelled')
- **不寄 email**（客戶自行取消）

#### POST /orders/{id}/confirm-refund（auth，E42-B）
- 驗證 order 屬於 me，status IN ['refunded','partially_refunded']，refund_confirmed_at IS NULL
- UPDATE order.refund_confirmed_at = now()
- 回傳 204

### 模組三：Admin 訂單管理

#### GET /admin/orders（admin）
- 分頁，filter: status, date_from, date_to, order_type, search（order_number / user.name / user.email）
- JOIN users 進行 search

#### GET /admin/orders/{id}（admin）
- 完整訂單詳情：含 order_items, shipments, production_progress, payment_submissions

#### PATCH /admin/orders/{id}/status（admin，SELECT FOR UPDATE，E21/E25 等）
- 允許轉換：
  - `→ paid`：FROM pending_payment；觸發 E21（建立 production_progress, email 客戶, 若客製訂單通知管理員）
  - `→ processing`：FROM paid
  - `→ shipped`：FROM processing（通常由 shipments 自動觸發，此處允許手動）
  - `→ completed`：FROM shipped
  - `→ refund_processing`：FROM paid/processing/shipped/completed；寄 email 客戶（E41）
  - `→ cancelled`：**僅允許 FROM pending_payment**；paid 後禁止；觸發 E25（回補+email）
- SELECT FOR UPDATE 鎖定；確認前置條件

#### POST /admin/orders/{id}/shipments（admin，E36）
- 驗證 order.status IN ['paid','processing','shipped']
- 呼叫 ECpay API stub（回傳 mock tracking_number）
- INSERT shipment(status='shipped', tracking_number, shipped_at=now())
- 聚合更新 order.status（≥1 shipped/delivered → shipped）
- UPDATE production_progress → 'shipped'（所有該訂單的 progress）
- Email 客戶（出貨通知 + 追蹤號）
- Response 201 或 502（ECpay 失敗時）

#### PATCH /admin/orders/{id}/production-progress/{progress_id}（admin，E35）
- 驗證 progress.order_item → order.id 匹配
- 允許推進：manufacturing, packaging, ready_to_ship
- `in_production` 由 production_jobs 完成時自動推進，不由此 endpoint
- `shipped` 由出貨自動推進，不由此 endpoint
- Email 依狀態：manufacturing=發, packaging=不發, ready_to_ship=發

#### POST /admin/orders/{id}/refund（admin，E42）
- 驗證 order.status == 'refund_processing'
- Request: `{ "refund_amount": float, "returned_item_ids": [uuid], "cancel_reason": str }`

  ⚠️ **規格差異**：api.md 只有 `refund_amount + cancel_reason`，admin_orders.md 有 `returned_item_ids` 決定哪些 items 退回。**以 admin_orders.md 為準**。
  
- 計算是否全退：`set(returned_item_ids) == set(all_item_ids)` → 全退 → status=refunded
- 否則 status=partially_refunded
- UPDATE order.refund_amount, refunded_at=now()
- 對 returned_item_ids 的 items：is_returned=true，回補 stock_ml（fulfilled_qty × required_ml）
- 呼叫 discount.service.revert_coupon（全退時）或跳過（部分退）
- 呼叫 discount.service.revoke_reward_coupons
- Email 客戶（退款金額 + 退回明細 + 確認連結）

#### PATCH /admin/orders/{id}/payment-submissions/{sub_id}/flag（admin，E22）
- 驗證 submission.order_id 匹配，is_flagged 目前為 false
- UPDATE submission.is_flagged = true
- 計算新 deadline = MIN(now()+24h, order.created_at + payment_absolute_deadline_hours×3600)
- UPDATE order.payment_deadline = 新 deadline
- Email 客戶（付款資訊有誤；若剩餘 < 6h 則緊急標題）
- Response: { payment_deadline }

#### PATCH /admin/orders/{id}/admin-notes（admin）
- UPDATE order.admin_notes（任何狀態）

### 模組四：ECpay Webhook

#### POST /webhooks/ecpay（public）
- 驗證 CheckMacValue（stub：暫跳過真實計算，記 TODO）
- 解析 RtnCode：
  - 「已取貨/已投遞」(RtnCode=3) → shipment.status=delivered, delivered_at=now()
  - 其他狀態 → CREATE admin_notification(type='ecpay_status')
- 聚合判斷：該訂單所有 shipments = delivered → order.status=completed，E40
- Response 200 "1|OK"（ECpay 要求）

---

## 5. 內部 service 函式（供其他模組呼叫）

- `_revert_order_effects(db, order)` — 回補庫存 + 呼叫 discount.service.revert_coupon + 呼叫 discount.service.revoke_reward_coupons
- `get_system_setting(db, key)` — 讀取 system_settings
- `complete_order(db, order_id)` — 訂單完成邏輯（E40 issue_reward_coupon）

---

## 6. Celery Task（E23）

`orders/tasks.py`：
```python
@celery.task
def check_payment_expired():
    """每 5 分鐘掃描：status=pending_payment AND payment_deadline < now()"""
    # SELECT FOR UPDATE 鎖定每筆
    # UPDATE status = payment_expired, cancel_reason_code = payment_expired
    # 回補庫存 + coupon
    # Email 客戶
```
Celery Beat 設定於 `core/celery_app.py`。

---

## 7. EVENT_MATRIX 對照

| Event | 實作位置 | 副作用 |
|-------|---------|--------|
| E19 | POST /orders | INSERT orders+items, 扣 stock, apply_discount, delete cart, email |
| E20 | POST /orders/{id}/payment-submission | INSERT payment_submissions, admin_notification |
| E21 | PATCH status→paid | UPDATE status, INSERT production_progress, email 客戶, 客製訂單 notification |
| E22 | PATCH payment-submissions flag | UPDATE deadline, email 客戶（緊急/一般）|
| E23 | Celery Beat | UPDATE status→payment_expired, 回補 stock+coupon, email |
| E24 | POST cancel | UPDATE status, 回補, notification（不 email）|
| E25 | PATCH status→cancelled（admin）| UPDATE status, 回補, email 客戶 |
| E35 | PATCH production-progress | UPDATE status, email（部分狀態）|
| E36 | POST shipments | INSERT shipment, ECpay stub, 更新 order.status, email |
| E37 | POST /webhooks/ecpay | UPDATE shipment.status, 可能 complete order, E40 |
| E38 | POST confirm-received | UPDATE shipments→delivered, order→completed, E40 |
| E40 | complete_order() | issue_reward_coupon |
| E41 | PATCH status→refund_processing | UPDATE status, email 客戶 |
| E42 | POST refund | 依全/部分退款執行副作用, email |
| E42-B | POST confirm-refund | UPDATE refund_confirmed_at |

---

## 8. 測試覆蓋範圍

### 購物車
| Case | 狀態碼 |
|------|-------|
| GET 空購物車 | 200 |
| POST 新增商品 | 201 |
| POST 下架商品拒絕 | 409 |
| POST 同 variant 累加 | 201 |
| PATCH 數量更新 | 200 |
| PATCH 數量=0 自動刪除 | 200 |
| DELETE 刪除商品 | 204 |
| DELETE 不屬於自己的項目 | 404 |
| checkout-preview 含折扣+免運計算 | 200 |

### 客戶下單
| Case | 狀態碼 |
|------|-------|
| POST /orders 成功（庫存足）| 201 |
| POST /orders 含預購拆單 | 201 |
| POST /orders 下架變體拒絕 | 409 |
| POST /orders 使用 user_coupon | 201 |
| GET /orders 列表 | 200 |
| GET /orders/{id} 訂單詳情 | 200 |
| GET /orders/{id} 不屬於自己 | 404 |
| POST payment-submission | 200 |
| POST payment-submission 非 pending_payment 狀態 | 400 |
| POST cancel 成功 | 200 |
| POST cancel paid 後拒絕 | 400 |
| POST confirm-received 成功 | 200 |
| POST confirm-received 非 shipped 拒絕 | 400 |
| POST confirm-refund 成功 | 204 |
| POST confirm-refund 已確認再次確認拒絕 | 400 |

### Admin 訂單管理
| Case | 狀態碼 |
|------|-------|
| GET /admin/orders 列表+搜尋 | 200 |
| GET /admin/orders/{id} 完整詳情 | 200 |
| PATCH status → paid 觸發 production_progress 建立 | 200 |
| PATCH status → cancelled FROM pending_payment | 200 |
| PATCH status → cancelled FROM paid 拒絕 | 400 |
| PATCH status → refund_processing | 200 |
| POST shipments 成功（ECpay mock）| 201 |
| PATCH production-progress manufacturing | 200 |
| PATCH production-progress shipped 拒絕（不允許）| 400 |
| POST refund 全退 | 200 |
| POST refund 部分退 | 200 |
| PATCH flag payment submission | 200 |
| PATCH admin-notes | 200 |

### Celery 與 Webhook
| Case | 說明 |
|------|------|
| check_payment_expired 觸發逾期訂單 | 庫存+coupon 回補 |
| POST /webhooks/ecpay delivered → completed | 訂單完成+E40 |
| POST /webhooks/ecpay 其他狀態 → notification only | - |

---

## 9. 待確認事項

### ⚠️ A — api.md vs admin_orders.md 退款規格不一致

**api.md：**
```json
POST /admin/orders/{id}/refund
Request: { "refund_amount": 397, "cancel_reason": "string" }
> 部分退款 → 記錄 refund_amount（coupon 與 stock_ml 不回補）
```

**admin_orders.md：**
- 需指定 `returned_item_ids`（勾選哪些 items 退回）
- 勾選的 items 回補庫存（部分退款時「僅勾選的 items」）
- 全退/部分退依「是否勾選全部 items」決定

**差異**：api.md 說部分退款不回補 stock；admin_orders.md 說部分退款仍回補已勾選 items 的 stock。

**建議**：以 admin_orders.md 為準（更詳細），api.md 需更新加入 `returned_item_ids`。

請確認：是否採用 admin_orders.md 規格（含 returned_item_ids）？

### ⚠️ B — ECpay 整合（已確認：開發期跳過，事後補）

**決議（2026-04-23）：** 本模組 ECpay 整合使用 stub：
- `POST /admin/orders/{id}/shipments`：呼叫 stub，回傳 mock `tracking_number = "MOCK-{uuid}"` 與 `ecpay_logistics_id`
- `POST /webhooks/ecpay`：CheckMacValue 驗證先 skip（log warning + 繼續處理），不實際計算
- 環境變數預留：`ECPAY_MERCHANT_ID`, `ECPAY_HASH_KEY`, `ECPAY_HASH_IV`，未填時 stub 生效

**TODO（正式上線前必須補上）：**
1. 實作真實 ECpay 物流 API 呼叫（建立物流訂單）
2. 實作 CheckMacValue 驗證（SHA256 HMAC）
3. 補上整合測試（需 ECpay sandbox 帳號）

### ⚠️ C — order_items.custom_request_id FK

`order_items.custom_request_id` 是 FK → custom_requests.id，但 custom_requests 表在 Module 10（客製申請）才建立。本模組暫定：
- 宣告為 plain UUID（nullable）
- 在 Module 10 migration 補上 FK constraint

請確認。

### ⚠️ D — confirm-refund endpoint（E42-B）不在 api.md

api.md 沒有明確列出 `POST /orders/{id}/confirm-refund` endpoint，但 store_orders.md 有此功能（含 email 連結 `/orders/:id?action=confirm_refund` 觸發機制）。本模組計畫加入此 endpoint。請確認。
