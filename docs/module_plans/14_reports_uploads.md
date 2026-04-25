# Module 14 - 銷售報表 + 上傳簽名 URL（reports + uploads）

> 補上 api.md 模組十九（上傳）與模組二十一（銷售報表）的最後 4 個 endpoint。Upload 全為 Firebase stub（與 Module 10 photo-signed-url 一致），sales 為真實計算。

## 1. 檔案清單

新建：
- `backend/reports/__init__.py`、`backend/reports/router.py`、`backend/reports/service.py`
- `backend/reports/schemas/__init__.py`、`backend/reports/schemas/response.py`
- `backend/tests/reports/__init__.py`、`backend/tests/reports/test_reports.py`

修改：
- `backend/upload/router.py` — 補 3 個 endpoint：product-image / custom-photo / case-image（皆 stub）
- `backend/upload/__init__.py` 不變
- 新增 `backend/upload/schemas/` 與 `backend/tests/upload/test_upload.py`
- `backend/main.py` 註冊 reports router

## 2. Endpoint

### Reports (1 admin endpoint)
- `GET /admin/reports/sales?date_from=&date_to=` — admin
  - WHERE `orders.status = 'completed'`
  - 對部分退款：使用 `total - refund_amount`；全退（refunded）排除
  - 回傳：`{ period:{from,to}, total_orders, total_revenue, note }`
  - date_from/date_to 為 `date` 型別；缺一即視為開放區間（min/max date）

### Uploads (3 stub endpoints + 1 既有)
- `POST /upload/product-image` — admin｜回傳 stub upload_url + public_url
- `POST /upload/custom-photo` — auth｜回傳 stub upload_url + firebase_path（私有）
- `POST /upload/case-image` — admin｜回傳 stub upload_url + public_url
- `POST /upload/production-image` — admin（既有）

所有 stub 回傳的 URL 都是 mock placeholder（含 timestamp + UUID），標記 TODO 等 Firebase Admin SDK 整合補上。

## 3. EVENT_MATRIX
不觸發任何 Event。

## 4. 測試

| Case | 預期 | 函數名 |
|---|---|---|
| GET /admin/reports/sales 空區間 | 200 + revenue=0 | test_sales_empty |
| GET sales 含 completed 訂單 | total_orders/revenue 正確 | test_sales_completed_only |
| GET sales 部分退款扣除 | revenue 為 total-refund | test_sales_partial_refund_deducted |
| GET sales 全退排除 | refunded 訂單不計入 | test_sales_full_refund_excluded |
| GET sales date_from filter | 對應 | test_sales_date_filter |
| GET sales 非 admin | 401/403 | test_sales_non_admin_blocked |
| POST product-image admin | 200 + upload_url | test_upload_product_image |
| POST product-image 非 admin | 401/403 | test_upload_product_image_non_admin |
| POST custom-photo auth | 200 + firebase_path | test_upload_custom_photo |
| POST custom-photo unauth | 401 | test_upload_custom_photo_unauth |
| POST case-image admin | 200 | test_upload_case_image |

## 5. ⚠️ 決議

### A — Upload 全部 stub
與 Module 10 photo-signed-url 一致。生產環境需以 Firebase Admin SDK 替換。

### B — 部分退款金額
schema：refund_amount 是 NUMERIC(10,2)。total - refund_amount 計算用 Decimal 保精度。
