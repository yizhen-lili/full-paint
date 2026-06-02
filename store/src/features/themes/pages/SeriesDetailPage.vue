<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Loader2, Layers, Star } from 'lucide-vue-next'
import {
  useSeriesDetailQuery,
  useSeriesQuery,
  useFeaturedSeriesQuery,
} from '@/features/browse/queries'
import { useProductsQuery } from '@/features/products/queries'
import ProductCard from '@/features/products/components/ProductCard.vue'
import SeriesCard from '@/features/themes/components/SeriesCard.vue'
import SectionMasthead from '@/shared/components/SectionMasthead.vue'
import type { ProductBrief } from '@/features/products/api'
import BackLink from '@/shared/components/BackLink.vue'

const route = useRoute()
const id = computed(() => String(route.params.id || ''))

const seriesQuery = useSeriesDetailQuery(id)
const series = computed(() => seriesQuery.data.value ?? null)

// 該系列真實精選商品（admin 勾選 is_featured） — Pick 最多 4 個
const featuredQuery = useProductsQuery(
  computed(() => ({
    series_id: id.value,
    featured: true,
    page: 1,
    page_size: 4,
  })),
)

const allProducts = computed<ProductBrief[]>(() => {
  if (!series.value) return []
  return series.value.products.map((p) => ({
    id: p.id,
    title: p.title,
    cover_image_url: p.cover_image_url,
    difficulty_range: p.difficulty_range as ProductBrief['difficulty_range'],
    price_min: p.price_min,
    price_max: p.price_max,
    is_preorder: p.is_preorder,
  }))
})

// Hero 4 cell mosaic — 優先 admin 真實精選 4 個；無則 fallback 前 4 個
const heroCells = computed<Array<ProductBrief | null>>(() => {
  const featured = featuredQuery.data.value?.items ?? []
  const list = featured.length > 0 ? featured.slice(0, 4) : allProducts.value.slice(0, 4)
  return [list[0] ?? null, list[1] ?? null, list[2] ?? null, list[3] ?? null]
})

// 4 種雜誌 mood 漸層（淡色版，避免暗沈）
const CELL_TONES = [
  'linear-gradient(135deg, rgba(221,229,210,0.9), rgba(151,166,135,0.6))',
  'linear-gradient(135deg, rgba(236,223,218,0.9), rgba(201,168,168,0.55))',
  'linear-gradient(135deg, rgba(236,227,210,0.9), rgba(184,160,132,0.55))',
  'linear-gradient(135deg, rgba(220,227,226,0.9), rgba(152,171,168,0.55))',
]
function toneFor(idx: number) {
  return CELL_TONES[idx % CELL_TONES.length]
}

// 同主題其他系列（沒商品時用來導覽用戶）；無 theme_id 則 fallback 到精選系列
const themeId = computed(() => series.value?.theme_id ?? undefined)
const siblingSeriesQuery = useSeriesQuery(themeId)
const featuredSeriesFallback = useFeaturedSeriesQuery()

const otherSeries = computed(() => {
  const currentId = series.value?.id
  const sameTheme = (siblingSeriesQuery.data.value?.items ?? [])
    .filter((s) => s.id !== currentId)
  if (sameTheme.length > 0) return sameTheme.slice(0, 4)
  return (featuredSeriesFallback.data.value?.items ?? [])
    .filter((s) => s.id !== currentId)
    .slice(0, 4)
})

const otherSeriesEyebrow = computed(() =>
  series.value?.theme_name
    ? `More in ${series.value.theme_name}`
    : 'Featured Series',
)
const otherSeriesTitle = computed(() =>
  series.value?.theme_name
    ? `${series.value.theme_name} 其他系列`
    : '精選系列',
)
</script>

<template>
  <section v-if="seriesQuery.isPending.value" class="page page-loading">
    <Loader2 :size="20" />
  </section>

  <section v-else-if="seriesQuery.isError.value || !series" class="page page-empty">
    <Layers class="empty-icon" />
    <h1 class="empty-title">找不到這個系列</h1>
    <p class="empty-hint">系列已下架或網址錯誤。</p>
    <RouterLink to="/themes" class="empty-cta">回主題列表</RouterLink>
  </section>

  <section v-else class="page">
    <BackLink fallback="/themes" />

    <nav class="breadcrumb">
      <RouterLink to="/themes">主題</RouterLink>
      <span>/</span>
      <RouterLink v-if="series.theme_id" :to="`/themes/${series.theme_id}`">
        {{ series.theme_name }}
      </RouterLink>
      <span v-if="series.theme_id">/</span>
      <span class="current">{{ series.name }}</span>
    </nav>

    <!-- Hero — 參考主題擺放：左 light text panel + 右 2x2 精選 mosaic（無灰黑 veil） -->
    <header class="hero">
      <div class="hero-text-side">
        <div class="text-inner">
          <div class="hero-top">
            <span class="hero-stamp">Series</span>
            <span class="hero-stamp-rule"></span>
            <span v-if="series.is_featured" class="featured-mark">
              <Star class="featured-icon" />Featured
            </span>
            <span v-else class="hero-stamp-cap">Yiimui Atelier</span>
          </div>

          <h1 class="hero-title">{{ series.name }}</h1>

          <p v-if="series.description" class="hero-desc">
            <em class="desc-quote">“</em>{{ series.description }}<em class="desc-quote">”</em>
          </p>
          <p v-else class="hero-desc hero-desc-empty">— 一個還在悄悄誕生的系列 —</p>

          <div class="hero-bottom">
            <div class="hero-meta">
              <span class="meta-num">{{ series.products.length }}</span>
              <span class="meta-label">Products</span>
              <template v-if="series.theme_name && series.theme_id">
                <span class="meta-divider"></span>
                <RouterLink
                  :to="`/themes/${series.theme_id}`"
                  class="meta-theme"
                >{{ series.theme_name }}</RouterLink>
              </template>
            </div>
            <RouterLink
              v-if="allProducts.length > 0"
              :to="`/products?series_id=${series.id}`"
              class="hero-cta"
            >
              該系列全部商品 →
            </RouterLink>
          </div>
        </div>
      </div>

      <!-- 右側 2x2 精選商品 mosaic（坐在頁面 canvas 上） -->
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
              <span class="empty-mark">{{ series.name.slice(0, 1) }}</span>
            </div>
          </template>
        </div>
      </aside>
    </header>

    <!-- 該系列全部商品 -->
    <section v-if="allProducts.length > 0" class="products-section">
      <SectionMasthead
        no="01"
        chapter="All Products"
        title="本系列全部商品"
        :caption="`${allProducts.length} items`"
      />
      <div class="products-grid">
        <ProductCard v-for="p in allProducts" :key="p.id" :product="p" />
      </div>
    </section>

    <!-- 沒商品時：導覽其他系列 -->
    <section v-else-if="otherSeries.length > 0" class="others-section">
      <SectionMasthead
        no="02"
        :chapter="otherSeriesEyebrow"
        :title="otherSeriesTitle"
        :caption="`${otherSeries.length} series`"
      />
      <div class="others-grid">
        <SeriesCard
          v-for="(s, idx) in otherSeries"
          :key="s.id"
          :series="s"
          :index="idx"
        />
      </div>
      <div class="others-footer">
        <RouterLink to="/themes" class="others-link">
          看全部主題與系列 →
        </RouterLink>
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
.empty-hint { font-size: 13px; color: var(--color-ink-muted); letter-spacing: 0.04em; margin: 0 0 24px; }
.empty-cta {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
}

/* ── Breadcrumb ── */
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

/* ── Hero (左 light text panel + 右 mosaic — 無灰黑 veil) ── */
.hero {
  margin-bottom: 80px;
  display: grid;
  grid-template-columns: 1fr 0.75fr;
  gap: 24px;
  align-items: stretch;
  min-height: clamp(440px, 60vh, 620px);
}

.hero-text-side {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-sm);
  background: var(--color-paper-surface);
}

.text-inner {
  position: relative;
  z-index: 2;
  height: 100%;
  padding: 56px;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 24px;
  color: var(--color-ink-strong);
}

.hero-top {
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
.hero-stamp {
  font-weight: 500;
  color: var(--color-accent);
}
.hero-stamp-rule {
  flex: 0 1 80px;
  height: 1px;
  background: var(--color-line);
}
.hero-stamp-cap {
  font-family: var(--font-display);
  font-style: italic;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
  text-transform: none;
}
.featured-mark {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-accent-wine);
  padding: 3px 9px;
  border: 1px solid var(--color-accent-wine);
  border-radius: var(--radius-xs);
  background: transparent;
}
.featured-icon {
  width: 10px; height: 10px;
  stroke: currentColor; fill: currentColor; stroke-width: 1.5;
}

.hero-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: clamp(48px, 8vw, 88px);
  line-height: 1.12;
  letter-spacing: 0.1em;
  margin: 16px 0 0;
  color: var(--color-ink-strong);
  align-self: end;
  word-break: keep-all;
  overflow-wrap: break-word;
}
.hero-desc {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 16px;
  line-height: 2;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
  max-width: 540px;
  margin: 0;
  align-self: start;
  white-space: pre-wrap;
}
.hero-desc-empty {
  color: var(--color-ink-muted);
  font-style: italic;
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

.hero-bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.hero-meta {
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
.meta-theme {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
  transition: color 150ms;
}
.meta-theme:hover { color: var(--color-accent-deep); }
.hero-cta {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  padding: 14px 28px;
  border: 1px solid var(--color-line);
  color: var(--color-ink-strong);
  text-decoration: none;
  transition: all 200ms;
  background: transparent;
}
.hero-cta:hover {
  background: var(--color-ink-strong);
  color: var(--color-paper-canvas);
  border-color: var(--color-ink-strong);
}

/* ── Hero mosaic 2x2 ── */
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
  /* 不再壓暗（之前 sepia 0.06 + saturate 0.92 偏灰） */
  filter: sepia(0.03) saturate(0.98);
  transition: transform 600ms ease, filter 200ms;
}
.mosaic-cell:hover .mosaic-img {
  transform: scale(1.06);
  filter: sepia(0.02) saturate(1.02);
}
.mosaic-tone { width: 100%; height: 100%; }

.mosaic-overlay {
  position: absolute;
  inset: auto 0 0 0;
  padding: 10px 12px 11px;
  /* 大幅減淡底部 veil — 只夠 hover 白字可讀，不壓圖 */
  background: linear-gradient(to top, rgba(31, 26, 21, 0.5) 0%, rgba(31, 26, 21, 0.1) 60%, transparent 100%);
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
  color: var(--color-paper-canvas);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.mosaic-price {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: rgba(247, 241, 227, 0.8);
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

/* ── Products section ── */
.products-section {
  padding-top: 8px;
}
.products-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 28px;
}

/* ── Other series section ── */
.others-section {
  padding-top: 8px;
}
.others-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 36px;
}
.others-footer {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid var(--color-line-subtle);
}
.others-link {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
  border-bottom: 1px solid var(--color-accent);
  padding-bottom: 4px;
  transition: color 150ms, border-color 150ms;
}
.others-link:hover {
  color: var(--color-accent-deep);
  border-color: var(--color-accent-deep);
}

@media (max-width: 1279px) {
  .hero { grid-template-columns: 1fr 0.7fr; gap: 20px; }
  .text-inner { padding: 48px 40px; }
  .products-grid,
  .others-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 1023px) {
  .page { padding: 40px 32px 64px; }
  .hero {
    grid-template-columns: 1fr;
    gap: 20px;
    min-height: auto;
  }
  .hero-text-side { min-height: 380px; }
  .text-inner { padding: 40px 36px; }
  .mosaic-grid { aspect-ratio: 2 / 1; }
  .products-grid,
  .others-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 767px) {
  .page { padding: 32px 24px 48px; }
  .text-inner { padding: 32px 24px; gap: 24px; }
  .hero-text-side { min-height: 320px; }
  .hero-title { letter-spacing: 0.06em; font-size: 40px; }
  .hero-bottom { flex-direction: column; align-items: flex-start; }
  .mosaic-grid { aspect-ratio: 1; }
  .products-grid,
  .others-grid { grid-template-columns: 1fr; }
}
</style>
