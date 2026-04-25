# 回頭驗收發現問題清單

> 建立時間：2026-04-22

## 待修正項目

### #1 users/service.py — 缺少 pending_email 衝突檢查
- **位置**：`backend/users/service.py:74-87`（`request_email_change` 函數）
- **問題**：若使用者申請換成與自身 `pending_email` 相同的 email，會被靜默接受（不應該）
- **要求**：`new_email == user.pending_email → 409 ConflictError`（`schema.md` § users & module plan `02_users_shipping.md` 明確列出）
- **狀態**：待修

### #2 tests/users/test_users.py — 缺少 pending_email 衝突測試
- **位置**：`backend/tests/users/test_users.py`
- **問題**：缺少 `test_request_email_change_same_as_pending → 409`
- **狀態**：待修

### #3 tests/auth/test_auth.py — 缺少 4 個 email_change 驗證測試
- **位置**：`backend/tests/auth/test_auth.py`
- **問題**：驗證流程有 4 個情境未覆蓋：
  1. 驗證連結已過期 → 400
  2. 成功驗證換信箱 → 200（user.email 更新、pending_email 清空）
  3. 換信箱後舊信箱無法登入 → 401
  4. 換信箱後新信箱可登入 → 200
- **狀態**：待修

### #4 palette/service.py — paint_min_ml / paint_buffer_ratio 預設值錯誤
- **位置**：`backend/palette/service.py:157-159`
- **問題**：
  - `paint_min_ml` 預設 "5.0"，`schema.md` 規定預設 **3**
  - `paint_buffer_ratio` 預設 "1.2"，`schema.md` 規定預設 **1.3**
- **狀態**：待修

### #5 product/service.py — 缺少 series_order 必填驗證
- **位置**：`backend/product/service.py`（`create_product` & `update_product`）
- **問題**：`schema.md` 規定「若 series_id IS NOT NULL 則 series_order 必填（後端驗證）」，但目前未實作此驗證
- **狀態**：待修

### #6 tests/product/test_products.py — 缺少 series_without_order 測試
- **位置**：`backend/tests/product/test_products.py`
- **問題**：缺少 `test_create_product_series_without_order → 400`
- **狀態**：待修

### #7 docs/schema.md — production_jobs.status ENUM 缺少 cancelled
- **位置**：`docs/schema.md:202`
- **問題**：ENUM 列出 `('pending','processing','completed','failed')`，但實作中包含 `cancelled`（module plan 04 及 router 都有），schema.md 未同步
- **狀態**：待修

---

## 已確認無問題模組

| 模組 | 結論 |
|------|------|
| Module 03 (Admin Users) | ✅ 測試完整，業務邏輯正確 |
| Module 04 (Production) | ✅ 測試完整；approve 用 400 非 422 符合 BadRequestError 設計 |
| Module 05b (Upload) | ✅ 附屬 Production 模組，無獨立問題 |
| Module 05 (Color) | ✅ 測試完整 |
| Module 06 (Palette) | ⚠️ 預設值問題見 #4 |
| Module 07 (Product) | ⚠️ series_order 驗證問題見 #5-6 |
