<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { Loader2, Layers, Star } from 'lucide-vue-next'
import { useSeriesDetailQuery } from '@/features/browse/queries'
import { useProductsQuery } from '@/features/products/queries'
import ProductCard from '@/features/products/components/ProductCard.vue'
import type { ProductBrief } from '@/features/products/api'

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

// Pick 區塊：優先真實精選；無則 fallback 前 4 個
const pickedProducts = computed<ProductBrief[]>(() => {
  const featured = featuredQuery.data.value?.items ?? []
  if (featured.length > 0) return featured.slice(0, 4)
  return allProducts.value.slice(0, 4)
})

// 排除 picked 已顯示的
const restProducts = computed<ProductBrief[]>(() => {
  const pickedIds = new Set(pickedProducts.value.map((p) => p.id))
  return allProducts.value.filter((p) => !pickedIds.has(p.id))
})
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
    <!-- breadcrumb -->
    <nav class="breadcrumb">
      <RouterLink to="/themes">主題</RouterLink>
      <span>/</span>
      <RouterLink v-if="series.theme_id" :to="`/themes/${series.theme_id}`">
        {{ series.theme_name }}
      </RouterLink>
      <span v-if="series.theme_id">/</span>
      <span class="current">{{ series.name }}</span>
    </nav>

    <!-- Hero — editorial 雜誌左右簡潔佈局，去掉裝飾框與 watermark -->
    <header class="hero">
      <div class="hero-info">
        <div class="hero-eyebrow">
          <span class="eyebrow-text">Series</span>
          <span v-if="series.is_featured" class="featured-mark">
            <Star class="featured-icon" />Featured
          </span>
        </div>

        <h1 class="hero-title">{{ series.name }}</h1>

        <p v-if="series.description" class="hero-desc">{{ series.description }}</p>

        <div class="hero-meta">
          <span class="meta-num">{{ series.products.length }}</span>
          <span class="meta-label">件商品</span>
          <span v-if="series.theme_name" class="meta-divider">·</span>
          <RouterLink
            v-if="series.theme_id"
            :to="`/themes/${series.theme_id}`"
            class="meta-theme"
          >{{ series.theme_name }}</RouterLink>
        </div>
      </div>
    </header>

    <!-- Pick：橫向 magazine strip（有商品時）；無商品時顯示 elegant empty panel -->
    <section v-if="pickedProducts.length > 0" class="picks">
      <div class="picks-header">
        <span class="picks-eyebrow">Pick of this Series</span>
        <span class="picks-count">{{ pickedProducts.length }} / {{ series.products.length }}</span>
      </div>
      <div class="picks-grid">
        <ProductCard v-for="p in pickedProducts" :key="p.id" :product="p" />
      </div>
    </section>

    <section v-else class="empty-panel">
      <div class="empty-eyebrow">— Coming Soon —</div>
      <h2 class="empty-headline">{{ series.name }}<br /><em>quietly under preparation</em></h2>
      <p class="empty-note">本系列商品正在悄悄誕生，請耐心等候。</p>
      <RouterLink to="/products" class="empty-link">看其他系列商品 →</RouterLink>
    </section>

    <!-- 系列其他商品 -->
    <section v-if="restProducts.length > 0" class="products-section">
      <div class="section-header">
        <span class="section-eyebrow">More in this Series</span>
        <h2 class="section-title">系列其他商品</h2>
      </div>
      <div class="products-grid">
        <ProductCard v-for="p in restProducts" :key="p.id" :product="p" />
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
  margin-bottom: 56px;
  flex-wrap: wrap;
}
.breadcrumb a { color: inherit; text-decoration: none; transition: color 150ms; }
.breadcrumb a:hover { color: var(--color-accent); }
.breadcrumb .current { color: var(--color-ink-default); }

/* ── Hero (editorial, 1 欄置中靠左; 大量留白) ── */
.hero {
  margin: 0 0 96px;
  max-width: 720px;
}

.hero-info { display: flex; flex-direction: column; }

.hero-eyebrow {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.eyebrow-text {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.34em;
  text-transform: uppercase;
  color: var(--color-fresh);
  position: relative;
  padding-left: 18px;
}
.eyebrow-text::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 12px;
  height: 1px;
  background: var(--color-fresh);
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
  font-size: 64px;
  line-height: 1.18;
  letter-spacing: 0.08em;
  color: var(--color-ink-strong);
  margin: 0 0 28px;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.hero-desc {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 17px;
  line-height: 2;
  color: var(--color-ink-default);
  letter-spacing: 0.04em;
  margin: 0 0 32px;
  white-space: pre-wrap;
  max-width: 560px;
}

.hero-meta {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  align-self: flex-start;
  padding-top: 20px;
  border-top: 1px solid var(--color-line-subtle);
}
.meta-num {
  font-family: var(--font-mono);
  font-size: 16px;
  color: var(--color-ink-strong);
  font-weight: 500;
}
.meta-label {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}
.meta-divider { color: var(--color-line); margin: 0 4px; }
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

/* ── Picks ── */
.picks {
  margin-bottom: 96px;
  padding-top: 28px;
  border-top: 1px solid var(--color-line-subtle);
}
.picks-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 36px;
  gap: 24px;
}
.picks-eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-fresh);
}
.picks-count {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--color-ink-muted);
}
.picks-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 28px;
}

/* ── Empty panel (沒商品時的優雅版面) ── */
.empty-panel {
  margin: 0 0 96px;
  padding: 80px 56px;
  background: var(--color-paper-surface);
  border: 1px solid var(--color-line-subtle);
  text-align: center;
}
.empty-eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.34em;
  text-transform: uppercase;
  color: var(--color-fresh);
  margin-bottom: 20px;
}
.empty-headline {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 36px;
  line-height: 1.5;
  letter-spacing: 0.08em;
  color: var(--color-ink-strong);
  margin: 0 0 24px;
}
.empty-headline em {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 22px;
  letter-spacing: 0.04em;
  color: var(--color-accent);
  display: inline-block;
  margin-top: 8px;
}
.empty-note {
  font-size: 13px;
  line-height: 1.95;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
  margin: 0 0 28px;
}
.empty-link {
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
.empty-link:hover {
  color: var(--color-accent-deep);
  border-color: var(--color-accent-deep);
}

/* ── Products section (More in this Series) ── */
.products-section {
  padding-top: 28px;
  border-top: 1px solid var(--color-line-subtle);
}
.section-header { margin-bottom: 36px; }
.section-eyebrow {
  display: block;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-bottom: 10px;
}
.section-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 28px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0;
}
.products-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 28px;
}

@media (max-width: 1279px) {
  .hero-title { font-size: 48px; }
  .picks-grid,
  .products-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 1023px) {
  .page { padding: 40px 32px 64px; }
  .hero-title { font-size: 40px; }
  .empty-panel { padding: 56px 28px; }
  .empty-headline { font-size: 28px; }
  .picks-grid,
  .products-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 767px) {
  .page { padding: 32px 24px 48px; }
  .hero { margin-bottom: 56px; }
  .hero-title { font-size: 32px; letter-spacing: 0.06em; }
  .hero-desc { font-size: 15px; }
  .empty-headline { font-size: 24px; }
  .picks-grid,
  .products-grid { grid-template-columns: 1fr; }
}
</style>
