"""SAM 真實 smoke test：真載 vit_b 模型 + 真跑 inference + 印結果。

用途：Phase B 完成後驗證真模型能用（pytest 走 mock 不能驗證這個）。
不操作 DB / Firebase；純驗證 sam_runtime.py 對接 segment_anything 這層工程是對的。

執行：
    cd backend
    venv/Scripts/python scripts/smoke_test_sam.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ── 設定環境變數（本地 dev 預設指向 paint-by-number/models/sam_vit_b.pth）─────
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent
_DEFAULT_MODEL = _REPO_ROOT / "paint-by-number" / "models" / "sam_vit_b.pth"

if "SAM_MODEL_PATH" not in os.environ:
    os.environ["SAM_MODEL_PATH"] = str(_DEFAULT_MODEL)

# 把 backend 加進 sys.path 才能 import production
sys.path.insert(0, str(_BACKEND_DIR))


def main():
    import cv2
    import numpy as np

    from production.sam_runtime import get_sam_predictor, predict_mask

    print(f"[1/4] SAM_MODEL_PATH = {os.environ['SAM_MODEL_PATH']}")
    if not Path(os.environ["SAM_MODEL_PATH"]).exists():
        print("[ERROR] 模型檔不存在，請確認路徑")
        sys.exit(1)

    # 載入測試圖片：用 paint-by-number/images 內任一張
    images_dir = _REPO_ROOT / "paint-by-number" / "images"
    candidates = sorted(images_dir.glob("*.jpg"))
    if not candidates:
        print(f"[ERROR] {images_dir} 沒有 .jpg 測試圖")
        sys.exit(1)
    test_img = candidates[0]
    print(f"[2/4] 測試圖：{test_img.name}")

    # 用 imdecode 處理含中文路徑（同 engine.py 慣例）
    img_bgr = cv2.imdecode(
        np.fromfile(str(test_img), dtype=np.uint8), cv2.IMREAD_COLOR,
    )
    h, w = img_bgr.shape[:2]
    print(f"      尺寸：{w}x{h}")

    # 點選圖片中央作為前景點
    sam_points = [{"x": float(w // 2), "y": float(h // 2), "label": 1}]

    print("[3/4] 載入 SAM vit_b 模型（首次冷啟 5-10 秒）...")
    t0 = time.time()
    predictor = get_sam_predictor()
    t_load = time.time() - t0
    print(f"      載入耗時：{t_load:.2f}s")

    print("[4/4] 推論 mask...")
    t0 = time.time()
    mask = predict_mask(predictor, img_bgr, sam_points)
    t_inf = time.time() - t0
    coverage = float(np.sum(mask)) / mask.size
    print(f"      推論耗時：{t_inf:.2f}s")
    print(f"      mask shape：{mask.shape}")
    print(f"      mask coverage：{coverage:.4f}（{coverage*100:.2f}%）")

    # 二次呼叫驗證單例（不重新載）
    print("[5/5] 二次推論驗證單例（應 < 5s）...")
    t0 = time.time()
    mask2 = predict_mask(predictor, img_bgr, sam_points)
    t_inf2 = time.time() - t0
    print(f"      二次推論耗時：{t_inf2:.2f}s")
    assert mask2.shape == mask.shape

    print("\n[OK] SAM smoke test PASSED")
    print(f"     首次冷啟：{t_load:.2f}s | 推論：{t_inf:.2f}s | 二次推論：{t_inf2:.2f}s")


if __name__ == "__main__":
    main()
