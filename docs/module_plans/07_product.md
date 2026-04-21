# Module 07：商品管理（product）

## 1. 建立的檔案清單

```
backend/product/
├── __init__.py
├── models.py           # ProductSeries, Product, ProductImage, ProductVariant, Tag, ProductTag
├── router.py           # 所有 admin/products, admin/series, admin/tags endpoints
├── service.py          # 業務邏輯
├── schemas/
│   ├── __init__.py
│   ├── request.py
│   └── response.py
backend/tests/product/
├── __init__.py
├── test_series.py
├── test_tags.py
└── test_products.py    # 含 variants, images
docs/module_plans/07_product.md   ← 此檔
```

main.py 加入 product router。
migrations/ 加入 Alembic migration。

---

## 2. DB 模型

### product_series
| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK, default uuid4 |
| name | VARCHAR | NOT NULL |
| description | TEXT | nullable |
| created_at | TIMESTAMP | NOT NULL, default now() |

> 系列下仍有商品時禁止刪除（service 層驗證，回 409）。

### products
| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK |
| title | VARCHAR | NOT NULL |
| description | TEXT | nullable |
| cover_image_url | VARCHAR | NOT NULL |
| series_id | UUID | nullable, FK → product_series.id |
| series_order | INTEGER | nullable |
| status | ENUM('draft','on_sale','off_sale') | NOT NULL, default 'draft' |
| created_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NOT NULL |

> 不支援硬刪除（DELETE endpoint 需先確認無進行中訂單，之後將商品 status 改為 off_sale）。
> 本模組暫不做訂單關聯檢查（訂單模組尚未實作），DELETE 先僅確認商品已 off_sale 且無 active variants 才允許刪除。

### product_images
| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK |
| product_id | UUID | NOT NULL, FK → products.id ON DELETE CASCADE |
| image_url | VARCHAR | NOT NULL |
| sort_order | INTEGER | NOT NULL, default 0 |
| created_at | TIMESTAMP | NOT NULL |

### product_variants
| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK |
| product_id | UUID | NOT NULL, FK → products.id |
| production_job_id | UUID | NOT NULL, FK → production_jobs.id |
| price | NUMERIC(10,2) | NOT NULL |
| price_formula_base | NUMERIC(10,2) | NOT NULL |
| is_active | BOOLEAN | NOT NULL, default true |
| created_at | TIMESTAMP | NOT NULL |

> UNIQUE(product_id, production_job_id)
> 建立時自動計算 price_formula_base（見第 5 節定價公式）。
> production_job 必須 approved=true 且 num_colors_used 不為 null 才可建立變體。

### tags
| 欄位 | 型別 | 限制 |
|------|------|------|
| id | UUID | PK |
| name | VARCHAR | NOT NULL, UNIQUE |
| created_at | TIMESTAMP | NOT NULL |

### product_tags（關聯表）
| 欄位 | 型別 | 限制 |
|------|------|------|
| product_id | UUID | NOT NULL, FK → products.id |
| tag_id | UUID | NOT NULL, FK → tags.id ON DELETE CASCADE |

> PRIMARY KEY (product_id, tag_id)

---

## 3. Endpoints

### 3.1 系列管理

#### GET /admin/series
- 回傳所有系列（含每個系列的商品數量）
- Response: `{ "items": [{ "id", "name", "description", "product_count", "created_at" }] }`

#### POST /admin/series
- Request: `{ "name": "string", "description": "string|null" }`
- Response 201: 系列資料
- Error 409: name 重複

#### PUT /admin/series/{id}
- Request: `{ "name": "string", "description": "string|null" }`
- Response 200: 更新後資料
- Error 404: 系列不存在
- Error 409: name 重複

#### DELETE /admin/series/{id}
- 系列下仍有商品 → 409
- Response 204

---

### 3.2 標籤管理

#### GET /admin/tags
- 回傳所有標籤（含每個標籤的商品數量）
- Response: `{ "items": [{ "id", "name", "product_count", "created_at" }] }`

#### POST /admin/tags
- Request: `{ "name": "string" }`
- Response 201: 標籤資料
- Error 409: name 重複

#### PUT /admin/tags/{id}
- Request: `{ "name": "string" }`
- Response 200
- Error 404, 409

#### DELETE /admin/tags/{id}
- CASCADE 移除所有 product_tags 關聯（DB 層 ON DELETE CASCADE 處理）
- Response 204
- Error 404

---

### 3.3 商品管理

#### GET /admin/products
- Query: `?search=&status=draft|on_sale|off_sale&page=1&page_size=20`
- Response: `{ "items": [...], "total", "page", "page_size" }`
- 每筆商品含：id, title, status, cover_image_url, variant_count, created_at, tags

#### POST /admin/products
- Request: `{ "title", "description", "cover_image_url", "series_id|null", "series_order|null", "status", "tag_ids": ["uuid"] }`
- 驗證 series_id 存在（若提供）；驗證所有 tag_ids 存在
- Response 201: 完整商品資料（含 tags）

#### PUT /admin/products/{id}
- 同 POST 欄位，全欄位更新
- 標籤先刪後插（delete product_tags where product_id=id → insert 新 tag_ids）
- Response 200

#### DELETE /admin/products/{id}
- 商品必須是 off_sale 狀態，且沒有 active variants（is_active=true）才能刪除
- 不符合條件 → 409
- Response 204

---

### 3.4 商品圖片

#### POST /admin/products/{id}/images
- Request: `{ "image_url": "string", "sort_order": 0 }`
- Response 201: `{ "id", "image_url", "sort_order", "created_at" }`

#### DELETE /admin/products/{id}/images/{image_id}
- Response 204
- Error 404

#### PATCH /admin/products/{id}/images/reorder
- Request: `{ "order": ["image_id_1", "image_id_2", ...] }`
- 按 order 陣列順序更新各圖片的 sort_order（index 即為 sort_order）
- 陣列內的 image_id 必須全部屬於此 product_id
- Response 200: 更新後的圖片列表

---

### 3.5 商品規格變體

#### POST /admin/products/{id}/variants
- Request: `{ "production_job_id": "uuid", "price": 397 }`
- 驗證 production_job.approved=true 且 num_colors_used 不為 null
- 自動計算 price_formula_base
- UNIQUE 衝突（同 product_id + production_job_id）→ UPDATE price, price_formula_base, is_active=true
- Response 200: 變體資料（含 job 規格資訊）

#### PATCH /admin/products/{id}/variants/{variant_id}
- Request: `{ "price": 420, "is_active": true }`（任一欄位可選填）
- Response 200
- Error 404

#### DELETE /admin/products/{id}/variants/{variant_id}
- 直接刪除（本模組不檢查訂單，訂單模組實作時補充）
- Response 204
- Error 404

---

## 4. 可用變體池 API（供建立變體時選擇）

#### GET /admin/production/jobs/available-for-variant
- 列出 approved=true 且 num_colors_used 不為 null 的 jobs
- 可選 Query: `?product_id=uuid`（排除已是該商品 variant 的 job）
- Response: `{ "items": [{ "id", "detail", "difficulty", "mode", "canvas_w_cm", "canvas_h_cm", "num_colors_used", "price_formula_base" }] }`

> price_formula_base 在列表中即預先計算，讓管理員參考後填入 price。

---

## 5. 定價公式

```python
def calc_price_formula_base(canvas_w_cm, canvas_h_cm, detail, num_colors_used) -> Decimal:
    # 基礎成本
    print_area = (canvas_w_cm + 10) * (canvas_h_cm + 10)
    print_cost = math.ceil(print_area / 900) * 45
    frame_cost = canvas_w_cm + canvas_h_cm
    fixed_cost = 25
    base_cost = fixed_cost + print_cost + frame_cost

    # 顏料費
    paint_cost = num_colors_used  # NT$1 × 色數

    # 細緻度加成率
    detail_multiplier = {"rough": 1.60, "standard": 1.75, "detailed": 1.80, "premium": 1.85}

    raw = (base_cost + paint_cost) * detail_multiplier[detail]
    return Decimal(str(round(raw)))  # 四捨五入至整數
```

---

## 6. 測試涵蓋範圍

### test_series.py
- 建立系列（ok, name 重複→409）
- 更新系列（ok, 不存在→404, name 重複→409）
- 刪除系列（ok, 有商品→409, 不存在→404）
- 列表（含 product_count）
- 非管理員 → 403，未登入 → 401

### test_tags.py
- 建立標籤（ok, name 重複→409）
- 更新標籤（ok, 不存在→404, name 重複→409）
- 刪除標籤（ok, 刪除後 product_tags 關聯消失）
- 列表（含 product_count）
- 非管理員 → 403，未登入 → 401

### test_products.py
- CRUD 商品（ok, 404, 欄位驗證）
- tag_ids 驗證（不存在的 tag_id → 400）
- series_id 驗證（不存在 → 400）
- DELETE 商品（off_sale 無 active variants→204, on_sale→409, 有 active variant→409）
- 圖片：新增、刪除、reorder（正常, 404, 陣列包含不屬於此商品的 image_id → 400）
- 變體：建立（ok, job 未 approved → 400, UNIQUE 衝突→覆蓋）
- 變體：更新 price / is_active
- 變體：刪除
- 可用 job 列表（已 approved + num_colors_used 不為 null 才出現）
- 分頁與篩選（status, search）
- 非管理員 → 403，未登入 → 401

---

## 7. 待確認事項

無。
