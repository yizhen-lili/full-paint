# Module 04 — Production Engine 真實整合（Phase 2）

> 取代 `production/tasks.py:11` 與 `tasks.py:46` 的 stub，將 `paint-by-number/src/pbn_gen.py` 真正接入。

## 目標

讓 admin 從 UI 上傳圖 → POST /admin/production/jobs → Celery worker 真實呼叫 PBN 引擎產出 SVG / filled 圖 / palette → 上傳 Firebase → 回寫 DB → admin UI 看得到結果。

## 範圍與排除

**Phase 2-A（本次）**：
- ✅ standard 模式 — 真實引擎呼叫
- ✅ Firebase 上傳真實檔案（svg / filled / snapped 全 gs://，公開讀走 signed URL）
- ✅ 失敗回滾：上傳失敗刪 orphan blob、DB 最終 commit 失敗也刪 orphan、status=failed、notes 寫錯誤

**Phase 2-B（後續）**：
- ⏸️ post-process（合併色塊 / 消邊界 / 平滑輪廓）真實實作
  - 需要對 PbnGen 加入「從 snapped_rgb 重新進入 output_to_svg」的能力（目前 set_final_pbn 是入口點之一，無法直接從 snapped_rgb 重啟）
  - 本次 run_post_process_job 維持 stub（status flip）以不破壞既有流程；admin UI 後處理按鈕仍可按、結果無變化（清楚標 Phase 2-B 範圍）
- ⏸️ sam_refine / sam_weighted（需 segment_anything + SAM 權重 ~360MB）
- ⏸️ print_batch PDF 真上傳（取代 stub URL）
- ⏸️ custom 舊照片 Firebase 刪除（清理 TODO）

**永遠不在範圍**：ECpay 真實整合（等 store 前端部署）

## 不修改的檔案（CLAUDE.md 強制）

- `paint-by-number/src/*.py` — 核心引擎不動。Wrapper 寫在 backend 端。

## 要建立 / 修改的檔案

| 檔案 | 動作 | 用途 |
|------|------|------|
| `backend/production/engine.py` | 新建 | PBN 引擎 wrapper：把 image/params dict 餵進 PbnGen，輸出 SVG / filled PNG / palette JSON |
| `backend/production/tasks.py` | 重寫 | 真實呼叫 engine.py + Firebase 上傳 + DB 回寫 + 錯誤處理 |
| `backend/production/service.py` | 微調 | （無新 endpoint，僅輔助函式如錯誤訊息格式化）|
| `backend/tests/production/test_engine.py` | 新建 | engine.py wrapper 單元測試（用小圖 50×50） |
| `backend/tests/production/test_tasks.py` | 新建 | tasks.py 整合測試（mock engine + mock Firebase）|

## DB 模型（不新增欄位）

`production_jobs` 既有欄位涵蓋本次需求：
- 輸入：`image_id`, `mode`, `difficulty`, `canvas_w_cm`, `canvas_h_cm`, `num_colors`, `min_brush_diam_cm`, `blur_*`, `prune_iterations`, `pruning_threshold`, `min_ratio_multiplier`, `bg_extra_blur`
- 輸出：`svg_url`, `filled_template_url`, `snapped_rgb_url`, `palette_json`, `num_colors_used`
- 狀態：`status` (pending → processing → completed | failed | cancelled), `notes`

## 業務流程

### 主流程：production.run_job（取代 stub）

```
1. 讀 job from DB by job_id
   - 找不到 → log warning，return（無條件 return：避免重試把錯誤放大）
2. 標記 status=processing
3. 從 Firebase 下載 image.original_url 到 temp dir
   - 失敗 → status=failed, notes="無法下載原圖：{錯誤}"
4. 解 job 的引擎參數（DETAIL_PRESETS 已內嵌在 difficulty 對應，預設用 detail="標準"）
5. 呼叫 engine.generate_standard(image_path, params, output_dir)
   - 內部：PbnGen → cluster_colors → set_final_pbn → merge_tiny_colors → output_to_svg → output_filled_from_template
   - 回傳 {svg_path, filled_path, snapped_rgb_path, palette_data}
   - 失敗（CV2 / KMeans 出錯）→ status=failed, notes=錯誤摘要，清理 temp dir，無上傳
6. 上傳 3 個檔案到 Firebase Storage：
   - production_jobs/{job_id}/template.svg → svg_url（私有，gs://）
   - production_jobs/{job_id}/filled_template.png → filled_template_url（公開讀，HTTPS）
   - production_jobs/{job_id}/snapped_rgb.png → snapped_rgb_url（私有，gs://）
   - 任一上傳失敗 → 嘗試清理已上傳，status=failed
7. 寫 DB：svg_url, filled_template_url, snapped_rgb_url, palette_json, num_colors_used, status=completed
8. 清理 temp dir
```

### 後處理：production.run_post_process（保留 stub，Phase 2-B 補）

本次保留為 stub（status pending → completed），不執行真實後處理。理由：

- PbnGen 目前的入口為 `set_final_pbn`（從 BGR 圖經 KMeans 出發），無「從 snapped_rgb 重啟」的能力
- 真實實作需擴展 PbnGen（`paint-by-number/src/`），這違反 CLAUDE.md「不修改核心引擎」原則
- 替代方案是在 wrapper 層用 OpenCV 直接處理 snapped_rgb，但合併色塊／消邊界的實作邏輯與 PbnGen 內部不同（風險高、需要對演算法正確性審查）

Phase 2-B 將與引擎作者協調是否擴展 PbnGen 介面，或在 wrapper 層自行重寫後處理操作。

### 失敗回滾

- 任何階段失敗 → 已上傳的 Firebase 檔刪除（避免 orphan）
- DB job 留著（不刪），status=failed，notes 寫錯誤摘要
- 不重試（max_retries=0 沿用既有設定）

## EVENT_MATRIX 對照

對應的 Event：
- **E14 production_job.completed** → 引擎完成、寫 svg_url / filled_template_url / palette_json
- **E15 production_job.failed** → 引擎或上傳失敗、status=failed、notes 寫錯誤
- **副作用**：custom_request 自動轉 quote_pending → negotiating（已在 service.create_jobs 處理，本次不動）

無新增 Email / 通知（admin 是 polling job 列表，不主動推）。

## 測試覆蓋

### test_engine.py（新建）— wrapper 單元測試
- `test_generate_standard_small_image`：50×50 純色圖 → 確認回傳 dict 含 4 個 path、檔案實際存在
- `test_generate_standard_invalid_image`：壞 bytes 餵入 → raise ValueError
- `test_generate_standard_palette_format`：palette_data 結構符合 schema (template_id, rgb, hex, pixels, percent)
- `test_calc_min_radius_px`：純函式驗算（畫布 30cm × 1024px → 正確 px 半徑）

### test_tasks.py（新建）— Celery 任務整合測試
- `test_run_production_job_success`（mock engine + mock Firebase）：job 從 pending → completed，DB 寫入 4 個 url + palette_json + num_colors_used
- `test_run_production_job_engine_error`：engine raise → status=failed, notes 含錯誤摘要，未上傳 Firebase
- `test_run_production_job_firebase_upload_error`：第 2 個檔上傳失敗 → 已上傳的第 1 個被刪除、status=failed
- `test_run_production_job_image_download_error`：Firebase download 404 → status=failed
- `test_run_production_job_not_found`：job_id 不存在 → silent return（log warning）

### test_post_process.py（沿用既有 mock 路徑）
- 既有的 post-process 測試已用 mock task → 通過。
- Phase 2-B 補真引擎測試。

## 規格依據

- `paint-by-number/src/run.py:235-374` — run_single_level 為引擎呼叫範本
- `docs/requirements/admin_production.md §6, §11` — production / post-process 規範
- `docs/schema.md:235-253` — production_jobs 欄位
- `docs/api.md:475-534` — production endpoints

## 依賴 / 環境

- Redis（broker）：Docker container `yiimui-redis:6379`，已啟
- Celery worker：`celery -A core.celery_app worker --pool=solo --loglevel=info`
- 引擎依賴：`opencv-python`, `numpy`, `scikit-learn`, `kneed`, `shapely`, `svgwrite`, `matplotlib`（已在 paint-by-number 的 requirements）— backend 端需確認 venv 已裝
- Firebase：既有 credentials JSON，bucket `paint-by-number-d9fa3.firebasestorage.app`

## 待確認事項（無）

所有規格已涵蓋；wrapper 設計沿用 `run_single_level` 的呼叫順序，不新增業務邏輯。
