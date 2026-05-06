<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Loader2, Layers } from 'lucide-vue-next'
import { useThemeDetailQuery } from '@/features/browse/queries'
import { useProductsQuery } from '@/features/products/queries'
import type { ProductBrief } from '@/features/products/api'
import SeriesCard from '../components/SeriesCard.vue'

const route = useRoute()
const id = computed(() => String(route.params.id || ''))

const themeQuery = useThemeDetailQuery(id)
const theme = computed(() => themeQuery.data.value ?? null)

// 該主題的精選商品（admin 勾選 is_featured）— 拼貼最多 4 個
const featuredQuery = useProductsQuery(
  computed(() => ({
    theme_id: id.value,
    featured: true,
    page: 1,
    page_size: 4,
  })),
)

// fallback：如果沒勾選任何 featured，就拿最新前 4 個
const fallbackQuery = useProductsQuery(
  computed(() => ({
    theme_id: id.value,
    sort: 'latest' as const,
    page: 1,
    page_size: 4,
  })),
)

const collageProducts = computed<ProductBrief[]>(() => {
  const featured = featuredQuery.data.value?.items ?? []
  if (featured.length > 0) return featured.slice(0, 4)
  return (fallbackQuery.data.value?.items ?? []).slice(0, 4)
})

// 4 個 cell 對應到的商品（不夠 4 個就 null，由裝飾色填）
const heroCells = computed(() => [
  collageProducts.value[0] ?? null,
  collageProducts.value[1] ?? null,
  collageProducts.value[2] ?? null,
  collageProducts.value[3] ?? null,
])

// cell 4 種 mood 漸層：苔綠 / 舊玫瑰 / 焦糖 / 煙青（對應 SeriesDetail 的）
const CELL_TONES = [
  'linear-gradient(135deg, #FCF7E5 0%, #DDE5D2 70%, #97A687 130%)',
  'linear-gradient(135deg, #FCF7E5 0%, #ECDFDA 70%, #C9A8A8 130%)',
  'linear-gradient(135deg, #FCF7E5 0%, #ECE3D2 70%, #B8A084 130%)',
  'linear-gradient(135deg, #FCF7E5 0%, #DCE3E2 70%, #98ABA8 130%)',
]
function toneFor(idx: number) {
  return CELL_TONES[idx % CELL_TONES.length]
}
</script>

<template>
  <section v-if="themeQuery.isPending.value" class="page page-loading">
    <Loader2 :size="20" />
  </section>

  <section v-else-if="themeQuery.isError.value || !theme" class="page page-empty">
    <Layers class="empty-icon" />
    <h1 class="empty-title">找不到這個主題</h1>
    <p class="empty-hint">主題已下架或網址錯誤。</p>
    <RouterLink to="/themes" class="empty-cta">回主題列表</RouterLink>
  </section>

  <section v-else class="page">
    <!-- Hero -->
    <header class="hero">
      <nav class="breadcrumb">
        <RouterLink to="/themes">主題</RouterLink>
        <span>/</span>
        <span class="current">{{ theme.name }}</span>
      </nav>

      <div class="hero-grid">
        <div class="hero-text">
          <div class="hero-eyebrow">Theme</div>
          <h1 class="hero-title">{{ theme.name }}</h1>
          <p v-if="theme.description" class="hero-desc">{{ theme.description }}</p>
          <div class="hero-meta">
            <span class="hero-meta-item">
              {{ theme.series.length }} 個系列
            </span>
            <span class="hero-meta-divider">·</span>
            <span class="hero-meta-item">
              {{ theme.series.reduce((sum, s) => sum + s.product_count, 0) }} 件商品
            </span>
          </div>
          <RouterLink :to="`/products?theme_id=${theme.id}`" class="hero-cta">
            該主題全部商品 →
          </RouterLink>
        </div>

        <!-- 右側：精選商品拼貼（4 格不對稱 magazine） -->
        <div class="hero-mosaic">
          <template v-for="(p, idx) in heroCells" :key="idx">
            <RouterLink
              v-if="p"
              :to="`/products/${p.id}`"
              :class="['mosaic-cell', `cell-${idx}`]"
            >
              <img
                v-if="p.cover_image_url"
                :src="p.cover_image_url"
                :alt="p.title"
                class="mosaic-img"
                loading="lazy"
              />
              <div
                v-else
                class="mosaic-tone"
                :style="{ background: toneFor(idx) }"
              ></div>
              <div class="mosaic-overlay">
                <div class="mosaic-title">{{ p.title }}</div>
                <div class="mosaic-price">NT$ {{ p.price_min.toLocaleString() }} 起</div>
              </div>
            </RouterLink>
            <div
              v-else
              :class="['mosaic-cell', 'cell-empty', `cell-${idx}`]"
              :style="{ background: toneFor(idx) }"
            >
              <div v-if="idx === 0" class="cell-deco cell-deco-main">
                <div class="deco-eyebrow">Theme</div>
                <div class="deco-name">{{ theme.name }}</div>
                <div class="deco-rule"></div>
                <div class="deco-meta">{{ theme.series.length }} 系列</div>
              </div>
              <div v-else class="cell-deco">
                <div class="deco-word">·</div>
                <div class="deco-caption">soon</div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </header>

    <!-- 該主題下的系列 -->
    <section class="series-section">
      <div class="series-header">
        <div>
          <div class="series-eyebrow">Series</div>
          <h2 class="series-title">系列</h2>
        </div>
      </div>

      <div v-if="theme.series.length === 0" class="empty-inner">
        <p>這個主題還沒有任何系列。</p>
      </div>

      <div v-else class="series-grid">
        <SeriesCard
          v-for="(s, idx) in theme.series"
          :key="s.id"
          :series="s"
          :index="idx"
        />
      </div>
    </section>
  </section>
</template>

<style scoped>
.page {
  max-width: 1440px;
  margin: 0 auto;
  padding: 56px 56px 96px;
}

.page-loading,
.page-empty {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
}
.page-loading :deep(svg) {
  animation: spin 1s linear infinite;
  stroke-width: 1.5; fill: none; stroke: currentColor;
  color: var(--color-ink-muted);
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty-icon {
  width: 32px; height: 32px;
  stroke: var(--color-ink-muted); stroke-width: 1.5; fill: none;
  margin-bottom: 24px;
}
.empty-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 28px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0 0 16px;
}
.empty-hint {
  font-size: 13px; color: var(--color-ink-muted); letter-spacing: 0.04em; margin: 0 0 24px;
}
.empty-cta {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
}

.hero {
  margin-bottom: 80px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-bottom: 32px;
  flex-wrap: wrap;
}
.breadcrumb a { color: inherit; text-decoration: none; transition: color 150ms; }
.breadcrumb a:hover { color: var(--color-accent); }
.breadcrumb .current { color: var(--color-ink-default); }

.hero-grid {
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 64px;
  align-items: center;
}

.hero-text {
  display: flex;
  flex-direction: column;
}

.hero-eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-accent);
  margin-bottom: 24px;
}

.hero-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 56px;
  line-height: 1.3;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0 0 28px;
}

.hero-desc {
  font-size: 15px;
  line-height: 1.95;
  color: var(--color-ink-default);
  letter-spacing: 0.04em;
  margin: 0 0 32px;
  max-width: 480px;
  white-space: pre-wrap;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-bottom: 36px;
}
.hero-meta-divider {
  opacity: 0.4;
}

.hero-cta {
  display: inline-block;
  align-self: flex-start;
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  padding: 16px 32px;
  border: 1px solid var(--color-ink-strong);
  color: var(--color-ink-strong);
  text-decoration: none;
  transition: all 200ms;
}
.hero-cta:hover {
  background: var(--color-ink-strong);
  color: var(--color-paper-canvas);
}

/* ── Hero Mosaic 拼貼（4 格不對稱：左 tall / 中上 wide / 中下 wide / 右 tall） ── */
.hero-mosaic {
  display: grid;
  grid-template-columns: 0.85fr 1.4fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 12px;
  aspect-ratio: 4 / 5;
}
.mosaic-cell {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-line-subtle);
  background: var(--color-paper-surface);
  text-decoration: none;
  color: inherit;
  transition: transform 400ms ease, box-shadow 300ms;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mosaic-cell:not(.cell-empty):hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(31, 26, 21, 0.06);
}
.cell-empty { cursor: default; }

.cell-0 { grid-column: 1; grid-row: 1 / span 2; }
.cell-1 { grid-column: 2; grid-row: 1; }
.cell-2 { grid-column: 2; grid-row: 2; }
.cell-3 { grid-column: 3; grid-row: 1 / span 2; }

.mosaic-img {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
  filter: sepia(0.04) saturate(0.95);
  transition: transform 600ms ease;
}
.mosaic-cell:not(.cell-empty):hover .mosaic-img {
  transform: scale(1.04);
}
.mosaic-tone { width: 100%; height: 100%; }

.mosaic-overlay {
  position: absolute;
  inset: auto 0 0 0;
  padding: 12px 14px;
  background: linear-gradient(to top, rgba(31, 26, 21, 0.62), rgba(31, 26, 21, 0));
  color: var(--color-paper-canvas);
  display: flex;
  flex-direction: column;
  gap: 2px;
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 240ms, transform 240ms;
}
.mosaic-cell:hover .mosaic-overlay {
  opacity: 1;
  transform: translateY(0);
}
.mosaic-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 14px;
  letter-spacing: 0.04em;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.mosaic-price {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  opacity: 0.85;
}

/* 空 cell 的 deco typography */
.cell-deco {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  padding: 18px;
}
.cell-deco-main { gap: 14px; padding: 24px; }
.deco-eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-fresh);
}
.deco-name {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 32px;
  letter-spacing: 0.12em;
  color: var(--color-ink-strong);
}
.deco-rule {
  width: 32px;
  height: 1px;
  background: var(--color-accent);
}
.deco-meta {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}
.deco-word {
  font-family: var(--font-display);
  font-weight: 300;
  font-size: 56px;
  line-height: 1;
  color: var(--color-accent);
  opacity: 0.5;
}
.deco-caption {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--color-ink-muted);
}

.series-section {
  padding-top: 32px;
  border-top: 1px solid var(--color-line);
}

.series-header {
  margin-bottom: 40px;
}

.series-eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-bottom: 12px;
}

.series-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 28px;
  letter-spacing: 0.04em;
  color: var(--color-ink-strong);
  margin: 0;
}

.empty-inner {
  padding: 48px 0;
  text-align: center;
  font-size: 13px;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
}

.series-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

@media (max-width: 1279px) {
  .hero-title { font-size: 44px; }
  .deco-name { font-size: 26px; }
  .deco-word { font-size: 44px; }
  .series-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 1023px) {
  .page { padding: 40px 32px 64px; }
  .hero-grid { grid-template-columns: 1fr; gap: 32px; }
  .hero-title { font-size: 36px; }
  .hero-mosaic {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr 1fr;
    aspect-ratio: 1;
  }
  .cell-0 { grid-column: 1; grid-row: 1 / span 2; }
  .cell-1 { grid-column: 2; grid-row: 1; }
  .cell-2 { grid-column: 2; grid-row: 2; }
  .cell-3 { grid-column: 1 / span 2; grid-row: 3; }
}
@media (max-width: 767px) {
  .page { padding: 32px 24px 48px; }
  .hero-title { font-size: 28px; }
  .hero-mosaic {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(4, 220px);
    aspect-ratio: auto;
  }
  .cell-0,
  .cell-1,
  .cell-2,
  .cell-3 {
    grid-column: 1;
    grid-row: auto;
  }
  .series-grid { grid-template-columns: 1fr; }
}
</style>
