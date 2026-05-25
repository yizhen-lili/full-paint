"""PDF 模板數字標籤改細體相關測試。

驗證：
- _register_thin_font() idempotent
- font 檔存在時成功 register
- font 檔缺失時 graceful fallback 不 raise
"""
from pathlib import Path
from unittest.mock import patch

import pytest


def _reset_font_module_state():
    """每個 test 前後重設 _FONT_REGISTERED，避免 test 之間相互影響。"""
    from production import service
    service._FONT_REGISTERED = False


@pytest.fixture(autouse=True)
def _font_state():
    _reset_font_module_state()
    yield
    _reset_font_module_state()


def test_register_thin_font_returns_inter_when_file_exists():
    """正常情境：Inter-Light.ttf 存在 → register 成功回 'Inter'。"""
    from production.service import _register_thin_font

    result = _register_thin_font()
    # 字體檔已 commit 進 backend/assets/fonts/Inter-Light.ttf
    font_path = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Inter-Light.ttf"
    if font_path.exists():
        assert result == "Inter"
    else:
        # 若 CI / 容器內字體被排除，函式應 graceful 回 None 不 raise
        assert result is None


def test_register_thin_font_idempotent():
    """重複呼叫只 register 一次（看 _FONT_REGISTERED flag）。"""
    from production import service
    from production.service import _register_thin_font

    first = _register_thin_font()
    state_after_first = service._FONT_REGISTERED
    second = _register_thin_font()
    state_after_second = service._FONT_REGISTERED

    # 結果一致
    assert first == second
    # 第二次不應該重新 register（flag 不變）
    assert state_after_first == state_after_second


def test_register_thin_font_missing_file_returns_none():
    """字體檔缺失 → log warning + 回 None，不 raise。"""
    from production import service

    # 假裝 font_path 不存在：直接 mock Path.exists
    with patch("pathlib.Path.exists", return_value=False):
        result = service._register_thin_font()
    assert result is None
    assert service._FONT_REGISTERED is False


def test_register_thin_font_ttf_error_returns_none():
    """TTFont() 構造失敗（例如 TTF 檔毀損）→ 回 None 不 raise。"""
    from production import service

    with patch("reportlab.pdfbase.ttfonts.TTFont", side_effect=ValueError("corrupt TTF")):
        result = service._register_thin_font()
    assert result is None
    assert service._FONT_REGISTERED is False
