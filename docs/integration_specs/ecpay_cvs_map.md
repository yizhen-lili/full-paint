# ECpay 門市電子地圖 API 規格（CVS Map）

> ECpay 提供的「超商選店」前端互動 API。用戶在 ECpay 提供的地圖頁挑選 7-11 / 全家 / 萊爾富 / OK 門市，挑完 ECpay 把門市資料 POST 回特店指定的 ServerReplyURL。
>
> **官方文件**：https://developers.ecpay.com.tw/8795/
> **CheckMacValue 規則**：https://developers.ecpay.com.tw/7424/
> **本規格寫於**：2026-05-07，包含官方文件 + 我們實測（沙箱 + production）的觀察。

---

## 1. 用途與定位

### 1.1 解決什麼問題
讓客戶**在結帳流程中視覺化選擇取貨超商門市**。ECpay 提供地圖 UI（會跳到各家超商的官方地圖系統，例如 7-11 走 PRESCO、全家走 mfme.map.com.tw），客戶選店後 ECpay 把資料 POST 回我們。

### 1.2 跟其他 API 的關係
```
[本 API /8795/]            ← 客戶選店時呼叫
       ↓
拿到 store_id, store_name, address
       ↓
存到 ShippingProfile (我們 DB)
       ↓
[/8809/ 門市訂單建立]      ← 客戶付款後，admin 出貨時呼叫
       ↓
產生託運單號
       ↓
[/7420/ 物流狀態通知]      ← ECpay 推狀態
```

**本 API 不建立物流訂單**，只是「選店資料拉取」。真實寄件靠 `/8809/`（Day 2 範圍）。

### 1.3 替代方案
`/47496/` 取得門市清單 — 純 API 拉全台門市資料，不跳 ECpay 視窗，要自己做 UI。我們**沒選這個**因為工程量大。

---

## 2. Endpoint

| 環境 | URL |
|---|---|
| Stage（測試／沙箱） | `https://logistics-stage.ecpay.com.tw/Express/map` |
| Production（正式） | `https://logistics.ecpay.com.tw/Express/map` |

**HTTP**：POST · `Content-Type: application/x-www-form-urlencoded` · `Accept: text/html` · 全程 HTTPS

---

## 3. Request 參數

| 欄位 | 型別 | 長度 | 必填 | 預設 | 範圍 / 說明 |
|---|---|---|---|---|---|
| `MerchantID` | String | 10 | ✓ | — | ECpay 給的特店編號 |
| `MerchantTradeNo` | String | 20 | ✓ | — | 廠商交易編號，**唯一**，英數混合。本 API 用一次性，不必對應實際訂單 |
| `LogisticsType` | String | 20 | ✓ | — | 固定值 `CVS` |
| `LogisticsSubType` | String | 20 | ✓ | — | 見 §3.1 |
| `IsCollection` | String | 1 | ✓ | — | `N`（不代收）/ `Y`（代收貨款）。我們用 `N` |
| `ServerReplyURL` | String | 200 | ✓ | — | ECpay 回 POST 給我們的 URL，**必須 https** |
| `ExtraData` | String | 20 | — | — | 廠商自訂字串，原值回傳 |
| `Device` | Int | — | — | `0` | `0` PC / `1` Mobile |
| `CheckMacValue` | String | — | ✓ | — | 簽章，演算法見 §5 |

### 3.1 LogisticsSubType 可選值

⚠️ **B2C 帳號跟 C2C 帳號允許的 SubType 完全不同**，混用會收到「找不到加密金鑰」。

#### B2C（大宗寄倉，需先測標）
| SubType | 對應超商 |
|---|---|
| `UNIMART` | 7-ELEVEN |
| `UNIMARTFREEZE` | 7-ELEVEN 冷凍店取 |
| `FAMI` | 全家 |
| `HILIFE` | 萊爾富 |

#### C2C（店到店，按單收費）
| SubType | 對應超商 |
|---|---|
| `UNIMARTC2C` | 7-ELEVEN 交貨便 |
| `FAMIC2C` | 全家店到店 |
| `HILIFEC2C` | 萊爾富店到店 |
| `OKMARTC2C` | OK 超商店到店 |

確認你帳號開通哪些 SubType 的方法：
- 到 ECpay 後台 → 服務管理 / 物流選單
- 或用我們的 diagnostic API：`GET /api/v1/logistics/probe-subtypes`（會自動探測 8 個 SubType 各送一筆假請求）

**yiimui 用 C2C**（2026-05-07 確認），預設 SubType：
- `seven_eleven` 配送方式 → `UNIMARTC2C`
- `family_mart` 配送方式 → `FAMIC2C`

---

## 4. Response（ServerReplyURL 收到的 POST）

ECpay 在用戶選完店後，**用瀏覽器 form POST**（不是 server-to-server）回傳到我們的 ServerReplyURL：

| 欄位 | 型別 | 長度 | 回傳條件 | 說明 |
|---|---|---|---|---|
| `MerchantID` | String | 10 | 必回 | 特店編號 |
| `MerchantTradeNo` | String | 20 | 必回 | 我們在 request 帶過去的同值 |
| `LogisticsSubType` | String | 20 | 必回 | 用戶選店時用的 SubType |
| `CVSStoreID` | String | 9 | 必回 | 門市代碼（例：`237024`） |
| `CVSStoreName` | String | 10 | 條件回 | 門市名稱（例：`新加昌門市`） |
| `CVSAddress` | String | 60 | 條件回 | 門市地址（例：`高雄市楠梓區加昌路275.277號`） |
| `CVSTelephone` | String | 20 | 條件回 | 門市電話 |
| `CVSOutSide` | String | 1 | 條件回 | `0` 本島 / `1` 離島（僅 UNIMART/UNIMARTC2C/FAMI/FAMIC2C） |
| `ExtraData` | String | 20 | 條件回 | request 帶的同值 |
| `CheckMacValue` | String | — | **❓ 不確定** | 文件列為必回，但**我們實測 CVS Map 沒有送**（2026-05-07 production 真實流程） |

### 4.1 ⚠️ 實測觀察（vs 文件不符的點）

**a. CheckMacValue 缺失**
- 文件 §5 列為 response 欄位
- 實測 production POST 回的 raw body **完全沒有 `CheckMacValue=` 欄位**
- 影響：無法做嚴格簽章驗證
- 推測：CVS Map 是「客戶端 form POST」（非 server-to-server），ECpay 自己也在客戶端瀏覽器，可能簽章機制設計上就不送

**b. CVSStoreName / CVSAddress / CVSTelephone 在 UNIMART/UNIMARTC2C 不回傳？**
- 文件寫「7-ELEVEN UNIMART/UNIMARTC2C 不回傳」
- 但我們實測 UNIMARTC2C 有回傳 storename + address，只有 telephone 是空字串
- 不要相信文件這條限制，依實際回傳處理（缺值用空字串）

**c. 字元編碼**
- 文件未指定 UTF-8 還是 Big5
- 實測 UTF-8 解碼中文正常（`新加昌門市` `高雄市楠梓區加昌路275.277號`）
- 但仍保留 Big5 fallback 以防特定 SubType 例外

---

## 5. CheckMacValue 演算法（**物流 = MD5**）

來源：[/7424/](https://developers.ecpay.com.tw/7424/)

⚠️ **物流 API 用 MD5，不是金流的 SHA256**。混用直接驗證失敗。

### 5.1 計算步驟

```
1. 把所有 request 參數依 key 字典序（A→Z）排序
2. 串成 raw string：HashKey={hk}&Key1=Val1&Key2=Val2&...&HashIV={hiv}
3. URL encode 整串（.NET style）
   - 保留 -_.!*() 不編碼
   - 空格 → +
4. 全部轉小寫
5. MD5
6. 轉大寫
```

### 5.2 範例（用沙箱公開 key）

```
HashKey = 5294y06JbISpM5x9
HashIV  = v77hoKGq4kWxNNIS

Params (sorted):
  Device=0
  IsCollection=N
  LogisticsSubType=UNIMARTC2C
  LogisticsType=CVS
  MerchantID=2000132
  MerchantTradeNo=CVSTEST123456789
  ServerReplyURL=https://example.com/reply

Raw:
  HashKey=5294y06JbISpM5x9&Device=0&IsCollection=N&LogisticsSubType=UNIMARTC2C&LogisticsType=CVS&MerchantID=2000132&MerchantTradeNo=CVSTEST123456789&ServerReplyURL=https://example.com/reply&HashIV=v77hoKGq4kWxNNIS

URL encoded + lowercase:
  hashkey%3d5294y06jbispm5x9%26device%3d0%26iscollection%3dn%26logisticssubtype%3dunimartc2c%26logisticstype%3dcvs%26merchantid%3d2000132%26merchanttradeno%3dcvstest123456789%26serverreplyurl%3dhttps%3a%2f%2fexample.com%2freply%26hashiv%3dv77hokgq4kwxnnis

MD5 + uppercase:
  EA90DF7C99E11C3D2A80402E16D448BE
```

### 5.3 我們的 Python 實作

`backend/logistics/service.py:calculate_check_mac_value()` — 已驗證對沙箱 B2C 算出的 MAC 能通過 ECpay 驗證。

---

## 6. 我們的整合流程（精確順序）

### 6.1 用戶端流程

```
[1] 用戶在 yiimui 結帳頁／會員中心收件資料填單
    └ 配送方式選「7-Eleven 取貨」或「全家取貨」
    └ ConvenienceStorePicker.vue 顯示「選擇門市」按鈕
    
[2] 用戶點「選擇門市」
    └ window.open('/api/v1/logistics/cvs-map?type=UNIMARTC2C', popup)
    └ button 變 loading 狀態，setInterval 偵測 popup 關閉
    
[3] popup 載入 backend cvs-map endpoint
    └ backend 產生 ECpay 所需參數（含 CheckMacValue）
    └ 回 auto-submit form HTML，瀏覽器自動 POST 到 ECpay
    
[4] ECpay 把瀏覽器 redirect 到該超商的地圖系統
    └ 7-11 → emap.presco.com.tw
    └ 全家 → mfme.map.com.tw
    
[5] 用戶在地圖上挑門市
    
[6] 地圖系統把資料帶回 ECpay 中介層 → ECpay 用瀏覽器 POST 到我們 ServerReplyURL
    └ 對我們的 backend：POST /api/v1/logistics/cvs-callback
    └ body 是 form-urlencoded，含 store_id, store_name, address...
    
[7] backend cvs-callback endpoint 處理
    ├ 讀 raw body（記錄 log 用）
    ├ 解碼（UTF-8 優先，Big5 fallback）
    ├ 若 CheckMacValue 存在 → 驗章；不存在 → 接受（CVS Map 已知 quirk）
    └ 回一段 HTML：window.opener.postMessage(payload) → window.close()
    
[8] 開啟 popup 的原視窗收到 message event
    └ ConvenienceStorePicker.vue 的 handleMessage()
    └ 把 store_id / store_name / address 寫進表單
    └ button 從 loading 切回，顯示「已選門市」card
    
[9] 用戶可繼續填收件人、電話 → 送出表單存進 ShippingProfile
```

### 6.2 後端 endpoints（我們實作的）

| Endpoint | 方法 | 用途 |
|---|---|---|
| `GET /api/v1/logistics/cvs-map?type={SubType}` | GET | 產生 auto-submit form HTML，瀏覽器自動 POST 到 ECpay |
| `POST /api/v1/logistics/cvs-callback` | POST | 接 ECpay 選店結果，驗章後 postMessage 給 opener |
| `GET /api/v1/logistics/debug-config` | GET | ⚠️ 過渡期診斷，正式上線前刪 |
| `GET /api/v1/logistics/probe-subtypes` | GET | ⚠️ 過渡期診斷，正式上線前刪 |

---

## 7. 可能錯誤情境與處理

| 錯誤 | 來源 | 我們處理方式 |
|---|---|---|
| **找不到加密金鑰，請確認是否有申請開通此物流方式** | ECpay 直接回（用戶看到） | (a) MerchantID 與 HashKey/HashIV 不匹配（環境錯了 stage/prod）<br>(b) LogisticsSubType 帳號沒開通<br>診斷：`GET /probe-subtypes` |
| **CheckMacValue Error** | ECpay 直接回 | 簽章演算法錯（key 排序、URL encode、MD5、大小寫） |
| 用戶手動關 popup 沒選店 | popup 直接消失 | picker 用 setInterval 500ms 偵測 popup.closed → 釋放 button |
| popup 被瀏覽器擋 | window.open 回 null | picker 顯示「請允許彈出視窗」訊息 |
| iOS 不支援新視窗 | 文件警告 | TODO Day 4：mobile UA 偵測，改成同視窗跳轉 + return URL |
| iframe 內嵌 | ECpay 拒絕 | 不要用 iframe（我們用 window.open） |
| Cookie 被禁 | 行動裝置 | TODO Day 4：偵測並提示用戶 |

---

## 8. 重要警告

1. **MerchantTradeNo 必須唯一**：每次點「選擇門市」都產一個新值（我們用 `CVS{YYMMDDHHMMSS}{rand}` 19 字元格式）
2. **B2C / C2C 不可混用**：帳號開哪個就用對應 SubType
3. **stage 環境是固定門市**：不會跳真地圖，這是 ECpay 設計，不是 bug
4. **iOS 不要 window.open**：要在同視窗跳轉，否則 cookie/session 會丟失
5. **iframe 絕對不行**：ECpay 直接拒絕
6. **ServerReplyURL 必須 https**：Railway proxy 要設 `--proxy-headers` 讓 FastAPI 看到 https scheme

---

## 9. 安全性與信任邊界

由於 §4.1a 觀察到 ECpay 的 CVS Map callback 不送 CheckMacValue，**我們無法 100% 驗證 callback 是 ECpay 發出的**。

威脅模型：
- ❓ 攻擊者偽造 callback POST 到我們 endpoint，塞假門市資料
- ✅ 影響有限：用戶要先去 popup window 才會收到 message，且我們在 Day 2 建單時會用 store_id 重新跟 ECpay 驗證真實門市存在

緩解措施（已實作）：
- callback 收到後**只塞進前端 sessionState**，不直接寫 DB
- ShippingProfile 寫進 DB 是用戶按「儲存」才發生（多一道用戶確認）

未實作的進階防禦（可考慮）：
- 在 cvs-map 階段產生一次性 nonce，存 server-side session，callback 時對照
- 用戶 IP 白名單（ECpay 公開 IP 範圍）

---

## 10. 待辦事項（Day 4 上線前清理）

- [ ] 刪除 `/api/v1/logistics/debug-config`、`/api/v1/logistics/probe-subtypes` 兩個 diagnostic endpoint
- [ ] 確認 iOS 行為：是否要改成同視窗跳轉 + return URL
- [ ] 確認 mobile cookie 行為，加 fallback 提示
- [ ] callback 加一次性 nonce 增強信任邊界

---

## 11. 欄位限制總表（給後端驗證 + 前端提示用）

### 11.1 我們**送給 ECpay** 的 request 欄位限制

| 欄位 | 限制 | 違反會發生什麼 | 我們的驗證位置 |
|---|---|---|---|
| `MerchantID` | 字串、最多 10 字元、英數 | ECpay 拒收 | env var 設定時驗，runtime 不驗（已固定） |
| `MerchantTradeNo` | 字串、**最多 20 字元**、英數混合、唯一 | 重複 → ECpay 報錯；超長 → 截斷 | service.py `generate_merchant_trade_no()` 固定產 19 字元 |
| `LogisticsType` | 固定 `CVS` | 改其他值會走宅配流程 | service.py 寫死 |
| `LogisticsSubType` | 列舉值（B2C 4 個 + C2C 4 個） | 帳號沒開通 → 「找不到加密金鑰」 | service.py `is_supported_sub_type()` 驗 |
| `IsCollection` | 固定 `Y` 或 `N`，1 字元 | 違反規則拒收 | service.py 寫死 `N` |
| `ServerReplyURL` | 字串、**最多 200 字元**、必須 https | http 會被 ECpay 拒；超長截斷 | router.py `_resolve_server_reply_url()` 強制 https |
| `ExtraData` | 字串、**最多 20 字元** | 超長截斷 | 若使用要在 caller 端驗 |
| `Device` | `0` 或 `1` | 不影響功能 | 寫死 `0` |

### 11.2 我們**從 ECpay 收到** 的 response 欄位限制（驗收用）

| 欄位 | 限制 | 我們收到時要做什麼 |
|---|---|---|
| `CVSStoreID` | **最多 9 字元**、必有 | **空值 → 拒絕並要求重選**（用戶沒選店就關 popup 會收到空） |
| `CVSStoreName` | 最多 10 字元、條件回 | 容錯空值；只當 display 用 |
| `CVSAddress` | 最多 60 字元、條件回 | 容錯空值；只當 display 用 |
| `CVSTelephone` | 最多 20 字元、條件回 | 容錯空值（UNIMARTC2C 永遠不送） |
| `CVSOutSide` | `0` 或 `1`、條件回 | 容錯空值；做出貨判斷時用 |
| `LogisticsSubType` | 必須跟 request 一致 | 不一致 → log 警告但接受（ECpay 可能改寫） |
| `MerchantTradeNo` | 必須跟 request 一致 | 不一致 → 拒絕（防 callback 偽造） |

### 11.3 用戶在 yiimui 自己填的欄位（ShippingProfile）

這部分**必須前後端雙驗證**（前端阻擋顯而易見的輸入錯誤、後端最終把關）：

| 欄位 | 前端規則 | 後端規則 | 違反訊息 |
|---|---|---|---|
| `recipient_name` 收件人 | required, maxLength=30 | `^.{1,30}$` | 「收件人姓名不可空白且不超過 30 字」 |
| `phone` 電話 | pattern=`09\d{8}` | regex `^09\d{8}$` | 「電話需為 09 開頭 10 碼數字」 |
| `email` Email | type=email, optional | RFC 5321 email regex | 「Email 格式不正確」 |
| `shipping_type` | radio, 三選一 | enum check | 「不支援的配送方式」 |
| `city` 縣市 | required when home, dropdown 限定 22 縣市 | enum check | 「請選擇正確的縣市」 |
| `district` 行政區 | required when home, dropdown 依 city 動態 | 必須存在於 city 對應行政區 | 「請選擇正確的行政區」 |
| `address_detail` 地址 | required when home, maxLength=200 | maxLength=200 | 「地址不可空白且不超過 200 字」 |
| `store_id` 門市代碼 | required when cvs, **由 picker 自動填**（用戶不能手改） | 必須是 ECpay 回來的值，**長度 ≤ 9** | 「請從地圖選擇門市」 |
| `store_name` 門市名稱 | 由 picker 自動填 | maxLength=20（容錯比官方 10 多一點） | （理論上不會違反，picker 控制） |
| `is_default` | checkbox | bool | — |

**安全考量：** `store_id` / `store_name` 雖然來自 ECpay 但用戶可以用 devtool 改 form value，所以後端**仍需驗證** `store_id` 是合法 ECpay 門市代碼（最終靠 Day 2 `/8809/` 建單時 ECpay 自己驗）。

---

## 12. 文件交叉索引

| 內容 | 路徑 |
|---|---|
| 整體推進計畫（4 階段） | `docs/module_plans/20_logistics_ecpay.md` |
| 本 API 規格（這份） | `docs/integration_specs/ecpay_cvs_map.md` |
| Day 2 訂單建立規格 | `docs/integration_specs/ecpay_cvs_order.md`（待寫） |
| Day 3 狀態通知規格 | `docs/integration_specs/ecpay_status_callback.md`（待寫） |
| Day 4 列印託運單規格 | `docs/integration_specs/ecpay_print_label.md`（待寫） |

---

## 12. 變更紀錄

| 日期 | 內容 |
|---|---|
| 2026-05-07 | 初版 — 完整抓 /8795/ + /7424/ 文件、加入沙箱+production 實測觀察、列出與我們實作對應、補 §4.1 文件 vs 實測差異、§9 安全考量 |
