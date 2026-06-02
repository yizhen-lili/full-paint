<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Loader2, Layers } from 'lucide-vue-next'
import { useThemeDetailQuery } from '@/features/browse/queries'
import { useProductsQuery } from '@/features/products/queries'
import SeriesCard from '../components/SeriesCard.vue'
import SectionMasthead from '@/shared/components/SectionMasthead.vue'
import BackLink from '@/shared/components/BackLink.vue'

const route = useRoute()
const id = computed(() => String(route.params.id || ''))

const themeQuery = useThemeDetailQuery(id)
const theme = computed(() => themeQuery.data.value ?? null)

// 該主題精選商品（admin 勾選 is_featured）— 取 4 張在 hero 右側 2x2 顯示
const featuredQuery = useProductsQuery(
  computed(() => ({
    theme_id: id.value,
    featured: true,
    page: 1,
    page_size: 4,
  })),
)
const fallbackQuery = useProductsQuery(
  computed(() => ({
    theme_id: id.value,
    sort: 'latest' as const,
    page: 1,
    page_size: 4,
  })),
)

const heroProducts = computed(() => {
  const featured = featuredQuery.data.value?.items ?? []
  if (featured.length > 0) return featured.slice(0, 4)
  return (fallbackQuery.data.value?.items ?? []).slice(0, 4)
})

// 4 格 cell（不夠 4 個就 null）
const heroCells = computed(() => [
  heroProducts.value[0] ?? null,
  heroProducts.value[1] ?? null,
  heroProducts.value[2] ?? null,
  heroProducts.value[3] ?? null,
])

const hasMosaic = computed(() => heroProducts.value.length > 0)

// 主題色卡（找不到 image 時的單格 fallback 色）
const CELL_TONES = [
  'linear-gradient(135deg, rgba(221,229,210,0.9), rgba(151,166,135,0.6))',
  'linear-gradient(135deg, rgba(236,223,218,0.9), rgba(201,168,168,0.55))',
  'linear-gradient(135deg, rgba(236,227,210,0.9), rgba(184,160,132,0.55))',
  'linear-gradient(135deg, rgba(220,227,226,0.9), rgba(152,171,168,0.55))',
]
function toneFor(idx: number) {
  return CELL_TONES[idx % CELL_TONES.length]
}

// hero 背景圖：第一張精選商品圖；無則 theme cover；無則用 gradient
const heroImage = computed<string | null>(() => {
  const first = heroProducts.value[0]?.cover_image_url
  if (first && !hasMosaic.value) return first
  if (theme.value?.cover_image_url) return theme.value.cover_image_url
  return null
})

const totalProducts = computed(() =>
  theme.value?.series.reduce((sum, s) => sum + s.product_count, 0) ?? 0,
)
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
    <BackLink fallback="/themes" />
    <nav class="breadcrumb">
      <RouterLink to="/themes">主題</RouterLink>
      <span>/</span>
      <span class="current">{{ theme.name }}</span>
    </nav>

    <!-- Page header — 文字從 cover 拿掉，獨立成上方 block -->
    <header class="page-header">
      <div class="header-top">
        <span class="header-stamp">Theme · No. {{ String(theme.sort_order).padStart(2, '0') }}</span>
        <span class="header-stamp-rule"></span>
        <span class="header-stamp-cap">Yiimui Atelier</span>
      </div>

      <h1 class="page-title">{{ theme.name }}</h1>

      <p v-if="theme.description" class="page-desc">
        <em class="desc-quote">“</em>{{ theme.description }}<em class="desc-quote">”</em>
      </p>

      <div class="page-meta-row">
        <div class="page-meta">
          <span class="meta-num">{{ theme.series.length }}</span>
          <span class="meta-label">Series</span>
          <span class="meta-divider"></span>
          <span class="meta-num">{{ totalProducts }}</span>
          <span class="meta-label">Products</span>
        </div>
        <RouterLink :to="`/products?theme_id=${theme.id}`" class="page-cta">
          該主題全部商品 →
        </RouterLink>
      </div>
    </header>

    <!-- Hero — 純圖：左 cover image clean / 右 2x2 精選 mosaic -->
    <section class="hero" aria-label="主題封面與精選">
      <div class="hero-cover">
        <img
          v-if="heroImage"
          :src="heroImage"
          :alt="theme.name"
          class="cover-img"
          loading="lazy"
        />
        <div v-else class="cover-tone"></div>
      </div>

      <!-- 右側 2x2 精選商品 -->
      <aside class="hero-mosaic" aria-label="精選商品">
          <span class="mosaic-cap" aria-hidden="true">— Featured —</span>
          <div class="mosaic-grid">
            <template v-for="(p, idx) in heroCells" :key="idx">
              <RouterLink
                v-if="p"
                :to="`/products/${p.id}`"
                class="mosaic-cell"
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
                <span class="mosaic-overlay">
                  <span class="mosaic-name">{{ p.title }}</span>
                  <span class="mosaic-price">NT$ {{ p.price_min.toLocaleString() }} 起</span>
                </span>
              </RouterLink>
              <div
                v-else
                class="mosaic-cell mosaic-empty"
                :style="{ background: toneFor(idx) }"
              >
                <span class="empty-mark">{{ theme.name.slice(0, 1) }}</span>
              </div>
            </template>
          </div>
        </aside>
    </section>

    <!-- 該主題下的系列 -->
    <section class="series-section">
      <SectionMasthead
        no="01"
        chapter="Series"
        title="系列"
        :caption="`under ${theme.name}`"
      />

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

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.breadcrumb a { color: inherit; text-decoration: none; transition: color 150ms; }
.breadcrumb a:hover { color: var(--color-accent); }
.breadcrumb .current { color: var(--color-ink-default); }

/* ── Page header（文字從 cover 拿掉後獨立的上方 block） ── */
.page-header {
  margin-bottom: 48px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 880px;
}
.header-top {
  display: flex;
  align-items: center;
  gap: 16px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  flex-wrap: wrap;
}
.header-stamp {
  font-weight: 500;
  color: var(--color-accent);
}
.header-stamp-rule {
  flex: 0 1 120px;
  height: 1px;
  background: var(--color-line);
}
.header-stamp-cap {
  font-family: var(--font-display);
  font-style: italic;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
  text-transform: none;
}

.page-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: clamp(48px, 9vw, 96px);
  line-height: 1.1;
  letter-spacing: 0.12em;
  margin: 8px 0 0;
  color: var(--color-ink-strong);
  word-break: keep-all;
  overflow-wrap: break-word;
}
.page-desc {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 17px;
  line-height: 1.95;
  letter-spacing: 0.06em;
  color: var(--color-ink-default);
  max-width: 640px;
  margin: 0;
}
.desc-quote {
  font-family: var(--font-display);
  font-style: italic;
  font-size: 26px;
  font-weight: 300;
  color: var(--color-accent);
  margin: 0 4px;
  vertical-align: -4px;
}

.page-meta-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  margin-top: 8px;
  padding-top: 20px;
  border-top: 1px solid var(--color-line-subtle);
}
.page-meta {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-family: var(--font-mono);
  color: var(--color-ink-default);
  flex-wrap: wrap;
}
.meta-num {
  font-size: 26px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: var(--color-ink-strong);
}
.meta-label {
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-right: 6px;
}
.meta-divider {
  width: 1px;
  height: 18px;
  background: var(--color-line);
  margin: 0 8px;
}
.page-cta {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  padding: 14px 28px;
  border: 1px solid var(--color-line);
  color: var(--color-ink-strong);
  text-decoration: none;
  background: transparent;
  transition: all 200ms;
}
.page-cta:hover {
  background: var(--color-ink-strong);
  color: var(--color-paper-canvas);
  border-color: var(--color-ink-strong);
}

/* ── Hero（純圖：左 cover image clean / 右 mosaic） ── */
.hero {
  margin-bottom: 80px;
  display: grid;
  grid-template-columns: 1fr 0.75fr;
  gap: 24px;
  align-items: stretch;
  min-height: clamp(440px, 60vh, 620px);
}

.hero-cover {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-sm);
  background: var(--color-paper-surface);
}
.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  filter: sepia(0.02) saturate(1);
}
.cover-tone {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 25%, rgba(255, 252, 244, 0.95), transparent 60%),
    radial-gradient(circle at 80% 75%, var(--color-accent-tint), transparent 65%),
    linear-gradient(135deg,
      var(--color-paper-surface) 0%,
      var(--color-paper-canvas) 60%,
      var(--color-accent-soft) 130%);
}

/* ── Hero mosaic 2x2（右側精選商品，坐在 canvas 上） ── */
.hero-mosaic {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
.mosaic-cap {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-fresh);
  align-self: flex-end;
  padding-top: 4px;
}
.mosaic-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 10px;
  flex: 1;
  min-height: 0;
}
.mosaic-cell {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-line-subtle);
  background: var(--color-paper-surface);
  text-decoration: none;
  color: inherit;
  transition: transform 400ms ease, border-color 200ms, box-shadow 300ms;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mosaic-cell:hover {
  border-color: var(--color-line);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(31, 26, 21, 0.06);
}
.mosaic-empty { cursor: default; }
.mosaic-empty:hover { transform: none; border-color: var(--color-line-subtle); box-shadow: none; }

.mosaic-img {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
  filter: sepia(0.06) saturate(0.92);
  transition: transform 600ms ease, filter 200ms;
}
.mosaic-cell:hover .mosaic-img {
  transform: scale(1.06);
  filter: sepia(0.04) saturate(0.98) brightness(1.04);
}
.mosaic-tone { width: 100%; height: 100%; }

.mosaic-overlay {
  position: absolute;
  inset: auto 0 0 0;
  padding: 10px 12px 11px;
  background: linear-gradient(to top, rgba(31, 26, 21, 0.72), rgba(31, 26, 21, 0));
  display: flex;
  flex-direction: column;
  gap: 2px;
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 240ms, transform 240ms;
}
.mosaic-cell:hover .mosaic-overlay {
  opacity: 1;
  transform: translateY(0);
}
.mosaic-name {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 13px;
  letter-spacing: 0.04em;
  color: rgba(250, 244, 221, 0.95);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.mosaic-price {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: rgba(250, 244, 221, 0.75);
}

.empty-mark {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 56px;
  line-height: 1;
  color: var(--color-ink-strong);
  opacity: 0.18;
  user-select: none;
}

/* ── Series section ── */
.series-section {
  padding-top: 8px;
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
  .hero { grid-template-columns: 1fr 0.7fr; gap: 20px; }
  .series-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 1023px) {
  .page { padding: 40px 32px 64px; }
  .page-header { margin-bottom: 32px; }
  .hero {
    grid-template-columns: 1fr;
    gap: 20px;
    min-height: auto;
  }
  .hero-cover { aspect-ratio: 3 / 2; }
  .mosaic-grid { aspect-ratio: 2 / 1; }
}
@media (max-width: 767px) {
  .page { padding: 32px 24px 48px; }
  .page-title { letter-spacing: 0.06em; }
  .page-meta-row { flex-direction: column; align-items: flex-start; }
  .hero-cover { aspect-ratio: 4 / 3; }
  .mosaic-grid { aspect-ratio: 1; }
  .series-grid { grid-template-columns: 1fr; }
}
</style>
