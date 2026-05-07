# ECpay 建立物流訂單規格（CVS + 宅配 HOME）

> Day 2 範圍：客戶付款確認後，admin 把訂單真實送進 ECpay 系統 → 產生實際託運單號 → 後續 7-11 / 全家 / 黑貓 / 中華郵政會收件配送。
>
> 對應 ECpay API：
> - **CVS 超商**：[/8809/ 門市訂單建立](https://developers.ecpay.com.tw/8809/)
> - **HOME 宅配**：[/7414/ 產生物流訂單Ⅱ](https://developers.ecpay.com.tw/?p=7414)
>
> 兩個 API 共用同一 endpoint（`/Express/Create`），靠 `LogisticsType` 區分。

---

## 1. 與 Day 1 (/8795/ CVS Map) 的銜接

```
[Day 1] 客戶結帳前 → CVS Map 選店 → store_id 寫進 ShippingProfile
                                    │
                                    ▼
[客戶下訂 + 付款]                  ShippingProfile 完整：
                                   - shipping_type
                                   - recipient_name + phone + email
                                   - city / district / address_detail (home)
                                   - store_id / store_name (cvs)
                                    │
                                    ▼
[Day 2] admin 確認付款後點按鈕 → /Express/Create → 託運單號寫進 Shipment 表
                                    │
                                    ▼
[Day 3] ECpay 推狀態通知 → Shipment.status 更新
                                    │
                                    ▼
[Day 4] admin 列印託運單貼包裹
```

---

## 2. Endpoint

| 環境 | URL |
|---|---|
| Stage | `https://logistics-stage.ecpay.com.tw/Express/Create` |
| Production | `https://logistics.ecpay.com.tw/Express/Create` |

**HTTP**：POST · `Content-Type: application/x-www-form-urlencoded` · `Accept: text/html`

---

## 3. Request 參數（CVS + HOME 兩個 API 共用大部分欄位）

### 3.1 通用必填欄位（兩種都要）

| 欄位 | 型別 | 長度 | 說明 |
|---|---|---|---|
| `MerchantID` | str | 10 | ECpay 給的特店編號 |
| `MerchantTradeNo` | str | 20 | 廠商交易編號，唯一。**對應 yiimui order_number**（如 `PL-20260507-000123` 19 字元，剛好 ≤ 20） |
| `MerchantTradeDate` | str | 20 | `yyyy/MM/dd HH:mm:ss` 格式 |
| `LogisticsType` | str | 20 | `CVS` 或 `HOME` |
| `LogisticsSubType` | str | 20 | 見 §3.2 |
| `GoodsAmount` | int | — | **1 ~ 20,000 元**。超過會 fail（錯誤碼 10500040） |
| `GoodsName` | str | 50 | 商品名稱。**禁用** `^'```!@#%&*+"<>\|_[]`。多商品用「+」串接 |
| `SenderName` | str | 4-10 | 寄件人姓名。**禁數字、特殊符號、emoji**。長度嚴格 4-10 |
| `SenderZipCode` | str | 6 | 寄件人郵遞區號（HOME 必填）。CVS 也建議填 |
| `SenderAddress` | str | 60 | 寄件人地址（HOME 必填）。長度 >6 |
| `SenderCellPhone` | str | 10 | 寄件人手機（C2C / HOME 必填）。10碼、09 開頭 |
| `ReceiverName` | str | 4-10 | 收件人姓名。**禁數字、特殊符號、emoji**。長度嚴格 4-10 |
| `ReceiverCellPhone` | str | 10 | 收件人手機。10碼、09 開頭 |
| `ReceiverEmail` | str | 50 | 收件人 email（必須含 `@` 與 `.`） |
| `ServerReplyURL` | str | 200 | 物流狀態通知 URL（**對應 Day 3** webhook） |
| `CheckMacValue` | str | — | 簽章（MD5） |

### 3.2 LogisticsSubType 可填值

#### CVS（超商，用 /8809/ 邏輯）
- `UNIMARTC2C` 7-Eleven 交貨便（**yiimui 用這個**）
- `FAMIC2C` 全家店到店（**yiimui 用這個**）
- `HILIFEC2C` 萊爾富店到店
- `OKMARTC2C` OK 店到店
- `UNIMART` `UNIMARTFREEZE` `FAMI` `HILIFE` 各家 B2C

#### HOME（宅配，用 /7414/ 邏輯）
- `TCAT` 黑貓宅急便
- `POST` 中華郵政

### 3.3 CVS 限定欄位

| 欄位 | 必填 | 說明 |
|---|---|---|
| `ReceiverStoreID` | ✓ | 從 Day 1 拿到的門市代碼。**最多 6 字元** |
| `ReturnStoreID` | — | 退貨門市（限 7-Eleven C2C） |

⚠️ 注意：/8809/ 文件說 `ReceiverStoreID` 長度 **6**，但 /8795/ Map 回傳的 `CVSStoreID` 是 **9**。實測門市代碼通常 6 碼（如 `237024`），9 是欄位上限非實際長度。我們存 store_id 取前 6 字元 fallback。

### 3.4 HOME 限定欄位

| 欄位 | 必填 | 說明 |
|---|---|---|
| `ReceiverZipCode` | ✓ | 收件人郵遞區號 (3 碼) |
| `ReceiverAddress` | ✓ | 收件人地址（>6 字、TCAT 須完整含巷弄號樓） |
| `Temperature` | — | `0001` 常溫（預設）/ `0002` 冷藏 / `0003` 冷凍。POST 只能 `0001`。**yiimui 用 `0001`** |
| `Specification` | — | `0001` 60cm / `0002` 90cm / `0003` 120cm / `0004` 150cm。冷藏/凍禁 150。POST 忽略。**yiimui 預設 `0001`**（畫布尺寸都 < 60cm） |
| `ScheduledPickupTime` | — | 固定填 `4`（不限時）。POST 忽略 |
| `ScheduledDeliveryTime` | — | `1`=13點前 / `2`=14-18 / `3`=14-18 / `4`=不限時。POST 忽略。**yiimui 預設 `4`** |
| `Distance` | — | `00` 同縣市 / `01` 外縣市 / `02` 離島。系統會自動更正 |
| `GoodsWeight` | POST 必填 | 商品重量 kg（≤ 20）。TCAT 不填 |
| `IsCollection` | — | `Y` 代收（TCAT 限）/ `N` 不代收（預設）。**yiimui 用 `N`** |

### 3.5 通用選填

| 欄位 | 說明 |
|---|---|
| `TradeDesc` | 交易描述 ≤ 200 |
| `ClientReplyURL` | 訂單建立成功後 redirect。**幕後建單留空** |
| `Remark` | 備註 ≤ 200 |
| `PlatformID` | 平台商代號，一般留空 |

---

## 4. Response 參數

ECpay 回傳格式（**注意是用 `|` 切分的 plain text，不是 JSON**）：

**成功**：
```
1|MerchantID=XXX&MerchantTradeNo=XXX&RtnCode=300&RtnMsg=訂單建立成功&AllPayLogisticsID=XXX&...&CheckMacValue=XXX
```

**失敗**：
```
0|錯誤訊息
```

### 4.1 成功時的欄位（解析 `&` 後）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `MerchantID` | 10 | 我們特店編號 |
| `MerchantTradeNo` | 20 | 我們的交易編號（同 request） |
| `RtnCode` | int | 物流狀態代碼。**`300` = 訂單建立成功**（其他見 ECpay 物流狀態表） |
| `RtnMsg` | str | 狀態說明 |
| **`AllPayLogisticsID`** | str(20) | **ECpay 物流交易編號 — 必須保存！後續查詢、退貨、列印都靠這個** |
| `LogisticsType` | str | CVS / HOME |
| `LogisticsSubType` | str | 同 request |
| `GoodsAmount` | int | 同 request |
| `UpdateStatusDate` | str | 狀態時間 |
| `ReceiverName/Phone/CellPhone/Email/Address` | — | echo 同 request |
| **`CVSPaymentNo`** | str(15) | **CVS 寄貨編號 — 寄包裹時要標註** |
| **`CVSValidationNo`** | str(10) | **CVS 驗證碼 — 寄包裹時要標註**（C2C 7-ELEVEN 才回傳） |
| **`BookingNote`** | str(50) | **HOME 託運單號** |
| `CheckMacValue` | str | 必驗 |

### 4.2 RtnCode 常見值

| RtnCode | 含意 |
|---|---|
| 300 | 訂單建立成功 |
| 10500017 | MerchantTradeNo 重複 |
| 10500040 | GoodsAmount 超過 20,000 |
| 10500053 | ReceiverStoreID 錯誤或不存在 |
| 10500077 | 帳戶餘額不足 |
| 10500099 | 字元限制違反（姓名、商品名等） |

⚠️ ECpay RtnCode 表很長且狀態碼共用其他 API。詳見 ECpay 文件「物流狀態一覽表」。

---

## 5. CheckMacValue

跟 [/7424/](https://developers.ecpay.com.tw/7424/) 的演算法一致（MD5），與 Day 1 我們已實作的 `service.calculate_check_mac_value()` 同一支。

⚠️ Response 也回傳 CheckMacValue → **必須驗章**（這個 API 的 callback 跟 CVS Map 不同，會送 MAC）。

---

## 6. 我們的 ShippingProfile / Order → ECpay request 對應

```
Order
 ├─ order_number ───────────────► MerchantTradeNo (前 20 字)
 ├─ created_at ─────────────────► MerchantTradeDate (yyyy/MM/dd HH:mm:ss)
 ├─ total_amount ───────────────► GoodsAmount (int, max 20000 → 超過拒絕建單)
 └─ shipping_snapshot
     ├─ shipping_type ─────────────► LogisticsType + LogisticsSubType (見 §3.2 對映)
     ├─ recipient_name ────────────► ReceiverName (sanitize, pad 到 4-10 字)
     ├─ phone ─────────────────────► ReceiverCellPhone (09xxxxxxxx)
     ├─ email ─────────────────────► ReceiverEmail
     ├─ city + district ───────────► ReceiverZipCode (HOME, derive from twzipcode)
     ├─ city + district + address_detail ─► ReceiverAddress (HOME)
     └─ store_id ──────────────────► ReceiverStoreID (CVS, 取前 6 字)

OrderItems
 └─ product_title (concat) ─────► GoodsName (sanitize 禁用符號, max 50)

Sender (從 system_settings 取或 hardcoded)
 ├─ name ───────────────────────► SenderName (4-10 字)
 ├─ phone ──────────────────────► SenderCellPhone
 ├─ zipcode ────────────────────► SenderZipCode
 └─ address ────────────────────► SenderAddress
```

---

## 7. 欄位限制處理策略（重要）

### 7.1 Receiver/SenderName 4-10 字限制
台灣常見本名 2-3 字 ❌ ECpay 規範要 ≥4 字。

**解法（自動 padding）：**
- ≥4 字 → 直接用
- 3 字 → 後綴 `先生` 或 `女士`（依 gender 沒收錄則用 `客戶`）→ `張小明客戶`（5 字）
- 2 字 → 後綴 `先生` / `女士` / `客戶您好`（4-6 字）
- 1 字 → 異常，拒絕建單
- > 10 字 → 截前 10 字

實作位置：`logistics/service.py:pad_name_to_ecpay_limit()`

### 7.2 GoodsName 禁用符號
台灣商品名常含 `+`、`*`、`@`、`&` 等。

**解法（sanitize）：**
- 禁用字元清單：`^'``!@#%&*+"<>|_[]`
- 全部替換成空白後 trim 多餘空白
- 多商品：用 `,` 串接（不用 `+`，因為 `+` 是禁用字元）

實作：`logistics/service.py:sanitize_goods_name()`

### 7.3 ReceiverZipCode 自動推導
twzipcode-data 套件有 city + district → 3 碼郵遞區號的對應表。

**解法：**
- 後端也安裝相同套件（pnpm 在 store；backend Python 用 `pyzipcode-tw` 或 inline JSON）
- `derive_zipcode(city, district)` → 回 3 碼字串

備援：拿不到 zipcode 時 fallback `"100"`（中正區）讓 ECpay 自己更正

### 7.4 GoodsAmount > 20,000
- 訂單金額超過 20,000 → 拒絕建單，admin 收到錯誤訊息「訂單金額超過 ECpay 上限，請拆分訂單或自行寄出」

### 7.5 MerchantTradeNo 唯一性
每筆訂單只能建單**一次**。重複 build 會收到 `10500017`。

**解法：**
- 建單前檢查 `Shipment.tracking_number` 是否已存在
- 已存在 → 拒絕重複建單
- 同訂單若需要重新建單（例如改地址）→ 必須先呼叫「取消訂單」API 再建（Day 4 範圍）

---

## 8. 我們的 endpoint 設計

### 8.1 單筆建單

```
POST /api/v1/admin/orders/{order_id}/create-shipment
Auth: admin only
Body: 無（資料從 order + shipping_snapshot 取）
Response 200:
{
  "shipment_id": "uuid",
  "tracking_number": "F12345678901234",     // CVSPaymentNo 或 BookingNote
  "ecpay_logistics_id": "789012345",
  "validation_no": "1234",                   // CVS 7-Eleven 才有
  "rtn_code": 300,
  "rtn_msg": "訂單建立成功"
}
Response 400:
{
  "detail": "訂單金額超過 ECpay 上限 NT$20,000，無法建單"
}
Response 409:
{
  "detail": "本訂單已建立物流單，不可重複建單"
}
Response 502:
{
  "detail": "ECpay 連線失敗，請稍後再試"
}
```

### 8.2 批次建單

```
POST /api/v1/admin/shipments/batch-create
Auth: admin only
Body:
{
  "order_ids": ["uuid1", "uuid2", ...]   // max 50 筆
}
Response 200:
{
  "total": 10,
  "success": 8,
  "failed": 2,
  "results": [
    {"order_id": "uuid1", "ok": true, "tracking_number": "..."},
    {"order_id": "uuid2", "ok": false, "error": "訂單金額超過上限"},
    ...
  ]
}
```

並發呼叫 ECpay（asyncio.gather），失敗筆不影響其他成功筆。

---

## 9. 業務流程（admin 點按鈕到收到回報）

```
[1] admin 在訂單詳情頁／訂單列表選一筆或多筆「已付款且未建單」訂單
[2] 點「建立物流訂單」→ 前端送 POST 到 /admin/orders/{id}/create-shipment
[3] backend 驗證：
    ├─ 訂單存在、屬該 admin 管轄
    ├─ 訂單狀態 = 已付款（status='paid'）
    ├─ Shipment 不存在（沒重複建）
    └─ GoodsAmount ≤ 20000
[4] 從 shipping_snapshot 組 ECpay request：
    ├─ pad ReceiverName 到 4-10 字
    ├─ sanitize GoodsName
    ├─ derive ReceiverZipCode (HOME)
    └─ truncate ReceiverStoreID 到 6 字 (CVS)
[5] POST 到 /Express/Create → 等 response
[6] Parse `1|key=val&...` 或 `0|errmsg`
[7] 成功 → 寫 Shipment(tracking_number, ecpay_logistics_id, status='shipped'),
         同步 update Order.status='shipped'
[8] 失敗 → 不寫 Shipment，回 admin 錯誤訊息
[9] 回前端 JSON
```

---

## 10. 安全與測試

### 10.1 必須驗章（與 CVS Map 不同）
- /8795/ CVS Map callback：實測沒送 CheckMacValue（CVS Map quirk）
- **/8809/ + /7414/ 建單 response：必送 CheckMacValue，必須驗證**

### 10.2 沙箱測試門市代碼
ECpay 提供 sandbox 測試門市：
- 7-Eleven C2C：`131386` `896539`
- 全家：`006598`
- OK：`1328`
- 沒給 7-Eleven B2C / 萊爾富 / 宅配 的 sandbox

### 10.3 測試前先確認沙箱餘額
ECpay sandbox 帳號可能餘額不足 → 建單會 fail (RtnCode 10500077)。建單沙箱前確認帳戶餘額 > NTD 500。

### 10.4 我們 production 帳號的測試
**不能直接用**。production 建一筆 = 真實託運單號 = 收手續費。
測試方式：
- 用 sandbox + sandbox 測試門市（如果 sandbox 有開通 C2C 物流）
- 或用 production + admin 自己訂一筆「測試訂單」（金額 NT$1）→ 建單後立刻去 ECpay 後台「取消物流訂單」

---

## 11. 待確認事項

1. **寄件人資訊**從哪裡取？
   - 選項 A：寫在 `system_settings` 表，admin 從後台改（如賣家姓名 / 地址 / 電話 / 郵遞區號）
   - 選項 B：寫在 env var 或 hardcoded constants
   - 選項 C：每次建單由 admin 在按鈕旁填（每次都要填？太煩）
   - **預設方案：A**，已在 `system_settings` 預留欄位

2. **同訂單但客戶買多種商品** 如何處理 GoodsName？
   - 選項 A：concat 所有 product_title（「商品 A,商品 B,...」）超過 50 字截斷
   - 選項 B：只取第一個 product_title 加「等」字尾（「畫布 A 等」）
   - **預設方案：A**

3. **商品包裝尺寸**（Specification）由 admin 個別設定還是統一？
   - yiimui 商品都是 cm 尺寸的畫布（多數 < 60cm）→ 一律用 `0001 60cm`
   - 例外（畫布 > 60cm）：admin 可在訂單頁手動 override

---

## 12. 文件交叉索引

| 內容 | 路徑 |
|---|---|
| 整體推進計畫 | `docs/module_plans/20_logistics_ecpay.md` |
| /8795/ CVS Map 規格 | `docs/integration_specs/ecpay_cvs_map.md` |
| **本文件 — /8809/ + /7414/ 建單** | `docs/integration_specs/ecpay_create_shipment.md` |
| Day 3 狀態通知 | `docs/integration_specs/ecpay_status_callback.md`（待寫） |
| Day 4 列印託運單 | `docs/integration_specs/ecpay_print_label.md`（待寫） |

---

## 13. 變更紀錄

| 日期 | 內容 |
|---|---|
| 2026-05-07 | 初版 — Day 2 Phase 1 規劃。fetch /8809/ + /7414/ 完整文件，列出與 yiimui 系統的對應、padding/sanitize 策略、批次建單設計 |
