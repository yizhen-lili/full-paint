# 易木 YIIMUI — Store Design System

> Store 端視覺與互動的單一來源。每個模組規劃書的「設計決策」段落引用此檔；不重新發明色票、字體、間距。
> 與 [admin/docs/design_system.md](../../admin/docs/design_system.md) 是**同品牌不同子產品**的關係（admin 工房後台、store 客戶門市），主色與字體刻意分流。

---

## 1. 方向 — 易木編輯誌（Yiimui Editorial）

### 一句話
**像翻一本日台慢生活雜誌——大留白、編輯感排版、清新典雅、商品攝影為主角。**

### 心象
- Kinfolk / Cereal magazine 的留白感
- 暮しの手帖 / 小日子的編輯排版
- Aesop 商品頁的安靜攝影
- 商品圖暖調，但不過度復古

### 紀律（禁區）
- ❌ 紙紋 noise（admin 有，store 不放，要更乾淨）
- ❌ 多色 accent（整站只一個栗色）
- ❌ 大圓角（≥ 8px）
- ❌ 漸層背景
- ❌ hover scale > 1.05、bounce、彈跳
- ❌ 商品卡花俏邊框 / 投影過重
- ❌ 中文標題粗體（weight ≥ 500）

### 取代之以
- ✓ 米白底 + 1px hairline 兩階線分層
- ✓ 商品圖 sepia 0.07 saturate 0.92 暖統一濾鏡
- ✓ 中文標題 weight 300 light、字距 0.04em（透氣）
- ✓ 按鈕全大寫 + 字距 0.24em（編輯感）
- ✓ Section header「eyebrow + 大標 + line」三層結構

---

## 1.5 Logo（B1 純文字版）

### 形式
純文字兩行：
- 主行：`易木 YIIMUI`（中文 + 英文，中間半形空格）
- 副行：`Paint by Number Atelier`（small caps、letter-spacing 加寬）

### 樣式
```css
.site-logo {
  text-align: center;
  font-family: 'Noto Serif TC', serif;
  font-weight: 300;
  font-size: 22px; letter-spacing: 0.12em;
  color: var(--color-ink-strong);
  line-height: 1.2;
}
.site-logo small {
  display: block;
  font-family: 'Cormorant Garamond', serif;
  font-weight: 400;
  font-size: 9px; letter-spacing: 0.4em;
  color: var(--color-ink-muted);
  margin-top: 4px;
  text-transform: uppercase;
}
```

### 三尺寸規格

| Context | 主行 size | 副行 size |
|---|---|---|
| Sticky Header | 22px | 9px |
| Footer 暗底 | 22px | 9px（顏色換淡米白）|
| Hero / Print 大尺寸 | 44px | 12px |

### 出貨單 / 感謝卡 / IG 頭像
純文字 logo 直接縮放使用，不另設計圓徽章 / 印章版本（B2/B3 不採用）。

如需 favicon / 社群頭像方形版本：取「易」單字，背景 `--color-paper-canvas`、文字 `--color-ink-strong`、Noto Serif TC weight 400 size 大、置中。

### 禁止
- ❌ 改主行字體為西文（Cormorant 等） — 中文要在前
- ❌ 改副行為粗體
- ❌ logo 上加色塊背景 / 框線
- ❌ 副行翻譯成中文（要保留 small caps 英文當編輯感點綴）

---

## 2. 字體

### 選擇

| 用途 | 字體 | CJK Fallback | 為什麼 |
|---|---|---|---|
| **Display 西文** | **Cormorant Garamond** weight 300/400 | — | 西式經典襯線、編輯誌典雅、不古典過頭 |
| **Display 中文** | **Noto Serif TC** weight 300 | — | Google Fonts 上能用的繁中襯線最纖細版本，明朝體典雅清新 |
| **Body** | **Manrope** weight 300/400 | **Noto Sans TC** weight 300 | 圓潤無襯線、有人文氣、與襯線標題對比恰到好處 |
| **Numerals** | **JetBrains Mono** weight 400 | — | 價格 / 訂單編號 / Issue 編號等 tabular figures |

### 不選哪些（決策痕跡）
- **Inter / SF Pro**：太 SaaS、無編輯感
- **Playfair Display**：高反差襯線太華麗（時尚誌路線，與「日系典雅」衝突）
- **Shippori Mincho B1**：書道筆觸偏厚重（admin 用，store 要更輕）
- **Hina Mincho**：user 試過明確不喜歡
- **Klee One**：偏童趣手寫感、不夠典雅
- **DM Sans**：幾何感比 Manrope 銳利、偏冷

### 載入

```html
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500&family=Noto+Serif+TC:wght@300;400&family=Noto+Sans+TC:wght@300;400&family=Manrope:wght@300;400;500&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
```

### 字級規模

| Token | 字體 | px / line-height | weight | 用途 |
|---|---|---|---|---|
| `text-hero` | Noto Serif TC | 60 / 1.4 | 300 | 首頁 / 大頁 hero 主標題 |
| `text-display` | Noto Serif TC | 42 / 1.45 | 300 | 客製 banner / 大型 section 標題 |
| `text-h1` | Noto Serif TC | 36 / 1.3 | 300 | section 標題 |
| `text-h2` | Noto Serif TC | 24 / 1.4 | 300 | 子區塊 / 商品詳情 / 主題名 |
| `text-h3` | Noto Serif TC | 20 / 1.4 | 300 | 商品卡標題 |
| `text-body` | Manrope + Noto Sans TC | 15 / 1.85 | 300 | 內文預設 |
| `text-meta` | Manrope | 12 / 1.7 | 400 | 表單 label / 標籤 / 時間戳 |
| `text-eyebrow` | Manrope | 11 / 1.7 | 400 | uppercase + letter-spacing 0.32em |
| `text-num-sm` | JetBrains Mono | 13 / 1.5 | 400 | 商品價格 / 數量 |
| `text-num-mono` | JetBrains Mono | 11 / 1.7 | 400 | uppercase + letter-spacing 0.18em，用於 No. 編號 |

### 字距 / 行距慣例
- 中文標題 `letter-spacing: 0.04em`（透氣感、不擁擠）
- 西文標題（Cormorant）`letter-spacing: 0.02em`
- Eyebrow / 按鈕 / 標籤 uppercase 字距 `0.18em – 0.32em`
- 中文 body 字距 `0.04em`
- 中文標題 line-height `1.4`
- 中文 body line-height `1.85`（比 admin 1.7 鬆，呼吸感）

---

## 3. 色票

### 設計準則
1. 整站只一個 accent — 深栗 `#7B5841`，不分模組各色
2. 米白底偏暖（`#F5F1E8` 比 admin `#F5F0E6` 偏暖一點）
3. 米白 paper 系統三階：canvas → surface → deep
4. **無第二輔色**：拒絕加任何抹茶綠 / 靛藍 / 麻布綠（純米栗系統）
5. 飽和度上限 `30%`，明度區間 `30–96%`

### 3.1 紙與墨

| Token | Hex | 用途 |
|---|---|---|
| `--color-paper-canvas` | `#F4EFE2` | 整頁底（pale ivory，user 確認） |
| `--color-paper-surface` | `#FBF7EC` | 卡片 / 商品卡底（比 canvas 亮一階） |
| `--color-paper-deep` | `#F2E8D5` | band（局部 highlighted，Pearl Linen） |
| `--color-ink-strong` | `#1F1A15` | 標題、價格 |
| `--color-ink-default` | `#3F362C` | 內文 |
| `--color-ink-muted` | `#7E7163` | 輔助、placeholder、meta |
| `--color-ink-disabled` | `#BBB1A1` | disabled |
| `--color-line-subtle` | `#EBE2D0` | 商品卡邊框、極細分隔 |
| `--color-line` | `#C8B99F` | section 分隔、表格 row、強分線 |

### 3.2 主色 — Taupe Walnut

> 用於文字、連結、eyebrow、icon、邊線。**不放整片大塊背景。**

| Token | Hex | 用途 |
|---|---|---|
| `--color-accent` | `#8C6E52` | 主色（連結、eyebrow、CTA outline） |
| `--color-accent-deep` | `#5E4732` | hover 深一階 |
| `--color-accent-soft` | `#B8A084` | 副 walnut（No. 編號、輕量分線） |
| `--color-accent-tint` | `#ECE3D2` | tint chip 底、選中態背景 |

### 3.2b 副色 — Fresh 苔綠（清新輔色）

> 用於 series eyebrow、Pick of this Series、success icon、chapter cap。

| Token | Hex | 用途 |
|---|---|---|
| `--color-fresh` | `#6B7F5C` | series 標籤、success 主色 |
| `--color-fresh-soft` | `#97A687` | 苔綠 soft |
| `--color-fresh-tint` | `#DDE5D2` | success icon 底 |

### 3.2c 點綴 — Wine 酒紅（pop accent）

> 用於 FEATURED chip、state-danger、雜誌封面式 italic em 強調。**極克制使用。**

| Token | Hex | 用途 |
|---|---|---|
| `--color-accent-wine` | `#7B2E40` | FEATURED chip border、danger 主色 |
| `--color-accent-wine-soft` | `#A85D6C` | wine 較淺一階 |

> 與 admin walnut `#7A4E32` 的差別：飽和度從 41% 降到 28%，明度從 34% 提到 36%，整體更柔。

### 3.3 狀態色

> 狀態色只用於 toast / form error / order status / payment status — 不滲入主視覺。

| Token | Hex | 對應狀態 |
|---|---|---|
| `--color-state-success` | `#6B7F5C` | paid / completed / 預購可接（= fresh） |
| `--color-state-warning` | `#B6924E` | pending / 待處理 / 報價中 |
| `--color-state-danger` | `#7B2E40` | error / 退款 / 已取消（= wine） |
| `--color-state-info` | `#74819A` | 中性提示 |

### 3.4 完整 Tailwind 4 Theme

```css
/* store/src/style.css @theme block — 與本檔保持同步 */
@theme {
  /* Paper — 三階淺底 */
  --color-paper-canvas: #F4EFE2;     /* 頁面底 */
  --color-paper-surface: #FBF7EC;    /* 卡片高光 */
  --color-paper-deep: #F2E8D5;       /* band — Pearl Linen */

  /* Ink */
  --color-ink-strong: #1F1A15;
  --color-ink-default: #3F362C;
  --color-ink-muted: #7E7163;
  --color-ink-disabled: #BBB1A1;

  /* Line */
  --color-line-subtle: #EBE2D0;
  --color-line: #C8B99F;

  /* Primary accent — Taupe Walnut */
  --color-accent: #8C6E52;
  --color-accent-deep: #5E4732;
  --color-accent-soft: #B8A084;
  --color-accent-tint: #ECE3D2;

  /* Fresh — 苔綠 */
  --color-fresh: #6B7F5C;
  --color-fresh-soft: #97A687;
  --color-fresh-tint: #DDE5D2;

  /* Wine — 酒紅 pop */
  --color-accent-wine: #7B2E40;
  --color-accent-wine-soft: #A85D6C;

  /* States */
  --color-state-success: #6B7F5C;
  --color-state-warning: #B6924E;
  --color-state-danger: #7B2E40;
  --color-state-info: #74819A;

  /* Typography */
  --font-display: 'Cormorant Garamond', 'Noto Serif TC', serif;
  --font-cn-serif: 'Noto Serif TC', serif;
  --font-body: 'Manrope', 'Noto Sans TC', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* Radius */
  --radius-xs: 2px;
  --radius-sm: 4px;
  --radius-md: 6px;
}
```

### 3.5 開發者工具

實機看色票時：
- **`/_palette`** — 完整 design tokens 列表頁
- **`/_band-picker`** — band 顏色挑選頁（保留候選色備用）

### 3.6 user 確認 / 禁止項

- ✅ 「同色系不單調」原則：用三階 paper 淺底分層，不靠色塊明暗大幅切換
- ✅ Taupe Walnut 是文字色，不是背景
- ✅ 章節以 hairline 收口
- ❌ 純白 surface（撕裂感）
- ❌ 太深的 sandy / khaki / 大塊深棕 walnut deep / wine 漸層做 section bg（user 反饋太深）
- ❌ AuthLayout 卡片頂部的 3 色漸層 stripe（已拿掉）

---

## 4. 間距 Scale

留白優先（電商呼吸感 > 資訊密度）。

| Token | px | 用途 |
|---|---|---|
| `--space-1` | 4 | icon gap、tag inset |
| `--space-2` | 8 | input 與 label |
| `--space-3` | 12 | 表單 stack 緊湊 |
| `--space-4` | 16 | 表單 group |
| `--space-5` | 20 | 卡片內距 |
| `--space-6` | 24 | section 內主要間距 |
| `--space-7` | 32 | 卡片間 gap、表單跨群組 |
| `--space-8` | 48 | 區塊分段 |
| `--space-9` | 64 | section header 與內容 |
| `--space-10` | 96 | section 上下 padding（比 admin 32 鬆 3 倍） |
| `--space-11` | 120 | hero 上下 padding、footer 上邊距 |

### 應用慣例
- **頁面外距桌面（≥ 1024）**：56–64px
- **頁面外距 mobile（< 768）**：24px
- **卡片內距（商品卡 product-body）**：22px
- **Hero 上下 padding**：96–120px
- **Section 上下 padding**：96px
- **商品卡間 gap**：28–32px

**為什麼比 admin 鬆 3 倍**：admin 是後台資訊密度高，store 是電商商品為主、文字退後、留白讓視覺呼吸。

---

## 5. 圓角 / 線條 / 陰影

### 圓角
| Token | 用途 |
|---|---|
| `0` | 商品卡、hero 大圖、主題卡、custom banner（直角紙感） |
| `--radius-xs: 2px` | tag、status badge |
| `--radius-sm: 4px` | button、input、icon-btn |
| `--radius-md: 6px` | modal、dropdown |

**禁止**：≥ 8px。商品卡刻意用直角，強化「雜誌頁面 / lookbook」視覺。

### 線條
- **永遠 1px**——不用 2px 線
- 兩階 hairline：`--color-line-subtle` 商品卡邊、極細分隔；`--color-line` section 分線、表格 row
- focus ring：`outline: 2px solid var(--color-accent); outline-offset: 2px`

### 陰影
- 商品卡 hover：`box-shadow: 0 4px 18px rgba(46, 40, 35, 0.06)`（極淡）
- modal / dropdown：`box-shadow: 0 8px 32px rgba(46, 40, 35, 0.10)`
- **預設無陰影**——靠 1px hairline 分層

---

## 6. 攝影策略

> 商品圖、主題圖、hero 圖、客製案例圖統一一個濾鏡，避免顏色雜亂。

```css
.image {
  filter: sepia(0.07) saturate(0.92);
}
.image:hover {
  filter: sepia(0.07) saturate(0.92) brightness(1.05);
}
```

- **比例**：商品圖 4:5 直幅；主題卡 1.3:1 橫幅；客製 banner 1:1
- **裁切**：物件居中或黃金分割
- **濾鏡解釋**：sepia 0.07 給整體暖調 wash；saturate 0.92 微降飽和讓配色不打架
- **暗色照片例外**：主題卡、hero 大圖可保留暗調（不過度提亮），用 overlay 漸層放標題

---

## 7. 動畫哲學

- **頁面進場**：fade-in，180ms ease
- **Hover**：色彩 / 邊框 / 陰影變化，120–200ms
- **商品圖 hover**：`transform: scale(1.03)` + `filter: brightness(1.05)`，600ms transform、200ms filter
- **主題圖 hover**：`transform: scale(1.03)`，800ms ease
- **Modal**：fade + 從中心向上 8px，180ms
- **Toast**：右下淡入，停 4s，淡出
- **Skeleton**：靜態灰塊（`--color-paper-deep`），不要 shimmer
- **絕對禁止**：bounce、spring physics、3D flip、parallax、scale > 1.05

---

## 8. 元件原則

### Button

| 變體 | 樣式 | 用途 |
|---|---|---|
| **Primary** | 實心 `--color-ink-strong` 底 + `--color-paper-canvas` 字 + uppercase + letter-spacing 0.24em | hero CTA、結帳「送出訂單」 |
| **Outline** | 1px `--color-ink-strong` 邊 + 透明底 + `--color-ink-strong` 字 + uppercase | secondary CTA |
| **Link** | 透明底 + `--color-accent` 字 + uppercase + letter-spacing 0.24em | 「Custom →」「View All →」 |
| **Danger** | 實心 `--color-state-danger` 底 + 白字 | 取消訂單、刪除地址 |

- 高度 44px（hero / 主 CTA）/ 36px（list / table 內）
- 圓角 `--radius-sm: 4px`
- Padding 16px 32px（lg）/ 13px 28px（md）

### Input / Textarea
- 1px `--color-line` 底邊（無上左右邊框，underline 風格）
- 或 1px `--color-line-subtle` 全邊框 + `--color-paper-surface` 內底
- focus → 邊框換 `--color-accent`
- error → 邊框換 `--color-state-danger`
- 高度 44px（form）/ 36px（filter / inline）

### Product Card
- `--color-paper-surface` 底 + 1px `--color-line-subtle` 邊
- 圓角 0（直角）
- 圖佔上半部 4:5 + 1px hairline 底邊分隔
- product-body 內距 22px
- 順序：No. 編號（mono）→ 商品標題（h3）→ meta（uppercase）→ 1px hairline → 價格 row（label 上 / 價格下）
- hover：邊框 `--color-line` + box-shadow 4px blur 6% alpha

### Theme Card
- 底圖 sepia 0.06 + 漸層 overlay（rgba(46,40,35,0.55) → 0）
- 標題 `--font-cn-serif` weight 300 + size 24
- meta uppercase mono
- hover：圖 scale 1.03、800ms

### Section Header
- eyebrow + 大標 + section-link 一行
- 下方 1px `--color-line` 分線 + padding-bottom 24px
- 大標 weight 300、size 36、letter-spacing 0.06em

### Site Header（sticky）
- 三段式 grid：左 nav / 中 logo / 右 actions
- 半透明背景 + backdrop-filter blur 12px
- 1px `--color-line-subtle` 底邊
- 高度 81px（含 padding 20px）

### Status Badge
- 高 22px、圓角 `--radius-xs`、padding 4 / 8
- state 色文字 + state 8% alpha 底
- mono 字體、uppercase、letter-spacing 0.16em

---

## 9. 圖示

- 統一 **Lucide Icons**（與 admin 一致）
- `stroke-width: 1.5`
- 16 / 18 / 20 / 24px 四種尺寸（store 比 admin 多一個 18，header icon 用）
- 顏色繼承（`currentColor`）
- 禁止與 Heroicons / Material 混用

---

## 10. A11y 基準

- 文字對比 ≥ 4.5:1（除 disabled）— 所有 token WCAG AA 驗證
- focus 可見：`outline: 2px solid var(--color-accent); outline-offset: 2px`
- 鍵盤可達、Esc 關 modal、focus trap
- form 必有 label
- icon button 必有 aria-label
- Lighthouse Accessibility ≥ 90

---

## 11. 暗色模式

**v1 不做。** Token 設計已預留通道（`:root[data-theme='dark']` 覆蓋同名 token），元件層只引 token 不直接寫色碼。

---

## 12. 跨模組強制慣例

- 頁面結構：`<header>` + `<main>` + `<footer>`，每個 page route 第一個元素是 hero / page-header
- 列表頁：篩選列（左欄 sticky）+ 商品 grid（4 col 桌面 / 2 col 平板 / 1 col 手機）+ 分頁底
- 詳情頁：左 1.1fr 圖片輪播 + 右 1fr 規格選擇與資訊
- 表單：縱向單欄、CTA 在頁尾右
- 空狀態：1 個 lucide icon（24px、`--color-ink-muted`）+ 1 句說明 + 1 個 CTA；不放插畫
- < 1024px：site-nav 折成漢堡抽屜；商品 grid 變 2 col
- < 768px：商品 grid 變 1 col；page padding 24px

---

## 13. 與 admin 差異速查

| 項目 | admin | store |
|---|---|---|
| Display 字體 | Shippori Mincho B1 weight 500 | Cormorant Garamond + Noto Serif TC weight 300 |
| Body 字體 | IBM Plex Sans + Noto Sans TC | Manrope + Noto Sans TC weight 300 |
| 主色 | walnut `#7A4E32`（飽和 41%） | walnut light `#7B5841`（飽和 28%、明度高） |
| 底色 | `#F5F0E6`（紙黃） | `#F5F1E8`（米白偏暖） |
| 紙紋 noise | 有（opacity 0.04） | **無**（要乾淨） |
| 頁面 padding | 32px 緊密 | 56–64px 寬鬆 |
| Section padding | 32px | 96px（3x） |
| 中文標題 weight | 500 medium | 300 light |
| 商品圖 | n/a | sepia 0.07 saturate 0.92 暖統一濾鏡 |
| 商品卡 hover | n/a | scale 1.03 + brightness 1.05 + box-shadow |
| 大圓角 | sm 4 / md 6 | **同**（紙感剪邊維持） |
| 動畫時長 | 120–180ms | 180–600ms（圖片變化更慢） |
| 多色 accent | 禁 | 禁（同） |

---

## 14. 黑名單

- 紫漸層 / 藍紫科技色
- 商品卡圓角 ≥ 8px
- 中文標題粗體（weight ≥ 500）
- shadow-2xl / 多層景深
- hover scale > 1.05、bounce、彈跳
- 多色 accent 同頁
- 圖示混風格
- emoji 當 icon
- Material Design 元件視覺
- shimmer skeleton
- 紙紋 noise（admin 才有，store 不放）
- 第二輔色（抹茶綠 / 靛藍 / 麻布綠等）
