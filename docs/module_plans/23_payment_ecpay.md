# Module 23 - ECpay 金流整合（payment）

> 把目前「手動網銀匯款 + admin 人工確認」的付款流程，**並存**新增 ECpay 線上付款（AioCheckOut）：
> 顧客結帳可選 `ecpay`（信用卡/Apple Pay/網路ATM/ATM虛擬帳號/超商代碼）或 `bank_transfer`（保留現狀）。
> 付款成功由 ECpay server-to-server webhook 自動標 `paid`，免 admin 人工確認。
> 來源文件：[ECpay 全方位金流 AioCheckOut](https://developers.ecpay.com.tw/?p=2856) — 規格詳見 [ecpay_aio_checkout.md](../integration_specs/ecpay_aio_checkout.md)。

---

## 0. 整體推進節奏（4 階段）

| 階段 | 範圍 | 對應 ECpay API | 狀態 |
|---|---|---|---|
| **階段 0** | module plan + integration spec + 規格比對報告 | — | ⏳ 本文件 |
| **階段 1** | 即時付款（信用卡 / Apple Pay）：config、model、SHA256、checkout form、ReturnURL webhook、抽 `_apply_paid_side_effects`、create_order 分支 | AioCheckOut + ReturnURL | ⏳ |
| **階段 2** | ATM / 超商非同步：`ChoosePayment=ALL`、PaymentInfoURL webhook、取號 vs 付款區分、Celery 逾期處理、重新付款 | PaymentInfoURL | ⏳ |
| **階段 3** | 前端串接：結帳付款方式選擇、OrderResultURL redirect、結果頁顯示虛擬帳號、SSE | OrderResultURL | ⏳ |
| **階段 4（後）** | 電子發票串接（另一組帳號） | B2C 電子發票 | 🟢 視需求 |

**規則：** 每階段完成後 commit + push + user 實測通過才往下；不自動連跑（同 Module 20）。

---

## 1. 帳號與環境

### 帳號類型分辨
- ECpay 的**金流**、**物流**、**電子發票**是三個獨立帳號，各有自己的 MerchantID / HashKey / HashIV。
- 本模組只用「**金流**」那組（與 Module 20 物流帳號不同）。
- ⚠️ **金流簽章用 SHA256**；物流用 MD5。`EncryptType=1` 必帶（告訴 ECpay 用 SHA256）。

### 環境差異
| 項目 | Stage（沙箱） | Production（正式） |
|---|---|---|
| Endpoint | `payment-stage.ecpay.com.tw` | `payment.ecpay.com.tw` |
| 簽章 | SHA256 | SHA256 |
| 資料保留 | 不留正式記錄、不真撥款 | 真實交易、ECpay 依撥款週期入帳 |

> **入帳（撥款）說明**：程式碼從頭到尾不經手金錢。錢路徑為 `顧客 → ECpay 代收 → 依撥款週期撥款到 user 綁定的銀行帳戶`。
> 訂單標 `paid` 僅代表「ECpay 確認顧客已付款」，撥款是 ECpay 後台設定（綁定銀行帳戶 + 撥款週期），非本模組職責。

### Env vars（Railway backend service Variables，金流獨立一組）
```
ECPAY_PAYMENT_MERCHANT_ID=3002607        # sandbox AioCheckOut 公開測試組（待確認，見 §6）
ECPAY_PAYMENT_HASH_KEY=pwFHCqoQZGmho4w6  # sandbox 公開（待確認）
ECPAY_PAYMENT_HASH_IV=EkRm7iFT261dpevs   # sandbox 公開（待確認）
ECPAY_PAYMENT_ENV=stage                   # stage / production
ECPAY_PAYMENT_RETURN_URL=                 # 留空 → service 由 request.base_url 推導
ECPAY_PAYMENT_CLIENT_BACK_URL=            # 顧客在 ECpay 按「返回商店」的前端 URL
ECPAY_PAYMENT_DRY_RUN=false               # true = 不真打 ECpay
```
正式上線：換成 user 正式金流帳號（HashKey/HashIV 不寫進本文件、不傳輸；比照 Module 20 規矩）。

### CheckMacValue 規則（金流 = SHA256）
1. 參數依 key 字典序升冪排序
2. 串成 `HashKey=xxx&Key1=Val1&...&HashIV=yyy`
3. URL encode（.NET style：保留 `-_.!*()` 不編碼）
4. 全部轉小寫
5. **SHA256**（非物流的 MD5）
6. 轉大寫

→ 沿用 `logistics/service.py` 的 `_ecpay_url_encode()`（純函數可 import 復用），只換 hash 演算法與帳號金鑰。

---

## 2. 檔案清單

### 新增模組 `backend/payment/`
```
backend/payment/
├── __init__.py
├── service.py        # SHA256 CheckMacValue + AioCheckOut 參數 builder + RtnCode 判定 + endpoint URL builder
├── router.py         # checkout form + return / payment-info / result 三個 webhook/redirect
├── schemas.py        # CheckoutInitResponse 等（webhook 讀 raw body 不用 schema）
└── tests/
    ├── __init__.py
    ├── test_check_mac_value.py        # SHA256 已知範例驗算
    ├── test_checkout_build.py         # AioCheckOut 參數 + 金額 + ChoosePayment
    ├── test_return_webhook.py         # 驗章成功/失敗、金額竄改、idempotency、標 paid 副作用
    ├── test_payment_info_webhook.py   # ATM/超商取號（pending_payment 維持 + 存帳號）
    └── test_repay.py                  # 重新付款（pending_payment 才可、逾期擋）
```

### 修改既有檔
| 檔案 | 變更 |
|---|---|
| `backend/core/config.py` | 新增 `ecpay_payment_*` env vars + field_validator strip（比照既有 `_strip_ecpay`） |
| `backend/orders/models.py` | `PaymentMethodEnum`、`Order.payment_method`、`PaymentTransactionStatusEnum`、`PaymentTransaction` 表 |
| `backend/orders/service.py` | 抽 `_apply_paid_side_effects()`；`create_order()` 加 `payment_method` 參數與分支；`admin_update_order_status` paid 分支改呼共用函數 |
| `backend/orders/router.py` | `POST /orders` 傳入 `payment_method` |
| `backend/orders/schemas.py` | `CreateOrderRequest` 加 `payment_method`；`CreateOrderResponse` 加 `payment_method`（ecpay 時 `payment_info` 可為 null） |
| `backend/orders/tasks.py` | 逾期掃描順帶把 `awaiting_atm` transaction 標 `expired` |
| `backend/main.py` | 註冊 `payment_router`（prefix `/api/v1`） |
| `backend/scripts/init_db.py` | 補 `paymentmethodenum` type + `orders.payment_method` 欄位 ALTER（Railway 只 stamp 不 upgrade，`payment_transactions` 表由 create_all 建） |
| `backend/tests/conftest.py` | `ecpay_payment_dry_run=True` + monkeypatch 金流 sandbox 帳號 |

### 沿用樣板（不重造）
- `logistics/service.py` L84-120：`_ecpay_url_encode` / CheckMacValue 算法 / `generate_merchant_trade_no`
- `logistics/router.py` L300-340：auto-submit form + `_html_escape`；L659-771：webhook + `_plain_text_response`

### init_db.py 要補的 SQL
```sql
-- enum type（PostgreSQL ADD TYPE 無 IF NOT EXISTS，用 DO $$ 包裹）
DO $$ BEGIN
  CREATE TYPE paymentmethodenum AS ENUM ('bank_transfer','ecpay');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Order 加欄位（既有表，create_all 不會補）
ALTER TABLE orders
  ADD COLUMN IF NOT EXISTS payment_method paymentmethodenum NOT NULL DEFAULT 'bank_transfer';

-- payment_transactions 表 + 其 enum 由 Base.metadata.create_all 建（已 import orders.models）
```

---

## 3. DB 模型

### 3.1 `Order` 表新增欄位
| 欄位 | 型別 | 限制 | 說明 |
|---|---|---|---|
| payment_method | ENUM('bank_transfer','ecpay') | NOT NULL, DEFAULT 'bank_transfer' | 付款方式；既有訂單 backfill 為 bank_transfer |

### 3.2 新增 `payment_transactions` 表（放 orders/models.py）
| 欄位 | 型別 | 限制 | 說明 |
|---|---|---|---|
| id | UUID | PK | 主鍵 |
| order_id | UUID | NOT NULL, FK → orders.id | 所屬訂單 |
| merchant_trade_no | VARCHAR | NOT NULL, UNIQUE | 我方送 ECpay 的單號（≤20 字，前綴 `PAY`）；webhook lookup / idempotency 主鍵 |
| status | ENUM('created','awaiting_atm','paid','failed','expired') | NOT NULL, DEFAULT 'created' | 交易狀態 |
| amount | NUMERIC(10,2) | NOT NULL | 發起時 `order.total` 快照（webhook 比對防竄改） |
| ecpay_trade_no | VARCHAR | nullable | ECpay 端交易號（TradeNo） |
| payment_type | VARCHAR | nullable | 實際付款方式（Credit_CreditCard / ATM_TAISHIN / CVS_CVS …） |
| bank_code | VARCHAR | nullable | ATM 虛擬帳號銀行代碼 |
| vaccount | VARCHAR | nullable | ATM 虛擬帳號 |
| payment_no | VARCHAR | nullable | 超商繳費代碼 |
| expire_date | TIMESTAMP(tz) | nullable | ECpay 取號繳費期限（ExpireDate） |
| last_rtn_code | INTEGER | nullable | 最後一次 webhook RtnCode |
| last_rtn_msg | VARCHAR | nullable | 最後一次 webhook RtnMsg |
| raw_callback | JSONB | nullable | 最後一次 webhook 全文（稽核） |
| paid_at | TIMESTAMP(tz) | nullable | 付款成功時間 |
| created_at | TIMESTAMP(tz) | NOT NULL, DEFAULT now() | 建立時間 |
| updated_at | TIMESTAMP(tz) | NOT NULL, DEFAULT now(), onupdate now() | 更新時間 |

索引：`UNIQUE(merchant_trade_no)`、`INDEX(order_id)`。

**為何獨立一張表而非塞進 Order**：一張訂單可多次取號/重試（每次一筆 transaction）；webhook idempotency 需要 per-transaction 唯一鍵；ATM 取號 + 付款成功是兩個獨立 server event 需累積；保留完整稽核軌跡。

---

## 4. Endpoints 與業務流程

模組前綴 `/api/v1/payment/ecpay`。三個 webhook 一律讀 raw body → `parse_qsl` → 驗 SHA256 CheckMacValue → 回 `PlainTextResponse`。

### 4.1 `POST /orders`（既有，加 payment_method）
- `CreateOrderRequest` 加 `payment_method: "bank_transfer" | "ecpay"`（預設 `bank_transfer` 向後相容）。
- `create_order` 建單流程（扣庫存、清車）不變，差異：
  - `payment_method=bank_transfer`：維持現狀，發「銀行帳號 + 期限」email，`payment_info` 帶銀行帳號。
  - `payment_method=ecpay`：**不發**銀行帳號 email（改由前端導去付款 / 或發「前往付款」email — 見 §6 待確認 #9）；`payment_info` 回 null，回傳含 `payment_method:"ecpay"`，前端拿 `order_id` 後呼 4.2 取 form。
- Response 201 加欄位 `payment_method`。

### 4.2 `GET /payment/ecpay/checkout/{order_id}`（auto-submit form，兼重新付款）
- **權限**：auth，且驗 order 屬於該 user。
- **前置**：`order.status == pending_payment` 且 `order.payment_method == ecpay` 且 `payment_deadline > now`，否則 409（已付/逾期/已取消/非 ecpay 單）。
- **流程**：
  1. 產 `MerchantTradeNo`（前綴 `PAY`，≤20 字），INSERT `PaymentTransaction(status=created, amount=order.total)`。
  2. 組 AioCheckOut 參數（`TotalAmount=int(order.total)`、`ItemName`、`ReturnURL`、`OrderResultURL`、`PaymentInfoURL`、`ClientBackURL`、`ChoosePayment`、`EncryptType=1`、`NeedExtraPaidInfo=Y`）+ SHA256 CheckMacValue。階段 1 先 `ChoosePayment=Credit`，階段 2 放開 `ALL`。
  3. 回 `HTMLResponse`（hidden inputs auto-submit form，action = `payment(-stage).ecpay.com.tw/Cashier/AioCheckOut/V5`）。
  4. `dry_run`：回可斷言的 mock 頁/params，不真導向。
- **重新付款**：每次呼叫產生**新的** MerchantTradeNo（新 transaction），避免 ECpay「重複交易」錯誤；舊待付 transaction 保留。

### 4.3 `POST /payment/ecpay/return`（付款成功權威 webhook）
- **公開**（ECpay server-to-server）。**唯一可標 paid 的路徑**。
- **流程**：
  1. raw body → parse_qsl → 驗 SHA256 CheckMacValue。失敗 → log + 回 `"0|CheckMacValueError"`（讓 ECpay 重送，不洩漏細節）。
  2. by `MerchantTradeNo` 查 `PaymentTransaction`（`with_for_update`）+ 對應 Order（`with_for_update`）。查無 → 回 `"0|OrderNotFound"`。
  3. **金額比對**：`int(params["TradeAmt"]) == int(transaction.amount)`，不等 → log + 回 `"0|AmountMismatch"`，**絕不標 paid**。
  4. **RtnCode 判定**：`RtnCode == 1` 才是付款成功；非 1 → transaction.status=failed + last_rtn_*，回 `"1|OK"`（已知失敗不需重送）。
  5. **Idempotency**：`transaction.status == paid` → 直接回 `"1|OK"`，不重複副作用。
  6. 成功：transaction.status=paid、paid_at、ecpay_trade_no、payment_type、raw_callback；若 `order.status == pending_payment` → 呼叫 `_apply_paid_side_effects(db, order, user)`（§5）。
  7. 回 `PlainTextResponse("1|OK")`。

### 4.4 `POST /payment/ecpay/payment-info`（ATM/超商取號通知，階段 2）
- **公開**。處理「取號成功」（≠ 付款成功），**絕不標 paid**。
- **流程**：
  1. raw body → parse_qsl → 驗 SHA256 → 失敗回 `"0|CheckMacValueError"`。
  2. by MerchantTradeNo 查 transaction（`with_for_update`）+ Order。
  3. 存 `bank_code`/`vaccount`（ATM）或 `payment_no`（CVS/BARCODE）、`expire_date`（解析 ECpay `ExpireDate`），transaction.status=`awaiting_atm`，raw_callback。
  4. **對齊期限**：`order.payment_deadline = min(現有 deadline, expire_date)`；訂單**維持 pending_payment**。
  5. 寄「虛擬帳號 / 繳費代碼 + 期限」email 給顧客（E_PAY_ATM_ISSUED）。
  6. 回 `PlainTextResponse("1|OK")`。
- **取號 vs 付款成功**：取號成功 RtnCode（ATM=2、CVS/BARCODE 依官方文件，集中成常數 `ATM_CODE_ISSUED_RTN_CODES` / `CVS_CODE_ISSUED_RTN_CODES`，見 §6 待確認 #3）。

### 4.5 `POST /payment/ecpay/result`（OrderResultURL，顧客瀏覽器導回）
- ECpay 付款後用瀏覽器 POST 帶結果回來。**不可作為標 paid 依據**（瀏覽器可竄改/中斷）。
- 可驗章後 303 redirect 到前端結果頁（`ecpay_payment_client_back_url` 或 `frontend_url + /orders/{order_number}`），帶 `?status=...`；DB 狀態以 4.3 ReturnURL 為準。
- ClientBackURL（顧客按「返回商店」）直接指向前端結果頁，後端不需 endpoint。

---

## 5. 與既有狀態機整合

### 5.1 抽共用 `_apply_paid_side_effects(db, order, user)`
從 `admin_update_order_status` 標 paid 分支（service.py L1495-1519）抽出，內容：
- `order.status = paid` + `order.paid_at = now()`
- 為每筆 OrderItem 建 `ProductionProgress(status=pending)`
- 客製訂單（任一 item.custom_request_id 非 null）→ `create_notification(type=custom_order_paid, requires_action=True)`
- 寄付款確認 email（「付款已確認，我們將盡快為您製作與出貨」）
- 關閉相關 `payment_submitted` 通知（標 completed）— 對齊 E21
- SSE：`_publish_order_status_changed(order)`

admin 路徑與 ReturnURL webhook **都呼叫此函數**，確保副作用完全一致（EVENT_MATRIX 要求 ECpay 標 paid 等同 E21）。

### 5.2 `_VALID_STATUS_TRANSITIONS`
- 不需新增（ECpay 標 paid 仍是 `pending_payment → paid`，已在表內）。
- ReturnURL webhook **不走** `admin_update_order_status`（其 transition 校驗 + admin 語意不適合 webhook）；直接呼叫 `_apply_paid_side_effects` 並以 `if order.status == pending_payment` guard 防重。

### 5.3 Celery 逾期掃描（tasks.py）
- 現行掃 `pending_payment 且 payment_deadline < now` → `payment_expired` + 回補庫存/優惠券/回饋券（E23）。ECpay ATM 待付款訂單也是 pending_payment，**一體適用**（已對齊 payment_deadline 到 ExpireDate）。
- 新增：逾期取消時若該 transaction 是 `awaiting_atm` → transaction.status=`expired`。
- **競態保護**：ReturnURL 與 Celery 都 `with_for_update` 鎖 Order，且都以 `status == pending_payment` 為 guard，先 commit 者贏（見 §6 待確認 #7「已取消卻仍繳費」邊界政策）。

---

## 6. EVENT_MATRIX 對照（需在 docs/EVENT_MATRIX.md 補登）

對照 [docs/EVENT_MATRIX.md](../EVENT_MATRIX.md) §三 訂單與付款事件（E19–E25）：

| Event | 觸發點 | 狀態變更 | DB 寫入 | 通知 / Email | 對齊 |
|---|---|---|---|---|---|
| **E19b** 結帳建單（ecpay） | create_order(payment_method=ecpay) | → pending_payment | INSERT orders(payment_method=ecpay) + order_items + DELETE cart_items + 扣庫存 + INSERT payment_transactions(created) | **不發**銀行帳號 email | 同 E19（扣庫存/清車），付款渠道不同 |
| **E_PAY_ATM_ISSUED** ATM/超商取號 | PaymentInfoURL webhook（取號碼） | 維持 pending_payment | UPDATE payment_transactions(awaiting_atm, vaccount/payment_no/expire_date) + UPDATE orders.payment_deadline | 寄虛擬帳號/繳費代碼 + 期限 → 顧客 | — |
| **E_PAY_SUCCESS** ECpay 付款成功 | ReturnURL webhook RtnCode=1 | pending_payment → paid | UPDATE payment_transactions(paid) + 同 E21 全寫入（paid_at、production_progress） | **完全對齊 E21**：custom_order_paid 通知、付款確認 email、SSE、關閉 payment_submitted | 共用 `_apply_paid_side_effects` |
| **E_PAY_FAILED** ECpay 付款失敗 | ReturnURL RtnCode≠1 | 不變 | UPDATE payment_transactions(failed, last_rtn_*) | （可選）通知顧客可重試 | — |
| **E_PAY_RETRY** 重新付款 | GET checkout/{id} 重試 | 不變（pending_payment） | INSERT payment_transactions(created, 新 MerchantTradeNo) | — | — |

E23（逾期）/ E24 / E25 對 ecpay 訂單行為不變，僅逾期時順帶把 `awaiting_atm` transaction 標 `expired`（§5.3）。

---

## 7. 測試覆蓋範圍

### 階段 1（即時付款）
- 🔲 CheckMacValue SHA256 算法（happy path + ECpay 官方範例驗算 hardcode 斷言）
- 🔲 `_ecpay_url_encode` 保留 `-_.!*()`
- 🔲 build AioCheckOut 參數正確（TotalAmount 整數、ChoosePayment、EncryptType=1、含 CheckMacValue）
- 🔲 checkout endpoint：非 pending_payment / 非 ecpay / 逾期 → 409
- 🔲 ReturnURL 驗章成功 + RtnCode=1 → transaction.paid + order.paid + ProductionProgress 建立數 = order_items 數
- 🔲 ReturnURL 驗章失敗 → `"0|CheckMacValueError"`、不標 paid
- 🔲 金額竄改（TradeAmt ≠ amount）→ `"0|AmountMismatch"`、不標 paid
- 🔲 Idempotency：同 ReturnURL 連送兩次 → ProductionProgress 只建一份、email 只發一次、第二次回 `"1|OK"`
- 🔲 標 paid 副作用與 admin_update_order_status 標 paid 結果一致（驗共用函數）
- 🔲 客製訂單 ecpay 付款 → 發 custom_order_paid 通知
- 🔲 dry_run mock：checkout 不真打 ECpay、回可斷言內容

### 階段 2（ATM/超商非同步）
- 🔲 PaymentInfoURL 取號 RtnCode → transaction.awaiting_atm、order 仍 pending_payment、不建 ProductionProgress、存 vaccount/expire_date
- 🔲 payment_deadline 對齊 min(deadline, ExpireDate)
- 🔲 取號後 ReturnURL RtnCode=1 → paid（取號 vs 付款區分正確）
- 🔲 重新付款：pending_payment 可、逾期/已付 → 409、產生新 MerchantTradeNo
- 🔲 逾期掃描：awaiting_atm 訂單逾期 → payment_expired + transaction.expired + 回補庫存
- 🔲 競態：order 已 payment_expired 時 ReturnURL 進來 → 不標 paid（guard 生效）

---

## 8. 待確認事項

### 已決（2026-06-09）
- ✅ **金流 sandbox 帳號**：用官方公開測試組 `3002607 / pwFHCqoQZGmho4w6 / EkRm7iFT261dpevs` 開發測試；正式帳號 user 已就緒（A 已備），上線前再換。
- ✅ **建單 email**：ecpay 訂單**不發** email，前端建單成功直接導去付款頁（呼 checkout endpoint）；bank_transfer 維持現狀發銀行帳號 email。
- ✅ **客製訂單**：與一般訂單走同一 create_order 路徑，**同樣開放** ecpay。

### 仍待確認 / 實作時查證
1. **ATM `ExpireDate` / CVS `StoreExpireDate` 設多久**：是否對齊現有 48h 絕對上限。預設先設 ExpireDate=3 天並取 `min(deadline, ExpireDate)`，實作時敲定。
2. **取號成功的確切 RtnCode**：ATM=2、CVS/BARCODE 依官方文件最終確認（階段 2 實作時查證並寫成常數）。
3. **電子發票**：本次**不做**，列階段 4。
4. **超商代碼/條碼上限 NT$20,000**：超過是否動態隱藏該付款方式（階段 2 處理）。
5. **ApplePay**：ECpay 後台開通 + 網域驗證檔是否含 ApplePay（A 已備，階段 2 切 ALL 時驗證）。
6. **競態邊界政策**：ATM 逾期已取消、顧客仍繳費 → 退款方式（人工 or ECpay 退款 API），階段 2 敲定。
7. **信用卡分期 / 紅利**（CreditInstallment）：預設不做。
