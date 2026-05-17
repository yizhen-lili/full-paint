"""svg_consolidate 單元測試 — 純函式，不需 DB / Firebase。

驗證重點：
- 同 output_label 的多 polygon 真的被 union 成單一 path
- 相鄰的同色 polygon 合併後內部邊界消失
- 分離的同色 polygon 變成 MultiPolygon，各 part 各標一次編號
- 不同 output_label 之間的邊界保留
"""
import xml.etree.ElementTree as ET

import pytest

from palette.svg_consolidate import _parse_points, _tint_hex, regenerate_merged_svg

_NS = "http://www.w3.org/2000/svg"
_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'


# pbn_gen 的 tint 計算：25% 原色 + 75% 白
def _tint(r: int, g: int, b: int) -> str:
    return _tint_hex([r, g, b])


# 模擬 palette_json（pbn_gen 輸出格式：template_id + algorithm rgb + pixels）
_PALETTE_JSON = [
    {"template_id": 1, "rgb": [247, 167, 132], "pixels": 4000},  # tint = #FDE9E0
    {"template_id": 2, "rgb": [100, 50, 200],  "pixels": 3500},  # tint = #D8CBF1
    {"template_id": 3, "rgb": [50, 200, 100],  "pixels": 2500},  # tint = #CBF1D8
]


def _make_svg(polys: list[tuple[str, list[tuple[int, int]]]]) -> bytes:
    """生成 mini SVG：each tuple = (fill_hex, points)。"""
    polygons = "".join(
        f'<polygon id="r{i}" points="{" ".join(f"{x},{y}" for x, y in pts)}" '
        f'fill="{fill}" stroke="#AAAAAA" stroke-width="0.5"/>'
        for i, (fill, pts) in enumerate(polys)
    )
    return (
        f'{_HEADER}'
        f'<svg xmlns="{_NS}" viewBox="0 0 100 100">'
        f'<rect x="0" y="0" width="100" height="100" fill="white"/>'
        f'{polygons}'
        f'</svg>'
    ).encode("utf-8")


def _parse_paths(svg_bytes: bytes):
    root = ET.fromstring(svg_bytes)
    return root.findall(f"{{{_NS}}}path")


def _parse_texts(svg_bytes: bytes) -> list[str]:
    root = ET.fromstring(svg_bytes)
    return [t.text for t in root.iter(f"{{{_NS}}}text")]


# ── 基礎工具函式 ──────────────────────────────────────────────────────────

def test_tint_hex_matches_pbn_gen():
    """tint 計算須與 pbn_gen 的公式完全對應。"""
    # 247, 167, 132 → r=int(247*0.25+255*0.75)=253，g=233，b=224
    assert _tint_hex([247, 167, 132]) == "#FDE9E0"
    assert _tint_hex([100, 50, 200]) == "#D8CBF1"
    assert _tint_hex([0, 0, 0]) == "#BFBFBF"
    assert _tint_hex([255, 255, 255]) == "#FFFFFF"


def test_parse_points_comma_separated():
    assert _parse_points("0,0 10,0 0,10") == [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]


def test_parse_points_space_separated():
    assert _parse_points("0 0 10 0 0 10") == [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]


def test_parse_points_handles_floats():
    assert _parse_points("0.5,0.5 10.5,0.5 0.5,10.5") == [(0.5, 0.5), (10.5, 0.5), (0.5, 10.5)]


# ── 合併行為 ─────────────────────────────────────────────────────────────

def test_three_polygons_three_colors_three_groups():
    """3 個 polygon 各對到不同 output_label → 輸出 3 個 path、3 個 text。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (40, 0), (0, 40)]),         # tid 1
        (_tint(100, 50, 200),  [(60, 0), (100, 0), (60, 40)]),      # tid 2
        (_tint(50, 200, 100),  [(0, 60), (40, 60), (0, 100)]),      # tid 3
    ])
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},
        {"output_label": 2, "rgb": [100, 50, 200]},
        {"output_label": 3, "rgb": [50, 200, 100]},
    ]
    label_map = {1: 1, 2: 2, 3: 3}
    out = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    paths = _parse_paths(out)
    texts = _parse_texts(out)
    assert len(paths) == 3
    assert sorted(texts) == ["1", "2", "3"]


def test_same_label_disconnected_becomes_multipolygon():
    """兩個分離 polygon 對到同 output_label → 1 個 path（MultiPolygon）+ 2 個 text（各 part）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (20, 0), (0, 20)]),         # tid 1
        (_tint(50, 200, 100),  [(80, 80), (100, 80), (100, 100)]),  # tid 3 (對 same physical)
    ])
    # template 1 跟 template 3 都對到 output_label 1
    label_map = {1: 1, 2: 2, 3: 1}
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},
        {"output_label": 2, "rgb": [100, 50, 200]},
    ]
    out = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    paths = _parse_paths(out)
    texts = _parse_texts(out)
    # 兩個 polygon 都 label 1，分離 → 1 path（MultiPolygon）
    assert len(paths) == 1
    # 各 part 各放一個 "1" → 兩個 text
    assert texts == ["1", "1"]


def test_same_label_adjacent_merges_into_single_polygon():
    """兩個相鄰 polygon 對到同 output_label → 合併成單一 polygon，內部邊界消失。"""
    # 兩個三角形共用邊 (0,50)-(50,0)
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (50, 0), (0, 50)]),     # tid 1，左下三角
        (_tint(50, 200, 100),  [(50, 0), (0, 50), (50, 50)]),   # tid 3，右下三角
    ])
    label_map = {1: 1, 2: 2, 3: 1}   # tid 1 與 tid 3 → 同 output_label 1
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},
    ]
    out = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    paths = _parse_paths(out)
    texts = _parse_texts(out)
    # 合併成單一 Polygon → 1 path + 1 text
    assert len(paths) == 1
    assert texts == ["1"]
    # path d 不應該還有內部邊界（兩個 M..Z 才是 MultiPolygon；合併後只有一個外環）
    d = paths[0].get("d", "")
    assert d.count("M ") == 1, f"expected single outer ring, got: {d}"


def test_path_has_fill_rule_evenodd():
    """path 必須帶 fill-rule=evenodd 才能正確渲染洞（unary_union 可能產出含洞 polygon）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (50, 0), (0, 50)]),
    ])
    out = regenerate_merged_svg(
        svg, {1: 1}, _PALETTE_JSON,
        [{"output_label": 1, "rgb": [247, 167, 132]}],
    )
    paths = _parse_paths(out)
    assert paths[0].get("fill-rule") == "evenodd"


def test_path_uses_physical_color_tint():
    """合併後的 path fill 應該是 palette_final 的 RGB 算出的 tint，
    而非原 polygon 的 algorithm tint（finalize 後可能 RGB 已改）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)]),
    ])
    # palette_final 給不同的 RGB（模擬使用者校正過 RGB 後的色）
    out = regenerate_merged_svg(
        svg, {1: 1}, _PALETTE_JSON,
        [{"output_label": 1, "rgb": [10, 20, 30]}],
    )
    paths = _parse_paths(out)
    expected_tint = _tint(10, 20, 30)
    assert paths[0].get("fill") == expected_tint


def test_polygon_with_unknown_fill_skipped():
    """polygon fill 不在 palette_json 任何 tint → skip，不影響其他 polygon。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)]),     # 認得，tid 1
        ("#123456",            [(20, 0), (30, 0), (20, 10)]),   # 不認得 fill
    ])
    out = regenerate_merged_svg(
        svg, {1: 1}, _PALETTE_JSON,
        [{"output_label": 1, "rgb": [247, 167, 132]}],
    )
    paths = _parse_paths(out)
    assert len(paths) == 1   # 只有第一個被處理


def test_empty_label_map_raises():
    svg = _make_svg([(_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)])])
    with pytest.raises(ValueError, match="label_map 不可為空"):
        regenerate_merged_svg(svg, {}, _PALETTE_JSON, [])


def test_invalid_svg_raises():
    with pytest.raises(ValueError, match="SVG 解析失敗"):
        regenerate_merged_svg(b"<not valid", {1: 1}, _PALETTE_JSON, [])


def test_preserves_viewbox():
    svg = _make_svg([(_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)])])
    out = regenerate_merged_svg(
        svg, {1: 1}, _PALETTE_JSON,
        [{"output_label": 1, "rgb": [247, 167, 132]}],
    )
    root = ET.fromstring(out)
    assert root.get("viewBox") == "0 0 100 100"


def test_no_recognizable_polygons_falls_back_to_renumber():
    """所有 polygon fill 都不在 palette_json → fallback 到 renumber_svg_labels。"""
    svg = (
        f'{_HEADER}'
        f'<svg xmlns="{_NS}" viewBox="0 0 100 100">'
        f'<polygon id="r0" points="0,0 10,0 0,10" fill="#000000"/>'
        f'<g id="0"><text x="5" y="5">1</text></g>'
        f'</svg>'
    ).encode("utf-8")
    out = regenerate_merged_svg(svg, {1: 7}, _PALETTE_JSON, [])
    # fallback: text content 應該變成 "7"
    texts = _parse_texts(out)
    assert "7" in texts
