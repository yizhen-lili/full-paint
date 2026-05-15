"""SVG 內標籤文字重編號工具（不重 render，純 XML 修改）。

用於對應完成（finalize）後，把 pbn_gen 產出的 template.svg 內每個 <text>
element 的內容（algorithm template_id 字串，例如 "5"）替換成
consolidated output_label 字串（例如 "3"）。其他 element（polygon、defs、
attrs）完全不動。

設計理由：
- pbn_gen.py 是 lock 狀態（pbn_gen lock memory），不重 render
- pbn_gen 的 output_to_svg 結構保證：每個標籤 <text> 的內容**完全等於** template_id
  的 str(int) 形式（pbn_gen.py:1712 `label = str(color_to_seq.get(...))`），
  沒有其他純數字文字會干擾
- 用 stdlib xml.etree.ElementTree，不引新依賴
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# pbn_gen 寫 SVG 用 svgwrite，預設 namespace 是 http://www.w3.org/2000/svg
_SVG_NS = "http://www.w3.org/2000/svg"
_TEXT_TAG = f"{{{_SVG_NS}}}text"


def renumber_svg_labels(svg_bytes: bytes, label_map: dict[int, int]) -> bytes:
    """重新編號 SVG 內所有純數字 <text> element。

    參數：
        svg_bytes:  原始 SVG 二進位內容（從 Firebase 拉下來的原 template.svg）
        label_map:  {template_id: output_label} 對應表

    回傳：
        修改後的 SVG bytes（同樣含 <?xml ...?> 宣告與 svg namespace）

    行為：
        - 走訪所有 <text> element
        - 若 text content 是純數字（去除前後空白後）且能 int() 解析
          且該 int 在 label_map → 替換 text content 為 str(label_map[int])
        - 不在 label_map → 不動（log debug 一筆）
        - 不是純數字 → 不動

    錯誤處理：
        - SVG parse fail → ValueError
        - label_map 是空字典 → ValueError（呼叫端責任）
    """
    if not label_map:
        raise ValueError("label_map 不可為空")

    try:
        # parser 保留 namespace 註冊，serialize 時才不會把 xmlns 拆得很怪
        ET.register_namespace("", _SVG_NS)
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as e:
        raise ValueError(f"SVG 解析失敗：{e}") from e

    replaced = 0
    skipped_unknown = 0
    for text_el in root.iter(_TEXT_TAG):
        content = (text_el.text or "").strip()
        if not content or not content.isdigit():
            continue  # 非數字標籤（理論上 pbn_gen 不會有，安全保險）
        try:
            tid = int(content)
        except ValueError:
            continue
        if tid not in label_map:
            skipped_unknown += 1
            continue
        text_el.text = str(label_map[tid])
        replaced += 1

    logger.info(
        "svg renumber: %d labels replaced, %d unknown template_id skipped, map size %d",
        replaced, skipped_unknown, len(label_map),
    )

    # ET.tostring 用 xml_declaration=True 才會加 <?xml ?> header
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
