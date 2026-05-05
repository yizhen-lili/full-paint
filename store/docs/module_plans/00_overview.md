# Store 前端 — 模組總覽

> 對應 [docs/store_design_brief.md](../../../docs/store_design_brief.md) 的 30 個頁面，切成 10 個可獨立開發驗收的模組。
> 每個模組走完整 SOP（規劃書 → 規格比對 → 寫 code → 手動驗收 → reviewer pass → commit），參照 [admin/docs/frontend_sop.md](../../../admin/docs/frontend_sop.md)。
> 設計系統見 [design_system.md](../design_system.md)，**所有模組沿用，不重新發明**。

---

## 模組切分

| # | 模組 | 包含 brief 頁面 | 依賴 |
|---|------|----------------|------|
| **S01** | App Shell + 共用導覽 + 設計系統落地 | #30 共用導覽 / footer / mega-menu | — |
| **S02** | 商品瀏覽（P0 主軸） | #1 首頁 / #2 商品列表 / #3 搜尋 / #4 商品詳情 | S01 |
| **S03** | 主題與系列瀏覽（P0+ 差異化） | #4a 主題列表 / #4b 主題詳情 / #4c 系列詳情 | S01, S02（商品卡） |
| **S04** | 會員認證 | #17 註冊 / #18 登入 / #19 忘記密碼 / #20 重設密碼 / #21 Email 驗證 | S01 |
| **S05** | 購物車 + 結帳 | #5 購物車 / #6 結帳 / #7 完成頁 | S04 |
| **S06** | 訂單管理 | #8 訂單列表 / #9 訂單詳情 / #10 付款核對表單 | S05 |
| **S07** | 客製申請（會員端） | #11 客製服務頁 / #12 申請表單 / #13 申請列表 / #14 詳情+訊息+SSE | S04 |
| **S08** | 報價確認頁（token） | #15 報價確認 / #16 客製結帳 | S07 |
| **S09** | 會員中心 | #22 個人資料 / #23 收件資料 / #24 折扣券錢包 | S04 |
| **S10** | 資訊頁 | #25–29 尺寸指南 / 出貨 / 訂製流程 / 報價參考 / 退款政策 | S01 |

---

## 落地順序

```
S01 → S02 → S04 → S05 → S06 → S07 → S08 → S03 → S09 → S10
```

### 順序理由
- **S01 先**：整站設計系統、字體、Token、共用導覽、Layout 基礎建設都在這裡。沒有 shell 後面寫不了。
- **S02 第二**：商品流程是電商主場、視覺定型在這個模組（商品卡、規格選擇器、列表篩選、搜尋）。先做完商品瀏覽，後面所有模組才有商品卡可用。
- **S04 第三**：購物車、訂單、客製申請都需登入才能進，認證必先解鎖。S03 不需登入但可以延後（backend public endpoint 還在補）。
- **S05 → S06 → S07 → S08**：購物車 → 訂單 → 客製 → 報價 token，依業務流程串接。
- **S03 在中後段**：等 backend 補 4 個 public endpoint（`/themes`, `/themes/:id`, `/series`, `/series/:id`）。先做 S02 已經能 cover P0 商品瀏覽。
- **S09 / S10 最後**：會員中心、靜態頁，相對單純、不阻塞主流程。

---

## 各模組「完成」標準（Definition of Done）

每個模組 done 的 7 條（沿用 admin SOP）：

1. **TypeScript 0 錯**：`pnpm type-check` 通過
2. **Build 成功**：`pnpm build` 無 error / warning
3. **手動驗收**：規劃書中每條 happy path / 錯誤情境，用 chrome-devtools 截圖驗證
4. **Console 乾淨**：`list_console_messages` 無 error / warn
5. **Network 正常**：登入 / 主要 API 200，無未預期 401 / 500
6. **設計風格一致**：跨頁面比對，色票、間距、字體統一（依 [design_system.md](../design_system.md)）
7. **a11y**：重要頁面 Lighthouse Accessibility ≥ 90
8. **reviewer pass**：呼叫 `/reviewer`，無「必須修正」項目

未達成以上前不得宣告完成、不得 commit、不得切下一個模組。

---

## 各模組重點

### S01 App Shell + 共用導覽 + 設計系統落地

**目標**：建立 store/ Vite 專案、套上 design_system 的 token、做共用導覽列 + footer + mega-menu。

**重點**：
- Vite + Vue3 + TS + Tailwind 4 + Pinia + TanStack Query + openapi-fetch + VeeValidate + Zod（與 admin 同套）
- `style.css` 套 design_system.md 的 `@theme` 完整 token
- Google Fonts 載入（Cormorant + Noto Serif TC + Manrope + JetBrains Mono）
- Site Header 三段式：左 nav / 中 logo / 右 actions（搜尋 / 會員 / 購物車）
- Mega-menu hover 顯示主題下拉
- Footer 4 column（Shop / Service / Account + Brand）
- 路由 guard 雛形（auth required pages 預留）
- 跨頁面 layout 元件 `<DefaultLayout>` / `<AuthLayout>`

**API**：`GET /auth/me`（檢查登入狀態用）

**手動驗收**：
- [ ] 首頁 hero 顯示，字體載入無 FOIT 跳動
- [ ] 導覽列 sticky on scroll
- [ ] Mega-menu hover 展開
- [ ] Footer 顯示完整
- [ ] 響應式 mobile 漢堡抽屜可開
- [ ] Console 0 error / 0 warn

### S02 商品瀏覽

**目標**：首頁 + 商品列表 + 搜尋 + 商品詳情，4 個頁面。

**重點**：
- 商品卡風格鎖定（[design_system.md §8](../design_system.md#product-card)）
- 規格選擇器三層級（尺寸 → 難易度 → 細緻度，無對應變體灰階禁用）
- URL query 支援（`?theme_id=&series_id=&difficulty=&detail=&canvas_size=&tag_id=&sort=&page=`）
- 商品詳情圖片輪播（封面 + product_images + 選定變體 filled_template）
- 加入購物車 toast
- 4 區商品說明摺疊（畫具內容 / 畫布材質 / 使用建議 / 注意事項）
- 「想要不同規格？」展開客製規格表單

**API**：`GET /products`、`/products/search`、`/products/:id`、`/products/:id/related`、`/tags`

### S03 主題與系列瀏覽

**目標**：主題列表 + 主題詳情 + 系列詳情。

**重點**：
- 等 backend 補 `GET /themes` / `/themes/:id` / `/series` / `/series/:id` 四個 public endpoint 才開工
- 主題卡 1.3:1 + 暗 overlay + 中文襯線標題
- 主題詳情 hero + 系列卡片 + 「該主題全部商品」CTA
- 系列詳情按 series_order 排序

### S04 會員認證

**目標**：5 個認證頁 + 路由 guard 強化。

**重點**：
- httpOnly cookie JWT、登入後重導回原頁
- Zod schema 表單驗證（密碼 ≥ 10 碼英數混合等）
- Email 驗證 token 點擊自動驗證 → 跳登入 → 自動發新用戶歡迎券
- 忘記密碼 token TTL 1h
- 路由 guard：未登入訪問 protected route 跳 `/login?redirect=...`

**API**：`POST /auth/register`、`/auth/login`、`/auth/logout`、`GET /auth/me`、`/auth/verify-email`、`/auth/resend-verification`、`/auth/forgot-password`、`/auth/reset-password`

### S05 購物車 + 結帳

**目標**：購物車 + 結帳 + 完成頁。

**重點**：
- 折扣三層機制（promo_code 優先 > user_coupon > auto_checkout 後台規則）
- 預購拆單提示（現貨 X 件 + 預購 Y 件）
- 免運進度條（NT$800 或 ≥3 件）
- 超商選店 popup（第三方地圖 + iframe 降級）
- 大尺寸警告（>40cm 邊長 + 超商 → 建議改宅配）
- 預購出貨偏好（合併 / 分開）
- 完成頁顯示付款帳號 + 24 小時付款期限倒數

**API**：`/cart/*`、`/cart/checkout-preview`、`POST /orders`、`GET /system-settings/public`

### S06 訂單管理

**目標**：訂單列表 + 訂單詳情 + 付款核對表單。

**重點**：
- 訂單列表三 tab（未付款 / 出貨中 / 已完成）
- 詳情：訂單資訊、生產進度 stepper、退款確認區塊、取消按鈕
- 付款核對表單（轉帳金額 / 日期 / 時間 / 帳號末五碼 / 截圖上傳）
- 確認收貨 / 確認退款按鈕
- 上傳走 Firebase signed URL

**API**：`/orders/*`、`/orders/:id/payment-submission`、`/orders/:id/confirm-received`、`/orders/:id/confirm-refund`、`/orders/:id/cancel`、`POST /upload/payment-screenshot`

### S07 客製申請

**目標**：客製服務頁 + 申請表單 + 申請列表 + 詳情（含 SSE 訊息）。

**重點**：
- 訪客可填表單，sessionStorage 暫存 → 送出時跳 `/login?redirect=resubmit-custom` → 登入後自動送出
- 上傳照片走 Firebase signed URL
- 詳情頁 SSE 連線（`/custom-requests/:id/sse`）
- 訊息對談氣泡（客戶右木質棕 / 管理員左米白）
- 離開頁面切換 email 通知（SSE 斷開）
- quote_pending 狀態可改照片 / 規格

**API**：`POST /custom-requests`、`GET /custom-requests`、`/custom-requests/:id`、`/custom-requests/:id/messages`、`PATCH /custom-requests/:id/photo`、`GET /custom-requests/:id/sse`、`POST /upload/custom-photo`

### S08 報價確認頁（token）

**目標**：報價確認頁 + 客製結帳。

**重點**：
- token 認證、不需登入
- 報價有效期限倒數（24h / 延後 48h）
- 三按鈕：確認 / 要求修改（draft_revision，限 3 次）/ 拒絕；額外延長一次
- 客製結帳：報價金額固定、不支援折扣
- token 過期 → 強制登入 → 導向 `/custom/requests/:id`

**API**：`GET /custom/quote/:token`、`/custom/quote/:token/confirm`、`/reject`、`/extend`、`/request-revision`

### S09 會員中心

**目標**：個人資料 + 收件資料 + 折扣券錢包。

**重點**：
- 個人資料 CRUD（姓名 / Email / 性別 / 生日 / 改密碼）
- Email 改 = 寄重驗證信、新 email 暫存 pending_email
- 收件資料多筆 CRUD（宅配 / 超商兩型 + 預設）
- 折扣券錢包：可用 / 已使用 / 已過期三類

**API**：`PATCH /users/me`、`/users/me/change-password`、`/users/me/request-email-change`、`/users/me/shipping-profiles/*`、`/users/me/coupons`

### S10 資訊頁

**目標**：5 個靜態頁 + 共用 Markdown 渲染元件。

**重點**：
- `GET /pages/:slug` 取後台編輯的 Markdown 內容
- 共用 `<MarkdownPage>` 元件
- 5 個 slug：size_guide、shipping、custom_process、pricing_reference、refund_policy
- SEO meta 完整

**API**：`GET /pages/:slug`

---

## 風險點

| 風險 | 影響模組 | 解法 |
|------|---------|------|
| backend `/themes` `/series` public endpoint 還沒補 | S03 | S03 排到 S08 之後，給後端足夠時間 |
| SSE 連線在 Vercel serverless 環境表現未知 | S07 | S07 開工前確認 Vercel SSE 支援度，否則 fallback long polling |
| Firebase signed URL 簽發機制 | S06、S07 | 已驗證 admin 的 upload pattern，store 沿用 |
| 超商選店第三方地圖 popup mobile 體驗 | S05 | 行動裝置 fallback iframe；S05 規劃書詳列 |
| ECpay 物流 webhook 對前端訂單詳情即時更新 | S06 | 後端 stub 中，前端 polling fallback；之後 webhook 通了改 SSE |

---

## 模組完成後 git commit 格式

```
feat(store/<module>): 完成 SXX - <模組名稱>
```

例如：`feat(store/auth): 完成 S04 - 會員認證`
