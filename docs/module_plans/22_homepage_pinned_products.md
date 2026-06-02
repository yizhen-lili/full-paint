# Module 22 — 首頁置頂商品（homepage_order + 拖曳排序）

> **目的**：admin 可以挑選任意數量的商品釘到 store 首頁，並用拖曳決定顯示順序。
> 商品的「精選 `is_featured`」與「是否上首頁 / 順序」拆成獨立概念，互不耦合。

---

## 一、概念與決策

| 概念 | 載體 |
|---|---|
| 「⭐ 精選」(目前)：產品卡上的徽章 + `?featured=true` 過濾 | `Product.is_featured: bool`（已存在，不改動） |
| 「首頁置頂第 N 位」(本模組新增) | `Product.homepage_order: int \| null`（越小越前面；`null` = 不上首頁） |

**為什麼拆開**：是否在首頁出現 ≠ 是否標為精選；admin 可能想把一張新作排到首頁 Top1 但不要打⭐徽章，反之亦然。

**Top1 = `homepage_order = 1`**；之後 2、3、4…依序往下。

---

## 二、受影響檔案清單

```
backend/
├── product/models.py                          # Product 加 homepage_order
├── product/schemas/request.py                 # HomepageOrderRequest 新增 (拖曳排序專用)
├── product/schemas/response.py                # ProductBriefResponse / ProductDetailResponse / PublicProductBrief 加 homepage_order
├── product/service.py                         # set_homepage_order() 新增；public_list_homepage_pinned() 新增
├── product/router.py                          # POST /admin/products/homepage-order；GET /products/homepage-pinned
├── migrations/versions/m3n4o5p6q7r8_add_product_homepage_order.py
└── tests/product/test_homepage_pinned.py

admin/
├── src/features/products/pages/HomepagePinnedPage.vue  # 新頁面：拖曳排序 + 新增 / 移除
├── src/features/products/components/DraggablePinnedList.vue  # 拖曳列表元件
├── src/features/products/components/PinProductPickerDialog.vue  # 商品挑選 modal
├── src/features/products/api.ts                # setHomepageOrder / listPinnedProducts
├── src/features/products/queries.ts            # useHomepagePinnedQuery + useSetHomepageOrderMutation
├── src/router.ts                               # 加 /admin/homepage-pinned 路由
└── src/shared/components/Sidebar.vue（或對應 nav）# 加「首頁排序」入口

store/
├── src/features/home/components/PinnedTopSection.vue  # 新 section（無置頂時不渲染）
├── src/features/home/pages/HomePage.vue        # 在 EditorLetter 之後插入 PinnedTopSection
├── src/features/browse/api.ts                  # listHomepagePinned()
└── src/features/browse/queries.ts              # useHomepagePinnedQuery
```

---

## 三、DB Model

`products` 表加一欄：

| 欄位 | 型別 | 限制 | 預設 | 索引 |
|---|---|---|---|---|
| `homepage_order` | INTEGER | NULL allowed | NULL | `idx_products_homepage_order ON (homepage_order) WHERE homepage_order IS NOT NULL`（部分索引，只索引非 null） |

**約束**：
- 不加 UNIQUE — 拖曳排序時短暫可能有兩筆同號（先 set null 再 renumber 的 race 太囉嗦）；改在 service layer 用 transaction 保證最後狀態唯一
- `homepage_order >= 1` CheckConstraint（避免 0 / 負數混淆）

**Alembic migration** `m3n4o5p6q7r8_add_product_homepage_order`：
- upgrade：
  - `op.add_column('products', sa.Column('homepage_order', sa.Integer(), nullable=True))`
  - `op.create_check_constraint('ck_products_homepage_order_positive', 'products', 'homepage_order IS NULL OR homepage_order >= 1')`
  - `op.create_index('idx_products_homepage_order', 'products', ['homepage_order'], postgresql_where=sa.text('homepage_order IS NOT NULL'))`
- downgrade：反向。

---

## 四、API 規格

### Admin endpoints

#### `POST /admin/products/homepage-order`
拖曳排序提交。Atomic：先清空所有商品的 homepage_order，再依序賦值 1..N。

**Request**：
```json
{
  "product_ids": ["uuid-of-top1", "uuid-of-top2", "uuid-of-top3"]
}
```
- 空陣列 = 全部清空首頁置頂
- 每個 id 必須是現存 product **且 status = on_sale**（draft / off_sale → 400）
- 不能重複；**max 12 筆**（超過 → 400）

**Response 200**：
```json
{
  "items": [
    { "id": "uuid", "title": "...", "homepage_order": 1, "status": "on_sale", "cover_image_url": "..." },
    ...
  ]
}
```
依新順序回傳 admin 端剛排定的內容（不需要 admin 自己 refetch）。

**錯誤**：
- 400 `product_ids 含不存在 id`
- 400 `product_ids 重複`
- 400 `product_ids 超過 12 筆`
- 400 `含未上架商品（必須全部 on_sale）`

#### `GET /admin/products/homepage-pinned`
列出目前置頂商品（依 homepage_order ASC）— admin 進入排序頁時用。Response 同 POST 200。

#### 既有 endpoints 改動
- `GET /admin/products`（list） response 每筆加 `homepage_order: int | null`
- `GET /admin/products/{id}`（detail） response 加 `homepage_order`
- `POST/PUT /admin/products` body **不接受** `homepage_order`（單獨用 reorder 端點管，避免雙寫路徑）

### Public endpoint

#### `GET /products/homepage-pinned`
Store 首頁取「置頂商品」用。**只回 `status=on_sale` 且 `homepage_order IS NOT NULL` 且至少有一個 active variant** 的商品。

**Response 200**：
```json
{
  "items": [
    { "id": "uuid", "title": "...", "cover_image_url": "...", "difficulty_range": ["beginner","intermediate"], "price_min": 397, "price_max": 860, "is_preorder": false, "is_featured": true }
  ]
}
```
照 `homepage_order ASC` 排。空 list 表示沒置頂 — store 端 hide 該 section。

---

## 五、業務流程

### Flow 1: admin 進入「首頁排序」頁
1. `GET /admin/products/homepage-pinned` 回目前置頂的 N 筆（順序排好）
2. UI 顯示 N 個可拖曳卡片（縮圖 + 標題 + 狀態徽章）
3. 上方按鈕「+ 加入商品到首頁」→ 開 `PinProductPickerDialog`
4. Dialog 內呼叫既有 `GET /admin/products?status=on_sale&search=...&exclude=<already_pinned_ids>`（要改 existing list 端點，加 `exclude` query）

### Flow 2: admin 拖曳
1. 前端 vue-draggable-plus 拖完後本地更新陣列順序（樂觀）
2. 點「儲存排序」按鈕 → 呼叫 `POST /admin/products/homepage-order` 帶新 product_ids 陣列
3. 後端 transaction：
   ```sql
   UPDATE products SET homepage_order = NULL WHERE homepage_order IS NOT NULL;
   -- 依序：
   UPDATE products SET homepage_order = 1 WHERE id = :id1;
   UPDATE products SET homepage_order = 2 WHERE id = :id2;
   ...
   ```
4. 回新 list，admin 端刷新顯示

### Flow 3: admin 從列表移除某個置頂
1. 點移除（×）→ 本地陣列 splice 拿掉那筆
2. 等使用者點「儲存排序」一起送（不每按一次就打 API）

### Flow 4: store 首頁載入
1. `useHomepagePinnedQuery()` 取置頂商品
2. `PinnedTopSection` v-if items.length > 0 才渲染（沒置頂時整段消失）
3. 渲染 ProductCard grid（複用既有元件），按 homepage_order 排

---

## 六、EVENT_MATRIX 對照

本模組**無 Event 觸發**。檢查 `docs/EVENT_MATRIX.md`：
- 純資料 toggle，不發 email
- 不影響訂單、製作、付款狀態
- 不影響庫存

---

## 七、Admin UI 拖曳設計

**技術選型**：`vue-draggable-plus`（Vue 3 原生、TS 支援、SortableJS 底層、MIT、active maintained）

**HomepagePinnedPage 結構**：
```
┌───────────────────────────────────────────────┐
│ 首頁置頂商品                  [+ 加入商品] [儲存排序] │
│ 拖曳卡片來調整 store 首頁顯示順序。Top1 在最左上方。  │
├───────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐         │
│  │ 1│ 縮圖 │ │ 2│ 縮圖 │ │ 3│ 縮圖 │         │
│  │  標題    │ │  標題    │ │  標題    │         │
│  │ on_sale  │ │ on_sale  │ │ draft⚠   │         │
│  │ [⋮] [×]  │ │ [⋮] [×]  │ │ [⋮] [×]  │         │
│  └─────────┘ └─────────┘ └─────────┘         │
└───────────────────────────────────────────────┘
```

**邊角警示**：
- 卡片若該商品 `status != on_sale` → 黃色框＋「⚠ 未上架」徽章（admin 知道排了也不會出現在 store）
- 沒任何置頂時 → empty state：「還沒有任何首頁置頂商品。點上方按鈕加入。」
- 「儲存排序」按鈕在沒變動時 disabled；有未儲存變動時 highlight

**PinProductPickerDialog**：
- 列出所有 on_sale 商品（既有 list endpoint，加 `exclude` query 排掉已置頂的）
- 縮圖 grid + 搜尋框
- 點商品 = 加入置頂尾端

---

## 八、Store 變更

- `HomePage.vue`：在 `<EditorLetterSection />` 與 `<LatestProductsSection />` 之間插入 `<PinnedTopSection />`
- `PinnedTopSection`：
  - 標題用 `SectionMasthead`：no="01" / chapter="Featured" / title="本季嚴選" / caption="hand picked"（**LatestProductsSection 的 no 改 "02" 並改 title 「最新上架」**，避免兩個 01）
  - 4 欄 grid（手機 1 欄、平板 2 欄、桌機 4 欄）
  - 沒置頂時整段不渲染（不留空白）

---

## 九、測試覆蓋

| Case | 預期 | 測試函數 |
|---|---|---|
| 列 admin pinned，DB 沒置頂 | 回空 list | test_list_pinned_empty |
| 列 admin pinned，有 3 筆置頂 | 依 homepage_order 排回 | test_list_pinned_ordered |
| POST homepage-order，空陣列 | 全部 homepage_order set NULL；回空 list | test_set_homepage_order_clear_all |
| POST homepage-order，3 筆 | 那 3 筆 order=1/2/3，其他 NULL | test_set_homepage_order_assigns_sequential |
| POST homepage-order，含不存在 id | 400 | test_set_homepage_order_rejects_unknown_id |
| POST homepage-order，含重複 id | 400 | test_set_homepage_order_rejects_duplicates |
| POST homepage-order，超過 50 筆 | 400 | test_set_homepage_order_rejects_over_limit |
| POST homepage-order，本來有 5 筆，新陣列只 2 筆 | 3 筆變 NULL、2 筆變 1/2 | test_set_homepage_order_shrinks_correctly |
| Public GET homepage-pinned，含 draft 商品 | draft 不回（仍只回 on_sale） | test_public_pinned_filters_out_draft |
| Public GET homepage-pinned，置頂但沒 active variant | 不回 | test_public_pinned_filters_out_no_active_variant |
| Public GET homepage-pinned，沒置頂 | 回空 list | test_public_pinned_empty |
| Admin product list response 含 homepage_order | 每筆都有此欄（null 或 int） | test_admin_list_includes_homepage_order |
| CheckConstraint 直接寫 homepage_order=0 | DB-level reject | test_db_rejects_zero_homepage_order |

---

## 十、規格文件同步

- `docs/schema.md`：products 表加 `homepage_order` 欄位 + 部分索引
- `docs/api.md`：
  - GET /products list / detail response 補 homepage_order
  - 新 endpoint：POST /admin/products/homepage-order
  - 新 endpoint：GET /admin/products/homepage-pinned
  - 新 endpoint：GET /products/homepage-pinned
- `docs/EVENT_MATRIX.md`：無新增 Event

---

## 十一、部署順序

1. **先 alembic upgrade head** 在 production DB（透過 Railway public proxy URL）→ ALTER TABLE + index + constraint
2. **後** push backend code → Railway redeploy
3. Admin Vercel auto deploy（拖曳頁出現）
4. Store Vercel auto deploy（PinnedTopSection 出現，空 list 自動 hide）
5. Admin 進 `/admin/homepage-pinned` 釘第一筆 → store 首頁立即可見

⚠️ 同 Module 19 部署順序，**不要先 push code 再跑 migration**（init_db.py stamp 只 stamp 不 ALTER）。

---

## 十二、已決議事項（2026-06-02 user 確認）

| # | 議題 | 決定 |
|---|---|---|
| 1 | **數量上限** | **12**（3 row × 4 col；POST endpoint > 12 筆 → 400） |
| 2 | **沒置頂時 store 行為** | **PinnedTopSection 整段 v-if 不渲染**；LatestProductsSection 照舊顯示「最新上架」 |
| 3 | **Draft 商品可否置頂** | **不可** — POST /admin/products/homepage-order 拒絕含 status ≠ on_sale 的 product_ids；admin Picker 也僅列 on_sale |
| 4 | **存檔模式** | **批次「儲存排序」按鈕** — 拖曳僅本地調順序，按按鈕才打 API；未存離開頁面跳確認框 |

### 對第三、四節的影響（已 inline 修改）

- **三、DB Model**：上限 12 不寫進 CheckConstraint（單列無法表達整表 count），改在 service layer 驗證
- **四、API 規格**：
  - POST `/admin/products/homepage-order` 上限改 **12**（原寫 50）
  - 新增驗證：所有 product_ids 必須 `status = on_sale`，否則 400 `含未上架商品`
- **七、Admin UI**：
  - 「⚠ 未上架徽章」對應的 draft 警示移除（draft 根本進不來）
  - 已達 12 筆時「+ 加入商品」按鈕 disabled，旁邊註記「已達上限 12」
  - 離開頁面有未存變動 → confirm dialog 防誤離
- **八、Store 變更**：
  - PinnedTopSection items.length === 0 → `v-if` false → 整段不渲染（含 SectionMasthead），下方 LatestProductsSection 完全不受影響

### 對應的測試 case 異動（覆蓋表第九節同步）

| Case | 預期 | 測試函數 |
|---|---|---|
| POST homepage-order，含 draft id | 400 `含未上架商品` | test_set_homepage_order_rejects_draft |
| POST homepage-order，含 off_sale id | 400 `含未上架商品` | test_set_homepage_order_rejects_off_sale |
| POST homepage-order，13 筆 | 400 `超過 12 筆上限` | test_set_homepage_order_rejects_over_limit |
| POST homepage-order，12 筆 | 成功（剛好邊界） | test_set_homepage_order_accepts_max_12 |

（取代原本「超過 50 筆」case；原 case 改名 `test_set_homepage_order_rejects_over_limit`）
