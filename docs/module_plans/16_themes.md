# Module 16 — Themes（主題）

> 後端模組：在 product 模組之上加一層分類「主題」(theme)。
>
> 結構：**主題 (theme) → 系列 (series) → 商品 (product)**
>
> 範例：「萌寵」主題 → 「貓咪系列」/「狗狗系列」 → 各別商品
>
> 此模組為 product 模組的擴充，不獨立成 backend folder（共用 product/ namespace），但概念上是獨立的子模組，故獨立規劃書。

---

## 1. 範圍

### 本模組做
- `themes` 新表（id / name / description / cover_image_url / sort_order / timestamps）
- `product_series` 加 `theme_id` FK 欄位（nullable，舊系列不歸主題仍可運作）
- 6 個 admin endpoint：themes CRUD + 既有 series/products endpoint 加 `theme_id` 欄位
- alembic migration 建表 + 欄位
- 完整 pytest 覆蓋

### 本模組不做
- 商店端展示（屬 store_browse 模組擴充，未來補）
- theme 排序拖拉 API（用 sort_order，admin 自己改數字即可）
- theme 巢狀（不支援 theme of theme，只一層）

---

## 2. 資料表設計

### `themes`（新表）

| 欄位 | 型別 | 限制 | 說明 |
|---|---|---|---|
| id | UUID | PK default gen_random_uuid() | |
| name | VARCHAR(50) | NOT NULL UNIQUE | 主題名稱（例：萌寵、風景）|
| description | TEXT | nullable | 主題說明 |
| cover_image_url | VARCHAR | nullable | 主題封面（store 首頁區塊用；Firebase URL）|
| sort_order | INTEGER | NOT NULL DEFAULT 0 | 顯示排序，數字小越靠前 |
| created_at | TIMESTAMP tz | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMP tz | NOT NULL DEFAULT now() onupdate now() | |

CHECK：name 長度 ≤ 50；sort_order ≥ 0。

### `product_series`（修改）

加一欄：

| 欄位 | 型別 | 限制 | 說明 |
|---|---|---|---|
| theme_id | UUID | nullable, FK → themes.id ON DELETE SET NULL | 所屬主題（nullable：未分類的系列允許存在）|

ON DELETE SET NULL 而非 CASCADE：刪除主題時系列保留（變成「未分類」狀態），admin 再手動改歸屬，避免資料意外消失。

---

## 3. API 端點設計

### Admin - Themes CRUD

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/admin/themes` | `?search=&page=&page_size=` | `{items, total, page, page_size}` 含 series_count |
| GET | `/admin/themes/{id}` | — | theme detail |
| POST | `/admin/themes` | `{name, description, cover_image_url, sort_order}` | created theme |
| PUT | `/admin/themes/{id}` | 同上 | updated theme |
| DELETE | `/admin/themes/{id}` | — | 204；series 自動 SET NULL |

### Admin - Series（修改既有，加 theme_id）

| Method | Path | 改動 |
|---|---|---|
| GET `/admin/series` | response 加 `theme_id` 與 `theme_name`；可選 query `?theme_id=` filter |
| POST `/admin/series` | request 加 `theme_id: nullable UUID` |
| PUT `/admin/series/{id}` | 同上 |

### Store - Public（為未來 store 預留，本模組可先不上）

| Method | Path | 說明 |
|---|---|---|
| GET | `/themes` | 公開列表（store 首頁用）|
| GET | `/themes/{id}` | 公開詳情 + 該主題下所有 on_sale 商品 |

**本模組僅實作 admin 部分。store 端等 F-store 模組統一處理。**

---

## 4. 業務規則

### 主題刪除
- 主題下仍有系列：刪除時 series 自動 SET NULL（變未分類）
- admin 不需要先把系列移出（友好；users 不會誤鎖）

### 主題封面圖
- 走 signed URL 上傳流程（同 product cover）
- 上傳走 `/upload/product-image`（重用同一個端點）

### 排序
- sort_order：admin 手動填數字（0, 10, 20...）
- 列表 default order: `ORDER BY sort_order ASC, created_at DESC`

### EVENT_MATRIX 對照
本模組無觸發任何 Event（純資料管理，無 Email、無 Notification）。

---

## 5. 檔案結構

新增：
```
backend/product/
├── models.py          # 加 Theme model + ProductSeries.theme_id 欄位
├── service.py         # 加 theme CRUD service
├── router.py          # 加 6 個 theme endpoint
└── schemas/
    ├── request.py     # 加 ThemeRequest schemas
    └── response.py    # 加 ThemeResponse schemas

backend/migrations/versions/
└── j0e1f2g3h4i5_add_themes.py    # alembic migration

backend/tests/product/
└── test_themes.py     # 新測試檔
```

不變動：tags 模組、其他 module。

---

## 6. 測試覆蓋

`tests/product/test_themes.py`：

| Case | 預期 |
|---|---|
| admin 建立主題 | 201；列表新增 |
| 重複 name | 409 UNIQUE 衝突 |
| 列表排序 | sort_order ASC, created_at DESC |
| series_count 統計 | 正確 |
| 修改 | 200；updated_at 更新 |
| 刪除（無 series）| 204 |
| 刪除（有 series）| 204；該 series 的 theme_id 變 NULL |
| customer role 訪問 | 403 |
| 未登入訪問 | 401 |
| Series 加 theme_id | POST/PUT 接受 theme_id 並 join 顯示 theme_name |
| 不存在的 theme_id | 404 |

---

## 7. 規格比對來源

| 來源 | 對應 |
|---|---|
| `docs/schema.md` | 加 themes 表規格 + product_series.theme_id 欄位 |
| `docs/api.md` | 模組六擴充 6 個 endpoint |
| `docs/requirements/admin_product.md` | 業務規則：主題分類概念 |

**待補**：上述三份文件目前都未提及主題；本模組會**同時更新這些文件**作為 deliverable。

---

## 8. 待確認事項

1. **`name UNIQUE`** 是否要加 case-insensitive？目前 PostgreSQL UNIQUE 預設 case-sensitive。預設保持，admin 自己控制大小寫。
2. **cover_image_url 必填還是 nullable？** 預設 nullable（admin 可先建主題不放圖，之後補）。
3. **sort_order 是否要支援負數？** CHECK `>= 0`，不支援負數（要往前插就把現有的數字調大）。

---

## 9. 完成標準

- [ ] alembic migration 建表 + 欄位 + 反向 downgrade 測試
- [ ] 6 個新 endpoint 都有 response_model
- [ ] tests/product/test_themes.py 全綠（11 條 case）
- [ ] 全套 quality_check 4 gates 全綠
- [ ] /reviewer pass
- [ ] docs/schema.md / api.md 同步更新
- [ ] git commit：`feat(themes): Module 16 - 主題分類（N tests passing）`
