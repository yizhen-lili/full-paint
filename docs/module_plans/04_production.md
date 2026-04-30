# Module 5：製作系統（Admin Production）實作規劃

> 對照規格：`requirements/admin_production.md`、`schema.md`（images、production_jobs）、`api.md`（模組七、模組十九部分）
> 撰寫日期：2026-04-20

> **⚠️ Custom Requests 模組建立時必須補做：**
> `production_jobs.custom_request_id` 目前為純 UUID（無 FK），
> custom_requests 表建立後需在 custom_requests migration 補上：
> `op.create_foreign_key(None, 'production_jobs', 'custom_requests', ['custom_request_id'], ['id'])`

---

## 一、要建立的檔案

```
backend/
├── core/
│   ├── firebase.py           ✅ 已建立
│   └── celery_app.py         ← Celery 應用程式設定
├── production/
│   ├── __init__.py
│   ├── router.py             # /admin/images/*、/admin/production/*
│   ├── service.py            # 業務邏輯
│   ├── tasks.py              # Celery tasks
│   ├── models.py             # Image、ProductionJob ORM
│   └── schemas/
│       ├── __init__.py
│       ├── request.py
│       └── response.py
├── upload/
│   ├── __init__.py
│   └── router.py             # POST /upload/production-image
└── tests/production/
    ├── __init__.py
    └── test_production.py
```

**修改現有檔案：**
- `main.py`：加入 production_router、upload_router
- `tests/conftest.py`：加入 `import production.models`
- `scripts/reset_test_db.py`、`drop_test_db.py`：加入 `import production.models`
- `migrations/`：新增 migration（images + production_jobs 兩張表）

---

## 二、DB 模型

### Image

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID PK | |
| uploader_id | UUID FK→users.id NOT NULL | |
| original_url | VARCHAR NOT NULL | Firebase Storage 公開 URL |
| filename | VARCHAR NOT NULL | |
| width | INTEGER NOT NULL | px |
| height | INTEGER NOT NULL | px |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |

### ProductionJob

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID PK | |
| image_id | UUID FK→images.id nullable | 手動上傳時填入 |
| custom_request_id | UUID nullable | 跨模組，Phase 1 保留欄位但不驗證 |
| status | ENUM('pending','processing','completed','failed','cancelled') NOT NULL DEFAULT 'pending' | |
| approved | BOOLEAN NOT NULL DEFAULT false | |
| detail | ENUM('rough','standard','detailed','premium') NOT NULL | |
| difficulty | ENUM('beginner','elementary','intermediate','advanced') NOT NULL | |
| mode | ENUM('standard','sam_refine','sam_weighted') NOT NULL DEFAULT 'standard' | |
| canvas_w_cm | NUMERIC(6,1) NOT NULL | |
| canvas_h_cm | NUMERIC(6,1) NOT NULL | |
| num_colors | INTEGER nullable | |
| blur_ksize | INTEGER nullable | |
| blur_sigma_color | NUMERIC(6,2) nullable | |
| blur_sigma_space | NUMERIC(6,2) nullable | |
| prune_iterations | INTEGER nullable | |
| pruning_threshold | NUMERIC(10,8) nullable | |
| min_ratio_multiplier | NUMERIC(6,2) nullable | |
| bg_extra_blur | INTEGER nullable | |
| min_brush_diam_cm | NUMERIC(4,2) NOT NULL DEFAULT 1.0 | |
| extra_colors | INTEGER nullable | sam_refine 專用 |
| weight_ratio | NUMERIC(4,2) nullable | sam_weighted 專用（0.5~0.8） |
| sam_points | JSONB nullable | [{x,y,label}] |
| polygons | JSONB nullable | [[[x,y],...]] |
| mask_url | VARCHAR nullable | Firebase 私有 |
| mask_coverage | NUMERIC(6,2) nullable | 0~1 比例（純 sam_points 等 worker 推論時為 null） |
| svg_url | VARCHAR nullable | Firebase 私有 |
| filled_template_url | VARCHAR nullable | Firebase 公開 |
| snapped_rgb_url | VARCHAR nullable | Firebase 私有 |
| palette_json | JSONB nullable | [{template_id, rgb, hex, pixels, percent}] |
| num_colors_used | INTEGER nullable | |
| approved | BOOLEAN NOT NULL DEFAULT false | |
| notes | TEXT nullable | |
| batch_id | UUID nullable | 同批 job 共用 |
| created_at | TIMESTAMP NOT NULL DEFAULT now() | |
| approved_at | TIMESTAMP nullable | |

---

## 三、Celery 設定（core/celery_app.py）

```python
from celery import Celery
from core.config import settings

celery_app = Celery("paintlearn", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
```

**批次串行執行機制：**
- 多筆 jobs 共用 `batch_id`
- `POST /admin/production/jobs` 呼叫 `chain(task1.si(), task2.si(), ...)` 確保依序執行
- 任一 job 失敗 → `on_failure` 取消同 batch_id 後續未執行 jobs（status = cancelled）

---

## 四、實作分階段

### Phase 1（本規劃書範圍）

```
POST /upload/production-image  → Firebase 簽名上傳 URL
POST /admin/images             → 登記圖片
GET  /admin/images             → 列表
POST /admin/production/jobs    → 建立 job + dispatch Celery（stub task）
GET  /admin/production/jobs    → 列表（含篩選分頁）
GET  /admin/production/jobs/{id} → 詳情
```

### Phase 2（下一規劃書）

```
GET  /admin/production/jobs/{id}/signed-url    → 私有檔案簽名 URL
POST /admin/production/jobs/{id}/approve       → 確認儲存
```

### Phase 3（已規劃）

```
POST /admin/production/jobs/{id}/post-process/merge-color
POST /admin/production/jobs/{id}/post-process/eliminate-border
```

> smooth-contour 已下架（2026-04-30）：相鄰 polygon 共享邊界對齊實作工時不划算，
> output_to_svg 內建 _smooth_quantized 已提供基本平滑。

**共同行為（Phase 3 stub）：**
- 前置條件：job 必須存在（404）、status=completed（400）
- 設 `approved=false`、`status=processing`，commit
- 派 Celery task（stub：改回 completed，不跑真實引擎）
- 回傳 202 Accepted + JobDetailResponse

**Request schemas：**
- `merge-color`：`{ "source_template_id": int, "target_template_id": int }`（兩個區塊編號不可相同）
- `eliminate-border`：`{ "absorbed_template_id": int, "surviving_template_id": int }`（不可相同）

**新增 Celery task：** `run_post_process_job(job_id)` — stub，只把 status 改回 completed

### Phase 4（最後）

```
POST /admin/production/jobs/{id}/sam-mask
GET  /admin/production/jobs/{id}/export-pdf
```

---

## 五、Endpoints 詳細規格（Phase 1）

### POST /upload/production-image（admin）

**流程：**
1. 用 Firebase Admin SDK 產生 Signed Upload URL（PUT 方式，15 分鐘 TTL）
2. 同時計算公開可讀的 public_url
3. 回傳兩個 URL，前端直接 PUT 上傳至 Firebase，不經過後端

**Response 200：**
```json
{ "upload_url": "https://storage.googleapis.com/...", "public_url": "https://storage.googleapis.com/..." }
```

---

### POST /admin/images（admin）

**Request：** `{ "original_url", "filename", "width", "height" }`

**流程：**
1. 建立 Image 記錄（uploader_id = operator.id）
2. 回傳 ImageResponse

**驗證：** width、height 必須 > 0

**Response 201：** ImageResponse

---

### GET /admin/images（admin）

**Query：** `page=1&page_size=20`

**Response 200：** 分頁列表，items 含 id、filename、original_url、width、height、created_at

---

### POST /admin/production/jobs（admin）

**Request：**
```json
{
  "image_id": "uuid|null",
  "custom_request_id": "uuid|null",
  "jobs": [{ ...per-job params... }]
}
```

**驗證規則：**
1. `image_id` 與 `custom_request_id` 不能同時為 null（至少一個）
2. `image_id` 若有值 → 查 images 表確認存在，否則 404
3. `jobs` 長度 1~10
4. `mode=sam_refine` → `extra_colors` 必填（> 0）
5. `mode=sam_weighted` → `weight_ratio` 必填（0.5 ~ 0.8）
6. `weight_ratio` 若有值 → 必須在 0.5 ~ 0.8 之間

**批次 vs 單筆：**
- jobs 長度 = 1 → `batch_id = null`
- jobs 長度 > 1 → 產生一個新 UUID 作為 `batch_id`，所有 jobs 共用

**Celery dispatch（Phase 1 stub）：**
- 每筆 job 建立後呼叫 `run_production_job.si(job_id)` 
- 批次時用 `chain(*tasks)` 確保依序
- Stub task 只把 status 改為 completed（不真的跑引擎）

**Response 201：**
```json
{ "batch_id": "uuid|null", "job_ids": ["uuid"] }
```

---

### GET /admin/production/jobs（admin）

**Query 參數：**

| 參數 | 說明 |
|------|------|
| status | pending/processing/completed/failed/cancelled |
| approved | true/false |
| batch_id | UUID |
| image_id | UUID |
| page | default=1 |
| page_size | default=20 max=100 |

**Response 200：** 分頁列表，items 含 id、status、approved、detail、difficulty、mode、canvas_w_cm、canvas_h_cm、batch_id、created_at

---

### GET /admin/production/jobs/{id}（admin）

**Response 200：** 完整 ProductionJobResponse（含 palette_json、所有參數欄位）

**找不到 → 404**

---

## 六、tasks.py（Celery stub）

```python
@celery_app.task(bind=True, name="production.run_job")
def run_production_job(self, job_id: str):
    # Phase 1：stub — 只更新 status，不跑引擎
    # Phase 2 起替換為真實邏輯
    ...
    job.status = "completed"
    db.commit()
```

批次失敗機制：`on_failure` callback 把同 batch_id 的 pending jobs 改為 cancelled。

---

## 七、測試覆蓋（Phase 1）

### POST /upload/production-image
| 情境 | 預期 |
|------|------|
| admin 呼叫 | 200，回傳 upload_url 和 public_url |
| 非 admin | 403 |

### POST /admin/images
| 情境 | 預期 |
|------|------|
| 正常建立 | 201，回傳 ImageResponse |
| width=0 | 422 |
| 非 admin | 403 |

### GET /admin/images
| 情境 | 預期 |
|------|------|
| 有資料 | 200，分頁正確 |
| 非 admin | 403 |

### POST /admin/production/jobs
| 情境 | 預期 |
|------|------|
| 單筆 standard | 201，batch_id=null，job_ids 有 1 個 |
| 多筆（批次） | 201，batch_id 有值，job_ids 有 N 個 |
| image_id 和 custom_request_id 都 null | 422 |
| image_id 不存在 | 404 |
| mode=sam_refine 但無 extra_colors | 422 |
| mode=sam_weighted 但 weight_ratio 超範圍 | 422 |
| 非 admin | 403 |

### GET /admin/production/jobs
| 情境 | 預期 |
|------|------|
| 無篩選 | 200，分頁正確 |
| status 篩選 | 200，只回傳指定 status |
| batch_id 篩選 | 200，只回傳同批 |
| 非 admin | 403 |

### GET /admin/production/jobs/{id}
| 情境 | 預期 |
|------|------|
| 存在 | 200，完整欄位 |
| 不存在 | 404 |
| 非 admin | 403 |

---

---

## 八、Phase 2 Endpoints 規格

### GET /admin/production/jobs/{id}/signed-url（admin）

**用途：** 讓管理員預覽私有 Firebase 檔案（svg、snapped_rgb）。`filled_template_url` 為公開檔案，直接使用 DB 儲存的 URL 即可，不需簽名。

**流程：**
1. 查詢 job，不存在 → 404
2. 對 `svg_url`、`snapped_rgb_url` 各自產生 Firebase Signed URL（GET 方式，15 分鐘 TTL）
3. 若對應 URL 欄位為 null（檔案尚未產生），該欄位回傳 null

**Response 200：**
```json
{
  "svg_signed_url": "https://...|null",
  "snapped_rgb_signed_url": "https://...|null"
}
```

---

### POST /admin/production/jobs/{id}/approve（admin）

**業務規則：**
1. 查詢 job，不存在 → 404
2. `status != completed` → 422（只有完成的 job 才能核准）
3. 已經 `approved=true` → 直接回傳 200（idempotent）
4. 設 `approved=true`、`approved_at=now()`

**Response 200：** JobDetailResponse（完整 job 資料）

---

### POST /admin/production/jobs/{id}/unapprove（admin）

**業務規則：**
1. 查詢 job，不存在 → 404
2. 已經 `approved=false` → 直接回傳 200（idempotent）
3. 設 `approved=false`、`approved_at=null`

**Response 200：** JobDetailResponse（完整 job 資料）

---

## 九、測試覆蓋（Phase 2）

### GET /admin/production/jobs/{id}/signed-url
| 情境 | 預期 |
|------|------|
| job 存在且有 svg_url | 200，svg_signed_url 有值 |
| job 存在但 svg_url=null | 200，svg_signed_url=null |
| job 不存在 | 404 |
| 非 admin | 403 |
| 未登入 | 401 |

### POST /admin/production/jobs/{id}/approve
| 情境 | 預期 |
|------|------|
| status=completed，未核准 | 200，approved=true |
| 已經 approved | 200（idempotent） |
| status=pending | 422 |
| job 不存在 | 404 |
| 非 admin | 403 |
| 未登入 | 401 |

### POST /admin/production/jobs/{id}/unapprove
| 情境 | 預期 |
|------|------|
| 已核准 → 撤銷 | 200，approved=false，approved_at=null |
| 已經 unapproved | 200（idempotent） |
| job 不存在 | 404 |
| 非 admin | 403 |
| 未登入 | 401 |

---

## 十、待確認事項

**Q1：`POST /upload/production-image` 需要 request body 嗎？**
→ 規格只說 `POST /upload/production-image`，參考 `POST /upload/product-image` 的格式，應需要 `filename` 和 `content_type`。假設同格式。

**Q2：Celery task 在測試中如何 mock？**
→ 使用 `unittest.mock.patch("production.tasks.run_production_job.delay")`，確認 `.delay()` 有被呼叫即可，不真的執行。

**Q3：`custom_request_id` 在 Phase 1 的處理？**
→ 存入 DB 但不驗證 custom_requests 表存在（該表尚未建立），Phase 1 只做格式驗證（UUID 格式）。
