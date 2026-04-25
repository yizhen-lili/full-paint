# Module 12 - 商品瀏覽（store_browse）

> 公開商品瀏覽 5 個 endpoint。所有端點 `public`（無 auth），只回傳 `status=on_sale` 與 `is_active=true` 的資料。

## 1. 檔案清單

修改既有：
- `backend/product/router.py` — 新增 5 個 public endpoints
- `backend/product/service.py` — 新增 public list / search / detail / related / public-tags 邏輯
- `backend/product/schemas/response.py` — 新增 `PublicProductBrief / PublicProductDetail / PublicVariant / PublicProductListResponse / RelatedProductsResponse / PublicTagListResponse`

新建：
- `backend/tests/product/test_public_browse.py`

不影響既有 admin endpoints / models / migrations。

## 2. Endpoint 業務流程

### `GET /products`（public）
Query: `difficulty?, detail?, canvas_size?, tag_id?, series_id?, sort=latest|popular|price_asc|price_desc, page=1, page_size=24`
- WHERE `products.status = on_sale`
- JOIN ProductVariant + ProductionJob 過濾 difficulty/detail/canvas_size（轉 `WxH` 字串為 w/h）
- JOIN ProductTag 過濾 tag_id
- 過濾 `variants.is_active=true`
- 各 sort：
  - `latest` → ORDER BY `created_at DESC`
  - `price_asc/desc` → ORDER BY MIN(variant.price) ASC/DESC
  - `popular` → JOIN order_items group by product, ORDER BY COUNT DESC（沒有 paid 狀態 fallback 為 latest）
- Aggregate: `price_min`/`price_max` 取 product 所有 active variants
- `is_preorder`: 任一 active variant 對應 production_job 還未完成或庫存不足（簡化：暫定 false，待庫存判斷補；列入待確認 ⚠️）
- `difficulty_range`: `[min, max]` from active variants

### `GET /products/search?q=`（public）
- ILIKE `title`/`description`/`tags.name` 任一含 q
- WHERE status=on_sale
- 同 list 的 response shape

### `GET /products/{id}`（public）
- WHERE status=on_sale；否則 404
- Include images（sort_order）/ tags / series（id+name 含 same series 商品 brief list）
- variants：only is_active=true，含 job_spec
- 不洩漏 admin 欄位（status/series_order）

### `GET /products/{id}/related`（public）
- 取 product.series_id；無系列回 `{ series: null, items: [] }`
- 同系列其他 status=on_sale 商品，ORDER BY series_order ASC, created_at ASC
- exclude self

### `GET /tags`（public）
- 全部 tags（不過濾 product_count），shape `{items: [{id, name}]}` 不洩漏 product_count

## 3. EVENT_MATRIX
不觸發任何 Event。純讀。

## 4. 測試覆蓋

| Case | 預期 | 測試函數 |
|---|---|---|
| GET /products 預設 | 200 + 全部 on_sale | test_list_default |
| GET /products draft 商品被排除 | 對應 | test_list_excludes_draft |
| GET /products filter difficulty | 200 + 對應 | test_list_filter_difficulty |
| GET /products filter canvas_size=30x40 | 200 + 對應 | test_list_filter_canvas_size |
| GET /products filter tag_id | 200 + 對應 | test_list_filter_tag |
| GET /products sort price_asc/desc | 順序正確 | test_list_sort_price |
| GET /products sort latest | DESC created_at | test_list_sort_latest |
| GET /products 分頁 | page/page_size 正確 | test_list_pagination |
| GET /products/search?q=... | ILIKE 跨 title+description+tag | test_search_returns_match |
| GET /products/{id} on_sale | 200 + variants 含 job_spec | test_detail_on_sale |
| GET /products/{id} draft 拒絕 | 404 | test_detail_draft_404 |
| GET /products/{id} 含 inactive variant 隱藏 | 對應 | test_detail_hides_inactive_variants |
| GET /products/{id}/related 有系列 | 200 + 含同系列 | test_related_in_series |
| GET /products/{id}/related 無系列 | 200 + items=[] | test_related_no_series |
| GET /tags public | 200 + 不洩漏 product_count | test_public_tags |

## 5. ⚠️ 決議

### A — `is_preorder` 計算
規格 §54「庫存狀態（預購中標示）」：商品卡片要標 preorder。需要計算「該 variant 對應 production_job 的 stock 是否足夠」。但這要求遍歷 PaletteColorMapping → PhysicalColor，每件商品做這計算成本高。
**決議**：本模組 `is_preorder = false` 暫定（穩定回應），列入最終稽核 TODO。前端目前已可呈現價格與基本資訊；庫存提示可在商品詳情頁的「加入購物車」即時計算（已在 Module 09 cart 路徑做過）。

### B — `popular` 排序
依 paid+ 訂單數排序，但 cold-start 訂單少時無意義。
**決議**：以 order_items 計數排序，無資料時 fallback 同 latest。

### C — `canvas_size` query 格式
api.md 寫 `canvas_size=30x40`，需 parse 為 w=30, h=40。
**決議**：以 `x` split；非合法格式回 422（Pydantic Query 自訂驗證）。
