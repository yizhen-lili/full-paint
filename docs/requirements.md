# 功能需求規格 — 索引

詳細需求各模組獨立存放於 `docs/requirements/` 資料夾。

---

## 定價

| 文件 | 狀態 |
|------|------|
| [定價公式](requirements/pricing_formula.md) | 完成 |

---

## 共用

| 模組 | 檔案 | 狀態 |
|------|------|------|
| 使用者系統（註冊 / 登入 / 收件資料 / JWT）| [auth_users.md](requirements/auth_users.md) | 完成 |

---

## 管理者端

| 模組 | 檔案 | 狀態 |
|------|------|------|
| 路由結構 | [admin_routes.md](requirements/admin_routes.md) | 完成 |
| 1. 製作模組 | [admin_production.md](requirements/admin_production.md) | 完成 |
| 2. 填色色號對應實體色管理 | [admin_color.md](requirements/admin_color.md) | 完成 |
| 3. 商品管理 | [admin_product.md](requirements/admin_product.md) | 完成 |
| 4. 折扣券管理 | [admin_discount.md](requirements/admin_discount.md) | 完成 |
| 5. 客戶訂單管理 | [admin_orders.md](requirements/admin_orders.md) | 完成 |
| 6. 內容管理 | [admin_content.md](requirements/admin_content.md) | 完成 |
| 7. 通知系統 | [admin_notifications.md](requirements/admin_notifications.md) | 完成 |

---

## 用戶商店端

| 模組 | 檔案 | 狀態 |
|------|------|------|
| 路由結構 | [store_routes.md](requirements/store_routes.md) | 完成 |
| 1. 瀏覽與購買 | [store/store_browse.md](requirements/store/store_browse.md) | 完成 |
| 2. 會員系統 | [store/store_auth.md](requirements/store/store_auth.md) | 完成 |
| 3. 訂單管理 | [store/store_orders.md](requirements/store/store_orders.md) | 完成 |
| 4. 客製化商品頁 | [store/store_custom.md](requirements/store/store_custom.md) | 完成 |
| 5. 資訊頁 | [store/store_info.md](requirements/store/store_info.md) | 完成 |

---

## 模組間的上架流程依賴

```
製作模組（status=completed, approved=true）
    ↓
實體色對應模組（所有 template_id 對應完成）
    ↓
商品管理模組（建立商品、設定定價、上架）
    ↓
用戶商店（瀏覽、購買、下載）
```
