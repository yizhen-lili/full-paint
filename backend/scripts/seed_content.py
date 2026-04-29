"""一次性：seed F10 內容管理需要的初始資料。

涵蓋：
1. static_pages — 5 個標準頁面（size_guide / shipping / custom_process / pricing_reference / refund_policy）
2. system_settings — 13 個預設 key-value
3. custom_photo_prices — 17 種尺寸 × 4 難易度共 68 筆基礎定價
4. custom_photo_surcharges — 5 個常用加費項目
5. case_categories — 4 個常用案例分類

冪等：已存在就跳過，不覆蓋管理員已調過的內容。

用法：
    cd backend && venv/Scripts/python scripts/seed_content.py
"""
import asyncio
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import core._windows_compat  # noqa: F401, E402

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import auth.models  # noqa: F401, E402
import color.models  # noqa: F401, E402
import custom.models  # noqa: F401, E402
import discount.models  # noqa: F401, E402
import orders.models  # noqa: F401, E402
import product.models  # noqa: F401, E402
import production.models  # noqa: F401, E402
from color.models import SystemSetting  # noqa: E402
from content.models import CaseCategory, Page  # noqa: E402
from core.config import settings  # noqa: E402
from custom.models import CustomPhotoPrice, CustomPhotoSurcharge  # noqa: E402

PAGES = [
    ("size_guide", "尺寸指南", """## 標準畫布尺寸

我們提供以下 17 種標準尺寸，分為**正方形**、**直幅**、**橫幅**三類。

### 正方形
- 20×20 cm（小型方）
- 30×30 cm（標準方）
- 40×40 cm
- 50×50 cm
- 60×60 cm（大型方）

### 直幅
- 30×40、30×50、30×60
- 40×50、40×60
- 50×60

### 橫幅
- 40×30、50×30、60×30
- 50×40、60×40
- 60×50

> 任何一邊 > 40cm 的商品建議選宅配，超商店到店尺寸有限制。
"""),
    ("shipping", "出貨流程", """## 出貨流程

1. **付款確認**：管理員核對轉帳資訊（24 小時內）
2. **生產製作**：客製訂單需 3–7 天製作
3. **打包出貨**：包裝後透過 ECpay 物流寄出
4. **收貨確認**：物流送達後，客戶可主動點「確認收貨」

### 取貨方式

- **黑貓宅配**：NT$120
- **7-11 店到店**：NT$70
- **全家店到店**：NT$70

### 免運條件

- 訂單滿 NT$800
- 或數量滿 3 件
"""),
    ("custom_process", "訂製流程", """## 訂製化服務流程

1. **提交申請**：上傳照片 + 填寫尺寸 / 難易度偏好 + 備註
2. **管理員製作初稿**：3 個工作天內回覆報價含預覽圖
3. **客戶確認 / 修改**：可修改 3 次內，每次調整後重新發報價
4. **付款 + 製作 + 出貨**：確認後進入正式生產流程

### 客製照片要求

- 解析度建議 1920×1080 以上
- JPEG 或 PNG，最大 20MB
- 主體清晰、避免過暗或過曝
"""),
    ("pricing_reference", "報價參考", """## 客製化照片報價參考

### 基礎價（NT$，依尺寸 × 難易度）

| 尺寸 | 入門 | 初級 | 中級 | 進階 |
|------|------|------|------|------|
| 30×40 | 480 | 580 | 680 | 880 |
| 40×50 | 580 | 680 | 880 | 1080 |
| 50×70 | 780 | 880 | 1080 | 1280 |

### 加費項目

可能依照片內容增加：
- 人物 2 人：+200
- 寵物毛髮細節：+250
- 複雜背景：+300

### 服務費率

最終售價 = 基礎價 × **2.0 倍**

> 實際報價以管理員確認為準。
"""),
    ("refund_policy", "退款退貨政策", """## 退款退貨政策

### 可退款情境

- 商品瑕疵 / 與訂單不符 → **全額退款 + 商品寄回（運費由我方負擔）**
- 客戶因素 7 天內申請退貨 → **退款 70%**（扣除製作成本）
- 客戶單方面取消已付款訂單 → 視製作進度個案處理

### 不可退款情境

- 商品已使用、損毀
- 客戶已確認收貨超過 14 天

### 退款流程

1. 透過聯絡表單或客服 email 申請
2. 管理員審核後標記退款處理中
3. 退款於 5 個工作天內完成入帳
4. 客戶收到退款後請於訂單頁點「確認已收到退款」

> 客製商品（依客戶提供照片製作）不適用 7 天鑑賞期。
"""),
]

SETTINGS = [
    ("bank_account_number", "1234-56-789012-0"),
    ("bank_name", "玉山銀行（808）"),
    ("bank_account_name", "易木 YIIMUI 工作室"),
    ("quote_reply_days", "3"),
    ("product_info_tools", "**包含內容物**\n- 數字模板畫布 × 1\n- 顏料套組（壓克力顏料）\n- 畫筆 × 3 支\n- 對照色卡"),
    ("product_info_material", "**畫布材質**：細棉麻織布裱於 MDF 板上，表面已上底劑，可直接上色。"),
    ("product_info_tips", "**繪畫建議**：\n1. 從淺色開始畫\n2. 一次只用一支筆，避免顏料混濁\n3. 大色塊先填，小細節最後修\n4. 可由淺至深疊加營造層次"),
    ("product_info_notes", "**注意事項**：請避免陽光直射；上色後需待乾燥 24 小時方可裝裱。"),
    ("paint_ml_per_cm2", "0.05"),
    ("paint_min_ml", "3"),
    ("paint_buffer_ratio", "1.3"),
    ("custom_photo_price_multiplier", "2.0"),
    ("payment_absolute_deadline_hours", "48"),
]

# 17 種標準畫布
CANVAS_SIZES = [
    (20, 20), (30, 30), (40, 40), (50, 50), (60, 60),
    (30, 40), (30, 50), (30, 60),
    (40, 50), (40, 60),
    (50, 60),
    (40, 30), (50, 30), (60, 30),
    (50, 40), (60, 40),
    (60, 50),
]

# 4 難易度的基礎價（依面積與難度線性 / 階梯式估）
def _price(w: int, h: int, difficulty: str) -> Decimal:
    area = w * h
    base = 200 + area * 0.4  # NT$200 起 + 每 cm² ~0.4
    multiplier = {
        "beginner": 1.0,
        "elementary": 1.2,
        "intermediate": 1.5,
        "advanced": 1.85,
    }[difficulty]
    return Decimal(str(round(base * multiplier / 10) * 10))


SURCHARGES = [
    ("人物數量", "2 人", 200),
    ("人物數量", "3 人以上", 400),
    ("背景複雜度", "細節豐富", 300),
    ("毛髮 / 質感", "寵物毛髮細節", 250),
    ("特殊處理", "限時加急（5 工作天內）", 500),
]

CASE_CATEGORIES = ["人像", "寵物", "風景", "建築"]


async def main():
    engine = create_async_engine(settings.database_url, echo=False)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        # static_pages
        existing_slugs = set(
            (await db.execute(select(Page.slug))).scalars().all()
        )
        added_pages = 0
        for slug, title, content in PAGES:
            if slug in existing_slugs:
                continue
            db.add(Page(slug=slug, title=title, content=content))
            added_pages += 1

        # system_settings
        existing_keys = set(
            (await db.execute(select(SystemSetting.key))).scalars().all()
        )
        added_settings = 0
        for key, value in SETTINGS:
            if key in existing_keys:
                continue
            db.add(SystemSetting(key=key, value=value))
            added_settings += 1

        # custom_photo_prices
        existing_prices = (
            await db.execute(select(CustomPhotoPrice.canvas_w, CustomPhotoPrice.canvas_h, CustomPhotoPrice.difficulty))
        ).all()
        existing_price_keys = {(int(w), int(h), str(d)) for w, h, d in existing_prices}
        added_prices = 0
        for w, h in CANVAS_SIZES:
            for diff in ("beginner", "elementary", "intermediate", "advanced"):
                if (w, h, diff) in existing_price_keys:
                    continue
                db.add(CustomPhotoPrice(canvas_w=w, canvas_h=h, difficulty=diff, price=_price(w, h, diff)))
                added_prices += 1

        # custom_photo_surcharges
        existing_surcharges = (
            await db.execute(select(CustomPhotoSurcharge.category, CustomPhotoSurcharge.label))
        ).all()
        existing_sur_keys = {(cat, label) for cat, label in existing_surcharges}
        added_surcharges = 0
        for cat, label, amount in SURCHARGES:
            if (cat, label) in existing_sur_keys:
                continue
            db.add(CustomPhotoSurcharge(
                category=cat, label=label, amount=Decimal(str(amount)), is_active=True,
            ))
            added_surcharges += 1

        # case_categories
        existing_cats = set(
            (await db.execute(select(CaseCategory.name))).scalars().all()
        )
        added_cats = 0
        for name in CASE_CATEGORIES:
            if name in existing_cats:
                continue
            db.add(CaseCategory(name=name))
            added_cats += 1

        await db.commit()

    print(f"static_pages:           +{added_pages}")
    print(f"system_settings:        +{added_settings}")
    print(f"custom_photo_prices:    +{added_prices}")
    print(f"custom_photo_surcharges:+{added_surcharges}")
    print(f"case_categories:        +{added_cats}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
