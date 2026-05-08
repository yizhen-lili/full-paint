<script setup lang="ts">
// 客製化 hub 4 個 layout 方向預覽
// 每個 variant 用同樣的 hero 文字 + 假資料，差別只在版面結構與裝飾
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import {
  ArrowRight, BookOpen, Image as ImageIcon, Sparkles,
  ImagePlus, MessageSquare, CheckCircle2, Palette,
} from 'lucide-vue-next'
import { listCustomCases, type CustomCase } from '@/features/custom/api'

type Variant = 'A' | 'B' | 'C' | 'D'
const variant = ref<Variant>('A')

const VARIANT_INFO: Record<Variant, { label: string; tag: string }> = {
  A: { label: '兩大主視覺 split', tag: '左圖右行動 · 不對稱 · 編輯風' },
  B: { label: '條列目錄式', tag: '純文字 · hairline 分隔 · 紙感' },
  C: { label: '雜誌封面式', tag: '滿版圖大 · 文字導航輕量' },
  D: { label: '案例為入口', tag: '砍 hub 概念 · /custom 直接 = cases' },
}

// 案例資料（用最新 6 件）
const casesQuery = useQuery({
  queryKey: ['custom-cases-preview'] as const,
  queryFn: () => listCustomCases({ page: 1, page_size: 6 }),
  staleTime: 60_000,
})
const cases = computed<CustomCase[]>(() => casesQuery.data.value?.items ?? [])
const heroCase = computed<CustomCase | null>(() => cases.value[0] ?? null)
</script>

<template>
  <main class="picker">
    <!-- 切換 bar -->
    <header class="picker-header">
      <h1>Hub Layout 4 方向預覽</h1>
      <p class="picker-sub">點上面的字選方向；下方即時預覽。確定後告訴 Claude 要哪個。</p>
      <div class="tabs">
        <button
          v-for="v in (['A','B','C','D'] as Variant[])"
          :key="v"
          class="tab"
          :class="{ active: variant === v }"
          @click="variant = v"
        >
          <span class="tab-letter">{{ v }}</span>
          <span class="tab-label">{{ VARIANT_INFO[v].label }}</span>
          <span class="tab-tag">{{ VARIANT_INFO[v].tag }}</span>
        </button>
      </div>
    </header>

    <!-- 預覽區 -->
    <section class="preview-frame">

      <!-- ────────────  方向 A — 兩大主視覺 split ──────────────────── -->
      <article v-if="variant === 'A'" class="va-page">
        <div class="va-hero">
          <p class="va-kicker">No. 07 · Custom · 客製化</p>
          <h2>把你的回憶<br />做成一幅畫</h2>
        </div>
        <div class="va-split">
          <RouterLink to="/custom/cases" class="va-left">
            <figure>
              <img v-if="heroCase" :src="heroCase.image_url" :alt="heroCase.title" />
              <div v-else class="va-img-placeholder">案例圖</div>
            </figure>
            <div class="va-left-meta">
              <span class="va-no">01</span>
              <h3>{{ heroCase?.title || '客製案例參考' }}</h3>
              <p>過去客戶完成的作品，喜歡的話直接諮詢類似規格。</p>
              <span class="va-link">瀏覽全部案例 →</span>
            </div>
          </RouterLink>
          <RouterLink to="/custom/apply" class="va-right">
            <span class="va-no">02</span>
            <h3>開始申請</h3>
            <p>上傳一張照片，1–3 個工作天回覆專屬報價。</p>
            <span class="va-link va-link-cta">送出申請 →</span>
            <RouterLink to="/custom/about" class="va-secondary" @click.stop>
              想先了解服務 →
            </RouterLink>
          </RouterLink>
        </div>
      </article>

      <!-- ────────────  方向 B — 條列目錄式 ──────────────────── -->
      <article v-else-if="variant === 'B'" class="vb-page">
        <header class="vb-hero">
          <p class="vb-kicker">No. 07 · Custom · 客製化</p>
          <h2>把你的回憶<br />做成一幅畫</h2>
          <p class="vb-lede">
            上傳一張照片，我們將它轉換為數字油畫模板。<br />
            每一份客製，從理解您的故事開始。
          </p>
        </header>
        <ol class="vb-toc">
          <RouterLink to="/custom/about" class="vb-row" tag="li">
            <span class="vb-no">No. 01</span>
            <span class="vb-rule"></span>
            <span class="vb-title">關於客製化服務</span>
            <ArrowRight :size="14" class="vb-arrow" />
          </RouterLink>
          <RouterLink to="/custom/cases" class="vb-row" tag="li">
            <span class="vb-no">No. 02</span>
            <span class="vb-rule"></span>
            <span class="vb-title">客製案例參考</span>
            <ArrowRight :size="14" class="vb-arrow" />
          </RouterLink>
          <RouterLink to="/custom/apply" class="vb-row" tag="li">
            <span class="vb-no">No. 03</span>
            <span class="vb-rule"></span>
            <span class="vb-title">開始申請</span>
            <ArrowRight :size="14" class="vb-arrow" />
          </RouterLink>
        </ol>
      </article>

      <!-- ────────────  方向 C — 雜誌封面式 ──────────────────── -->
      <article v-else-if="variant === 'C'" class="vc-page">
        <div class="vc-hero">
          <img v-if="heroCase" :src="heroCase.image_url" :alt="heroCase.title" />
          <div v-else class="vc-placeholder">案例大圖（管理員上傳後自動換）</div>
          <div class="vc-overlay">
            <p class="vc-kicker">No. 07 · Custom</p>
            <h2>把你的回憶，做成一幅畫</h2>
          </div>
        </div>
        <nav class="vc-nav">
          <RouterLink to="/custom/about">
            <span class="vc-no">01</span>
            <span class="vc-label">About</span>
            <span class="vc-cn">服務說明</span>
          </RouterLink>
          <RouterLink to="/custom/cases">
            <span class="vc-no">02</span>
            <span class="vc-label">Cases</span>
            <span class="vc-cn">案例</span>
          </RouterLink>
          <RouterLink to="/custom/apply">
            <span class="vc-no">03</span>
            <span class="vc-label">Apply</span>
            <span class="vc-cn">開始申請</span>
          </RouterLink>
        </nav>
      </article>

      <!-- ────────────  方向 D — 案例為入口 ──────────────────── -->
      <article v-else-if="variant === 'D'" class="vd-page">
        <nav class="vd-tabs">
          <RouterLink to="/custom/cases" class="active">案例</RouterLink>
          <RouterLink to="/custom/about">服務說明</RouterLink>
          <RouterLink to="/custom/apply">開始申請</RouterLink>
        </nav>
        <p class="vd-kicker">No. 07 · Custom · 客製案例</p>
        <h2 class="vd-title">把你的回憶，做成一幅畫</h2>
        <div class="vd-grid">
          <RouterLink
            v-for="(c, i) in cases.slice(0, 6)"
            :key="c.id"
            to="/custom/cases"
            class="vd-card"
            :class="{ feature: i === 0 }"
          >
            <figure>
              <img :src="c.image_url" :alt="c.title" />
            </figure>
            <div class="vd-meta">
              <span v-if="c.canvas_w_cm">{{ c.canvas_w_cm }}×{{ c.canvas_h_cm }} cm</span>
              <h3>{{ c.title }}</h3>
            </div>
          </RouterLink>
          <div v-if="cases.length === 0" class="vd-empty">
            尚無案例（admin 後台上傳後自動顯示）
          </div>
        </div>
      </article>
    </section>

    <footer class="picker-footer">
      <p>說明：選定後告訴 Claude「<strong>用 {{ variant }}</strong>」。<br>
      此頁僅供預覽，不會影響正式 /custom 頁。</p>
    </footer>
  </main>
</template>

<style scoped>
.picker { max-width: 1280px; margin: 0 auto; padding: 32px 24px 64px; }

.picker-header {
  padding-bottom: 24px;
  border-bottom: 1px solid var(--color-line);
  margin-bottom: 32px;
}
.picker-header h1 {
  font-family: var(--font-cn-serif); font-weight: 300; font-size: 24px;
  letter-spacing: 0.04em; margin: 0 0 8px; color: var(--color-ink-strong);
}
.picker-sub { font-size: 13px; color: var(--color-ink-muted); margin: 0 0 20px; }

.tabs {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
}
@media (max-width: 880px) { .tabs { grid-template-columns: 1fr 1fr; } }

.tab {
  cursor: pointer; padding: 16px;
  background: var(--color-paper-surface);
  border: 1px solid var(--color-line-subtle);
  border-radius: 4px;
  display: flex; flex-direction: column; gap: 4px;
  text-align: left; font-family: inherit;
  transition: border-color 150ms;
}
.tab:hover { border-color: var(--color-accent); }
.tab.active {
  background: var(--color-paper-deep);
  border-color: var(--color-accent-deep);
}
.tab-letter {
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em;
  color: var(--color-fresh);
}
.tab-label {
  font-family: var(--font-cn-serif); font-size: 16px;
  color: var(--color-ink-strong);
}
.tab-tag { font-size: 11px; color: var(--color-ink-muted); }

.preview-frame {
  background: var(--color-paper-canvas);
  border: 1px dashed var(--color-line);
  border-radius: 8px;
  padding: 32px;
  min-height: 480px;
}

.picker-footer {
  margin-top: 32px; padding-top: 16px;
  border-top: 1px solid var(--color-line-subtle);
  font-size: 12px; color: var(--color-ink-muted);
}
.picker-footer strong { color: var(--color-accent-deep); }

/* ────────────  方向 A ──────────────────── */
.va-page {}
.va-hero { margin-bottom: 32px; }
.va-kicker { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; color: var(--color-fresh); margin: 0 0 12px; }
.va-hero h2 { font-family: var(--font-cn-serif); font-weight: 300; font-size: clamp(32px, 4.5vw, 48px); letter-spacing: 0.04em; margin: 0; line-height: 1.25; color: var(--color-ink-strong); }
.va-split {
  display: grid; grid-template-columns: 1.2fr 1fr; gap: 0;
  border-top: 1px solid var(--color-line);
}
@media (max-width: 880px) { .va-split { grid-template-columns: 1fr; } }
.va-left, .va-right {
  text-decoration: none; color: inherit;
  padding: 32px;
  display: flex; flex-direction: column; gap: 20px;
  transition: background 200ms;
}
.va-left { border-right: 1px solid var(--color-line); }
@media (max-width: 880px) { .va-left { border-right: 0; border-bottom: 1px solid var(--color-line); } }
.va-left:hover, .va-right:hover { background: var(--color-paper-surface); }
.va-left figure { margin: 0; aspect-ratio: 4 / 3; overflow: hidden; background: var(--color-paper-deep); border-radius: 2px; }
.va-left figure img { width: 100%; height: 100%; object-fit: cover; }
.va-img-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: var(--color-ink-muted); font-size: 13px; }
.va-no { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; color: var(--color-fresh); }
.va-left-meta h3, .va-right h3 { font-family: var(--font-cn-serif); font-weight: 300; font-size: 22px; letter-spacing: 0.04em; margin: 8px 0; color: var(--color-ink-strong); }
.va-left-meta p, .va-right > p { font-size: 14px; line-height: 1.85; color: var(--color-ink-muted); margin: 0; }
.va-link { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.18em; color: var(--color-ink-default); border-bottom: 1px solid currentColor; padding-bottom: 2px; align-self: flex-start; margin-top: auto; }
.va-link-cta { color: var(--color-accent-deep); }
.va-secondary { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.18em; color: var(--color-ink-muted); text-decoration: none; }
.va-secondary:hover { color: var(--color-accent-deep); }
.va-right { display: flex; flex-direction: column; gap: 12px; padding: 48px 40px; background: var(--color-paper-deep); }

/* ────────────  方向 B ──────────────────── */
.vb-page { max-width: 720px; margin: 0 auto; padding: 24px 0; }
.vb-hero { margin-bottom: 56px; }
.vb-kicker { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; color: var(--color-fresh); margin: 0 0 16px; }
.vb-hero h2 { font-family: var(--font-cn-serif); font-weight: 300; font-size: clamp(36px, 5vw, 56px); letter-spacing: 0.04em; margin: 0 0 24px; line-height: 1.25; color: var(--color-ink-strong); }
.vb-lede { font-size: 15px; line-height: 1.85; color: var(--color-ink-default); margin: 0; }
.vb-toc { list-style: none; padding: 0; margin: 0; border-top: 1px solid var(--color-line); }
.vb-row {
  display: flex; align-items: center; gap: 20px;
  padding: 24px 4px;
  border-bottom: 1px solid var(--color-line);
  text-decoration: none; color: inherit;
  transition: padding 200ms;
}
.vb-row:hover { padding-left: 16px; background: var(--color-paper-surface); }
.vb-no { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; color: var(--color-fresh); flex-shrink: 0; }
.vb-rule { flex: 0 0 60px; height: 1px; background: var(--color-line); }
.vb-title { flex: 1; font-family: var(--font-cn-serif); font-size: 19px; color: var(--color-ink-strong); }
.vb-arrow { color: var(--color-ink-muted); }
.vb-row:hover .vb-arrow { color: var(--color-accent-deep); }

/* ────────────  方向 C ──────────────────── */
.vc-page {}
.vc-hero { position: relative; aspect-ratio: 16 / 9; overflow: hidden; border-radius: 4px; background: var(--color-paper-deep); margin-bottom: 32px; }
.vc-hero img { width: 100%; height: 100%; object-fit: cover; }
.vc-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: var(--color-ink-muted); font-size: 14px; }
.vc-overlay { position: absolute; inset: auto 0 0 0; padding: 32px 40px; background: linear-gradient(to top, rgba(31, 26, 21, 0.65), transparent); color: var(--color-paper-canvas); }
.vc-kicker { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; opacity: 0.9; margin: 0 0 8px; }
.vc-overlay h2 { font-family: var(--font-cn-serif); font-weight: 300; font-size: clamp(28px, 4vw, 44px); letter-spacing: 0.04em; margin: 0; line-height: 1.25; }
.vc-nav {
  display: grid; grid-template-columns: repeat(3, 1fr);
  border-top: 1px solid var(--color-line);
  border-bottom: 1px solid var(--color-line);
}
.vc-nav a {
  display: flex; flex-direction: column; gap: 4px;
  padding: 24px 28px;
  text-decoration: none; color: inherit;
  border-right: 1px solid var(--color-line);
  transition: background 200ms;
}
.vc-nav a:last-child { border-right: 0; }
.vc-nav a:hover { background: var(--color-paper-surface); }
.vc-no { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; color: var(--color-fresh); }
.vc-label { font-family: var(--font-display); font-style: italic; font-size: 22px; color: var(--color-accent); }
.vc-cn { font-family: var(--font-cn-serif); font-size: 14px; color: var(--color-ink-strong); margin-top: 4px; }

/* ────────────  方向 D ──────────────────── */
.vd-page {}
.vd-tabs {
  display: flex; gap: 28px;
  padding-bottom: 16px; border-bottom: 1px solid var(--color-line);
  margin-bottom: 32px;
}
.vd-tabs a {
  text-decoration: none; font-family: var(--font-cn-serif); font-size: 16px;
  color: var(--color-ink-muted);
  padding-bottom: 8px; border-bottom: 2px solid transparent;
  transition: color 200ms, border-color 200ms;
}
.vd-tabs a:hover { color: var(--color-accent-deep); }
.vd-tabs a.active { color: var(--color-ink-strong); border-bottom-color: var(--color-accent-deep); }
.vd-kicker { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.22em; color: var(--color-fresh); margin: 0 0 12px; }
.vd-title { font-family: var(--font-cn-serif); font-weight: 300; font-size: clamp(28px, 4vw, 40px); letter-spacing: 0.04em; margin: 0 0 32px; color: var(--color-ink-strong); }
.vd-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;
}
@media (max-width: 880px) { .vd-grid { grid-template-columns: 1fr 1fr; } }
.vd-card { text-decoration: none; color: inherit; transition: transform 200ms; }
.vd-card:hover { transform: translateY(-2px); }
.vd-card.feature { grid-column: span 2; grid-row: span 2; }
@media (max-width: 880px) { .vd-card.feature { grid-column: span 2; grid-row: auto; } }
.vd-card figure { margin: 0; aspect-ratio: 4 / 3; overflow: hidden; background: var(--color-paper-deep); border-radius: 2px; }
.vd-card.feature figure { aspect-ratio: 4 / 5; }
.vd-card figure img { width: 100%; height: 100%; object-fit: cover; }
.vd-meta { padding: 12px 0; }
.vd-meta span { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.18em; color: var(--color-ink-muted); }
.vd-meta h3 { font-family: var(--font-cn-serif); font-weight: 400; font-size: 15px; margin: 4px 0 0; color: var(--color-ink-strong); }
.vd-empty { grid-column: 1 / -1; padding: 60px; text-align: center; color: var(--color-ink-muted); font-size: 14px; }
</style>
