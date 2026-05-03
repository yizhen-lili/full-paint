# 易木 YIIMUI 電商前端設計 Brief（給 Claude.ai 設計師）

> 給 Claude.ai 用的 context 文件。複製整份到 claude.ai 對話開頭，請它出 mockup。
> Backend API + 規格範圍已固定，請只設計這份文件列出的頁面與功能，**不要發明 backend 沒有的東西**。

---

## 一、品牌定調

**易木 YIIMUI** — 數字油畫平台

| 屬性 | 值 |
|---|---|
| 風格關鍵詞 | 日系雜貨鋪、無印、紙感、工藝、療癒 |
| 主色 | 木質暖棕 `#8B6F47` |
| 背景 | 米白水彩紙 `#F5EFE5` |
| 狀態色 | 天然顏料色（低飽和：松綠、土紅、墨灰）|
| 字體 | 中文：思源宋體 / Noto Serif TC（標題）；無印良品風 sans（正文）|
| 視覺語彙 | 大量留白、淡邊框（hairline）、柔和陰影、不要尖銳角 |
| 反例 | 不要蝦皮 / 拍賣風（資訊密集、紅黃跳色）；不要科技風（霓虹色 / 漸層）|

---

## 二、目標客戶 + 差異化

- 25-50 歲女性為主，重美感 + 工藝感
- 願意花時間在過程而非只追求結果
- 部分客戶想用「**自己的照片**」做客製油畫（**核心差異化**）

商品分兩類：
1. **目錄商品**（products）— 預先做好的圖（風景、人物插畫、藝術畫等），客戶選規格購買
2. **客製商品**（custom_request）— 客戶上傳照片或想要不同規格 → 管理員報價 → 確認後成為訂單

---

## 三、需要設計的頁面（30 個，按優先序）

### 🔴 P0 — 視覺定調 + 核心商品流程

| # | 頁面 | 路徑 | 重點 |
|---|---|---|---|
| 1 | **首頁** | `/` | hero、最新上架橫向捲動、熱門商品、三個分類入口（難易度 / 標籤主題 / 細緻度）、客製化服務 banner |
| 2 | **商品列表** | `/products` | 卡片網格、左側篩選（難易度 / 細緻度 / 尺寸 / 標籤）、排序（最新 / 熱門 / 價格升降）、24 筆/頁 + 頁碼 |
| 3 | **搜尋結果** | `/search?q=xxx` | 同列表頁，篩選保留 |
| 4 | **商品詳情** | `/products/:id` | 圖片輪播（封面 + 多圖）、規格三層級選擇器（尺寸→難易度→細緻度，無對應變體灰階禁用）、價格、庫存（現貨/預購標示）、加購車、同系列商品橫列、商品說明摺疊區（畫具內容 / 畫布材質 / 使用建議 / 注意事項，4 區）、「想要不同規格？」展開客製規格表單 |

### 🟠 P1 — 結帳 + 訂單核心

| # | 頁面 | 路徑 | 重點 |
|---|---|---|---|
| 5 | **購物車** | `/cart` | 商品列表（規格 / 數量調整 / 小計 / 刪除）、庫存拆單提示（現貨 X + 預購 Y）、**折扣券區**（手動 promo_code 輸入 + 持有券 dropdown 選擇）、**auto_checkout 自動套用**標示、**免運進度條**（NT$800 或 ≥3 件免運）、取貨方式（宅配 / 7-11 / 全家 + 運費）、超大尺寸警告（>40cm 邊長 + 超商 → 建議改宅配）、金額明細 |
| 6 | **結帳** | `/checkout` | 訂單明細、收件資料（從 shipping_profiles 選或新填）、**超商選店**（第三方地圖 popup，行動裝置降級 iframe）、**預購出貨偏好**（合併出貨 / 分開出貨）、確認金額、送出 |
| 7 | **訂單建立完成** | `/checkout/complete` | 訂單編號、付款帳號（system_settings）、24 小時付款期限倒數 |
| 8 | **訂單列表** | `/orders` | 三 tab：未付款（pending_payment）/ 出貨中（paid / processing / shipped）/ 已完成（completed / cancelled / refund_*）。每筆：訂單編號、商品縮圖（最多 3）、總額、狀態。**未付款 tab 每筆有「填寫付款資訊」連結** |
| 9 | **訂單詳情** | `/orders/:id` | 訂單資訊（編號 / 建立時間 / 付款期限倒數）、商品明細（含現貨 / 預購分離）、金額明細、收件資訊、付款資訊、出貨資訊（物流追蹤號）、**生產進度**（每項目 pending / 製作中 / 備貨中 / 備貨完成 / 已出貨）、取消按鈕（pending_payment 才有）、**確認已收到商品**按鈕（status=shipped 才有）、**退款確認區塊**（refund_processing / refunded 兩態）、取消確認彈窗 |
| 10 | **付款核對表單** | 訂單詳情內展開 | 轉帳金額 / 日期 / 時間 / 帳號末五碼 / 備注，提交後管理員核對 |

### 🟡 P2 — 客製化（核心差異化）

| # | 頁面 | 路徑 | 重點 |
|---|---|---|---|
| 11 | **客製化服務頁** | `/custom` | 上方完成案例展示（卡片：成品圖 / 類型標籤 / 尺寸 / 難易度，點擊展開大圖）、下方客製照片申請表單 |
| 12 | **客製照片申請表單** | `/custom` 下方 | 上傳照片（JPG/PNG ≤ 10MB）、畫布尺寸偏好（dropdown 從 canvas_sizes 選或留空讓管理員建議）、難易度（含「讓管理員建議」選項）、備注、送出。**訪客可填表單，送出時暫存 sessionStorage 並跳登入頁，登入後自動送出** |
| 13 | **客製申請列表** | `/custom/requests` | 分類顯示所有 custom_requests，狀態 chip：待報價 / 洽談中 / 報價已送出 / 修改中 / 已確認待付款 / 已拒絕 / 已過期 |
| 14 | **客製申請詳情 + 訊息** | `/custom/requests/:id` | 申請基本資訊、提交內容（照片預覽 / 規格 / 備註）、**狀態與可操作**（quote_pending 可改照片 / 規格；quote_sent 點「待確認」進報價頁；quote_confirmed 進付款）、**訊息對談區**（聊天式 UI，sender_type 分客戶 / 管理員，**SSE 即時推播**，離開頁面時改 email 通知）|
| 15 | **報價確認頁** | `/custom/quote/:token` | **不需登入**（token 即憑證，24h / 延後 48h）、規格摘要、報價金額、初稿樣稿圖、報價有效期限倒數。三按鈕：**確認報價**（→ 客製結帳）/ **要求修改**（draft_revision）/ **拒絕報價**（quote_rejected） / **延長考慮**（每筆限 1 次） |
| 16 | **客製結帳** | `/custom-orders/:id/checkout` | 報價金額 + 收件資訊 + **不支援折扣**（一對一報價）+ 運費（宅配 NT$120 / 超商 NT$70）+ 送出 |

### 🟢 P3 — 會員系統 + 折扣錢包

| # | 頁面 | 路徑 | 重點 |
|---|---|---|---|
| 17 | **註冊** | `/register` | 姓名（≥4 字）/ Email / 密碼（≥10 碼英數混合）→ 寄驗證信 |
| 18 | **登入** | `/login` | Email + 密碼，「忘記密碼」連結。登入後重導回原頁 |
| 19 | **忘記密碼** | `/forgot-password` | 輸入 Email → 寄重設連結（1h TTL） |
| 20 | **重設密碼** | `/reset-password/:token` | 輸入新密碼 |
| 21 | **Email 驗證** | `/verify-email/:token` | 點信內連結進來自動驗證 → 跳登入頁，**驗證後自動發新用戶歡迎券** |
| 22 | **個人資料** | `/profile` | 姓名 / Email（改 email 需重驗，新 email 暫存 pending_email）/ 性別 / 生日 / 改密碼（需舊密碼） |
| 23 | **收件資料管理** | `/profile/shipping` | 多筆收件人 CRUD：宅配（姓名 / 電話 / Email / 地址）+ 超商門市（姓名 / 電話 / Email / 門市代號 / 門市名稱），可設預設 |
| 24 | **折扣券錢包** | `/profile/coupons` | 持有券列表：券名稱、折扣內容（百分比 / 固定金額）、最低消費門檻、到期日。狀態分：可用 / 已使用（折疊）/ 已過期（折疊）。**券種類包含**：new_user（註冊歡迎）/ spend_reward（消費回饋）/ returning_loyal（回購忠誠）/ manual（管理員發）|

### ⚪ P4 — 資訊頁（純靜態 Markdown）

| # | 頁面 | 路徑 | 內容由管理員後台編輯 |
|---|---|---|---|
| 25 | **尺寸指南** | `/size-guide` | 17 種畫布尺寸對照、擺放情境建議、框架說明 |
| 26 | **出貨流程** | `/shipping-info` | 付款 → 備貨 → 包裝 → 出貨 → 取貨 5 步驟 |
| 27 | **訂製流程** | `/custom-process` | 申請 → 審核 → 報價 → 付款 → 製作 → 出貨 6 步驟 |
| 28 | **報價參考** | `/pricing` | 文字說明 + 目錄商品價格區間表（17 尺寸 × 4 難易度 matrix）+ 客製照片參考區間 |
| 29 | **退款退貨政策** | `/refund-policy` | 條件、流程、處理時間、客服聯繫 |
| 30 | **共用導覽列 + Footer** | 全站 | 導覽列：商品列 / 尺寸指南 / 客製化商品 / 🔍 搜尋 / 購物車（件數）/ 登入 or 會員下拉。Footer：資訊頁連結 + 版權 |

---

## 四、Backend API 全清單（前端可用）

> 完整規格在我們專案 `docs/api.md`。以下是電商前端會用到的所有 endpoint。

### 認證
- `POST /auth/register` / `/auth/login` / `/auth/logout` / `GET /auth/me`
- `POST /auth/verify-email` / `/auth/resend-verification`
- `POST /auth/forgot-password` / `/auth/reset-password`

### 用戶資料
- `PATCH /users/me`（姓名 / 性別 / 生日 / pending_email）
- `POST /users/me/change-password`
- `POST /users/me/request-email-change`

### 收件資料
- `GET / POST /users/me/shipping-profiles`
- `PUT / DELETE /users/me/shipping-profiles/:id`
- `PATCH /users/me/shipping-profiles/:id/set-default`

### 商品（公開）
- `GET /products?difficulty=&detail=&canvas_size=&tag_id=&series_id=&sort=&page=&page_size=`
- `GET /products/search?q=`（ILIKE title / description / tags.name）
- `GET /products/:id`（含 variants、images、series、tags）
- `GET /products/:id/related`（同系列）
- `GET /tags`

### 購物車
- `GET /cart` / `POST /cart/items` / `PATCH /cart/items/:id` / `DELETE /cart/items/:id`
- `POST /cart/checkout-preview`（試算金額：含 discount / shipping / total）

### 訂單
- `POST /orders`（建單，body 含 shipping_profile_id / promo_code / user_coupon_id / shipping_method / shipping_preference）
- `GET /orders` / `GET /orders/:id`
- `POST /orders/:id/payment-submission`（付款核對表單）
- `POST /orders/:id/confirm-received`（確認收貨）
- `POST /orders/:id/confirm-refund`（確認收到退款）
- `POST /orders/:id/cancel`

### 客製申請
- `POST /custom-requests`（提交申請，含 photo_url / canvas size / difficulty 偏好 / 備注）
- `GET /custom-requests` / `GET /custom-requests/:id`
- `POST /custom-requests/:id/messages`（發訊息）
- `PATCH /custom-requests/:id/photo`（換照片，舊照立即 Firebase 刪）
- `GET /custom-requests/:id/sse`（**SSE 連線**，即時推送新訊息 / 狀態變更）

### 報價（token 認證，不需登入）
- `GET /custom/quote/:token`
- `POST /custom/quote/:token/confirm` / `reject` / `extend` / `request-revision`

### 折扣
- `GET /users/me/coupons`（持有券：available / used / expired 三類）
- `POST /promo-codes/validate`（公開折扣碼驗證 + 折扣金額預覽）

### 靜態頁
- `GET /pages/:slug`（size_guide / shipping / custom_process / pricing_reference / refund_policy）
- `GET /system-settings/public`（付款帳號 / 付款期限 / 預估工作天等）
- `GET /custom-cases` / `GET /custom-cases/:id`（案例展示）

### 上傳（前端直傳 Firebase）
- `POST /upload/custom-photo`（客製申請照片）
- `POST /upload/payment-screenshot`（轉帳截圖）

### Webhook
- `POST /webhooks/ecpay`（物流狀態回呼，前端不直接呼叫）

---

## 五、Backend **不做** 的（請勿設計）

避免 mockup 出現以下功能 — 規格沒這些，做了也沒 API：

- ❌ 會員等級 / 點數系統 / 簽到積分
- ❌ 商品評論 / 評價星等
- ❌ 收藏 / 我的最愛 / 願望清單
- ❌ 商品分享到社群（除了基本 OG meta）
- ❌ 直播 / 限時搶購 / 倒數計時促銷頁
- ❌ 多語系（先做繁體中文）
- ❌ 內建客服聊天室（只有客製申請內建訊息系統，不是全站客服）
- ❌ 部落格 / 文章發布

---

## 六、規格細節

### 畫布尺寸（17 種固定）
- 正方：20×20、30×30、40×40、50×50、60×60
- 直幅：30×40、30×50、30×60、40×50、40×60、50×60
- 橫幅：40×30、50×30、60×30、50×40、60×40、60×50

### 難易度（4 級）
入門 / 初級 / 中級 / 進階

### 細緻度（4 級）
粗糙 / 標準 / 細緻 / 高級
（客製照片時客戶不必填，由管理員根據圖質決定）

### 訂單狀態流
```
pending_payment → paid → processing → shipped → completed
        ↓                                            ↑
     cancelled                              （客戶確認 or ECpay webhook 自動）
                ↓ refund 流程
   refund_processing → refunded（含 refund_confirmed_at 客戶確認）
                  → partially_refunded
```

### 生產進度（訂單詳情顯示）
| 後端 | 客戶顯示 |
|---|---|
| pending | 等待備貨 |
| in_production | 製作中 |
| manufacturing / packaging | 備貨中（合併） |
| ready_to_ship | 備貨完成 |
| shipped | 已出貨 |

### 客製申請狀態
| 狀態 | 顯示文字 |
|---|---|
| quote_pending | 等待報價中（可自由改照片 / 規格 / 備註）|
| negotiating | 洽談中（鎖定不可改） |
| quote_sent | 報價已送出，請確認 |
| draft_revision | 修改中（已要求修改初稿） |
| quote_confirmed | 已確認，等待付款 |
| quote_rejected | 已拒絕（可重新申請） |
| quote_expired | 已過期 |

### 取貨方式 + 運費
- **宅配**：全國，運費 NT$80（目錄）/ NT$120（客製）
- **7-11 / 全家**：超商取貨，NT$70（客製）；目錄商品免運門檻 NT$800 或 ≥3 件
- 邊長 > 40cm 的商品 + 超商取件 → **顯示警告建議改宅配**

### 付款方式
- **銀行轉帳**：付款帳號從 system_settings 讀取，24 小時付款期限，搭配付款核對表單
- **ECpay 信用卡**：後續整合（先預留 UI 位置）

### 預購機制
庫存不足時可預購：
- 商品卡標示「預購中」
- 結帳要選**合併出貨**（等齊）或**分開出貨**（現貨先出，運費仍只一次）

### 訊息系統（僅客製申請有）
- 客戶 ↔ 管理員 雙向對話
- **用戶在頁面**：SSE 即時推送新訊息，不發 email
- **用戶離開頁面**：發 email 通知，附連結回對話頁
- sender_type = `customer | admin`，UI 左右氣泡分

### 折扣三層機制（結帳套用優先序）
1. **promo_code**（公開折扣碼）有填 → 以 public_code 為準，**不套 auto_checkout**
2. **user_coupon_id**（持有券）有填 → 套持有券，**不套 auto_checkout**
3. 兩者皆 null → 自動套符合條件的 **auto_checkout**（取折扣最高）

券類型：
- `new_user`：新用戶歡迎券（驗證 email 後自動發）
- `spend_reward`：消費回饋（訂單完成後自動發）
- `returning_loyal`：回購忠誠券（管理員規則設定）
- `manual`：管理員手動發
- `auto_checkout`：自動套用促銷（不需 code）

### 報價 token 流程
```
管理員報價 → 寄 email 含 /custom/quote/:token 連結（24h TTL）
        ↓
客戶點連結 → /custom/quote/:token 頁（不需登入，token 即憑證）
        ↓ 三選一
   確認報價 → 客製結帳 → 建立訂單
   要求修改 → draft_revision 狀態，管理員重新出稿
   拒絕 → quote_rejected，可重新申請
   延長考慮 → +1 天（每筆 1 次）
```

Token 過期後 → 強制登入並導向 `/custom/requests/:id` 查看。

---

## 七、視覺與互動細節

### 商品卡片
- 封面圖（filled_template 風格的成品示意圖，4:5 直幅多）
- 商品名稱（思源宋體）
- 難易度標籤（小 chip）
- 價格區間（NT$397 ~ NT$860 — 最低變體 ~ 最高變體）
- 預購標示（若有 variant 為預購中）

### 商品詳情圖片輪播
- 封面圖 + product_images（多張）排在前
- 選定變體後**多顯示一張該變體的 filled_template.png**

### 規格選擇器
- 三層級依序：尺寸 → 難易度 → 細緻度
- 後續層級依前面選項過濾可用變體
- 無對應變體 → **灰色禁用**（不消失，讓客戶知道有但這組合沒做）
- 選完顯示：售價、預覽圖、庫存（現貨 X 件 / 預購中）

### 訂單詳情狀態條
水平 stepper：付款 → 備貨 → 出貨 → 完成。當前步驟強調，已完成步驟綠勾，未到淡灰。

### 客製訊息對談 UI
- 聊天氣泡：客戶右側木質棕，管理員左側米白
- 時間戳輕量
- 支援 markdown / 換行 / 連結
- 底部固定輸入框 + 送出
- SSE 連線時頁面右上小綠點「即時連線中」
- 系統訊息（如「歡迎」、「報價已送出」）置中淡灰

### Toast 通知
加購車成功、申請送出成功、Email 重發等用 toast，木質棕底白字。

### 表單錯誤
inline 顯示在欄位下方，土紅色 + 圖示，不用 alert。

---

## 八、給 Claude.ai 的指示模板

複製貼上這段給 Claude.ai 開頭：

```
我有一個數字油畫電商「易木 YIIMUI」要設計前端。
完整 brief 在這份文件裡（貼上整份 store_design_brief.md）。

請按以下順序出 mockup（HTML + Tailwind CSS，artifact 格式）：

第一輪 — 視覺定調：
1. 全站共用導覽列 + footer
2. 首頁 hero 區 + 最新上架橫向捲動列
3. 商品卡片元件（單張，3 個變體：現貨 / 預購 / 缺貨）
4. 訊息對談 UI 元件（聊天氣泡客戶 vs 管理員）

風格嚴格符合「日系雜貨鋪 / 紙感 / 木質暖棕」。
配色照 brief 第一節：主色 #8B6F47、背景 #F5EFE5、低飽和狀態色。
中文標題用思源宋體類字體。
不要過度裝飾、不要漸層、不要科技感。

每張 mockup 完成後我會 feedback，再修第二輪。

之後依序：商品列表 → 商品詳情 → 購物車 → 結帳 → 訂單頁
        → 客製申請列表 → 客製申請詳情（含訊息）→ 報價確認頁
        → 會員（個人資料 / 收件 / 折扣錢包）→ 註冊登入 → 資訊頁
```

---

## 九、回到我這（Claude Code）做什麼

設計確定後，把以下任一帶回我這個 terminal session：
- HTML + Tailwind code（artifact 整段複製）
- 截圖（PNG）

我會：
1. 翻成 Vue 3 SFC（套 admin codebase 已有的 Tailwind tokens：木質棕 / 紙感等已定義）
2. 串 backend 已實作的 API（前述全清單）
3. SSE 連線 / 上傳直傳 Firebase 等基礎設施
4. 部署 Vercel
5. push 到 yizhen-lili remote（Vercel 連的是 yizhen-lili 不是 origin — 這個我會處理）

---

## 十、已知技術前提

- Vue 3 + Vite（跟 admin 同套）
- TanStack Vue Query（資料快取）
- Tailwind CSS 4
- Vue Router
- httpOnly cookie JWT（7 天有效）
- Firebase Storage 直傳（client → signed PUT URL → Firebase）
- SSE（不用 WebSocket，輕量單向推播）
- ECpay 物流 webhook（後端 handle，前端不直接接觸）

我的 admin codebase 已有：
- 共用 UI primitives（Button、Card、Select、Input 等）
- 木質棕 / 米白等 Tailwind tokens 已配
- API fetcher pattern
- 路由 guard

設計時不必擔心這些底層，**專注視覺 + 互動**。
