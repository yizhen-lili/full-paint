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
import math
import xml.etree.ElementTree as ET  # nosec B405 — 僅解析自家 pbn_gen 產生的 SVG
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

# 字級再以「放置點到邊界距離(內接半徑) × 此比例」為上限 —— 確保數字塞得進自己的
# 區塊、不會溢出到鄰格（原本字級只看面積、不看形狀，細長大面積區塊會放超大字溢出）。
# 1.6：數字置中(dominant-baseline central)，2 位數半寬/半高 ≈ 0.55×font，需 ≤ inradius
# → font ≤ ~1.8×inradius；取 1.6 留邊距。極細區塊 floor 在 MIN（不再放超大字）。
_FONT_FIT_RATIO = 1.6

# 數字字形外框相對 font 的比例（Inter Light 數字）：每位寬 ≈ 0.62×font、高 ≈ 0.72×font。
# 用於 _number_fits 判斷「n 位數字在最小字級下塞不塞得進這塊區域」，取代固定短邊門檻 →
# 一位數小格塞得進就給號、兩位數小格塞不進才合併（依實際數字位數，不再一刀切）。
_DIGIT_W_RATIO = 0.62
_DIGIT_H_RATIO = 0.72
# 算字級時相對「剛好填滿」再留的安全邊距（0.85 = 字形佔可用空間 85%、邊緣留 15% 不碰邊）
_FONT_SAFE_MARGIN = 0.85

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

# 長寬比 ≥ 此 → 視為細長，數字旋轉沿長軸放（寬→長邊、高→短邊）
_ELONGATED_ASPECT = 2.0
# 真碎片合併判定：_number_fits 回 False（連最小字、最佳方向都放不下號）AND 面積 < 此
# （面積上限防呆 —— 永不合大塊；放不下號才是 speck）。合進幾何最近鄰居，可跨實體色。
_SPECK_MAX_AREA = 50.0
# 碎片只在「最近鄰居距離 ≤ 此」時才合（相鄰碎片 distance≈0）。孤立碎片（四周是
# 背景、最近 large 在遠處）不合，避免合進遠方不相干的錯色 sliver。
_SPECK_MERGE_MAX_DIST = 5.0


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
    label_map: dict[int, int],
) -> list[dict]:
    """真碎片（連最小字、最佳方向都放不下號 + 面積小）合進「幾何最近」鄰居，改 template_id。

    碎片 = `_number_fits(shp, n_digits) is False`（放不下這格的實際數字）AND
    `area < _SPECK_MAX_AREA`（面積上限防呆 —— 永不合大塊）。細長條面積大且沿長軸 fits →
    不在此合併。合進**幾何距離最近**的非碎片鄰居，**可跨實體色**（碎片太小、色差可忽略），
    讓塗色者不再看到「放不下號」的孤兒小點。

    與 Pass C 放號的關係（重要，避免誤解）：兩者共用 `_number_fits` predicate，但**幾何層級
    不同** —— 本函式跑在 union **前**的個別 polygon（all_polygons[i].shp），Pass C 跑在
    union **後**的 per-part。因此「合併 ceiling = 放號 floor」只在**同一塊幾何**上嚴格成立；
    跨層級有一個窄邊界情況：同色相鄰小 polygon 各自放不下號、但 union 後本可放號，若其中之一
    在距離門檻內緊鄰異色大塊，會在此被先合走。此情況有三層緩衝：(1) 主版本 template_final.svg
    用 enable_tiny_merge=False、**完全不跑本函式**，union 後由 Pass C 重新評估放號 → 不受影響；
    (2) 孤立同色小塊（門檻內無大鄰居）不會被合、會 union 後放號；(3) 本函式只產**建議**
    （pending_auto_merges），admin 確認才落地。故對「塗色者實際畫的版本」無損。

    Algorithm（O(n²) 對典型 SVG 規模可接受）：
    1. 分 specks（碎片）/ large（非碎片，合併目標池）
    2. 每個 speck → 取與 large 的 shapely distance 最近者（距離同→面積大破 tie），
       改 speck.template_id = nearest.template_id 並紀錄 merge_record
    3. 回 merge_records（給 finalize_template 寫進 pending_auto_merges）

    Side effect：直接 mutate all_polygons[i]["template_id"]
    """
    speck_indexes = []
    large_polys = []
    for i, p in enumerate(all_polygons):
        shp = p["shp"]
        # tid 必在 label_map（Step 3a 已過濾掉 tid not in label_map 的 polygon）→ 直接取，
        # 用此 polygon「自己的」編號位數判斷塞不塞得進（與 Pass C 對同一 polygon 同位數）。
        n_digits = len(str(int(label_map[p["template_id"]])))
        fits, _, _ = _number_fits(shp, n_digits)
        if not fits and shp.area < _SPECK_MAX_AREA:
            speck_indexes.append(i)
        else:
            large_polys.append(p)

    if not speck_indexes or not large_polys:
        return []

    merge_records: list[dict] = []
    for idx in speck_indexes:
        speck = all_polygons[idx]
        # 幾何最近的 large（可跨色）；距離相同用面積大者（較穩定的塗色目標）
        best = None
        best_key = (float("inf"), 0.0)
        for large in large_polys:
            try:
                d = speck["shp"].distance(large["shp"])
            except Exception:  # noqa: BLE001, S112  # nosec B112 — 個別 polygon 距離失敗就跳過
                continue
            key = (d, -large["shp"].area)
            if key < best_key:
                best_key = key
                best = large
        # 孤立碎片（最近 large 太遠）不合，避免合進遠方錯色；同 template_id 不用合
        if (
            best is None
            or best_key[0] > _SPECK_MERGE_MAX_DIST
            or best["template_id"] == speck["template_id"]
        ):
            continue

        merge_records.append({
            # polygon_id 是「per-polygon merge」(走既有 post_process merge_color
            # op) 的關鍵 — 沒有它 confirm 只能 fallback 到 per-template_id 邏輯
            "polygon_id": speck.get("polygon_id"),
            "tiny_template_id": int(speck["template_id"]),
            "target_template_id": int(best["template_id"]),
            "tiny_area": float(speck["shp"].area),
        })
        speck["template_id"] = best["template_id"]

    if merge_records:
        logger.info(
            "svg consolidate: auto-merged %d specks into nearest neighbor",
            len(merge_records),
        )
    return merge_records


def _oriented_dims(geom) -> tuple[float, float, float]:
    """用 minimum_rotated_rectangle 回 (長邊長 L, 短邊長 S, 長邊角度 θ 度數 [-90,90])。

    給 Pass C 判斷區塊是否細長 + 把數字旋轉到沿長軸方向。失敗 fallback 用 bbox。
    """
    try:
        coords = list(geom.minimum_rotated_rectangle.exterior.coords)  # 5 點（首尾同）
        if len(coords) < 4:
            raise ValueError("degenerate mrr")
        e1 = (coords[1][0] - coords[0][0], coords[1][1] - coords[0][1])
        e2 = (coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        (long_len, short_len, edge) = (l1, l2, e1) if l1 >= l2 else (l2, l1, e2)
        theta = math.degrees(math.atan2(edge[1], edge[0]))
        # 正規化到 [-90, 90]（避免數字上下顛倒）
        if theta > 90:
            theta -= 180
        elif theta < -90:
            theta += 180
        return long_len, short_len, theta
    except Exception:  # noqa: BLE001 — 幾何退化 → 用 bbox 當 fallback
        minx, miny, maxx, maxy = geom.bounds
        w, h = maxx - minx, maxy - miny
        return (w, h, 0.0) if w >= h else (h, w, 90.0)


def _number_fits(geom, n_digits: int) -> tuple[bool, float, float | None]:
    """「n 位數字在最小字級下、取最佳方向，塞不塞得進這塊區域」的唯一判準。

    放號（Pass C）與合併（_merge_tiny_polygons）共用此 predicate → 放號 floor 與合併
    ceiling 對齊、不留「沒號又沒合併」的死區。依**實際數字位數**判斷：一位數小格塞得進
    就給號，兩位數小格塞不進才合併。

    幾何：用 _oriented_dims 的長邊 L、短邊 S（min rotated rect）當可用空間；數字沿長軸排
    （寬→L、高→S）。最小字級下字形外框 need_w = n×_DIGIT_W_RATIO×MIN、need_h =
    _DIGIT_H_RATIO×MIN。fits ⟺ L ≥ need_w 且 S ≥ need_h。

    回 (fits, font_size, rotate_deg)：
    - font_size：寬受 L/(n×w_ratio)、高受 S/h_ratio、上限 _MAX_FONT_SIZE 夾擠後再 floor MIN。
    - rotate_deg：細長（L/S ≥ _ELONGATED_ASPECT）→ theta（沿長軸）；否則 None（水平）。
    - 不 fits → (False, 0.0, None)。
    """
    n_digits = max(1, n_digits)
    long_dim, short_dim, theta = _oriented_dims(geom)
    need_w = n_digits * _DIGIT_W_RATIO * _MIN_FONT_SIZE
    need_h = _DIGIT_H_RATIO * _MIN_FONT_SIZE
    eps = 1e-6
    if long_dim + eps < need_w or short_dim + eps < need_h:
        return (False, 0.0, None)

    font_w_cap = long_dim / (n_digits * _DIGIT_W_RATIO)
    font_h_cap = short_dim / _DIGIT_H_RATIO
    font_size = max(
        _MIN_FONT_SIZE,
        min(font_w_cap, font_h_cap, _MAX_FONT_SIZE) * _FONT_SAFE_MARGIN,
    )
    rotate_deg = theta if long_dim >= _ELONGATED_ASPECT * max(short_dim, eps) else None
    return (True, font_size, rotate_deg)


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
        root = ET.fromstring(svg_bytes)  # noqa: S314  # nosec B314 — 解析自家 pbn_gen 產生的 SVG
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

    # ── Step 3b：真碎片 auto-merge（in-memory only，合進幾何最近鄰居、可跨色）
    # enable_tiny_merge=False 時跳過、產「未合併版」給對比 UI 當主版本
    merge_records = (
        _merge_tiny_polygons(all_polygons, label_map) if enable_tiny_merge else []
    )

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
    bg.set("x", "0")
    bg.set("y", "0")
    bg.set("width", bg_w)
    bg.set("height", bg_h)
    bg.set("fill", "white")

    # ── Step 5：三 pass 渲染，per-part z-order
    # Pass A 蒐集每個 output_label 的 union 幾何、拆成「個別多邊形 (part)」；
    # Pass B 依「個別 part 面積」由大到小寫所有 <path>（一個 part = 一條 path）；
    # Pass C 寫所有 <text>。兩個 z-order 重點：
    #  1. path 之間：個別多邊形大的先畫（底層）、小的後畫（上層）。SVG 後畫蓋先畫、
    #     evenodd 只在同一條 path 內挖洞、跨不同實體色不互挖；不排序的話外圍大塊若
    #     document 順序晚於被它環繞的中間異色小塊，就會把中間 fill 蓋掉。**依「個別
    #     part 面積」排序**：被包覆的區域面積必小於包覆它的區域，故 part 面積序 =
    #     幾何包覆序 → 被環繞的中間小塊永遠在上層、不被蓋。（修舊「色群總面積」排序
    #     的漏洞：中間小塊所屬色在他處剛好是大面積色時，舊排序會把它誤畫在底層被蓋。）
    #  2. path 與 text：所有 path 必須先寫完，text 才能疊在最上面不被後續 path 蓋住。

    parts_count = 0
    render_parts: list[dict] = []   # 個別多邊形（per-part），給 Pass B 的 path z-order
    render_items: list[dict] = []   # per-output_label，給 Pass C 編號放置

    # Pass A：union → 拆成個別 part
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

        # 每個 part 各成一條 path：exterior + 自己的洞（evenodd 處理本 part 的洞）
        for geom in geom_list:
            if not geom.exterior:
                continue
            d_parts = ["M " + " ".join(
                f"{x:.1f},{y:.1f}" for x, y in geom.exterior.coords
            ) + " Z"]
            for hole in geom.interiors:
                d_parts.append("M " + " ".join(
                    f"{x:.1f},{y:.1f}" for x, y in hole.coords
                ) + " Z")
            render_parts.append({
                "output_label": output_label,
                "tint": tint,
                "path_d": " ".join(d_parts),
                "area": geom.area,
            })

        render_items.append({
            "output_label": output_label,
            "geom_list": geom_list,
            # Pass C 編號放置優先序用色群總面積
            "area": sum(g.area for g in geom_list),
        })

    # Pass B：per-part 面積由大到小寫 path（大塊底層、小塊上層）。output_label 破 tie。
    render_parts.sort(key=lambda p: (-p["area"], p["output_label"]))
    for part in render_parts:
        path_el = ET.SubElement(new_root, f"{{{_SVG_NS}}}path")
        path_el.set("d", part["path_d"])
        path_el.set("fill", part["tint"])
        path_el.set("fill-rule", "evenodd")
        path_el.set("stroke", "#AAAAAA")
        path_el.set("stroke-width", sample_stroke_width)
        path_el.set("stroke-linejoin", "round")
        path_el.set("id", f"o{part['output_label']}")
    merged_count = len(render_parts)

    # Pass C 用：per-output_label 依色群總面積排序（編號放置優先序，與舊行為一致）
    render_items.sort(key=lambda it: (-it["area"], it["output_label"]))

    # Pass C：所有 path 都寫完後，把 <text> 標籤疊上去
    # 碰撞偵測用空間網格（grid）：(gx,gy) -> [(cx,cy,font_size,label)]，只比對候選點
    # 所在格 + 周圍 8 格，把原本 O(n²) 全域比對降為 O(n)，密集模板才不會逾時。
    label_grid: dict[tuple[int, int], list[tuple[float, float, float, int]]] = (
        defaultdict(list)
    )
    for item in render_items:
        output_label = item["output_label"]
        # 每個獨立 part 各放一個編號，三層篩選：
        #  1. _number_fits：這格放得下這個（n 位）數字嗎？非最大塊放不下 → skip（消死區）
        #  2. font size cap：細長用 _number_fits 字級、compact 再以 inradius 防凹形溢出
        #  3. 碰撞偵測：與既有標籤太近 → skip（密集區不互相打架）
        # 注意：collision 一律檢查（包括該色最大塊），重疊就直接 skip。
        # 這意味某些被夾在 dense 區域的色號可能無 label — admin 對小色塊改靠
        # palette_final.json 的 legend 對照查詢，不靠 SVG label。
        geom_list_by_area = sorted(item["geom_list"], key=lambda g: -g.area)
        for idx, geom in enumerate(geom_list_by_area):
            is_largest = (idx == 0)
            n_digits = len(str(output_label))

            # 篩選 1：唯一判準 —— 這格（union 後的 part）放得下這個數字嗎（最佳方向、依實際
            # 位數）？與 _merge_tiny_polygons 共用同一 predicate，消除舊「短邊 3.5–6 既不放號也
            # 不合併」的死區。（跨 union 層級的窄邊界見 _merge_tiny_polygons docstring。）
            fits, fit_font, fit_rotate = _number_fits(geom, n_digits)

            # 非最大塊：放得下才放（取代舊 _MIN_EXTRA_PART_BBOX 短邊門檻）。
            # 最大塊：維持「每色至少一個 label」保證 → 放不下也以最小字水平盡力放。
            if not is_largest and not fits:
                continue

            # polylabel 找穩定的內部點
            try:
                tol = max(1.0, (geom.area ** 0.5) / 100.0)
                pt = polylabel(geom, tolerance=tol)
            except Exception:  # noqa: BLE001
                pt = geom.centroid
            cx, cy = pt.x, pt.y

            # 篩選 2：font size。
            area_sqrt = max(geom.area, 1.0) ** 0.5
            if fits and fit_rotate is not None:
                # 細長 → 數字旋轉沿長軸；字級用 _number_fits（短邊夾擠、含安全邊距）→
                # 填滿細長條又不溢出。不套 inradius（細長 inradius 太小會誤縮字）。
                rotate_deg: float | None = fit_rotate
                font_size = fit_font
            else:
                # 方塊/compact（或最大塊放不下的盡力情況）→ 水平。
                # 字級取 _number_fits 與「內接半徑」上限的較小者（防凹形溢出到鄰格），
                # 再以 area_sqrt/8 壓大塊、floor 在 _MIN_FONT_SIZE。
                rotate_deg = None
                inradius = pt.distance(geom.boundary)
                base_font = fit_font if fits else _MIN_FONT_SIZE
                font_size = max(
                    _MIN_FONT_SIZE,
                    min(base_font, inradius * _FONT_FIT_RATIO, area_sqrt / 8.0,
                        _MAX_FONT_SIZE),
                )

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
            # 細長區塊：把數字旋轉到沿長軸（>1° 才設，避免無意義的 rotate(0)）
            if rotate_deg is not None and abs(rotate_deg) > 1.0:
                text_el.set("transform", f"rotate({rotate_deg:.1f} {cx:.1f} {cy:.1f})")
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
        "svg consolidate: %d unique colors → %d paths (per-part), "
        "%d label texts placed (skipped no_fill=%d unknown_tint=%d invalid=%d), "
        "%d tiny polygons auto-merged",
        len(polygons_by_label), merged_count, parts_count,
        skipped_no_fill, skipped_unknown_tint, skipped_invalid_geom,
        len(merge_records),
    )

    return ET.tostring(new_root, encoding="utf-8", xml_declaration=True), merge_records


def render_filled_png(
    svg_bytes: bytes,
    palette_final: list[dict],
    supersample: int = 2,
) -> bytes:
    """把 finalize 產出的 template_final.svg 多邊形用「實體色原色」填滿成 PNG。

    填色預覽 = 照線稿塗完的真實樣子 —— 與線稿**同一份幾何、同一套 z-order**，
    故不會出現「填色比線稿細／顏色位置對不上」（修「填色用 snapped 點陣、線稿用
    向量」兩套幾何不一致）。

    作法：解析 template_final.svg 的 <path id="oN">（已按 part 面積大→小排序，即
    document 順序就是底→上的正確繪製序），每條 path 取 exterior 用 palette_final
    的實體色原色實心填。被包覆的小塊在 document 序較後 → 畫在上層蓋掉外圍洞，holes
    交給後畫的小塊覆蓋（與 SVG painter 行為一致）。supersample 2x + LANCZOS 抗鋸齒。
    """
    import io  # noqa: PLC0415
    import re  # noqa: PLC0415

    from PIL import Image, ImageDraw  # noqa: PLC0415

    root = ET.fromstring(svg_bytes)  # noqa: S314  # nosec B314 — 解析自家產生的 SVG
    vb = (root.get("viewBox") or "0 0 1000 1000").split()
    try:
        w, h = int(round(float(vb[2]))), int(round(float(vb[3])))
    except (IndexError, ValueError):
        w, h = 1000, 1000
    label_rgb = {
        int(p["output_label"]): tuple(int(c) for c in p["rgb"])
        for p in palette_final
    }

    ss = max(1, int(supersample))
    canvas = Image.new("RGB", (w * ss, h * ss), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    path_tag = f"{{{_SVG_NS}}}path"
    for path_el in root.iter(path_tag):
        d = path_el.get("d")
        pid = path_el.get("id") or ""
        m = re.match(r"o(\d+)$", pid)
        if not d or not m:
            continue
        rgb = label_rgb.get(int(m.group(1)))
        if rgb is None:
            continue
        # 取 exterior（第一個 M..Z）實心填；洞交給後畫的小塊覆蓋
        subs = re.findall(r"M ([^MZ]+) Z", d)
        if not subs:
            continue
        coords = subs[0].replace(",", " ").split()
        pts = [
            (float(coords[i]) * ss, float(coords[i + 1]) * ss)
            for i in range(0, len(coords) - 1, 2)
        ]
        if len(pts) >= 3:
            draw.polygon(pts, fill=rgb)

    if ss > 1:
        canvas = canvas.resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
