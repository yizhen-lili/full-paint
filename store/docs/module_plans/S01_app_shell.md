# S01 — App Shell + 共用導覽 + 設計系統落地

> 後端對應：`backend/auth/`（`GET /auth/me`）、`backend/product/`（`GET /themes`）
> 規格來源：[docs/api.md](../../../docs/api.md)（模組一 + Store - Browse）、[docs/requirements/store_routes.md](../../../docs/requirements/store_routes.md)、[docs/store_design_brief.md](../../../docs/store_design_brief.md)
> 設計依據：[design_system.md](../design_system.md)
> SOP：[frontend_sop.md](../frontend_sop.md)（含「後端規格從原始碼查」§7）

---

## 1. 範圍

### 本模組做

1. **Vite 專案 scaffold** 在 `store/`，採用與 admin 同套技術棧
2. **設計系統落地** — `style.css` 套上 [design_system.md §3.4](../design_system.md) 完整 Tailwind 4 `@theme` token + Google Fonts 載入
3. **路由 scaffold** — 全部 22 條路由（[store_routes.md](../../../docs/requirements/store_routes.md)）建立檔案，page component 都是 placeholder，後續 S02–S10 各自填入
4. **共用 Layout 元件**：
   - `<DefaultLayout>` — header + main + footer（多數頁面用）
   - `<AuthLayout>` — 無 header、置中卡片（登入/註冊/忘記密碼/重設密碼/Email 驗證 5 頁用）
   - `<MinimalLayout>` — 僅 header + main（報價確認頁 token 流程用）
5. **共用元件**：
   - `<SiteHeader>` — sticky、三段式（左 nav / 中 logo / 右 actions）
   - `<SiteFooter>` — 4 column
   - `<MegaMenu>` — 商品 / 主題 hover 下拉。**主題列表接 `GET /themes` 實 API**（容錯處理 DB 主題不夠的情境，顯示「主題建設中」）；商品 mega-menu v1 寫死分類入口（依難易度 / 標籤主題 / 細緻度 3 個入口），後續 S02 完成後可改接 popular products
   - `<MobileMenu>` — < 1024 漢堡抽屜
   - `<SiteLogo>` — B1 純文字版（[design_system.md §1.5](../design_system.md)）
   - `<NotFoundPage>` — 404
6. **App Boot 流程** — 啟動時呼叫 `GET /auth/me` 嘗試讀取登入狀態（401 沒事，靜默處理；200 寫入 `useAuthStore`）
7. **401 全域攔截** — 任何受 auth 保護的 API 回 401 → 清 store + 重導 `/login?redirect=<原路徑>`
8. **路由 guard** — 標 `requiresAuth: true` 的路由未登入時重導
9. **基礎 Pinia store** — `useAuthStore`（user、role、isLoggedIn）
10. **API client** — openapi-fetch + `/api/v1` base + `credentials: 'include'`（同 admin）

### 本模組不做

- 認證頁面內容（LoginPage / RegisterPage / ForgotPasswordPage / ResetPasswordPage / VerifyEmailPage） → 留 placeholder，**屬 S04**
- 商品 / 訂單 / 客製 / 會員中心 / 資訊頁內容 → 留 placeholder，屬 S02–S10
- Dashboard / 個人中心首頁設計 → 屬 S09
- 暗色模式（[design_system.md §11](../design_system.md) 已決議 v1 不做）
- 多語系（brief 已決議先做繁中）
- SEO meta 動態化（v1 用靜態 meta，動態化在後續模組補）
- PWA / 離線模式

---

## 2. 路由清單

依據 [docs/requirements/store_routes.md](../../../docs/requirements/store_routes.md)，全部 22 條。

| Path | Component | Layout | Guard | 模組 |
|---|---|---|---|---|
| `/` | `HomePage` (placeholder) | DefaultLayout | — | S02 |
| `/products` | `ProductListPage` (ph) | DefaultLayout | — | S02 |
| `/products/:id` | `ProductDetailPage` (ph) | DefaultLayout | — | S02 |
| `/search` | `SearchPage` (ph) | DefaultLayout | — | S02 |
| `/cart` | `CartPage` (ph) | DefaultLayout | requiresAuth | S05 |
| `/checkout` | `CheckoutPage` (ph) | DefaultLayout | requiresAuth | S05 |
| `/checkout/complete` | `CheckoutCompletePage` (ph) | DefaultLayout | requiresAuth | S05 |
| `/orders` | `OrderListPage` (ph) | DefaultLayout | requiresAuth | S06 |
| `/orders/:id` | `OrderDetailPage` (ph) | DefaultLayout | requiresAuth | S06 |
| `/custom` | `CustomPage` (ph) | DefaultLayout | — | S07 |
| `/custom/requests` | `CustomRequestListPage` (ph) | DefaultLayout | requiresAuth | S07 |
| `/custom/requests/:id` | `CustomRequestDetailPage` (ph) | DefaultLayout | requiresAuth | S07 |
| `/custom/quote/:token` | `QuotePage` (ph) | MinimalLayout | — (token 即憑證) | S08 |
| `/profile` | `ProfilePage` (ph) | DefaultLayout | requiresAuth | S09 |
| `/profile/shipping` | `ShippingProfilesPage` (ph) | DefaultLayout | requiresAuth | S09 |
| `/profile/coupons` | `CouponsPage` (ph) | DefaultLayout | requiresAuth | S09 |
| `/register` | `RegisterPage` (ph) | AuthLayout | guestOnly | S04 |
| `/login` | `LoginPage` (ph) | AuthLayout | guestOnly | S04 |
| `/forgot-password` | `ForgotPasswordPage` (ph) | AuthLayout | guestOnly | S04 |
| `/reset-password/:token` | `ResetPasswordPage` (ph) | AuthLayout | — | S04 |
| `/verify-email/:token` | `VerifyEmailPage` (ph) | AuthLayout | — | S04 |
| `/size-guide` | `SizeGuidePage` (ph) | DefaultLayout | — | S10 |
| `/shipping-info` | `ShippingInfoPage` (ph) | DefaultLayout | — | S10 |
| `/custom-process` | `CustomProcessPage` (ph) | DefaultLayout | — | S10 |
| `/pricing` | `PricingPage` (ph) | DefaultLayout | — | S10 |
| `/refund-policy` | `RefundPolicyPage` (ph) | DefaultLayout | — | S10 |
| `*` (未匹配) | `NotFoundPage` | DefaultLayout | — | S01 |

### Guard 規則（`app/router.ts`）

1. 路由 meta 標 `requiresAuth: true` → 未登入重導 `/login?redirect=<原路徑>`
2. 路由 meta 標 `guestOnly: true`（登入頁 / 註冊頁 / 忘記密碼）→ 已登入時重導 `/`
3. App boot 時先呼叫 `GET /auth/me`：
   - 200 → 寫入 store、放行
   - 401 → 不寫 store（訪客模式），訪問 `requiresAuth` 頁面再觸發 redirect
4. `quote_token` 路由（`/custom/quote/:token`）— 不需登入，token 即憑證；token 無效 / 過期由 S08 該頁自己處理（顯示「請登入查看」+ redirect `/login`）

---

## 3. 後端 API 對應

從 [docs/api.md](../../../docs/api.md) 與 [backend/auth/router.py](../../../backend/auth/router.py)、[backend/product/router.py](../../../backend/product/router.py) 逐條核對。

| Endpoint | 用於 | Request | Response 200 | 4xx |
|---|---|---|---|---|
| `GET /api/v1/auth/me` | App boot + guard 觸發 | — | `{ id: UUID, name: str, email: str, pending_email: str\|null, role: str, gender: str\|null, birthday: date\|null }` | 401 未登入 / cookie 失效 |
| `GET /api/v1/themes` | MegaMenu 主題下拉資料源 | — | `{ items: [{ id: UUID, name: str, description: str\|null, cover_image_url: str\|null, sort_order: int, series_count: int, product_count: int }] }` | — |

### 規格來源

**`GET /auth/me`**：
- [docs/api.md:70-75](../../../docs/api.md#L70-L75)
- [backend/auth/router.py:53-55](../../../backend/auth/router.py#L53-L55)
- [backend/auth/schemas/response.py:13-22](../../../backend/auth/schemas/response.py#L13-L22) — `MeResponse`

**`GET /themes`**：
- [docs/api.md:282-294](../../../docs/api.md#L282-L294)
- [backend/product/router.py:115-118](../../../backend/product/router.py#L115-L118)
- 實作於 `service.public_list_themes(db)`，回 `PublicThemeListResponse`

**Cookie 設定**（[backend/auth/router.py:21-29](../../../backend/auth/router.py#L21-L29)）：
- key: `access_token`
- httponly: True
- samesite: `lax`
- secure: True
- max_age: customer 7 天 / admin 8 小時（store 用客戶版）
- 前端 client 要設 `credentials: 'include'`（同 admin）

**錯誤格式**（[docs/api.md:29-32](../../../docs/api.md#L29-L32)）：
```json
{ "detail": "中文錯誤描述" }
```

---

## 4. 元件樹

### Layouts

```
src/shared/layouts/
├── DefaultLayout.vue          # SiteHeader + <RouterView /> + SiteFooter
├── AuthLayout.vue             # 無 header，置中 hero（logo + form），simple footer
└── MinimalLayout.vue          # SiteHeader (簡化版) + <RouterView />，無 footer（quote token 頁用）
```

### Shared Components

```
src/shared/components/
├── SiteHeader.vue             # sticky、三段式 grid
├── SiteFooter.vue             # 4 column
├── SiteLogo.vue               # B1 純文字版 logo（design_system §1.5）
├── MegaMenu.vue               # 商品 / 主題 hover 下拉（v1 寫死，後續接 API）
├── MobileMenu.vue             # < 1024 漢堡抽屜
├── IconButton.vue             # header 圖示按鈕（搜尋 / 會員 / 購物車）
├── PageHeader.vue             # 每個內頁頂部：eyebrow + title + section-link slot
└── NotFoundPage.vue           # 404
```

### Shared UI primitives（從 admin/shared/ui/ 複製，調整 token 引用）

```
src/shared/ui/
├── Button.vue                 # primary / outline / link / danger 4 變體
├── Input.vue
├── Select.vue
├── Card.vue
├── Badge.vue                  # status badge
├── Spinner.vue
├── Toast.vue                  # 木質栗底白字
└── ...                        # 後續模組需要再補
```

### Features 雛形（placeholder pages）

```
src/features/
├── home/pages/HomePage.vue                          # placeholder「易木 YIIMUI 首頁建設中」
├── products/pages/ProductListPage.vue               # placeholder
├── products/pages/ProductDetailPage.vue             # placeholder
├── search/pages/SearchPage.vue                      # placeholder
├── cart/pages/CartPage.vue                          # placeholder
├── checkout/pages/CheckoutPage.vue                  # placeholder
├── checkout/pages/CheckoutCompletePage.vue          # placeholder
├── orders/pages/OrderListPage.vue                   # placeholder
├── orders/pages/OrderDetailPage.vue                 # placeholder
├── custom/pages/CustomPage.vue                      # placeholder
├── custom/pages/CustomRequestListPage.vue           # placeholder
├── custom/pages/CustomRequestDetailPage.vue         # placeholder
├── custom/pages/QuotePage.vue                       # placeholder（用 MinimalLayout）
├── profile/pages/ProfilePage.vue                    # placeholder
├── profile/pages/ShippingProfilesPage.vue           # placeholder
├── profile/pages/CouponsPage.vue                    # placeholder
├── auth/pages/RegisterPage.vue                      # placeholder
├── auth/pages/LoginPage.vue                         # placeholder
├── auth/pages/ForgotPasswordPage.vue                # placeholder
├── auth/pages/ResetPasswordPage.vue                 # placeholder
├── auth/pages/VerifyEmailPage.vue                   # placeholder
├── auth/store.ts                                    # useAuthStore（Pinia）
├── auth/api.ts                                      # fetchMe()、logout()
├── auth/guards.ts                                   # requiresAuth / guestOnly
└── pages/                                           # 靜態頁
    ├── SizeGuidePage.vue
    ├── ShippingInfoPage.vue
    ├── CustomProcessPage.vue
    ├── PricingPage.vue
    └── RefundPolicyPage.vue
```

---

## 5. 狀態 / Pinia Store

### `useAuthStore` (`features/auth/store.ts`)

```ts
interface AuthState {
  user: MeResponse | null   // 從 GET /auth/me 取得
  bootstrapped: boolean     // App boot 完成後標 true（避免 race）
}

// Getters
get isLoggedIn(): boolean
get isCustomer(): boolean   // user?.role === 'customer'

// Actions
async fetchMe(): Promise<void>      // 呼叫 GET /auth/me
async logout(): Promise<void>       // 呼叫 POST /auth/logout（S04 才實作 button；S01 只放 method）
clear(): void                       // 清 user + bootstrapped=true
```

### TanStack Query keys

| Key | 對應 endpoint | 用於 | Stale time |
|---|---|---|---|
| `['public', 'themes']` | `GET /themes` | MegaMenu 主題下拉 | 10 分鐘（主題不常變） |

其他資料（商品 / 訂單 / 客製等）query keys 在後續模組規劃。

---

## 6. App Boot 流程

```
main.ts
  → createApp
  → use(pinia)
  → use(VueQueryPlugin)
  → use(router)
  → router.beforeEach(authGuard)   // 但先不 navigate，等 boot
  → await useAuthStore().fetchMe() // 不 throw，401 視為訪客
  → app.mount('#app')
```

`fetchMe()` 內部處理：
- 200：寫 user 進 store、`bootstrapped = true`
- 401：`clear()`、`bootstrapped = true`（訪客模式）
- 其他錯誤：`bootstrapped = true`、丟 console.warn（避免初始載入失敗讓整站卡住）

---

## 7. 設計決策（引用 design_system.md）

### 字體
- `style.css` 載入 4 套 Google Fonts（Cormorant Garamond / Noto Serif TC / Noto Sans TC / Manrope / JetBrains Mono），weight 與 [design_system.md §2](../design_system.md) 一致
- body default：Manrope 300 + Noto Sans TC 300，font-size 15px、line-height 1.85

### 色票
- Tailwind v4 `@theme` 注入 [design_system.md §3.4](../design_system.md) 完整 token
- 整頁底色 `--color-paper-canvas` `#F5F1E8`
- **不放紙紋 noise**（admin 才有）

### Logo
- `<SiteLogo>` 純文字版（[design_system.md §1.5](../design_system.md)）
- header 用 22px / footer 暗底用 22px（換淡米白色）/ hero 用 44px

### Layout 結構
- `<DefaultLayout>` 結構：
  ```
  <SiteHeader />
  <main><RouterView /></main>
  <SiteFooter />
  ```
- max-width 1440px、page padding 桌面 56–64px / mobile 24px
- Section padding 96px（hero 96–120px）

### 動效
- 頁面切換 fade-in 180ms
- header backdrop-blur 12px
- 圖示按鈕 hover 變 paper-deep 背景
- 不放 hover scale > 1.05

### 響應式 breakpoints（沿用 admin）
- `< 768px` mobile：商品 grid 1 col、page padding 24px、header 漢堡選單
- `768–1023px` tablet：商品 grid 2 col、header 仍漢堡
- `≥ 1024px` desktop：完整三段式 header、商品 grid 3 col
- `≥ 1280px` large：商品 grid 4 col、page padding 56px

---

## 8. Vite 專案 scaffold 清單

### `package.json` dependencies（與 admin 同步版本）

```json
{
  "dependencies": {
    "@tanstack/vue-query": "^5.100.5",
    "@vee-validate/zod": "^4.15.1",
    "@vueuse/core": "^14.2.1",
    "dayjs": "^1.11.20",
    "lucide-vue-next": "^1.0.0",
    "openapi-fetch": "^0.17.0",
    "pinia": "^3.0.4",
    "vee-validate": "^4.15.1",
    "vue": "^3.5.32",
    "vue-router": "^4.6.4",
    "zod": "^4.3.6"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.2.4",
    "@vitejs/plugin-vue": "^6.0.6",
    "@vue/tsconfig": "^0.9.1",
    "openapi-typescript": "^7.13.0",
    "tailwindcss": "^4.2.4",
    "typescript": "~6.0.2",
    "vite": "^8.0.10",
    "vue-tsc": "^3.2.7"
  },
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "preview": "vite preview",
    "gen:api": "openapi-typescript http://localhost:8001/openapi.json -o src/api/schema.ts",
    "type-check": "vue-tsc --noEmit"
  }
}
```

### `vite.config.ts`

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5174,                        // 避開 admin 5173
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
})
```

### `src/api/client.ts`

```ts
import createClient from 'openapi-fetch'
import type { paths } from './schema.ts'

export const api = createClient<paths>({
  baseUrl: '/api/v1',
  credentials: 'include',
})
```

### 目錄結構（建置完）

```
store/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vercel.json                 # 部署 SPA fallback
├── public/
│   └── favicon.ico             # 暫用 admin 同款，後續 S01 結束前換
├── docs/                       # 已建立
│   ├── design_system.md
│   ├── frontend_sop.md
│   └── module_plans/
└── src/
    ├── App.vue
    ├── main.ts
    ├── style.css               # @theme + base reset
    ├── api/
    │   ├── client.ts
    │   └── schema.ts           # gen:api 產生
    ├── app/
    │   ├── pinia.ts
    │   ├── query.ts
    │   └── router.ts
    ├── shared/
    │   ├── layouts/
    │   ├── components/
    │   └── ui/
    └── features/
        ├── auth/
        ├── home/
        ├── products/
        ├── search/
        ├── cart/
        ├── checkout/
        ├── orders/
        ├── custom/
        ├── profile/
        └── pages/
```

---

## 9. 手動驗收清單

每條都要用 chrome-devtools 跑過 + 截圖 + console.error / console.warn 為 0。

### A. 設計系統落地
- [ ] 開首頁 `/`，placeholder 顯示「易木 YIIMUI · 首頁建設中」中文 Noto Serif TC 主標
- [ ] 字體載入無 FOIT 跳動（用 `document.fonts.ready` 驗證）
- [ ] 整頁底色 `#F5F1E8`、無紙紋 noise
- [ ] Logo 顯示正確：header 22px / 副行 small caps「PAINT BY NUMBER ATELIER」

### B. Header / Footer
- [ ] Header sticky on scroll、半透明 + backdrop-blur
- [ ] 導覽（商品 / 主題 / 客製 / 尺寸指南）hover 變栗色
- [ ] Header 三圖示按鈕（搜尋 / 會員 / 購物車）hover 變 paper-deep 底
- [ ] Footer 4 column 顯示完整、版權行 + email 對齊
- [ ] Footer email 連結 mailto

### C. 路由 + Guard
- [ ] `/` 正常顯示
- [ ] 訪問 `/cart` 未登入 → 重導 `/login?redirect=/cart`（即使 LoginPage 是 placeholder 也要看到 URL 變化）
- [ ] 訪問 `/profile` 未登入 → 重導 `/login?redirect=/profile`
- [ ] 訪問 `/login` 已登入時 → 重導 `/`
- [ ] 訪問 `/aaa-not-exist` → 顯示 NotFoundPage（不是白屏）
- [ ] `/custom/quote/:token` 不需登入也能進入（S08 placeholder 顯示）

### D. App Boot
- [ ] 首次載入呼叫 `GET /auth/me`，未登入 401 不噴錯給使用者（console 也不要錯）
- [ ] 已登入用戶 reload 頁面 → store 正確重建（從 cookie 還原 user）
- [ ] DevTools Network 看 `/api/v1/auth/me` 帶 cookie

### E. 401 攔截
- [ ] 手動清 cookie 後在已登入狀態的 page 觸發 API → 自動重導 `/login`

### F. Mobile (< 768)
- [ ] Header 縮為漢堡 + logo + 購物車三段
- [ ] 點漢堡開啟 MobileMenu 抽屜
- [ ] page padding 縮為 24px
- [ ] Footer 4 column 縮成單欄

### G. Tablet (768–1023)
- [ ] Header 仍是漢堡（不是三欄）
- [ ] page padding 32–40px

### H. Desktop (≥ 1024)
- [ ] Header 三段式完整顯示
- [ ] 主題 / 商品 mega-menu hover 展開（v1 內容寫死）

### I. 開發品質
- [ ] `pnpm type-check` 0 錯
- [ ] `pnpm build` 0 error / 0 warning
- [ ] Lighthouse Accessibility（首頁）≥ 90

---

## 10. 已解決決議（從原 ⚠️）

| # | 原問題 | 結論 |
|---|--------|------|
| **A** | Mega-menu 主題資料源 | 接 `GET /themes` 實 API（不寫死）。DB 主題不夠時 UI 容錯：items=0 顯示「主題建設中，敬請期待」字樣；items < 3 時不展開 mega-menu，僅單一連結到 `/themes` 列表頁 |
| **B** | NotFoundPage 內容 | 簡單版（lucide icon `package-x` 24px ink-muted + 文字「找不到這頁」+ 「回首頁」button），沿用 admin F01 樣式 |
| **C** | Favicon | 32×32 SVG「易」字（`Noto Serif TC` weight 400 size 24，bg `--color-paper-canvas`，文字 `--color-ink-strong`），由 Claude 直接做進 `public/favicon.svg` |
| **D** | shared/ui 來源 | 從 admin 複製一份到 `store/src/shared/ui/`，store 獨立演化；不引入 monorepo 共用 package |
| **E** | Vercel 部署 | monorepo 同 yizhen-lili remote、store/ 為獨立 Vercel project（root dir 設 `store/`、build cmd `pnpm build`、output dir `dist`）。**首次 deploy 時機**：S01 全部完成（含本地驗收）後一次性 deploy，不每階段 deploy。|

---

## 11. 完成標準

1. `pnpm type-check` 0 錯
2. `pnpm build` 0 error / 0 warning
3. 手動驗收（§9）每條 ✓ + chrome-devtools 截圖貼回對話
4. Console 0 error / 0 warn
5. Network `/auth/me` 200 (登入時) / 401 (訪客) 都正確
6. 設計風格與 [design_system.md](../design_system.md) 一致（人工肉眼比對）
7. Lighthouse Accessibility（首頁）≥ 90
8. reviewer pass、git commit `feat(store/app-shell): 完成 S01 - App Shell + 共用導覽`
