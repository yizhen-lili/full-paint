# F13 用戶管理 模組規劃書

> 對應後端 Module 03 (admin/users)、admin_routes 用戶區、auth_users.md。

---

## 1. 路由

| 路由 | 頁面 | guard | 說明 |
|---|---|---|---|
| `/admin/users` | `UsersListPage.vue` | requireAdmin | 列表 + 篩選 + 搜尋 |
| `/admin/users/:id` | `UserDetailPage.vue` | requireAdmin | 詳情：個人資料 + 訂單 / 客製 / 持有券 三 tab |

---

## 2. 後端 API

| Endpoint | Method | 用途 |
|---|---|---|
| /admin/users | GET | 列表（search / role / is_active / page）|
| /admin/users/{id} | GET | 詳情 |
| /admin/users/{id} | PATCH | 修改（name / role / is_active / password）|
| /admin/orders?search=email | GET | 詳情頁的訂單 tab（既有 endpoint）|
| /admin/custom-requests | GET | 詳情頁的客製 tab（client filter user_id）|
| /admin/user-coupons?user_id=&is_used= | GET | 詳情頁的持有券 tab |

**沒有獨立的 reset_password / unban endpoint** — 全部透過 PATCH 一個欄位達成。

---

## 3. 元件樹

```
UsersListPage
├─ PageHeader
├─ FilterBar：search / role select / is_active select
├─ AppDataTable
│  └─ row：頭像（initials）/ name / email / role badge / 狀態 badge / 註冊時間
└─ AppPagination

UserDetailPage
├─ Breadcrumb（工坊 / 用戶 / id 短碼）
├─ Header
│  ├─ avatar + name + email + role badge + status badge
│  └─ HeaderActions：[編輯][停用 / 解封][發券]
├─ Grid 兩欄
│  ├─ Side：個人資料卡（name / gender / birthday / 註冊 / 最後修改）
│  └─ Main 三 tab：訂單 / 客製 / 持有券
└─ Dialogs：EditUserDialog / IssueCouponsDialog（沿用 F08）
```

---

## 4. 狀態 / Query

```ts
const KEYS = {
  list: (params) => ['admin', 'users', 'list', params],
  detail: (id) => ['admin', 'users', 'detail', id],
}
```

---

## 5. 操作 / 安全規則

| 規則 | 來源 | UX |
|---|---|---|
| 禁止停用自己 | api.md + auth_users.md §8 | 操作者就是自己 → 「停用」按鈕隱藏 |
| 禁止停用其他 admin | api.md | 對方是 admin → 「停用」按鈕隱藏 |
| 重設密碼需符合格式（min 10、英數混合）| auth_users.md | zod 驗證 |
| 切到 admin role 是高敏感操作 | — | 加二次確認 dialog |

---

## 6. 設計決策

- 頭像用 initials（取 name 首字 + 第二字）
- role 色票：admin = accent / customer = neutral
- is_active 色票：true = success / false = danger
- 訂單 / 客製 tab 沿用 F04 / F05 的 client filter（client side filter user_id）
- 統一密碼欄位：留空 = 不改密碼

---

## 7. 待確認
- 全 A 預設（無未解 ⚠️）— 直接開工
