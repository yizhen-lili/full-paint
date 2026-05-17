"""對應完成後產出「實體色版」SVG — 不只換數字，而是把同實體色的相鄰區域**真的合併**
成一個多邊形。塗色者看到「一個色塊 = 一個編號 = 一罐顏料」，符合 paint-by-number 原則。

跟 svg_renumber.py 的差別：
- renumber 只改 <text> 文字，polygon 還是演算法分組畫的，相同色號之間仍有假邊界
- consolidate 用 Shapely unary_union 真的合併幾何，相同實體色之間的內部線條消失

實作方式：
1. 解析原 template.svg 所有 <polygon>（pbn_gen 用 svgwrite 寫的）
2. 用 fill 屬性比對 palette_json 的 tint(rgb)，反推每個 polygon 的 template_id
   （tint 公式 = 25% 原色 + 75% 白，是 pbn_gen 寫死的視覺效果）
3. 透過 label_map 分組到 output_label
4. 每組跑 Shapely unary_union → 可能是 Polygon、MultiPolygon（同色多個獨立區）
5. 渲染為 <path>（用 fill-rule="evenodd" 支援洞，用多個 M..Z 支援獨立區）
6. 每個獨立 part 各放一個編號（同 output_label，多個 part 各自 polylabel 點位）

沒有 shapely 時 fallback 到 svg_renumber.renumber_svg_labels（純文字替換）。
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from collections import defaultdict

logger = logging.getLogger(__name__)

_SVG_NS = "http://www.w3.org/2000/svg"


def _normalize_hex(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().upper()
    if not s.startswith("#"):
        s = "#" + s
    return s if len(s) == 7 else None


def _tint_hex(rgb) -> str:
    """pbn_gen 寫 polygon fill 的計算：25% 原色 + 75% 白 → #RRGGBB 大寫。

    對應 pbn_gen.py output_to_svg 內：
        r = int(color[0] * 0.25 + 255 * 0.75)
        g = int(color[1] * 0.25 + 255 * 0.75)
        b = int(color[2] * 0.25 + 255 * 0.75)
    """
    if isinstance(rgb, dict):
        r, g, b = int(rgb.get("r", 0)), int(rgb.get("g", 0)), int(rgb.get("b", 0))
    else:
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    tr = int(r * 0.25 + 255 * 0.75)
    tg = int(g * 0.25 + 255 * 0.75)
    tb = int(b * 0.25 + 255 * 0.75)
    return f"#{tr:02X}{tg:02X}{tb:02X}"


def _parse_points(pts: str) -> list[tuple[float, float]]:
    """SVG polygon points 屬性 "x1,y1 x2,y2 ..." 或 "x1 y1 x2 y2 ..." → [(x, y), ...]"""
    nums: list[float] = []
    for token in pts.replace(",", " ").split():
        if not token:
            continue
        try:
            nums.append(float(token))
        except ValueError:
            continue
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def regenerate_merged_svg(
    svg_bytes: bytes,
    label_map: dict[int, int],
    palette_json: list[dict],
    palette_final: list[dict],
) -> bytes:
    """把原 template.svg 依 label_map 重新分組合併，產出「實體色版」SVG。

    Args:
        svg_bytes:     原 pbn_gen 產出的 template.svg 二進位
        label_map:     {template_id: output_label}
        palette_json:  pbn_gen 原始 palette_json（含 template_id 與 algorithm rgb，
                       用來把 polygon 的 fill 反查回 template_id）
        palette_final: finalize 產出的色號對照表（含 output_label, rgb, hex 等）

    回傳：新 SVG bytes（XML 宣告 + 含合併幾何 + 編號標籤）

    錯誤處理：shapely 未安裝 → 自動 fallback 到 renumber_svg_labels（純文字替換，
    但仍可用）；單一 polygon 解析失敗 → skip，整體仍輸出。
    """
    if not label_map:
        raise ValueError("label_map 不可為空")

    try:
        from shapely.geometry import Polygon as ShPolygon
        from shapely.ops import polylabel, unary_union
    except ImportError as e:
        logger.warning(
            "shapely not available, falling back to renumber-only: %s", e,
        )
        from palette.svg_renumber import renumber_svg_labels  # noqa: PLC0415
        return renumber_svg_labels(svg_bytes, label_map)

    try:
        ET.register_namespace("", _SVG_NS)
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as e:
        raise ValueError(f"SVG 解析失敗：{e}") from e

    # ── Step 1：建 tint(algorithm_rgb) → template_id 對應表
    # pbn_gen 的 polygon fill = 25% 原色 + 75% 白，故同 template_id 所有 polygon
    # 都有相同 fill。反查可靠。
    tint_to_tid: dict[str, int] = {}
    for entry in palette_json:
        rgb = entry.get("rgb")
        if rgb is None:
            continue
        tid = int(entry["template_id"])
        tint_to_tid[_tint_hex(rgb)] = tid

    # ── Step 2：output_label → palette_final entry（取 rgb 用來算新 tint）
    palette_by_label: dict[int, dict] = {
        int(p["output_label"]): p for p in palette_final
    }

    # ── Step 3：解析 polygon，分組到 output_label
    polygons_by_label: dict[int, list] = defaultdict(list)
    polygon_tag = f"{{{_SVG_NS}}}polygon"
    sample_stroke_width = "1"
    skipped_no_fill = 0
    skipped_unknown_tint = 0
    skipped_invalid_geom = 0

    for poly in root.iter(polygon_tag):
        pts_str = poly.get("points", "")
        if not pts_str:
            continue
        coords = _parse_points(pts_str)
        if len(coords) < 3:
            continue

        fill = _normalize_hex(poly.get("fill"))
        if not fill:
            skipped_no_fill += 1
            continue
        tid = tint_to_tid.get(fill)
        if tid is None:
            skipped_unknown_tint += 1
            continue
        if tid not in label_map:
            continue
        output_label = int(label_map[tid])

        try:
            shp = ShPolygon(coords)
            if not shp.is_valid:
                # buffer(0) 是 shapely 修無效幾何的標準技巧
                shp = shp.buffer(0)
            if not shp.is_valid or shp.is_empty:
                skipped_invalid_geom += 1
                continue
            polygons_by_label[output_label].append(shp)
        except Exception as e:  # noqa: BLE001
            logger.debug("skip polygon (parse error): %s", e)
            skipped_invalid_geom += 1
            continue

        sw = poly.get("stroke-width")
        if sw:
            sample_stroke_width = sw

    if not polygons_by_label:
        logger.warning(
            "no polygons could be grouped (no_fill=%d unknown_tint=%d invalid=%d); "
            "falling back to renumber-only",
            skipped_no_fill, skipped_unknown_tint, skipped_invalid_geom,
        )
        from palette.svg_renumber import renumber_svg_labels  # noqa: PLC0415
        return renumber_svg_labels(svg_bytes, label_map)

    # ── Step 4：建新 SVG 骨架（保留 viewBox、width、height）
    # register_namespace("", _SVG_NS) 會自動加 xmlns，不可再 set("xmlns")（會重複）
    new_root = ET.Element(f"{{{_SVG_NS}}}svg")
    viewbox = root.get("viewBox", "0 0 1000 1000")
    new_root.set("viewBox", viewbox)
    if (w := root.get("width")):
        new_root.set("width", w)
    if (h := root.get("height")):
        new_root.set("height", h)

    vb_parts = viewbox.split()
    if len(vb_parts) >= 4:
        bg_w, bg_h = vb_parts[2], vb_parts[3]
    else:
        bg_w, bg_h = "1000", "1000"
    bg = ET.SubElement(new_root, f"{{{_SVG_NS}}}rect")
    bg.set("x", "0"); bg.set("y", "0")
    bg.set("width", bg_w); bg.set("height", bg_h)
    bg.set("fill", "white")

    # ── Step 5：每個 output_label 做 union → 渲染 path + label
    merged_count = 0
    parts_count = 0
    for output_label, polys in polygons_by_label.items():
        try:
            merged = unary_union(polys)
        except Exception as e:  # noqa: BLE001
            logger.warning("union failed for label %d: %s; using single polys", output_label, e)
            merged = polys[0] if len(polys) == 1 else None
            if merged is None:
                continue

        # 統一拆成 list[Polygon]
        if merged.geom_type == "Polygon":
            geom_list = [merged]
        elif merged.geom_type == "MultiPolygon":
            geom_list = list(merged.geoms)
        else:
            logger.debug("unexpected geom for label %d: %s", output_label, merged.geom_type)
            continue

        pf = palette_by_label.get(output_label, {})
        rgb = pf.get("rgb", [200, 200, 200])
        tint = _tint_hex(rgb)

        # 把所有 part 與洞合成一個 path d（fill-rule=evenodd 自動處理洞）
        path_d_parts: list[str] = []
        for geom in geom_list:
            if not geom.exterior:
                continue
            ext = " ".join(f"{x:.1f},{y:.1f}" for x, y in geom.exterior.coords)
            path_d_parts.append("M " + ext + " Z")
            for hole in geom.interiors:
                h = " ".join(f"{x:.1f},{y:.1f}" for x, y in hole.coords)
                path_d_parts.append("M " + h + " Z")

        if not path_d_parts:
            continue

        path_el = ET.SubElement(new_root, f"{{{_SVG_NS}}}path")
        path_el.set("d", " ".join(path_d_parts))
        path_el.set("fill", tint)
        path_el.set("fill-rule", "evenodd")
        path_el.set("stroke", "#AAAAAA")
        path_el.set("stroke-width", sample_stroke_width)
        path_el.set("stroke-linejoin", "round")
        path_el.set("id", f"o{output_label}")
        merged_count += 1

        # 每個獨立 part 各放一個編號（多個分離區域都需要標）
        for geom in geom_list:
            # polylabel 比 centroid 穩，凹形也保證在內部
            try:
                tol = max(1.0, (geom.area ** 0.5) / 100.0)
                pt = polylabel(geom, tolerance=tol)
                cx, cy = pt.x, pt.y
            except Exception:  # noqa: BLE001
                centroid = geom.centroid
                cx, cy = centroid.x, centroid.y

            # font size 根據 part 面積，sqrt(area)/8 clip 在 [6, 32]
            area_sqrt = max(geom.area, 1.0) ** 0.5
            font_size = max(6.0, min(area_sqrt / 8.0, 32.0))

            text_el = ET.SubElement(new_root, f"{{{_SVG_NS}}}text")
            text_el.set("x", f"{cx:.1f}")
            text_el.set("y", f"{cy:.1f}")
            text_el.set("text-anchor", "middle")
            text_el.set("dominant-baseline", "central")
            text_el.set("font-size", f"{font_size:.1f}")
            text_el.set("fill", "black")
            text_el.text = str(output_label)
            parts_count += 1

    logger.info(
        "svg consolidate: %d unique colors merged into %d label groups, "
        "%d label texts placed (skipped no_fill=%d unknown_tint=%d invalid=%d)",
        len(polygons_by_label), merged_count, parts_count,
        skipped_no_fill, skipped_unknown_tint, skipped_invalid_geom,
    )

    return ET.tostring(new_root, encoding="utf-8", xml_declaration=True)
