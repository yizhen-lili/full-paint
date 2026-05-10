# S09 — 會員中心（個人資料 / 收件 / 折扣券）

> Brief #22 個人資料 / #23 收件資料 / #24 折扣券錢包，規格見：
> - [docs/requirements/auth_users.md](../../../docs/requirements/auth_users.md)（users 表、流程）
> - [docs/requirements/store/store_auth.md](../../../docs/requirements/store/store_auth.md)（個人資料/收件/折扣券 UX）

---

## 1. 範圍

| Brief # | 頁面 | URL | 現況 |
|---|---|---|---|
| #22 | 個人資料 | `/profile` | **Placeholder** ← 待做 |
| #23 | 收件資料 | `/profile/shipping` | **完整實作** ✓（CRUD + form + set-default）|
| #24 | 折扣券錢包 | `/profile/coupons` | **Placeholder** ← 待做 |

ShippingProfilesPage 沿用，本 plan 只做 ProfilePage 與 CouponsPage + 補 api.ts 缺少的 endpoint client。

---

## 2. 檔案清單

```
store/src/features/profile/
├── api.ts                            # 補 updateProfile / changePassword / requestEmailChange / listCoupons
├── pages/
│   ├── ProfilePage.vue               # ← 重做（個人資料 CRUD）
│   └── CouponsPage.vue               # ← 重做（三 tab 列表）
└── components/
    ├── PersonalInfoForm.vue          # 新：姓名/性別/生日 inline 表單
    ├── ChangePasswordDialog.vue      # 新：舊密碼+新密碼 modal
    ├── ChangeEmailDialog.vue         # 新：申請新 email modal
    └── CouponCard.vue                # 新：單張折扣券視覺（折扣金額/類型/期限）
```

---

## 3. API 對接

### 個人資料

| Endpoint | Method | 用途 | 來源 |
|---|---|---|---|
| `/auth/me` | GET | 拿 user 完整 profile（已存在於 auth store fetchMe）| [backend/auth/router.py:53](../../../backend/auth/router.py#L53) |
| `/users/me` | PATCH | 改 name / gender / birthday | [backend/users/router.py:23](../../../backend/users/router.py#L23) |
| `/users/me/change-password` | POST | 改密碼（old_password + new_password） | [backend/users/router.py:33](../../../backend/users/router.py#L33) |
| `/users/me/request-email-change` | POST | 申請 email 變更（系統寄驗證信） | [backend/users/router.py:43](../../../backend/users/router.py#L43) |

### 折扣券

| Endpoint | Method | 用途 | 來源 |
|---|---|---|---|
| `/users/me/coupons` | GET | 回 `{ available, used, expired }` 三 list | [backend/discount/router.py:34](../../../backend/discount/router.py#L34) |

---

## 4. UI 設計（依 design_system.md）

### ProfilePage 結構

```
SectionMasthead（No.06 · Account · 會員中心）
  ↓
Tab nav（個人資料 / 收件資料 / 折扣券錢包）— RouterLink 導向 /profile, /shipping, /coupons
  ↓
PersonalInfoForm
  ├─ 姓名（inline editable，blur 自動 PATCH）
  ├─ Email（顯示 + 「修改」按鈕 → ChangeEmailDialog）
  │    pending_email 狀態：「已寄驗證信至 new@x.com，舊 email 仍可登入」
  ├─ 性別（select：女 / 男 / 其他 / 不指定）
  ├─ 生日（date input）
  └─ 「修改密碼」按鈕 → ChangePasswordDialog
```

### CouponsPage 結構

```
SectionMasthead（No.06 · Wallet · 折扣券錢包）
  ↓
Tab nav（可用 N / 已使用 / 已過期）
  ↓
CouponCard grid（responsive 1col mobile / 2col tablet / 3col desktop）
  ├─ 折扣金額（大字 mono）：NT$ 100 OFF 或 10% OFF
  ├─ coupon_type chip：新用戶歡迎 / 滿額贈 / 推廣碼
  ├─ min_purchase：滿 NT$ 800 可用（無則「不限金額」）
  └─ expires_at：3 月 15 日到期 / 倒數 X 天
```

### 設計決策（引用 [design_system.md](../design_system.md)）

| 元素 | Token / Rule | 為什麼 |
|---|---|---|
| Tab nav | hairline + 選中底線（accent）| §5 線條風格 + §1 紀律 |
| Form input | `--color-line-subtle` 全邊框 + `--color-paper-surface` 底，focus 換 accent | §8 Input 規格 |
| CouponCard | `--color-paper-surface` + 1px hairline + 直角 + 折扣金額用 `--font-mono` 24px | §8 Product Card 同款 |
| 已用/過期 coupon | sepia 0.2 saturate 0.6 灰調 + 「已使用」chip | §1 紀律：狀態用透明度區分 |
| 倒數警示 | < 3 天用 `--color-state-warning` | §3.3 |
| Modal（改密碼/換 email）| 中央 fade，180ms | §7 動畫 |

---

## 5. 業務流程關鍵點（規格摘要）

### Email 變更流程（[auth_users.md L62 / store_auth.md L43](../../../docs/requirements/auth_users.md#L62)）

1. user 在 ChangeEmailDialog 輸入新 email
2. POST `/users/me/request-email-change` → 後端立即檢查：
   - 新 email 已在 `users.email` or `users.pending_email` → 回錯誤（不寄信）
   - 通過 → 寫入 `users.pending_email` + 寄驗證信
3. UI 顯示「驗證信已寄至 new@x.com（舊 email 仍可登入直到完成驗證）」
4. user 點信內連結 → 後端覆蓋 `users.email` + 清空 `pending_email` + **舊 email 立即失效**

### 改密碼流程（[auth_users.md §3 / store_auth.md L46](../../../docs/requirements/auth_users.md)）

1. user 在 ChangePasswordDialog 輸入舊密碼 + 新密碼（最少 10 碼英數混合）
2. POST `/users/me/change-password` → 後端比對舊密碼，通過則更新
3. 不會登出（cookie token 仍有效），UI 顯示「密碼已更新」toast

### 折扣券狀態判定（[store_auth.md L73-77](../../../docs/requirements/store/store_auth.md#L73)）

backend 已分組（available / used / expired），前端直接渲染。

---

## 6. 手動驗收（chrome-devtools）

- [ ] `/profile` 載入 → 顯示 user 真實 name / email / gender / birthday
- [ ] 修改姓名 → 看 PATCH /users/me 200，UI 立即更新
- [ ] 點「修改密碼」→ modal 開 → 輸錯舊密碼 → 顯示明確錯誤
- [ ] 點「修改 Email」→ 輸入新 email → 顯示「驗證信已寄」+ pending_email banner
- [ ] `/profile/coupons` 三個 tab 切換正確；可用券有 N → 數字對；空 list 顯示空狀態
- [ ] Console 0 error / Network 0 unexpected 401
- [ ] Lighthouse Accessibility ≥ 90

---

## 7. 待確認事項（⚠️ 開工前需 user 回答）

見對話中的問題清單。
