# 規格比對報告 — Module 16 Themes

> 配對 `16_themes.md` 規劃書與所有規格來源。**注意：themes 是新概念，原 docs 沒提到，所以多數比對是「新增到 spec」而非「找差異」。**

---

## 1. schema.md 欄位比對

`themes` 表是新表，schema.md 還沒有對應條目。**規劃書 §2 設計的欄位即未來 schema.md 的權威定義。**

| 欄位 | 規劃 | 狀態 |
|---|---|---|
| themes.id UUID PK | ✓ | 新增到 schema.md |
| themes.name VARCHAR(50) NOT NULL UNIQUE | ✓ | 新增 |
| themes.description TEXT nullable | ✓ | 新增 |
| themes.cover_image_url VARCHAR nullable | ✓ | 新增 |
| themes.sort_order INTEGER NOT NULL DEFAULT 0 CHECK >= 0 | ✓ | 新增 |
| themes.created_at / updated_at | ✓ | 新增 |
| product_series ADD theme_id UUID nullable FK ON DELETE SET NULL | ✓ | schema.md product_series 表加欄位 |

**資料表變動 deliverable：** docs/schema.md 必須在實作 commit 同時更新。

---

## 2. api.md 端點比對

| Endpoint | 規劃 | 規格現況 | 結果 |
|---|---|---|---|
| `GET /admin/themes` | 列表 | 不存在 | 新增 |
| `GET /admin/themes/{id}` | 詳情 | 不存在 | 新增 |
| `POST /admin/themes` | 建立 | 不存在 | 新增 |
| `PUT /admin/themes/{id}` | 更新 | 不存在 | 新增 |
| `DELETE /admin/themes/{id}` | 刪除（系列 SET NULL）| 不存在 | 新增 |
| `GET /admin/series` 加 `theme_id` 欄位 + `?theme_id=` filter | 改動 | 既有，需修 | 修改 |
| `POST /admin/series` 加 `theme_id` 欄位 | 改動 | 既有 | 修改 |
| `PUT /admin/series/{id}` 加 `theme_id` 欄位 | 改動 | 既有 | 修改 |

**API spec deliverable：** docs/api.md 模組六章節新增 themes endpoint + 修改 series endpoint。

---

## 3. requirements/admin_product.md 比對

現有規範未提及主題。本模組會新增小節：

```
3.6 主題分類
管理員可建立主題，將相關系列歸類於同一主題下。
主題之上不再分類；主題下可有 0 ~ N 個系列；系列可不歸屬任何主題。
刪除主題時：該主題下的所有系列 theme_id 自動變為 NULL（保留資料），
系列不會被刪除。
```

**requirements deliverable：** docs/requirements/admin_product.md 加 §3.6。

---

## 4. EVENT_MATRIX.md 對照

本模組**無觸發 Event**（純 CRUD，無 Email、無 Notification、無自動觸發）。EVENT_MATRIX 不需要更新。

✓ 確認。

---

## 5. requirements/admin_routes.md 比對

admin 後台路由：`/admin/products?tab=themes` 走前端內部 tab，**不需新增獨立路由**。admin_routes 也不需更新。

✓ 確認。

---

## 6. 測試覆蓋表

11 條測試 case 對應規劃書 §6，逐一映射：

| # | Case | endpoint / 業務規則來源 |
|---|---|---|
| 1 | 建立主題 → 201 | POST /admin/themes |
| 2 | 重複 name → 409 | UNIQUE constraint |
| 3 | 列表排序 sort_order ASC, created_at DESC | GET /admin/themes |
| 4 | series_count 統計正確 | GET /admin/themes（join 回傳）|
| 5 | 修改 → 200, updated_at 變 | PUT /admin/themes/{id} |
| 6 | 刪除無 series → 204 | DELETE /admin/themes/{id} |
| 7 | 刪除有 series → 204 + theme_id 變 NULL | ON DELETE SET NULL |
| 8 | customer 訪問 → 403 | require_admin dependency |
| 9 | 未登入 → 401 | require_admin dependency |
| 10 | Series 加 theme_id（POST/PUT 接受）+ 列表 join theme_name | series 修改後行為 |
| 11 | 不存在的 theme_id → 404 | FK 防呆 |

每條都對應到具體規格 / endpoint，無孤兒測試。

---

## 7. 差異與待確認

### 待確認（內部預設）
1. **name UNIQUE case-sensitive**：預設 PostgreSQL 預設行為（case-sensitive）
2. **cover_image_url nullable**：預設 nullable
3. **sort_order CHECK >= 0**：不支援負數

以上三項皆規劃書內部決定，不涉及外部介面，可後調。

### 與 spec 衝突
**無 ⚠️**。所有改動是新增 / 擴充，不違反任何既有業務規則或 endpoint 行為。

---

## 8. 結論

✅ **可開始寫 code**。

deliverables（隨 commit 一起更新）：
1. backend/product/{models,service,router,schemas/} 新增 theme 相關
2. backend/migrations/versions/ 新增 j0e1f2g3h4i5_add_themes.py
3. backend/tests/product/test_themes.py 11 條測試
4. docs/schema.md 加 themes 表 + product_series.theme_id 欄位
5. docs/api.md 模組六新增 themes endpoint + series endpoint 改動
6. docs/requirements/admin_product.md 加 §3.6 主題分類

實作順序：
1. models.py + migration → 跑 alembic 確認 DB 變動成功
2. schemas + service + router → 加 6 個 endpoint
3. tests 11 條 → quality_check.py product
4. docs 更新（schema、api、requirements）
5. /reviewer
6. commit
