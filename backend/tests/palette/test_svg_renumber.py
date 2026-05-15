"""SVG text surgery 單元測試 — 純函式，不需 DB / Celery / Firebase。"""
import pytest

from palette.svg_renumber import renumber_svg_labels

_SVG_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'


def _make_svg(labels: list[int]) -> bytes:
    """產生帶 N 個 <text> element 的 mini SVG，模擬 pbn_gen 的輸出結構。"""
    inner = "".join(
        f'<g id="{i}"><text x="0" y="0">{lbl}</text></g>'
        for i, lbl in enumerate(labels)
    )
    return (
        f'{_SVG_HEADER}'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<rect x="0" y="0" width="100" height="100" fill="white"/>'
        f'<polygon id="r0" points="0,0 10,0 0,10" fill="#ff0000"/>'
        f'{inner}'
        f'</svg>'
    ).encode("utf-8")


def _text_contents(svg_bytes: bytes) -> list[str]:
    """從 SVG bytes 取出所有 <text> 內容（順序保留）。"""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svg_bytes)
    return [
        (t.text or "").strip()
        for t in root.iter("{http://www.w3.org/2000/svg}text")
    ]


def test_renumber_basic_mapping():
    """三個 label 各自被換成新的編號。"""
    svg = _make_svg([1, 2, 3])
    out = renumber_svg_labels(svg, {1: 10, 2: 20, 3: 30})
    assert _text_contents(out) == ["10", "20", "30"]


def test_renumber_multiple_template_to_same_output():
    """多個 template_id 對到同一 output_label（這是 finalize 的核心場景）。"""
    svg = _make_svg([1, 2, 3, 4])
    # template 1, 3 → output 1（最大區）；template 2, 4 → output 2
    out = renumber_svg_labels(svg, {1: 1, 2: 2, 3: 1, 4: 2})
    assert _text_contents(out) == ["1", "2", "1", "2"]


def test_renumber_preserves_non_numeric_text():
    """非數字內容的 <text> 不該被動到（防呆，理論上 pbn_gen 不會產生）。"""
    svg = (
        f'{_SVG_HEADER}'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<text x="0" y="0">標題</text>'
        f'<text x="0" y="10">5</text>'
        f'<text x="0" y="20"> </text>'
        f'</svg>'
    ).encode("utf-8")
    out = renumber_svg_labels(svg, {5: 99})
    contents = _text_contents(out)
    assert contents[0] == "標題"  # 非數字保留
    assert contents[1] == "99"      # 數字 5 → 99
    assert contents[2] == ""        # 空白原樣


def test_renumber_unknown_template_id_skipped():
    """SVG 有 label 但 map 沒對應 → 該 label 不動，不報錯。"""
    svg = _make_svg([1, 99])
    out = renumber_svg_labels(svg, {1: 5})  # 沒給 99
    assert _text_contents(out) == ["5", "99"]


def test_renumber_preserves_other_elements():
    """polygon / rect / 屬性都應保留不變（只動 text content）。"""
    svg = _make_svg([1])
    out = renumber_svg_labels(svg, {1: 7})
    out_str = out.decode("utf-8")
    assert 'fill="white"' in out_str
    assert 'id="r0"' in out_str
    assert 'fill="#ff0000"' in out_str
    assert 'viewBox="0 0 100 100"' in out_str


def test_renumber_empty_map_raises():
    svg = _make_svg([1, 2])
    with pytest.raises(ValueError, match="label_map 不可為空"):
        renumber_svg_labels(svg, {})


def test_renumber_invalid_svg_raises():
    with pytest.raises(ValueError, match="SVG 解析失敗"):
        renumber_svg_labels(b"<not valid xml", {1: 2})


def test_renumber_idempotent():
    """重複呼叫第二次（同樣的 map）→ 結果不變（because output_label 已寫進去，
    不在 map keys 內 → skip）。

    這保證 finalize 多次安全。
    """
    svg = _make_svg([1, 2])
    map1 = {1: 10, 2: 20}
    once = renumber_svg_labels(svg, map1)
    twice = renumber_svg_labels(once, map1)
    assert _text_contents(once) == _text_contents(twice) == ["10", "20"]
