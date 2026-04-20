# 管理者端：客戶訂單管理模組

---

## 5.1 訂單生命週期

**一般目錄商品**

```
客戶結帳 → 建立訂單（pending_payment）
    ↓
24 小時內完成銀行轉帳
    ↓ 逾期未付
payment_expired（自動取消，保留歷史記錄）
    ↓ 已付款
管理員確認付款 → paid → processing → shipped → completed
```

**客製服務**

```
客戶提交申請表單 → 建立客製申請（quote_pending）
系統自動發歡迎訊息
    ↓
管理員與客戶透過訊息系統溝通（可選：negotiating，管理員在申請詳情頁手動點「標記洽談中」切換，不自動觸發）
    ↓
管理員計算報價 → 送出報價（quote_sent）
系統寄 email 給客戶，含報價確認連結（導回網站）
    ↓
客戶登入後在報價確認頁操作：
  ├── 確認報價 → quote_confirmed → 進入付款流程（pending_payment）
  └── 拒絕報價 → quote_rejected
        └── 客戶可重新申請 → 建立新申請（parent_request_id 關聯原申請）
    ↓ 報價逾期未回應
quote_expired（自動取消，保留記錄）
    ↓ 付款後
paid → processing（含製作時間）→ shipped → completed
```

**取消 / 退款**

- 客戶在 `paid` 狀態前可自行取消
- `paid` 之後需聯繫管理員人工處理；管理員**不可直接將已付款訂單改為 cancelled**，必須走退款流程
- 退款透過人工對談處理，訂單標記 `refund_processing` → 全額退款 `refunded` / 部分退款 `partially_refunded`

---

## 5.2 訂單狀態一覽

> `quote_pending / negotiating / quote_sent / quote_confirmed / quote_rejected / quote_expired` 是 `custom_requests.status` 的狀態，存於 `custom_requests` 表，**不是** `orders.status`。客製申請在客戶確認報價後才建立 `orders` 記錄，進入 `pending_payment`。

**`orders.status` 狀態（目錄商品 + 客製服務共用）**

| 狀態 | 說明 |
|------|------|
| pending_payment | 等待付款（24 小時倒數）|
| payment_expired | 逾期未付，自動取消 |
| paid | 管理員已確認付款 |
| processing | 備貨中（客製服務含製作時間）|
| shipped | 已出貨 |
| completed | 已完成 |
| cancelled | 客戶取消（付款前）|
| refund_processing | 退款處理中 |
| refunded | 已退款（全額）|
| partially_refunded | 部分退款完成 |

**`custom_requests.status` 狀態（客製申請專用，見 5.9）**

| 狀態 | 說明 |
|------|------|
| quote_pending | 等待管理員計算報價 |
| negotiating | 洽談中 |
| quote_sent | 報價已寄出，等待客戶確認 |
| quote_confirmed | 客戶確認報價，等待付款（此時建立 orders 記錄）|
| quote_rejected | 客戶拒絕報價 |
| quote_expired | 報價逾期未回應，自動取消 |

所有取消 / 逾期 / 拒絕記錄保留在資料庫，含原因說明，不實際刪除。

**自動化定時任務（Celery Beat）**

以下三個狀態變更由 Celery Beat 排程定時掃描執行，非人工觸發：

| 任務 | 掃描條件 | 執行頻率 | 動作 |
|------|---------|---------|------|
| 付款逾期 | `status = pending_payment` 且 `payment_deadline < now()` | 每 5 分鐘 | 狀態改為 `payment_expired`，寄通知 email |
| 報價逾期 | `custom_requests.status = quote_sent` 且 `quote_expires_at < now()` | 每 5 分鐘 | 狀態改為 `quote_expired`，寄通知 email |
| 出貨逾期提醒 | `orders.status = shipped` 且存在 `shipments.shipped_at < now() - 14 days` 且無 `shipments.status = delivered` | 每天一次 | 發 email 通知管理員確認物流狀況，不自動變更狀態 |

**狀態變更並發保護**

所有訂單狀態變更（客戶取消、系統自動逾期、管理員確認付款）必須使用資料庫交易 + `SELECT FOR UPDATE` 鎖定訂單列，並在鎖定後重新確認當前狀態符合前置條件才執行，否則拒絕並回傳錯誤。

```
例：客戶取消 與 系統自動 payment_expired 同時觸發
→ 先搶到鎖的操作成功執行
→ 後到的操作讀到狀態已變更，條件不符，自動拒絕
→ 前端顯示「訂單狀態已變更，請重新整理」
```

---

## 5.3 購物車與一般訂單內容

**購物車**

- 客戶可將多個商品變體加入購物車一起結帳
- 同一變體可加入多件（`quantity` 不限 1）
- 結帳時快照商品資訊（商品名稱、規格、單價），避免之後商品修改影響歷史訂單

**庫存拆單邏輯**

下單數量超過現有庫存時，系統自動拆分同一 order_item 為現貨 + 預購：

```
客戶下單 quantity = 3，現有庫存可供 = 1
→ fulfilled_qty = 1（現貨，正常出貨）
→ preorder_qty = 2（預購，等待庫存補齊後出貨）
```

結帳頁顯示拆單明細，讓客戶確認後再送出訂單。
預購部分庫存補齊時，系統自動通知客戶並進入出貨流程。

---

## 5.4 物流整合（ECpay）

使用 **ECpay（綠界科技）** 作為物流聚合器，統一處理三種取貨方式：

| 取貨方式 | ECpay 支援 |
|---------|-----------|
| 宅配到府 | 黑貓宅急便 |
| 7-11 店到店 | 統一超商 |
| 全家店到店 | 全家便利商店 |

**出貨流程**

1. 管理員在後台點「出貨」→ 確認收件資訊（已從下單時快照帶入）
2. 系統透過 ECpay API 建立物流訂單 → ECpay 回傳物流追蹤號碼
3. 系統自動記錄追蹤號碼至 `shipments.tracking_number`，寄出貨通知 email 給客戶
4. ECpay Webhook 監聽物流狀態變更

**Webhook URL 設定**：直接使用 Railway 部署後的公開 URL（如 `https://paintlearn-backend.up.railway.app/webhooks/ecpay`），填入 ECpay 後台。開發與正式環境共用同一套部署流程，不需本機穿透工具。

**Webhook 安全驗證**：後端驗證 ECpay 回傳的 `CheckMacValue`，防止偽造請求，驗證失敗回傳 400。

**已完成判定（三軌並行）**

| 方式 | 說明 | 優先序 |
|------|------|--------|
| ECpay Webhook | 收到「已取貨/已投遞」事件 → 將對應 `shipment.status` 改為 `delivered`；所有 shipments 均 `delivered` 後自動將 `order.status` 改為 `completed`。其他中間物流狀態（如「派送中」）只建立 `ecpay_status` 類型的 admin_notification，不改訂單狀態。 | 最高 |
| 客戶主動確認 | 點「確認收貨」按鈕 → 立即 completed | 次之 |
| 逾期提醒 | 出貨後 14 天無取貨確認 → 系統發 email 通知管理員確認物流，由管理員手動處理 | 備用 |

完成後觸發 email 通知客戶（內容：「您的訂單已完成，感謝購買」），並發放回饋券（若符合條件）。

---

## 5.5 運費

- 方案：固定費用 + 免運條件
- 宅配到府：NT$120
- 超商店到店（7-11 / 全家）：NT$70
- 同一訂單統一一種取貨方式，運費只收一次
- 任一邊 > 40cm 的商品建議宅配，結帳時若選超商會顯示警告提示（如 40×60、60×40、50×50 等）
- 選擇「分開出貨」時，現貨與預購各自建立一筆 ECpay 物流訂單，實際產生兩次物流費用，差額由店家自行吸收，不向客戶額外收費

**免運條件（任一符合即免運）**

| 條件 | 說明 |
|------|------|
| subtotal ≥ NT$800 | 商品小計（折扣前）滿 NT$800 |
| 總數量 ≥ 3 件 | order_items 總 quantity 達 3 件 |

> 免運判斷以折扣前小計為基準，使用折扣券不影響免運資格。

---

## 5.6 金額計算

```
小計（subtotal）  = Σ（單價 × quantity）
折扣（discount）  = 折扣券 或 auto_checkout 促銷折抵（取最優惠，擇一）
運費（shipping）  = 依取貨方式（符合免運條件則為 0）
總計（total）     = subtotal - discount + shipping
```

> 折扣券 `min_purchase` 以**折扣前小計**為基準，與免運條件一致。

---

## 5.7 管理員操作

| 操作 | 說明 |
|------|------|
| 訂單列表 | 分頁、篩選（狀態、日期區間、訂單類型）；關鍵字搜尋範圍：訂單編號、客戶名稱、客戶 email |
| 訂單詳情 | 客戶資訊、商品明細、金額明細、收件資料、目前狀態 |
| 確認付款 | 將狀態從 pending_payment 改為 paid，觸發付款確認 email |
| 更新狀態 | 手動推進訂單狀態（processing → shipped 等）|
| 出貨 | 確認收件資訊 → 系統呼叫 ECpay API 建立物流訂單（帶入 `shipping_profiles.email`，若為 null 則用 `users.email` 作為物流通知 email），追蹤號碼自動取得並寄出貨通知。若 ECpay API 失敗，前端顯示錯誤訊息，訂單狀態維持不變，管理員可重試。|
| 新增內部備註 | 管理員對訂單的內部說明（客戶不可見），任何狀態下均可修改 |
| 查看取消歷史 | 顯示所有逾期 / 取消訂單，含原因 |
| 標記付款資訊有誤 | 填寫原因（如：金額不符）→ 系統 email 通知客戶重新填寫，訂單維持 pending_payment |
| 查看付款核對表單 | 訂單詳情中顯示客戶所有提交記錄，以最新一筆為準（金額、時間、帳號末五碼）|
| 標記退款處理中 | 將訂單狀態改為 `refund_processing`，填寫退款原因（客戶退貨 / 管理員主動退款等）|
| 標記已退款 | 確認退款完成後填入 `refund_amount`：**全額退款** → `status = refunded`；**部分退款** → `status = partially_refunded`，`refund_amount` 記錄退款金額 |

---

## 5.8 Email 通知

**發信服務：Resend**（後端 Python SDK 呼叫，免費額度 3,000 封/月）

所有 email 均由系統在狀態變更時自動發出，不論觸發來源為 Celery 排程、客戶操作或管理員操作。

| 觸發時機 | 觸發來源 | 收件人 | 內容 |
|---------|---------|-------|------|
| 訂單建立 | 客戶下單 | 客戶 | 訂單明細 + 付款帳號 + 24 小時付款期限 |
| 逾期未付（`payment_expired`）| Celery Beat 自動 | 客戶 | 訂單已取消說明 |
| 客戶主動取消 | 客戶操作 | 客戶 | 取消確認通知 |
| 管理員取消訂單 | 管理員操作 | 客戶 | 取消原因說明 |
| 管理員確認付款（`paid`）| 管理員操作 | 客戶 | 付款確認 + 預估交期 |
| 管理員標記付款資訊有誤 | 管理員操作 | 客戶 | 說明哪裡有誤 + 請重新填寫付款核對表單 |
| 訂單出貨（ECpay 建單成功）| 系統自動 | 客戶 | 出貨通知 + 追蹤號碼 + 取貨方式說明 |
| 預購商品到貨備貨 | 系統自動（進貨觸發）| 等待中的客戶 | 「您的預購商品已可備貨，即將進入出貨流程，請耐心等候」|
| 退款完成（`refunded`）| 管理員操作 | 客戶 | 退款完成通知 |
| 管理員送出報價（客製）| 管理員操作 | 客戶 | 規格摘要 + 報價金額 + 確認連結（`/custom/quote/:token`，帶獨立安全 token，後端驗證 token 對應的 custom_request）|
| 報價逾期未回應（`quote_expired`）| Celery Beat 自動 | 客戶 | 申請已自動取消說明 |
| 客戶確認報價 | 客戶操作 | 管理員 | 通知開始製作，含訂單連結 |
| 客製申請收到新訊息 | 客戶操作 | 管理員（若不在對話頁）| 訊息摘要 + 導回對話頁連結 |
| 客戶收到新訊息 | 管理員操作 | 客戶（若不在對話頁）| 訊息摘要 + 導回對話頁連結 |

---

## 5.9 客製申請管理介面

管理員後台獨立頁面，管理所有 `custom_requests`。

**列表頁**
- 顯示所有申請，依建立時間倒序排列
- 可依狀態篩選（quote_pending / negotiating / quote_sent / quote_confirmed / quote_rejected / quote_expired）
- 每筆顯示：申請類型、客戶名稱、提交時間、目前狀態

**詳情頁**
- 申請規格：類型、畫布尺寸、難易度、細緻度、備注
- 客戶上傳照片（custom_photo 類型）
- 訊息對話區（與客戶來回溝通）
- 報價操作：帶入基礎定價建議 → 勾選加費項目 → 確認或手動覆蓋 → 送出報價
- 從 `admin_notifications` 通知點入時直接跳至此頁

---

## 5.10 資料庫欄位

**購物車（cart_items）**

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| user_id | FK → users.id（需登入才能使用）|
| product_variant_id | FK → product_variants.id |
| quantity | 數量 |
| created_at | 加入購物車時間 |

> 購物車只存一般目錄商品。客製申請（custom_photo / custom_spec）走 custom_requests 流程，不進購物車。
> 購物車不儲存價格快照，結帳時以當下 `product_variants.price` 為準。若管理員在客戶加入後調整售價，購物車頁面即時顯示新價格。
> 結帳時後端驗證每個購物車項目的 `is_active` 狀態，若有已下架變體則拒絕結帳，前端提示「部分商品已下架，請移除後再結帳」，並在購物車頁面將該項目標記為灰色。

**訂單表（orders）**

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| order_number | 訂單編號（格式：PL-YYYYMMDD-XXXXXX，流水號由全域 PostgreSQL SEQUENCE 原子產生，永遠遞增不重置。日期為建立當天，流水號不跨日歸零，例如當日第一筆可能為 PL-20260418-000312）|
| user_id | FK → users.id |
| status | 見 5.2 |
| subtotal | 商品總價 |
| discount_amount | 折扣總額（來源為折扣券或 auto_checkout，擇優） |
| discount_source | coupon / auto_checkout（記錄實際套用的折扣來源）|
| shipping_fee | 運費 |
| total | 實付金額（subtotal - discount_amount + shipping_fee）|
| user_coupon_id | FK → user_coupons.id（nullable）|
| shipping_type | home / seven_eleven / family_mart |
| shipping_preference | together / separate（含預購項目時的出貨偏好）|
| shipping_snapshot | 收件資料快照 JSON（含收件人、地址/門市）|
| payment_deadline | 付款期限（created_at + 24h）|
| paid_at | 付款確認時間 |
| completed_at | 完成時間 |
| cancel_reason | 取消原因：`payment_expired`（逾期自動取消）/ `customer_cancelled`（客戶取消）/ `admin_cancelled`（管理員取消）|
| refund_amount | 退款金額（nullable，退款時填入，支援部分退款）|
| refunded_at | 退款完成時間（nullable）|
| customer_notes | 客戶備注 |
| admin_notes | 管理者備註 |
| created_at | 下單時間 |
| updated_at | 最後更新時間 |

> `tracking_number` 與 `shipped_at` 移至 `shipments` 表，一筆訂單可對應多筆出貨記錄。

**出貨記錄表（shipments）**

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| order_id | FK → orders.id |
| shipment_type | `fulfilled`（現貨出貨）/ `preorder`（預購出貨）|
| status | `pending` / `shipped` / `delivered`（見下方說明）|
| tracking_number | ECpay 物流追蹤號 |
| ecpay_logistics_id | ECpay 物流訂單 ID |
| shipped_at | 出貨時間（ECpay API 成功回傳追蹤號時自動填入）|
| delivered_at | 取貨 / 投遞確認時間（ECpay Webhook 填入，nullable）|
| created_at | 建立時間 |

**shipments.status 說明**

| 值 | 說明 |
|---|---|
| `pending` | 已建立出貨記錄，尚未填入追蹤號 |
| `shipped` | 已填入追蹤號，物流進行中 |
| `delivered` | 已送達 / 已取貨（ECpay Webhook 回報或客戶主動確認）|

> 一般合併出貨只有一筆 `shipments` 記錄；選「分開出貨」時現貨與預購各建一筆。
> 客戶與管理員均可查看所有出貨記錄與各自的追蹤號碼。

**分開出貨時的 order.status 轉換規則**

- 部分出貨期間（第一筆 shipment 已出、第二筆尚未出）：`order.status` 維持 `processing`
- 所有 shipments 均已出貨 → `order.status` 改為 `shipped`
- 訂單詳情頁內各 shipment 各自顯示狀態與追蹤號碼，讓客戶清楚掌握每筆出貨進度

**訂單明細表（order_items）**

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| order_id | FK → orders.id |
| product_variant_id | FK → product_variants.id（nullable，客製訂單為 null）|
| custom_request_id | FK → custom_requests.id（nullable，一般目錄商品為 null）|
| production_job_id | 客製製作完成後自動填入（nullable）。觸發時機：production_job 狀態變為 `approved` 時，系統透過 `production_job.custom_request_id` 反查對應的 order_item，自動寫入此欄位。|
| product_title_snapshot | 下單時商品名稱快照 |
| variant_spec_snapshot | 下單時規格快照 JSON |
| unit_price | 下單時單價快照 |
| quantity | 購買總數量 |
| fulfilled_qty | 現貨數量（下單時庫存足夠的部分）|
| preorder_qty | 預購數量（庫存不足需等待的部分）|

> 客製訂單（`custom_request_id` 非 null）：`fulfilled_qty = 0`、`preorder_qty = 1`，全部算預購。製作進度以 `production_progress` 狀態為準，不更新這兩個欄位。

**客製申請表（custom_requests）**

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| user_id | FK → users.id |
| request_type | `custom_photo`（客戶自帶照片）/ `custom_spec`（目錄圖自訂規格）|
| photo_url | 客戶上傳照片（custom_photo 用，Firebase Storage）。客戶可在申請詳情頁點「更換照片」重新上傳，系統覆蓋此欄位並刪除 Firebase 上的舊照片。|
| ref_product_id | 參考商品（custom_spec 用，nullable）|
| canvas_w_cm | 指定畫布寬度（custom_photo 選填，nullable）|
| canvas_h_cm | 指定畫布高度（custom_photo 選填，nullable）|
| difficulty | 指定難易度（必填；選「讓管理員建議」時存 null，但前端必須要求客戶明確選擇此選項，不可空白送出）|
| detail | 指定細緻度（必填；選「讓管理員建議」時存 null，但前端必須要求客戶明確選擇此選項，不可空白送出）|
| customer_notes | 客戶備注 |
| quoted_price | 管理員填入的報價金額 |
| quote_token | 報價確認信的安全 token（hashed，用於 `/custom/quote/:token` 連結驗證，與 `quote_expires_at` 同步到期）|
| quote_expires_at | 報價有效期限（送出後 +1 天，延長後再 +1 天）|
| is_extended | 客戶是否已使用延長一次（boolean）|
| status | quote_pending / negotiating / quote_sent / quote_confirmed / quote_rejected / quote_expired |
| parent_request_id | FK → custom_requests.id（重新申請時指向原始申請，nullable）|
| order_id | 客戶確認後建立的訂單（FK → orders.id，nullable）|
| admin_notes | 管理員內部備注 |
| created_at | 申請時間 |
| quoted_at | 報價時間 |

> 照片保留政策：申請被拒絕或逾期後照片不自動刪除，保留供日後查閱。更換照片時舊照片立即從 Firebase 刪除。

**客製申請狀態說明**

| 狀態 | 說明 |
|------|------|
| quote_pending | 等待管理員報價 |
| negotiating | 洽談中（管理員與客戶來回溝通細節）|
| quote_sent | 報價已送出，等待客戶確認 |
| quote_confirmed | 客戶確認報價，等待付款 |
| quote_rejected | 客戶拒絕報價 |
| quote_expired | 報價逾期未回應 |

> 一位客戶可同時提交多筆客製申請，無數量限制，管理員依序處理。

**重新申請邏輯**

客戶拒絕報價後可重新申請：
- 系統建立新的 custom_request，帶入原始申請的規格資料
- 新申請的 `parent_request_id` 指向原申請（id）
- 原申請保留存檔，狀態維持 `quote_rejected`
- 管理員後台顯示「此為重新申請，原申請 #X 已拒絕」，可查看歷史

**訊息系統（custom_request_messages）**

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| request_id | FK → custom_requests.id |
| sender_type | admin / customer |
| message | 訊息內容 |
| created_at | 發送時間 |

- 申請建立時系統自動發送歡迎訊息（第一則，sender_type = admin）
- 管理員在後台訊息區回覆；客戶在「客製申請」頁回覆
- 管理員發送報價時，報價金額 + 備注訊息同步進入訊息系統
- 訊息僅支援純文字，不支援圖片附件；客戶需換圖請使用「更換照片」功能

**即時推送機制（SSE）**

用戶開啟對話頁面時，瀏覽器建立 SSE 連線，伺服器記錄該用戶正在查看此申請。

```
對方傳訊息時（雙向邏輯相同）：
  if 收件方有活躍 SSE 連線（在對話頁）→ 即時推送到頁面，不發 email
  else（收件方不在頁面）              → 發 email 通知，附連結導回對話頁

適用情境：
  客戶傳訊息，管理員不在後台對話頁 → email 通知管理員 Gmail
  管理員傳訊息，客戶不在對話頁     → email 通知客戶 Gmail
```

用戶離開頁面 → SSE 連線自動斷開 → 後端偵測離線。
用戶傳訊息給後端仍使用一般 HTTP POST；SSE 只負責伺服器→前端的推送。

**Railway SSE 保活機制（Heartbeat）**

Railway 負載平衡器會在連線閒置超過 60 秒時強制斷線。後端需每 30 秒推送一次 SSE 注解行保持連線：

```
: heartbeat\n\n
```

前端 `EventSource` 會自動忽略注解行，但 Railway 偵測到資料流動而不斷線。
前端需監聽 `onerror` 事件，斷線後自動重連（`EventSource` 瀏覽器原生支援）。

**付款核對表（payment_submissions）**

客戶付款後主動填寫轉帳資訊，方便管理員比對：

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| order_id | FK → orders.id |
| is_flagged | 管理員標記有誤（boolean，預設 false）|
| transfer_amount | 轉帳金額 |
| transfer_date | 轉帳日期 |
| transfer_time | 轉帳時間 |
| account_last5 | 轉帳帳號末五碼 |
| notes | 備注 |
| created_at | 填寫時間 |

客戶可多次填寫（如填錯可重填），管理員後台在訂單詳情中可查看所有提交記錄，以最新一筆為準，對照銀行帳款記錄。管理員標記有誤時，該筆記錄的 `is_flagged` 設為 true，同時系統重設 `orders.payment_deadline = now() + 24h`，並通知客戶重新提交。24 小時內未提交新的核對表單，Celery Beat 自動將訂單狀態改為 `payment_expired`。

**生產進度表（production_progress）**

每個訂單項目獨立追蹤生產狀態，狀態更新自動觸發 email 通知客戶。

**建立時機**：訂單狀態變為 `paid` 時，系統自動為每筆 `order_item` 建立一筆 `production_progress`，初始狀態為 `pending`。後續狀態由管理員手動推進。

**操作介面**：管理員在**訂單詳情頁**內，每筆 order_item 旁顯示目前生產狀態與「標記下一步」按鈕，直接操作不需跳頁。

| 欄位 | 說明 |
|------|------|
| id | 主鍵 |
| order_item_id | FK → order_items.id |
| status | 見下方狀態說明 |
| notes | 備注（管理員填寫，客戶可見）|
| updated_at | 狀態更新時間 |
| created_at | 建立時間 |

**生產進度狀態**

| 狀態 | 說明 | 自動發 email |
|------|------|------------|
| pending | 等待開始（付款確認後建立）| 否 |
| in_production | 製作中（客製訂單專用：跑 production_job；一般目錄商品跳過此狀態）| 是 |
| manufacturing | 印製模板 + 備妥顏料套組 | 是 |
| packaging | 打包中 | 否 |
| ready_to_ship | 備貨完成，等待出貨 | 是 |
| shipped | 已出貨（管理員點「出貨」→ ECpay API 成功取得追蹤號後，系統自動將該訂單所有 production_progress 推進至此狀態，不需手動操作）| 是（含追蹤號碼）|
