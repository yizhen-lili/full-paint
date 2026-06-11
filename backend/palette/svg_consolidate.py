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

# 數字標籤字體：Light (300) 細體 + Inter 字體（PDF 端會 register；瀏覽器有 fallback chain）
_LABEL_FONT_WEIGHT = "300"
_LABEL_FONT_FAMILY = "Inter, Helvetica, Arial, sans-serif"

# 色彩濃度（25% 原色 + 75% 白）— **pbn_gen 寫死的值**，用來反查 template.svg 內
# 的 polygon fill → template_id。不可改動，會破壞 input lookup。
_INPUT_TINT_RATIO = 0.25

# 色彩濃度（10% 原色 + 90% 白）— template_final.svg 輸出用，淺色但仍可辨識
# 5% 太淺幾乎看不出色塊位置，調回 10% 留一點視覺引導
_OUTPUT_TINT_RATIO = 0.10

# 數字標籤大小限制（SVG userspace 單位，等同 pbn_gen viewBox 內的像素）
# 上限 14：避免大面積區域的標籤被放大到佔據整個畫面
# 下限 5：再小就糊掉看不清
_MIN_FONT_SIZE = 5.0
_MAX_FONT_SIZE = 14.0

# 同一 output_label 的小碎片，bbox 短邊 < 此值且不是該色最大塊 → 不放標籤
# （太細長的區域硬塞標籤會超出邊界；最大塊永遠標，確保每色 ≥ 1 個 label）
_MIN_EXTRA_PART_BBOX = 6.0

# 碰撞偵測：跨 output_label 之間，新 label 中心與任何既有 label 距離
# 若 < (size_a + size_b) × _COLLISION_TOLERANCE → 略過（保留較大那一個）
_COLLISION_TOLERANCE = 0.7

# 跨編號標籤的「絕對最小間距」下限：font 算出的門檻太小時用這個兜底。
# 只防「不同數字真的疊在一起」—— font 5 數字約 4~5px 寬，下限取 8px 即可避免重疊，
# 又不會在密集模板裡把相鄰小格的不同編號砍掉（放寬：原 12 → 8）。
_COLLISION_MIN_GAP_PX = 8.0

# 同一個 output_label 的相鄰 part 要再放一次編號，必須距既有「同號」標籤 ≥ 此值。
# 覆蓋率優先（user：每格都要看得到數字、能精準畫）：只擋「同號真的疊在一點」的
# 重複（< 12px），相鄰小格的同色號各自保留 —— 寧可同數字出現兩次，也不要有格子沒號。
_SAME_LABEL_MIN_GAP_PX = 12.0

# 碰撞偵測用空間網格的格寬：必須 ≥「任何兩標籤可能的最大 required 距離」，這樣只需
# 檢查候選點所在格 + 周圍 8 格即可涵蓋所有可能碰撞 → 把 O(n²) 降為 O(n)，密集模板
# （上萬格）finalize 才不會逾時 502。max required = max(同號門檻, 兩個最大字級的 font 門檻)。
_COLLISION_GRID_PX = max(
    _SAME_LABEL_MIN_GAP_PX,
    _COLLISION_MIN_GAP_PX,
    2 * _MAX_FONT_SIZE * _COLLISION_TOLERANCE,
)

# 微小色塊偵測：面積 < 此 OR bbox 短邊 < _TINY_POLYGON_SHORT_EDGE 視為微小、
# 自動合併到色差最近的鄰居（SVG 層級視覺合併，DB 不動）
_TINY_POLYGON_AREA = 60.0
_TINY_POLYGON_SHORT_EDGE = 5.0
# auto-merge 候選鄰居池：取距離最近的 K 個再用 LAB 色差選最佳
_MERGE_NEIGHBOR_TOPK = 5
# LAB 色差超過此值 → 不合（差太多就不該被「自動合進去」）
_MERGE_MAX_LAB_DIST = 30.0


def _normalize_hex(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().upper()
    if not s.startswith("#"):
        s = "#" + s
    return s if len(s) == 7 else None


def _tint_hex(rgb, ratio: float = _INPUT_TINT_RATIO) -> str:
    """色彩 25%/75% 混白後的 #RRGGBB hex（大寫）。

    預設 ratio = _INPUT_TINT_RATIO (0.25) 對應 pbn_gen 寫的 polygon fill，
    供反查 template_id 用。輸出 path 用 _OUTPUT_TINT_RATIO 顯式傳入。
    """
    if isinstance(rgb, dict):
        r, g, b = int(rgb.get("r", 0)), int(rgb.get("g", 0)), int(rgb.get("b", 0))
    else:
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    inv = 1.0 - ratio
    tr = int(r * ratio + 255 * inv)
    tg = int(g * ratio + 255 * inv)
    tb = int(b * ratio + 255 * inv)
    return f"#{tr:02X}{tg:02X}{tb:02X}"


def _rgb_from_palette(palette_json: list[dict], template_id: int) -> list[int] | None:
    """從 palette_json 找 template_id 對應的 RGB list [r, g, b]。"""
    for entry in palette_json:
        try:
            if int(entry.get("template_id", -1)) != template_id:
                continue
        except (TypeError, ValueError):
            continue
        rgb = entry.get("rgb")
        if isinstance(rgb, dict):
            return [int(rgb.get("r", 0)), int(rgb.get("g", 0)), int(rgb.get("b", 0))]
        if isinstance(rgb, (list, tuple)) and len(rgb) >= 3:
            return [int(rgb[0]), int(rgb[1]), int(rgb[2])]
        return None
    return None


def _merge_tiny_polygons(
    all_polygons: list[dict],
) -> list[dict]:
    """微小色塊找鄰居中色差最近者，改 template_id（in-memory only，DB 不動）。

    Algorithm（O(n²) 對典型 SVG 規模可接受）：
    1. 收 large_polys = 面積 ≥ _TINY_POLYGON_AREA 且 short_edge ≥ _TINY_POLYGON_SHORT_EDGE
    2. 對每個 tiny polygon：
       a. 計算與所有 large 的 shapely distance（0 = 共享邊界）
       b. 取最近 _MERGE_NEIGHBOR_TOPK 個鄰居
       c. 在候選池內取與 tiny 色差最小（LAB）的鄰居
       d. 若色差 < _MERGE_MAX_LAB_DIST → 改 tiny.template_id = neighbor.template_id
          並紀錄 merge_record
    3. 回 merge_records list（給 finalize_template 寫進 pending_auto_merges）

    Side effect：直接 mutate all_polygons[i]["template_id"]
    """
    try:
        from color.service import lab_distance  # noqa: PLC0415
    except ImportError:
        logger.warning("color.service.lab_distance 不可用 — 跳過 tiny merge")
        return []

    tiny_indexes = []
    large_polys = []
    for i, p in enumerate(all_polygons):
        shp = p["shp"]
        minx, miny, maxx, maxy = shp.bounds
        short_edge = min(maxx - minx, maxy - miny)
        if shp.area < _TINY_POLYGON_AREA or short_edge < _TINY_POLYGON_SHORT_EDGE:
            tiny_indexes.append(i)
        else:
            large_polys.append(p)

    if not tiny_indexes or not large_polys:
        return []

    merge_records: list[dict] = []
    for idx in tiny_indexes:
        tiny = all_polygons[idx]
        tiny_rgb = tiny.get("raw_rgb")
        if tiny_rgb is None:
            continue
        # 計算與每個 large 的距離
        dist_pairs: list[tuple[float, dict]] = []
        for large in large_polys:
            try:
                d = tiny["shp"].distance(large["shp"])
            except Exception:  # noqa: BLE001
                continue
            dist_pairs.append((d, large))
        if not dist_pairs:
            continue

        dist_pairs.sort(key=lambda x: x[0])
        topk = [c for _, c in dist_pairs[:_MERGE_NEIGHBOR_TOPK]]

        best = None
        best_lab = float("inf")
        for cand in topk:
            cand_rgb = cand.get("raw_rgb")
            if cand_rgb is None:
                continue
            lab = lab_distance(tiny_rgb, cand_rgb)
            if lab < best_lab:
                best_lab = lab
                best = cand

        if best is None or best_lab > _MERGE_MAX_LAB_DIST:
            continue
        if best["template_id"] == tiny["template_id"]:
            continue

        merge_records.append({
            # polygon_id 是「per-polygon merge」(走既有 post_process merge_color
            # op) 的關鍵 — 沒有它 confirm 只能 fallback 到 per-template_id 邏輯
            "polygon_id": tiny.get("polygon_id"),
            "tiny_template_id": int(tiny["template_id"]),
            "target_template_id": int(best["template_id"]),
            "tiny_area": float(tiny["shp"].area),
        })
        tiny["template_id"] = best["template_id"]

    if merge_records:
        logger.info(
            "svg consolidate: auto-merged %d tiny polygons into nearest similar-color neighbors",
            len(merge_records),
        )
    return merge_records


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
    *,
    enable_tiny_merge: bool = True,
) -> tuple[bytes, list[dict]]:
    """把原 template.svg 依 label_map 重新分組合併，產出「實體色版」SVG。

    Args:
        svg_bytes:     原 pbn_gen 產出的 template.svg 二進位
        label_map:     {template_id: output_label}
        palette_json:  pbn_gen 原始 palette_json（含 template_id 與 algorithm rgb，
                       用來把 polygon 的 fill 反查回 template_id）
        palette_final: finalize 產出的色號對照表（含 output_label, rgb, hex 等）
        enable_tiny_merge: True（預設）= 跑 _merge_tiny_polygons 把微小色塊
                       in-memory 改 template_id 合進鄰居（產「合併版」），
                       merge_records 回偵測到的清單。
                       False = 跳過、保留所有原 template_id（產「未合併版」），
                       merge_records 回 []。仍會做同 output_label 相鄰 polygon
                       的 unary_union（消除假邊界）。
                       finalize 同時呼叫兩次給對比 UI 用：False=主版本、True=preview，
                       記得從 True 那次取 merge_records 寫進 pending_auto_merges。

    回傳：(新 SVG bytes, merge_records)
        merge_records: 微小色塊 auto-merge 建議清單 [{tiny_template_id,
        target_template_id, tiny_area, polygon_id}, ...]；DB 不動，給上層存
        pending_auto_merges。enable_tiny_merge=False 時為 []。

    錯誤處理：shapely 未安裝 → 自動 fallback 到 renumber_svg_labels（純文字替換，
    但仍可用、回 ([], )）；單一 polygon 解析失敗 → skip，整體仍輸出。
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
        return renumber_svg_labels(svg_bytes, label_map), []

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

    # ── Step 3a：解析 polygon → flat list[{shp, template_id, raw_rgb}]
    # 注意：先不分組，先收集為 flat list 讓 Step 3b 跑微小色塊合併（會改 template_id）
    all_polygons: list[dict] = []
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

        try:
            shp = ShPolygon(coords)
            if not shp.is_valid:
                # buffer(0) 是 shapely 修無效幾何的標準技巧
                shp = shp.buffer(0)
            if not shp.is_valid or shp.is_empty:
                skipped_invalid_geom += 1
                continue
            all_polygons.append({
                "shp": shp,
                "template_id": tid,
                "raw_rgb": _rgb_from_palette(palette_json, tid),
                # polygon_id (pbn_gen 寫的 r{N}) — auto-merge confirm 走 post_process
                # 的 merge_color op 時 per-polygon 需要這個值
                "polygon_id": poly.get("id"),
            })
        except Exception as e:  # noqa: BLE001
            logger.debug("skip polygon (parse error): %s", e)
            skipped_invalid_geom += 1
            continue

        sw = poly.get("stroke-width")
        if sw:
            sample_stroke_width = sw

    # ── Step 3b：微小色塊 auto-merge（in-memory only）
    # enable_tiny_merge=False 時跳過、產「未合併版」給對比 UI 當主版本
    merge_records = _merge_tiny_polygons(all_polygons) if enable_tiny_merge else []

    # ── Step 3c：建 polygons_by_label（已套用 merge 後的 template_id）
    polygons_by_label: dict[int, list] = defaultdict(list)
    for p in all_polygons:
        tid = p["template_id"]
        if tid not in label_map:
            continue
        output_label = int(label_map[tid])
        polygons_by_label[output_label].append(p["shp"])

    if not polygons_by_label:
        logger.warning(
            "no polygons could be grouped (no_fill=%d unknown_tint=%d invalid=%d); "
            "falling back to renumber-only",
            skipped_no_fill, skipped_unknown_tint, skipped_invalid_geom,
        )
        from palette.svg_renumber import renumber_svg_labels  # noqa: PLC0415
        return renumber_svg_labels(svg_bytes, label_map), merge_records

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

    # ── Step 5：兩 pass 渲染避免 z-order bug
    # 先 pass A 把每個 output_label 的 path + label 候選蒐集起來；
    # 再 pass B 寫所有 path（色塊）；最後 pass C 寫所有 text（編號在最上面）。
    # 重點：所有 path 必須先寫完，text 才能疊在最上面不被後續 path 蓋住。

    merged_count = 0
    parts_count = 0
    # (output_label, tint, path_d, [(geom, ...)]) 給 pass B/C 用
    render_items: list[dict] = []

    # Pass A：蒐集每個 output_label 的渲染資料
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
        tint = _tint_hex(rgb, ratio=_OUTPUT_TINT_RATIO)

        # 組 path d（含 evenodd 處理洞）
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

        render_items.append({
            "output_label": output_label,
            "tint": tint,
            "path_d": " ".join(path_d_parts),
            "geom_list": geom_list,
        })

    # Pass B：先寫所有 <path>（色塊）
    for item in render_items:
        path_el = ET.SubElement(new_root, f"{{{_SVG_NS}}}path")
        path_el.set("d", item["path_d"])
        path_el.set("fill", item["tint"])
        path_el.set("fill-rule", "evenodd")
        path_el.set("stroke", "#AAAAAA")
        path_el.set("stroke-width", sample_stroke_width)
        path_el.set("stroke-linejoin", "round")
        path_el.set("id", f"o{item['output_label']}")
        merged_count += 1

    # Pass C：所有 path 都寫完後，把 <text> 標籤疊上去
    # 碰撞偵測用空間網格（grid）：(gx,gy) -> [(cx,cy,font_size,label)]，只比對候選點
    # 所在格 + 周圍 8 格，把原本 O(n²) 全域比對降為 O(n)，密集模板才不會逾時。
    label_grid: dict[tuple[int, int], list[tuple[float, float, float, int]]] = (
        defaultdict(list)
    )
    for item in render_items:
        output_label = item["output_label"]
        # 每個獨立 part 各放一個編號，三層篩選：
        #  1. font size 上限 _MAX_FONT_SIZE（避免大塊區域寫超大）
        #  2. bbox 短邊太小且不是最大塊 → skip（細長碎片標籤超出邊界）
        #  3. 碰撞偵測：與既有標籤太近 → skip（密集區不互相打架）
        # 注意：collision 一律檢查（包括該色最大塊），重疊就直接 skip。
        # 這意味某些被夾在 dense 區域的色號可能無 label — admin 對小色塊改靠
        # palette_final.json 的 legend 對照查詢，不靠 SVG label。
        geom_list_by_area = sorted(item["geom_list"], key=lambda g: -g.area)
        for idx, geom in enumerate(geom_list_by_area):
            is_largest = (idx == 0)

            # 篩選 2：bbox 短邊太小且非最大塊 → skip
            minx, miny, maxx, maxy = geom.bounds
            short_edge = min(maxx - minx, maxy - miny)
            if not is_largest and short_edge < _MIN_EXTRA_PART_BBOX:
                continue

            # polylabel 找穩定的內部點
            try:
                tol = max(1.0, (geom.area ** 0.5) / 100.0)
                pt = polylabel(geom, tolerance=tol)
                cx, cy = pt.x, pt.y
            except Exception:  # noqa: BLE001
                centroid = geom.centroid
                cx, cy = centroid.x, centroid.y

            # 篩選 1：font size cap
            area_sqrt = max(geom.area, 1.0) ** 0.5
            font_size = max(_MIN_FONT_SIZE, min(area_sqrt / 8.0, _MAX_FONT_SIZE))

            # 篩選 3：碰撞偵測（只比對候選點所在格 + 周圍 8 格，O(1) 均攤）。
            # - 跨編號：font 門檻 + 絕對下限 _COLLISION_MIN_GAP_PX（不同數字不疊字）
            # - 同編號：再拉高到 _SAME_LABEL_MIN_GAP_PX（同數字不在一點重複）
            gx, gy = int(cx // _COLLISION_GRID_PX), int(cy // _COLLISION_GRID_PX)
            too_close = False
            for dgx in (-1, 0, 1):
                for dgy in (-1, 0, 1):
                    # .get 不建空鍵（只有真的放標籤時才在 append 處建格）
                    for px, py, pfs, plabel in label_grid.get((gx + dgx, gy + dgy), ()):
                        base = max(
                            (font_size + pfs) * _COLLISION_TOLERANCE,
                            _COLLISION_MIN_GAP_PX,
                        )
                        required = (
                            max(base, _SAME_LABEL_MIN_GAP_PX)
                            if plabel == output_label else base
                        )
                        if (cx - px) ** 2 + (cy - py) ** 2 < required ** 2:
                            too_close = True
                            break
                    if too_close:
                        break
                if too_close:
                    break
            if too_close:
                continue

            text_el = ET.SubElement(new_root, f"{{{_SVG_NS}}}text")
            text_el.set("x", f"{cx:.1f}")
            text_el.set("y", f"{cy:.1f}")
            text_el.set("text-anchor", "middle")
            text_el.set("dominant-baseline", "central")
            text_el.set("font-size", f"{font_size:.1f}")
            text_el.set("font-weight", _LABEL_FONT_WEIGHT)
            text_el.set("font-family", _LABEL_FONT_FAMILY)
            text_el.set("fill", "black")
            text_el.text = str(output_label)
            label_grid[(gx, gy)].append((cx, cy, font_size, output_label))
            parts_count += 1

    logger.info(
        "svg consolidate: %d unique colors merged into %d label groups, "
        "%d label texts placed (skipped no_fill=%d unknown_tint=%d invalid=%d), "
        "%d tiny polygons auto-merged",
        len(polygons_by_label), merged_count, parts_count,
        skipped_no_fill, skipped_unknown_tint, skipped_invalid_geom,
        len(merge_records),
    )

    return ET.tostring(new_root, encoding="utf-8", xml_declaration=True), merge_records
