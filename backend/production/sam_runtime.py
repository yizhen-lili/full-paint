"""SAM (Segment Anything) 推論 runtime — 與 FastAPI 同進程懶載入單例。

依規格 [admin_production.md §1.3]：
- 服務啟動時不載入模型；第一次呼叫才載入並常駐記憶體
- 第一次冷啟動 ~5-10 秒；後續推論 1-3 秒
- 使用 vit_b checkpoint（375MB）；模型路徑由 settings.sam_model_path 提供

設計：
- `get_sam_predictor()` 模組級單例（threading.Lock 保護初始化）
- `predict_mask(predictor, image_bgr, sam_points)` 同步推論；
  caller 用 asyncio.to_thread 包裹避免 block event loop
"""
from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import numpy as np

# 模組級單例 + 初始化 lock（thread-safe lazy load）
_PREDICTOR: Any = None
_LOAD_LOCK = threading.Lock()


def get_sam_predictor() -> Any:
    """懶載入 SAM predictor 單例。

    第一次呼叫：
      1. 取 settings.sam_model_path（缺失 → ValueError）
      2. 確認檔案存在（不在 → FileNotFoundError）
      3. 載入 sam_model_registry["vit_b"](checkpoint=...) + to("cpu")
      4. 包成 SamPredictor 並快取於模組級變數

    後續呼叫：直接返回快取。

    raise:
      ValueError — settings.sam_model_path 未設定
      FileNotFoundError — 模型檔不存在
      ImportError — segment_anything 未安裝
    """
    global _PREDICTOR

    if _PREDICTOR is not None:
        return _PREDICTOR

    with _LOAD_LOCK:
        # double-check：可能其他 thread 已載入完成
        if _PREDICTOR is not None:
            return _PREDICTOR

        from core.config import settings  # noqa: PLC0415

        model_path = settings.sam_model_path
        if not model_path:
            raise ValueError(
                "settings.sam_model_path 未設定（環境變數 SAM_MODEL_PATH）"
            )
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"SAM 模型檔不存在：{model_path}")

        try:
            import torch  # noqa: PLC0415
            from segment_anything import (  # noqa: PLC0415
                SamPredictor,
                sam_model_registry,
            )
        except ImportError as e:
            raise ImportError(
                "segment-anything 未安裝（pip install segment-anything）"
            ) from e

        logger.info("Loading SAM vit_b model from %s ...", model_path)
        # segment_anything 1.0 build_sam.py 內部用 `torch.load(file_object)`
        # 在 torch 2.5 + Windows 上會 segfault（無論 weights_only=True/False）。
        # 唯一穩定路徑是 `torch.load(path_string, weights_only=True)`。
        # 因此繞開 segment_anything 的 checkpoint 載入：先建空模型、再自己 load state_dict。
        # weights_only=True 同時防 pickle 反序列化 RCE（部署到 Linux 後仍保留此防護）。
        sam = sam_model_registry["vit_b"](checkpoint=None)
        state_dict = torch.load(model_path, weights_only=True, map_location="cpu")
        sam.load_state_dict(state_dict)
        # 顯式 eval mode（避免依賴 segment_anything 內部 _build_sam 順序的隱含契約）
        sam.eval()
        sam.to("cpu")
        _PREDICTOR = SamPredictor(sam)
        logger.info("SAM predictor ready")

    return _PREDICTOR


def predict_mask(
    predictor: Any,
    image_bgr: np.ndarray,
    sam_points: list[dict],
) -> np.ndarray:
    """同步呼叫 SAM 推論 → 回傳 bool 遮罩（True = 選取區）。

    sam_points 格式：[{x: float, y: float, label: int (1=foreground/0=background)}]

    raise:
      ValueError — sam_points 為空（caller 應先驗證）
    """
    import cv2  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    if not sam_points:
        raise ValueError("sam_points 不能為空")

    # SamPredictor.set_image 接受 RGB
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    predictor.set_image(image_rgb)

    points = np.array([[float(p["x"]), float(p["y"])] for p in sam_points], dtype=np.float32)
    labels = np.array([int(p["label"]) for p in sam_points], dtype=np.int32)

    masks, scores, _ = predictor.predict(
        point_coords=points,
        point_labels=labels,
        multimask_output=True,
    )
    # 多 mask 取分數最高那一張（mirror paint-by-number/src/sam_select.py:predict_mask_sam）
    return masks[int(np.argmax(scores))]


def reset_predictor_for_test() -> None:
    """測試專用：清掉單例（讓下個測試重新走載入路徑）。"""
    global _PREDICTOR
    _PREDICTOR = None
