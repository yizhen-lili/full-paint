<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useProductsQuery } from '@/features/products/queries'
import type { ThemeListItem } from '@/features/browse/api'

const props = defineProps<{
  theme: ThemeListItem
}>()

// 取該主題精選商品最多 4 個（無精選 fallback 取最新 4 個）
const featuredQuery = useProductsQuery(
  computed(() => ({
    theme_id: props.theme.id,
    featured: true,
    page: 1,
    page_size: 4,
  })),
)
const fallbackQuery = useProductsQuery(
  computed(() => ({
    theme_id: props.theme.id,
    sort: 'latest' as const,
    page: 1,
    page_size: 4,
  })),
)

const products = computed(() => {
  const featured = featuredQuery.data.value?.items ?? []
  if (featured.length > 0) return featured.slice(0, 4)
  return (fallbackQuery.data.value?.items ?? []).slice(0, 4)
})

// 永遠 4 格（不夠 product 用 null 填）
const cells = computed(() => [
  products.value[0] ?? null,
  products.value[1] ?? null,
  products.value[2] ?? null,
  products.value[3] ?? null,
])

// 4 種 mood 漸層 — 跟 ThemeDetail hero mosaic 對齊
const TONES = [
  'linear-gradient(135deg, #DDE5D2 0%, #97A687 110%)',
  'linear-gradient(135deg, #ECDFDA 0%, #C9A8A8 110%)',
  'linear-gradient(135deg, #ECE3D2 0%, #B8A084 110%)',
  'linear-gradient(135deg, #DCE3E2 0%, #98ABA8 110%)',
]
function toneFor(idx: number) {
  return TONES[idx % TONES.length]
}

const themeInitial = computed(() => props.theme.name.slice(0, 1))
</script>

<template>
  <RouterLink :to="`/themes/${theme.id}`" class="theme-card">
    <div class="mosaic">
      <template v-for="(p, idx) in cells" :key="idx">
        <div class="cell">
          <img
            v-if="p?.cover_image_url"
            :src="p.cover_image_url"
            :alt="p.title"
            class="cell-img"
            loading="lazy"
          />
          <div
            v-else
            class="cell-tone"
            :style="{ background: toneFor(idx) }"
          >
            <span class="cell-mark">{{ themeInitial }}</span>
          </div>
        </div>
      </template>
    </div>
    <div class="overlay">
      <div class="name">{{ theme.name }}</div>
      <div class="meta">{{ theme.series_count }} 系列 · {{ theme.product_count }} 件商品</div>
    </div>
  </RouterLink>
</template>

<style scoped>
.theme-card {
  display: block;
  text-decoration: none;
  color: inherit;
  position: relative;
  aspect-ratio: 1.3 / 1;
  overflow: hidden;
  border-radius: var(--radius-xs);
  border: 1px solid var(--color-line-subtle);
  background: var(--color-paper-deep);
  transition: border-color 200ms, transform 400ms ease;
}
.theme-card:hover {
  border-color: var(--color-line);
}

/* 2x2 mosaic 鋪滿整個卡片 */
.mosaic {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 2px;
}
.cell {
  position: relative;
  overflow: hidden;
  background: var(--color-paper-deep);
}
.cell-img {
  width: 100%; height: 100%;
  object-fit: cover;
  filter: sepia(0.06) saturate(0.88);
  transition: transform 700ms ease;
}
.theme-card:hover .cell-img {
  transform: scale(1.04);
}
.cell-tone {
  width: 100%; height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.cell-mark {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 38px;
  color: var(--color-ink-strong);
  opacity: 0.18;
  letter-spacing: 0.04em;
  user-select: none;
}

/* 暗化覆蓋 + 標題在底部 */
.overlay {
  position: absolute;
  inset: 0;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  background: linear-gradient(
    to top,
    rgba(31, 26, 21, 0.62) 0%,
    rgba(31, 26, 21, 0.18) 45%,
    rgba(31, 26, 21, 0) 75%
  );
  pointer-events: none;
}

.name {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 22px;
  letter-spacing: 0.06em;
  color: var(--color-paper-canvas);
  margin-bottom: 4px;
  text-shadow: 0 2px 8px rgba(31, 26, 21, 0.4);
}

.meta {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(250, 244, 221, 0.88);
}

@media (max-width: 767px) {
  .cell-mark { font-size: 28px; }
}
</style>
