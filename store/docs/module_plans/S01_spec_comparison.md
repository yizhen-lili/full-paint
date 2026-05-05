# 規格比對報告 — S01 App Shell + 共用導覽 + 設計系統落地

> 配對 [S01_app_shell.md](S01_app_shell.md) 規劃書與所有規格來源逐項比對。任何 ⚠️ 必須先解決才能進入下一階段（scaffold）。

---

## 1. api.md 端點比對

| Endpoint | api.md 規定 | backend 實際 | 規劃書對應 | 結果 |
|---|---|---|---|---|
| `GET /auth/me` | 權限 auth；res 200 `{id, name, email, pending_email, role, gender, birthday}`；401 未登入 | [router.py:53-55](../../../backend/auth/router.py#L53-L55)、[response.py:13-22](../../../backend/auth/schemas/response.py#L13-L22) `MeResponse`；`require_auth` dep 失敗回 401 | §3 完整列出；§5 `useAuthStore.fetchMe()`；§6 App boot 流程（401 視為訪客）；§9 case D + E 涵蓋 200 reload + 401 攔截 | ✓ |
| `GET /themes` | 權限 public；res 200 `{ items: [{id, name, description, cover_image_url, sort_order, series_count, product_count}] }` | [router.py:115-118](../../../backend/product/router.py#L115-L118) `store_list_themes`；回 `PublicThemeListResponse` | §3 完整列出；§4 `<MegaMenu>` 元件；§5 TanStack Query key `['public', 'themes']` stale 10 分鐘；§9 case H 涵蓋 mega-menu hover 展開 | ✓ |

**Cookie / 認證機制核對**：
- backend [router.py:21-29](../../../backend/auth/router.py#L21-L29) cookie key `access_token`、httponly、samesite lax、secure True、max_age 7 天
- 規劃書 §3 完整列出 cookie 細節，§8 client.ts 設 `credentials: 'include'`
- 結果：✓

**錯誤格式核對**（[docs/api.md:29-32](../../../docs/api.md#L29-L32)）：
- 統一 `{ "detail": "中文錯誤描述" }`
- 規劃書 §6 App boot 401 處理（不噴使用者錯）；§9 case E 401 全域攔截
- 結果：✓

---

## 2. requirements/store_routes.md 路由比對

| 路由（store_routes.md）| Component | 需登入 | 規劃書對應 | 結果 |
|---|---|---|---|---|
| `/` | 首頁 | — | §2 第 1 列、HomePage placeholder | ✓ |
| `/products` | 商品列表 | — | §2 第 2 列、ProductListPage placeholder | ✓ |
| `/products/:id` | 商品詳情 | — | §2 第 3 列 | ✓ |
| `/search` | 搜尋結果 | — | §2 第 4 列 | ✓ |
| `/cart` | 購物車 | 是 | §2、guard `requiresAuth` | ✓ |
| `/checkout` | 結帳 | 是 | §2、guard `requiresAuth` | ✓ |
| `/checkout/complete` | 訂單建立完成 | 是 | §2、guard `requiresAuth` | ✓ |
| `/orders` | 訂單列表 | 是 | §2、guard `requiresAuth` | ✓ |
| `/orders/:id` | 訂單詳情 | 是 | §2、guard `requiresAuth` | ✓ |
| `/custom` | 客製服務頁 | — | §2、不需登入（store_routes.md 未標需登入）| ✓ |
| `/custom/requests` | 客製申請列表 | 是 | §2、guard `requiresAuth` | ✓ |
| `/custom/requests/:id` | 客製申請詳情 | 是 | §2、guard `requiresAuth` | ✓ |
| `/custom/quote/:token` | 報價確認頁 | **不需登入**（token 即憑證） | §2、MinimalLayout、無 guard | ✓ |
| `/profile` | 個人資料 | 是 | §2、guard `requiresAuth` | ✓ |
| `/profile/shipping` | 收件資料 | 是 | §2、guard `requiresAuth` | ✓ |
| `/profile/coupons` | 折扣券錢包 | 是 | §2、guard `requiresAuth` | ✓ |
| `/register` | 註冊 | — | §2、guard `guestOnly`、AuthLayout | ✓ |
| `/login` | 登入 | — | §2、guard `guestOnly`、AuthLayout | ✓ |
| `/forgot-password` | 忘記密碼 | — | §2、guard `guestOnly`、AuthLayout | ✓ |
| `/reset-password/:token` | 重設密碼 | — | §2、AuthLayout | ✓ |
| `/verify-email/:token` | Email 驗證 | — | §2、AuthLayout | ✓ |
| `/size-guide` | 尺寸指南 | — | §2 第 22 列 | ✓ |
| `/shipping-info` | 出貨流程 | — | §2 第 23 列 | ✓ |
| `/custom-process` | 訂製流程 | — | §2 第 24 列 | ✓ |
| `/pricing` | 報價參考 | — | §2 第 25 列 | ✓ |
| `/refund-policy` | 退款退貨政策 | — | §2 第 26 列 | ✓ |
| `*`（未匹配）| — | — | §2 NotFoundPage | ✓ |

**全部 26 條路由 + NotFound 已涵蓋。Token 過期處理特別注意**：
- store_routes.md L19 規定：「token 過期後改為強制登入並導向 `/custom/requests/:id`」
- 規劃書 §2 guard 規則 4 註明：S01 不處理（屬 S08），S01 路由配置允許 `/custom/quote/:token` 訪客進入
- 結果：✓（範圍切割正確）

---

## 3. store_design_brief.md #30 共用導覽 + Footer 比對

來源：[docs/store_design_brief.md:107](../../../docs/store_design_brief.md#L107)

| 規格要點 | 規劃書對應 | 結果 |
|---|---|---|
| 導覽列：商品列 / 主題 / 客製化商品 / 尺寸指南 | §1.5 列出（商品 / 主題 / 客製 / 尺寸指南）| ✓ |
| 🔍 搜尋按鈕 | §4 SiteHeader IconButton、§9 case B 驗收 | ✓ |
| 購物車（件數） | §4 SiteHeader IconButton；件數顯示由 S05 補（v1 顯示空）| ⚠️ 已標記範圍外 |
| 登入 or 會員下拉 | §4 SiteHeader 第三段 actions；登入按鈕 v1 連結 `/login`；會員下拉由 S04 補（v1 圖示按鈕）| ⚠️ 已標記範圍外 |
| 「商品列」「主題」可滑鼠 hover 顯示下拉 mega-menu（列出主要主題或熱門系列）| §4 MegaMenu；§1 範圍含主題 mega-menu 接 GET /themes、商品 mega-menu 寫死 3 入口（依難易度 / 標籤主題 / 細緻度）| ✓ |
| Footer：資訊頁連結 + 版權 | §4 SiteFooter；§9 case B 「Footer 4 column」+ 版權行 | ✓ |

**⚠️ 標記詳述**：
- **購物車件數**：S01 v1 顯示空（or「0」），S05 完成後接購物車 store；不算衝突，是合理的範圍切割
- **會員下拉**：S01 v1 顯示為連結到 `/login` 的圖示按鈕（已登入時用戶名 placeholder 顯示），S04 / S09 補完整下拉內容；不算衝突

**結論**：✓ 兩個 ⚠️ 都是範圍切割（後續模組補完），不是規格與規劃書衝突。

---

## 4. design_system.md 一致性比對

| 規則 | 來源（§）| 規劃書對應 | 結果 |
|---|---|---|---|
| 字體：Cormorant Garamond + Noto Serif TC + Manrope + JetBrains Mono | §2 | §7 設計決策第 1 點 + §8 style.css `@theme` 注入 | ✓ |
| 中文標題 weight 300、字距 0.04em | §2 字距/行距慣例 | §7 + §8 token | ✓ |
| 色票：米白 #F5F1E8 + 深栗 #7B5841 + 兩階線色 + 4 狀態色 | §3.4 完整 token | §7 + §8 完整 `@theme` 注入 | ✓ |
| 不放紙紋 noise（admin 才有） | §1 紀律 | §7 設計決策明寫「不放紙紋 noise」| ✓ |
| 大留白：page padding 56–64px / section padding 96px / hero 96–120px | §4 應用慣例 | §7 設計決策 + §9 case F/G/H 響應式驗證 | ✓ |
| 圓角：商品卡 0、按鈕 4px、modal 6px | §5 | shared/ui Button 4px、Card 待 S02 商品卡時鎖 0 | ✓ |
| 線條 1px 兩階：line-subtle 商品卡邊、line section 分線 | §5 | §8 token 兩階線色 | ✓ |
| Logo B1 純文字版 | §1.5 | §7 設計決策 + §4 `<SiteLogo>` 元件 | ✓ |
| 動效：fade only、商品卡 hover scale 1.03 + brightness 1.05 | §7 | §7 設計決策第 5 點；S01 不含商品卡，scale 規範由 S02 落實 | ✓ |
| Site Header 三段式（左 nav / 中 logo / 右 actions）| §8 元件原則 | §1.5 + §4 SiteHeader + §9 case H 桌面驗證 | ✓ |
| Footer 4 column | §8 | §1.5 + §4 SiteFooter | ✓ |
| 圖示：Lucide stroke 1.5 | §9 | §4 IconButton + 引入 lucide-vue-next | ✓ |
| 響應式 < 1024 漢堡抽屜、< 768 商品 grid 1 col | §12 | §7 RWD breakpoints + §9 case F/G | ✓ |
| 暗色模式 v1 不做 | §11 | §1 不做範圍明列 | ✓ |
| Lighthouse a11y ≥ 90 | §10 | §9 case I + §11 完成標準 | ✓ |
| 黑名單：紙紋 noise / 多色 accent / 大圓角 / hover scale > 1.05 | §14 | §7 + §8 全部遵守 | ✓ |

**全部 ✓，無 ⚠️。**

---

## 5. 手動測試覆蓋表

逐條對應規劃書 §9 的 9 大項驗收 case 到實作位置 / 驗證手段：

| Group | Case | 預期結果 | 驗證手段 | 對應規格來源 |
|---|---|---|---|---|
| A 設計系統 | A1 首頁 placeholder 顯示 Noto Serif TC 主標 | 中文標題用對字體、weight 300 | chrome screenshot + computed style | design_system §2 |
| | A2 字體無 FOIT 跳動 | document.fonts.ready resolved 後才 paint 主標 | evaluate_script | — |
| | A3 整頁底色 #F5F1E8、無 noise | computed background-color | chrome screenshot | design_system §3.1 + §1 紀律 |
| | A4 Logo 22px 主行 + 9px small caps 副行 | DOM 渲染正確 | chrome screenshot | design_system §1.5 |
| B Header/Footer | B1 Header sticky on scroll、半透明 + blur | scroll 100px 截圖檢查 | chrome scroll + screenshot | design_system §8 |
| | B2 導覽 hover 變栗色 | hover 觸發 + 截圖 | chrome hover + screenshot | design_system §3.2 |
| | B3 圖示按鈕 hover 變 paper-deep 底 | 同上 | chrome | design_system §8 IconButton |
| | B4 Footer 4 column 對齊 | screenshot 比對 | chrome | brief #30 + design_system §12 |
| | B5 Footer email 連結 mailto | href="mailto:..." | DOM check | brief #30 |
| C 路由+Guard | C1 / 顯示 | navigate 後渲染 | chrome | store_routes.md L7 |
| | C2 /cart 未登入 → 重導 /login?redirect=/cart | URL 變化 | chrome navigate | store_routes.md L11 + 規劃書 §2 guard 1 |
| | C3 /profile 未登入 → 重導 /login?redirect=/profile | 同上 | chrome | store_routes.md L20 |
| | C4 /login 已登入時 → 重導 / | 模擬 cookie + navigate | chrome + bypass cookie | 規劃書 §2 guard 2 |
| | C5 /aaa-not-exist → NotFoundPage | 不白屏 | chrome | 規劃書 §2 row 27 |
| | C6 /custom/quote/:token 訪客可進 | 不重導 | chrome | store_routes.md L19 |
| D App Boot | D1 首載呼叫 GET /auth/me | network panel 看 request | chrome network | 規劃書 §6 |
| | D2 401 不噴錯 | console 0 error | chrome console | 規劃書 §6 + design_system §1 紀律 |
| | D3 已登入 reload → store 重建 | F5 後 store 仍有 user | chrome reload + Vue devtools | 規劃書 §5 |
| | D4 cookie 帶到 /auth/me | request headers 含 cookie | chrome network | api.md cookie 規格 |
| E 401 攔截 | E1 清 cookie 後 API 401 → 重導 /login | 模擬 + 觀察 URL | chrome devtools 清 cookie | 規劃書 §1.7 |
| F Mobile <768 | F1 Header 漢堡 | viewport 375 截圖 | chrome resize | design_system §12 |
| | F2 漢堡開抽屜 | 點擊後抽屜出現 | chrome click | 規劃書 §1 MobileMenu |
| | F3 page padding 24px | computed style | chrome devtools | design_system §4 |
| | F4 Footer 縮單欄 | screenshot | chrome | design_system §12 |
| G Tablet 768-1023 | G1 Header 仍漢堡 | viewport 800 截圖 | chrome resize | design_system §12 |
| | G2 padding 32-40px | computed | chrome | design_system §4 |
| H Desktop ≥1024 | H1 Header 三段式完整 | viewport 1440 截圖 | chrome | design_system §8 |
| | H2 主題 mega-menu hover 展開（接真 GET /themes）| network 看請求、UI 看下拉 | chrome hover + network | brief #30 + 規劃書 §3 |
| I 開發品質 | I1 pnpm type-check 0 錯 | terminal 輸出 | bash | SOP §4 |
| | I2 pnpm build 0 錯/0 warn | terminal 輸出 | bash | SOP §4 |
| | I3 Lighthouse a11y ≥ 90 | lighthouse 跑 | chrome devtools lighthouse | design_system §10 |

**共 28 個 case，全部對應到驗收手段。**

---

## 6. 差異與 ⚠️ 清單

| 等級 | 內容 | 處理 |
|---|---|---|
| **無 ⚠️ 規格衝突** | — | — |
| 範圍切割（不是衝突，是 S01 邊界）| 購物車件數顯示（S05 補）/ 會員下拉（S04 補）| 已在 §3 比對表標記、規劃書 §1 不做範圍列出 |

**結論**：S01 規劃書與 4 份規格來源（api.md、store_routes.md、store_design_brief.md、design_system.md）**0 ⚠️ 衝突**。可以進入下一階段（scaffold Vite 專案）。

---

## 7. 下一階段檢查清單

進 scaffold 階段前確認：
- [x] 規劃書 5 個 ⚠️ 全部已解決決議
- [x] api.md 端點 2 條（auth/me、themes）已對照 backend 原始碼
- [x] store_routes.md 26 條路由全部進規劃書
- [x] design_system.md 規範全部對應到規劃書設計決策
- [x] 28 條手動驗收 case 全部對應到驗證手段
- [ ] **user 點頭** ← 等使用者確認
