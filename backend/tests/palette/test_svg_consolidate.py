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
    ).encode()


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
    out, _ = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    paths = _parse_paths(out)
    texts = _parse_texts(out)
    assert len(paths) == 3
    assert sorted(texts) == ["1", "2", "3"]


def test_same_label_disconnected_becomes_two_parts():
    """兩個分離 polygon 對到同 output_label → per-part 渲染：2 條 path（各一 part，
    都 id=o1）+ 2 個 text（各 part 一個）。"""
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
    out, _ = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    paths = _parse_paths(out)
    texts = _parse_texts(out)
    # per-part：兩個分離 part → 2 條 path，都是 o1
    assert len(paths) == 2
    assert all(p.get("id") == "o1" for p in paths)
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
    out, _ = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    paths = _parse_paths(out)
    texts = _parse_texts(out)
    # 合併成單一 Polygon → 1 path + 1 text
    assert len(paths) == 1
    assert texts == ["1"]
    # path d 不應該還有內部邊界（兩個 M..Z 才是 MultiPolygon；合併後只有一個外環）
    d = paths[0].get("d", "")
    assert d.count("M ") == 1, f"expected single outer ring, got: {d}"


def test_same_label_overlapping_dedups_to_one_text():
    """同 output_label 兩塊「疊在一點」(~7px < 12) → 只放一個編號（避免同號疊字）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(10, 10), (20, 10), (10, 20)]),   # tid 1，label ~13,13
        (_tint(50, 200, 100),  [(17, 10), (27, 10), (17, 20)]),   # tid 3，label ~20,13 → 同 label 1
    ])
    label_map = {1: 1, 2: 2, 3: 1}
    palette_final = [{"output_label": 1, "rgb": [247, 167, 132]}]
    out, _ = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    texts = _parse_texts(out)
    assert texts == ["1"]


def test_same_label_separate_cells_keep_both_for_coverage():
    """同 output_label 兩塊是相鄰「不同小格」(~18px > 12) → 兩格各保留編號（覆蓋率優先）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(10, 10), (20, 10), (10, 20)]),   # label ~13,13
        (_tint(50, 200, 100),  [(28, 10), (38, 10), (28, 20)]),   # label ~31,13 → 同 label 1
    ])
    label_map = {1: 1, 2: 2, 3: 1}
    palette_final = [{"output_label": 1, "rgb": [247, 167, 132]}]
    out, _ = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    texts = _parse_texts(out)
    # ~18px > 12 → 兩格都標，每格都看得到數字
    assert texts == ["1", "1"]


def test_different_labels_kept_when_not_overlapping():
    """兩個不同 output_label 標籤點 ~10px (> 8) → 各保留（覆蓋率優先，不為乾淨砍號）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(10, 10), (18, 10), (10, 18)]),   # label ~12.7,12.7
        (_tint(100, 50, 200),  [(20, 10), (28, 10), (20, 18)]),   # label ~22.7,12.7 → ~10px
    ])
    label_map = {1: 1, 2: 2}
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},
        {"output_label": 2, "rgb": [100, 50, 200]},
    ]
    out, _ = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    texts = _parse_texts(out)
    assert sorted(texts) == ["1", "2"]


def test_collision_suppressed_across_grid_boundary():
    """跨「網格邊界」的同號碰撞仍被抑制 —— 驗證碰撞用 3×3 鄰格、不是只查同格。
    GRID≈19.6：兩個 label 點約 (19,13) 落格0、(30,13) 落格1，相距 ~11px < 同號門檻 12
    → 第二個應被抑制。若 grid 只查同格（不查鄰格）此測試會失敗（會放出 2 個）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(16, 10), (22, 10), (22, 16), (16, 16)]),  # tid1 中心 ~(19,13)
        (_tint(50, 200, 100),  [(27, 10), (33, 10), (33, 16), (27, 16)]),  # tid3 中心 ~(30,13)
    ])
    label_map = {1: 1, 2: 2, 3: 1}
    palette_final = [{"output_label": 1, "rgb": [247, 167, 132]}]
    out, _ = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    texts = _parse_texts(out)
    assert texts == ["1"]


def test_different_labels_overlapping_suppressed():
    """兩個不同 output_label 標籤點疊在一起 (~5px < 8) → 只留一個（防疊字看不清）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(10, 10), (18, 10), (10, 18)]),   # label ~12.7,12.7
        (_tint(100, 50, 200),  [(15, 10), (23, 10), (15, 18)]),   # label ~17.7,12.7 → ~5px
    ])
    label_map = {1: 1, 2: 2}
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},
        {"output_label": 2, "rgb": [100, 50, 200]},
    ]
    out, _ = regenerate_merged_svg(svg, label_map, _PALETTE_JSON, palette_final)
    texts = _parse_texts(out)
    assert len(texts) == 1


def test_path_has_fill_rule_evenodd():
    """path 必須帶 fill-rule=evenodd 才能正確渲染洞（unary_union 可能產出含洞 polygon）。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (50, 0), (0, 50)]),
    ])
    out, _ = regenerate_merged_svg(
        svg, {1: 1}, _PALETTE_JSON,
        [{"output_label": 1, "rgb": [247, 167, 132]}],
    )
    paths = _parse_paths(out)
    assert paths[0].get("fill-rule") == "evenodd"


def test_path_uses_physical_color_tint():
    """合併後的 path fill 應該是 palette_final 的 RGB 算出的 tint，
    而非原 polygon 的 algorithm tint（finalize 後可能 RGB 已改）。
    輸出用 _OUTPUT_TINT_RATIO (0.10)，比 input 的 0.25 更淺。"""
    from palette.svg_consolidate import _OUTPUT_TINT_RATIO

    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)]),
    ])
    # palette_final 給不同的 RGB（模擬使用者校正過 RGB 後的色）
    out, _ = regenerate_merged_svg(
        svg, {1: 1}, _PALETTE_JSON,
        [{"output_label": 1, "rgb": [10, 20, 30]}],
    )
    paths = _parse_paths(out)
    # output 用 10% 濃度，不是 _tint() 預設的 25%
    expected_tint = _tint_hex([10, 20, 30])  # ratio defaults to 0.25... 改用顯式
    expected_tint = _tint_hex([10, 20, 30], ratio=_OUTPUT_TINT_RATIO)
    assert paths[0].get("fill") == expected_tint


def test_output_tint_is_lighter_than_input_tint():
    """確認 output fill 比 input lookup tint 更淺（10% vs 25%），讓塗色者畫上去能蓋過。"""
    from palette.svg_consolidate import _INPUT_TINT_RATIO, _OUTPUT_TINT_RATIO

    assert _OUTPUT_TINT_RATIO < _INPUT_TINT_RATIO, \
        f"output tint ({_OUTPUT_TINT_RATIO}) should be lighter than input ({_INPUT_TINT_RATIO})"

    # 同一個 vivid color，output tint 應該更接近 #FFFFFF
    color = [200, 50, 30]
    input_tint = _tint_hex(color, ratio=_INPUT_TINT_RATIO)
    output_tint = _tint_hex(color, ratio=_OUTPUT_TINT_RATIO)
    # output 每個 channel 都該更高（更白）
    def _hex_to_rgb(h):
        return [int(h[i:i+2], 16) for i in (1, 3, 5)]
    assert all(
        o >= i
        for o, i in zip(_hex_to_rgb(output_tint), _hex_to_rgb(input_tint), strict=True)
    )


def test_polygon_with_unknown_fill_skipped():
    """polygon fill 不在 palette_json 任何 tint → skip，不影響其他 polygon。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)]),     # 認得，tid 1
        ("#123456",            [(20, 0), (30, 0), (20, 10)]),   # 不認得 fill
    ])
    out, _ = regenerate_merged_svg(
        svg, {1: 1}, _PALETTE_JSON,
        [{"output_label": 1, "rgb": [247, 167, 132]}],
    )
    paths = _parse_paths(out)
    assert len(paths) == 1   # 只有第一個被處理


def test_z_order_paths_before_texts():
    """SVG element 順序：所有 <path> 必須在所有 <text> 之前，
    否則後續 path 會蓋住前面 output_label 已放的 text。

    Regression：先前 path/text 交錯（一個 output_label 一組），密集區的數字被
    後續 output_label 的色塊蓋住。修法：兩 pass 渲染，全部 path 寫完才寫 text。
    """
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (40, 0), (0, 40)]),
        (_tint(100, 50, 200),  [(60, 0), (100, 0), (60, 40)]),
        (_tint(50, 200, 100),  [(0, 60), (40, 60), (0, 100)]),
    ])
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},
        {"output_label": 2, "rgb": [100, 50, 200]},
        {"output_label": 3, "rgb": [50, 200, 100]},
    ]
    out, _ = regenerate_merged_svg(svg, {1: 1, 2: 2, 3: 3}, _PALETTE_JSON, palette_final)
    root = ET.fromstring(out)

    # 走訪 root 的直接子 element 收順序
    children_tags = [c.tag.split("}")[-1] for c in root]
    # 第一個 text 出現的 index
    first_text_idx = next(
        (i for i, t in enumerate(children_tags) if t == "text"), None,
    )
    # 最後一個 path 出現的 index
    last_path_idx = max(
        (i for i, t in enumerate(children_tags) if t == "path"),
        default=-1,
    )
    assert first_text_idx is not None, "expected at least one <text>"
    assert last_path_idx >= 0, "expected at least one <path>"
    assert last_path_idx < first_text_idx, (
        f"path must precede all texts to avoid z-order coverage: "
        f"last_path_idx={last_path_idx}, first_text_idx={first_text_idx}"
    )


def test_z_order_large_path_drawn_before_small_path():
    """被包圍的「中間」異色小塊不可被外圍大塊蓋掉（圓形四周改色號後中間消失的 bug）。

    SVG 是 painter's model（後畫蓋先畫），且 evenodd 只在同一條 path 內挖洞、跨不同
    實體色不互挖。若外圍大色塊在 document 順序上晚於被它環繞的中間異色小塊，就會把
    中間 fill 蓋掉。修法：Pass B 依面積由大到小繪製 path（大塊在底層、小塊在上層）。

    本測試故意把「中間小塊」polygon 在 document 中排在「外圍大塊」之前（觸發原 bug），
    斷言輸出 SVG 中面積大的 path 反而被拉到面積小的 path 之前（底層）。
    """
    svg = _make_svg([
        # document 順序故意把「中間小塊」放前面 — 原 bug：它先畫、被後畫的大塊蓋掉
        (_tint(100, 50, 200),  [(10, 10), (30, 10), (30, 30), (10, 30)]),  # tid 2，小（中間）
        # 「外圍大塊」放後面 — 原 bug：它後畫蓋住中間
        (_tint(247, 167, 132), [(0, 0), (100, 0), (100, 100), (0, 100)]),  # tid 1，大（外圍）
    ])
    label_map = {1: 1, 2: 2}
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},  # 大塊
        {"output_label": 2, "rgb": [100, 50, 200]},   # 小塊（中間）
    ]
    out, _ = regenerate_merged_svg(
        svg, label_map, _PALETTE_JSON, palette_final, enable_tiny_merge=False,
    )
    paths = _parse_paths(out)
    ids = [p.get("id") for p in paths]
    assert "o1" in ids and "o2" in ids, f"expected both paths, got {ids}"
    # 大塊 o1 必須排在小塊 o2 之前（底層）→ 被環繞的中間小塊 o2 在上層、不被蓋
    assert ids.index("o1") < ids.index("o2"), (
        f"large path (o1) must be drawn before small path (o2) so the enclosed "
        f"small region stays on top and is not covered; got order={ids}"
    )
    # 中間小塊的編號也應仍在（沒被吃掉）
    texts = _parse_texts(out)
    assert "2" in texts, f"enclosed small region's label should survive, got {texts}"


def _first_poly_area(d: str) -> float:
    """path d 第一個 M..Z 多邊形的面積（shoelace）。"""
    import re as _re
    m = _re.search(r"M ([^MZ]+) Z", d or "")
    if not m:
        return 0.0
    c = m.group(1).replace(",", " ").split()
    pts = [(float(c[i]), float(c[i + 1])) for i in range(0, len(c) - 1, 2)]
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def test_z_order_per_part_not_group_area():
    """per-part z-order：被包覆的小塊即使「所屬色總面積大」也在最上層、不被蓋。

    這是修「改四周中間被蓋」resurface 的關鍵 case，舊「色群總面積」排序會錯：
    色 A(label1) = 大塊(60x60=3600) + 中間小塊(10x10=100)，總面積 3700；
    色 B(label2) = 包住中間的方塊(20x20=400)，總面積 400 < A。
    舊排序把 A(3700) 整組先畫 → 中間(屬 A)在底層 → B(400)後畫蓋住中間。
    per-part 排序：big(3600) → B(400) → 中間(100) 最後畫 → 中間在最上層。
    """
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (60, 0), (60, 60), (0, 60)]),       # tid1 大塊 A
        (_tint(247, 167, 132), [(75, 75), (85, 75), (85, 85), (75, 85)]),   # tid1 中間小塊 A
        (_tint(100, 50, 200),  [(70, 70), (90, 70), (90, 90), (70, 90)]),   # tid2 包住中間的 B
    ])
    label_map = {1: 1, 2: 2}
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},
        {"output_label": 2, "rgb": [100, 50, 200]},
    ]
    out, _ = regenerate_merged_svg(
        svg, label_map, _PALETTE_JSON, palette_final, enable_tiny_merge=False,
    )
    paths = _parse_paths(out)
    areas = [_first_poly_area(p.get("d", "")) for p in paths]
    # 每條 path 依個別 part 面積由大到小（非遞增）
    assert areas == sorted(areas, reverse=True), f"paths not per-part area-desc: {areas}"
    # 最上層（最後一條 path）= 中間小塊（面積最小、色 A=o1）→ 證明不被 B 蓋
    assert paths[-1].get("id") == "o1"
    assert areas[-1] < 200, f"top path should be the tiny center, got area {areas[-1]}"


def test_render_filled_png_uses_template_geometry():
    """render_filled_png 把 template_final.svg 多邊形用實體色原色 rasterize 成 PNG，
    保證填色預覽 = 線稿同一份幾何（非 snapped 點陣）。"""
    import io

    import numpy as np
    from PIL import Image

    from palette.svg_consolidate import regenerate_merged_svg, render_filled_png

    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (50, 0), (50, 50), (0, 50)]),     # tid1 → label1
        (_tint(100, 50, 200),  [(50, 0), (100, 0), (100, 50), (50, 50)]),  # tid2 → label2
    ])
    palette_final = [
        {"output_label": 1, "rgb": [247, 167, 132]},
        {"output_label": 2, "rgb": [100, 50, 200]},
    ]
    final_svg, _ = regenerate_merged_svg(
        svg, {1: 1, 2: 2}, _PALETTE_JSON, palette_final, enable_tiny_merge=False,
    )
    png = render_filled_png(final_svg, palette_final, supersample=1)
    arr = np.array(Image.open(io.BytesIO(png)).convert("RGB"))
    # 左半 = label1 實體色原色（飽和，非 10% tint）；右半 = label2 原色
    assert tuple(arr[25, 10]) == (247, 167, 132)
    assert tuple(arr[25, 90]) == (100, 50, 200)


def test_text_elements_have_light_font_weight():
    """每個 <text> 都應該有 font-weight=300（Light）讓塗色者讀起來不刺眼。"""
    svg = _make_svg([
        (_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)]),
    ])
    out, _ = regenerate_merged_svg(
        svg, {1: 1}, _PALETTE_JSON,
        [{"output_label": 1, "rgb": [247, 167, 132]}],
    )
    root = ET.fromstring(out)
    texts = root.findall(f"{{{_NS}}}text")
    assert len(texts) >= 1
    for t in texts:
        assert t.get("font-weight") == "300", \
            f"expected font-weight=300 (Light), got {t.get('font-weight')!r}"
        # font-family chain 必須含 "Inter"，後端 register Inter-Light 後 svglib 才命中
        family = t.get("font-family") or ""
        assert "Inter" in family, f"expected font-family to include 'Inter', got: {family!r}"


def test_empty_label_map_raises():
    svg = _make_svg([(_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)])])
    with pytest.raises(ValueError, match="label_map 不可為空"):
        regenerate_merged_svg(svg, {}, _PALETTE_JSON, [])


def test_invalid_svg_raises():
    with pytest.raises(ValueError, match="SVG 解析失敗"):
        regenerate_merged_svg(b"<not valid", {1: 1}, _PALETTE_JSON, [])


def test_preserves_viewbox():
    svg = _make_svg([(_tint(247, 167, 132), [(0, 0), (10, 0), (0, 10)])])
    out, _ = regenerate_merged_svg(
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
    ).encode()
    out, _ = regenerate_merged_svg(svg, {1: 7}, _PALETTE_JSON, [])
    # fallback: text content 應該變成 "7"
    texts = _parse_texts(out)
    assert "7" in texts


# ── enable_tiny_merge 開關（雙版本 SVG 給 admin 對比 UI 用） ────────────────

def test_enable_tiny_merge_false_returns_empty_merge_records():
    """enable_tiny_merge=False 時 — 跳過 _merge_tiny_polygons、merge_records 必為空。

    finalize 雙版本用：False 跑出來的「未合併版」是主版本，給 user 看細緻版；
    True 跑出來的「合併版」是 preview，給 admin 對比看「按確認合併會變什麼」。
    """
    # 建一個含微小 polygon 的 SVG：tid 1（小、area<60）+ tid 2（大、area>60）
    # 兩個鄰接、color 相近（LAB<30），預期 enable=True 時會被合進去
    palette_with_small = [
        {"template_id": 1, "rgb": [240, 240, 240], "pixels": 10},   # tint 接近白
        {"template_id": 2, "rgb": [220, 220, 220], "pixels": 5000}, # tint 也接近白
    ]
    palette_final = [
        {"output_label": 1, "rgb": [240, 240, 240]},
        {"output_label": 2, "rgb": [220, 220, 220]},
    ]
    svg = _make_svg([
        # tid 1：tiny（2×2 = 4 px²）
        (_tint(240, 240, 240), [(0, 0), (2, 0), (2, 2), (0, 2)]),
        # tid 2：large（50×50 = 2500 px²）緊鄰 tid 1
        (_tint(220, 220, 220), [(2, 0), (52, 0), (52, 50), (2, 50)]),
    ])

    # False 路徑：merge_records 必為空
    _, records_off = regenerate_merged_svg(
        svg, {1: 1, 2: 2}, palette_with_small, palette_final,
        enable_tiny_merge=False,
    )
    assert records_off == []


def test_tiny_merge_only_within_same_physical_color():
    """微小色塊只在同實體色（同 output_label）內 auto-merge；不同實體色絕不合併。

    修「不是同實體色的顏色也被合併」：same output_label → 合併並回 record；
    different output_label（不同實體色）→ 即使顏色相近(LAB<30)也不合併、records 為空。
    """
    palette_with_small = [
        {"template_id": 1, "rgb": [240, 240, 240], "pixels": 10},
        {"template_id": 2, "rgb": [220, 220, 220], "pixels": 5000},
    ]
    svg = _make_svg([
        (_tint(240, 240, 240), [(0, 0), (2, 0), (2, 2), (0, 2)]),       # tid 1 tiny
        (_tint(220, 220, 220), [(2, 0), (52, 0), (52, 50), (2, 50)]),   # tid 2 large 緊鄰
    ])

    # 同實體色（tid 1、tid 2 都 output_label 1）→ tiny 合進 large、回 record
    palette_same = [{"output_label": 1, "rgb": [220, 220, 220]}]
    _, records_same = regenerate_merged_svg(
        svg, {1: 1, 2: 1}, palette_with_small, palette_same,
    )
    assert len(records_same) >= 1
    rec = records_same[0]
    assert rec["tiny_template_id"] == 1
    assert rec["target_template_id"] == 2
    assert "polygon_id" in rec

    # 不同實體色（output_label 1 vs 2）→ 顏色相近仍不合併、records 為空
    palette_diff = [
        {"output_label": 1, "rgb": [240, 240, 240]},
        {"output_label": 2, "rgb": [220, 220, 220]},
    ]
    _, records_diff = regenerate_merged_svg(
        svg, {1: 1, 2: 2}, palette_with_small, palette_diff,
    )
    assert records_diff == []
