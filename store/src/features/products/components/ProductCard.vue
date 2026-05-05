<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ImageOff } from 'lucide-vue-next'
import type { ProductBrief, Difficulty } from '../api'

const props = defineProps<{
  product: ProductBrief
  /** 雜誌感編號（如 "01"），不傳則不顯示 */
  number?: string
  /** 設計示意模式 — 不渲染 RouterLink、加「示意」badge */
  preview?: boolean
}>()

const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  beginner: '入門',
  elementary: '初級',
  intermediate: '中級',
  advanced: '進階',
}

const difficultyLabel = computed(() => {
  const range = props.product.difficulty_range
  if (!range) return null
  if (range[0] === range[1]) return DIFFICULTY_LABEL[range[0]]
  return `${DIFFICULTY_LABEL[range[0]]} – ${DIFFICULTY_LABEL[range[1]]}`
})

const priceLabel = computed(() => {
  const { price_min, price_max } = props.product
  if (price_min === price_max) return `NT$ ${price_min.toLocaleString()}`
  return `NT$ ${price_min.toLocaleString()} — ${price_max.toLocaleString()}`
})

const imageError = ref(false)
const showImage = computed(
  () => !imageError.value && !!props.product.cover_image_url,
)
function onImgError() {
  imageError.value = true
}
</script>

<template>
  <component
    :is="preview ? 'div' : RouterLink"
    :to="preview ? undefined : `/products/${product.id}`"
    class="card"
    :class="{ 'card-preview': preview }"
  >
    <div class="img-wrap">
      <span v-if="preview" class="badge badge-preview">示意</span>
      <span v-if="product.is_featured" class="badge badge-featured">★ 精選</span>
      <span v-if="product.is_preorder" class="badge badge-preorder">預購中</span>
      <img
        v-if="showImage"
        :src="product.cover_image_url"
        :alt="product.title"
        loading="lazy"
        @error="onImgError"
      />
      <div v-else class="img-fallback" aria-label="商品圖片暫缺">
        <ImageOff class="fallback-icon" />
        <span class="fallback-text">圖片即將上線</span>
      </div>
    </div>
    <div class="body">
      <div v-if="number" class="num">No. {{ number }}</div>
      <div class="title">{{ product.title }}</div>
      <div v-if="difficultyLabel" class="meta">{{ difficultyLabel }}</div>
      <div class="price-row">
        <span class="price-label">售價</span>
        <span class="price">{{ priceLabel }}</span>
      </div>
    </div>
  </component>
</template>

<style scoped>
.card {
  display: block;
  text-decoration: none;
  background: var(--color-paper-surface);
  border: 1px solid var(--color-line-subtle);
  transition: border-color 200ms, box-shadow 300ms;
  color: inherit;
}
.card:not(.card-preview):hover {
  border-color: var(--color-line);
  box-shadow: 0 4px 18px rgba(46, 40, 35, 0.06);
}
.card-preview {
  cursor: default;
  opacity: 0.96;
}

.img-wrap {
  position: relative;
  aspect-ratio: 4 / 5;
  overflow: hidden;
  border-bottom: 1px solid var(--color-line-subtle);
  background: var(--color-paper-deep);
}

.img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: sepia(0.07) saturate(0.92);
  transition: transform 600ms ease, filter 200ms;
}
.card:not(.card-preview):hover .img-wrap img {
  transform: scale(1.03);
  filter: sepia(0.07) saturate(0.92) brightness(1.05);
}

.img-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: linear-gradient(
    135deg,
    var(--color-paper-deep) 0%,
    var(--color-accent-tint) 60%,
    var(--color-accent-soft) 120%
  );
  background-size: 200% 200%;
  background-position: 30% 30%;
  color: var(--color-ink-muted);
}
.fallback-icon {
  width: 32px;
  height: 32px;
  stroke: currentColor;
  stroke-width: 1.25;
  fill: none;
  opacity: 0.5;
}
.fallback-text {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.7;
}

.badge {
  position: absolute;
  top: 12px;
  height: 22px;
  padding: 0 10px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  border-radius: var(--radius-xs);
  display: inline-flex;
  align-items: center;
  z-index: 2;
}
.badge-preorder {
  left: 12px;
  background: rgba(184, 145, 73, 0.12);
  color: var(--color-state-warning);
}
.badge-preview {
  right: 12px;
  background: var(--color-ink-strong);
  color: var(--color-paper-canvas);
}
.badge-featured {
  left: 12px;
  top: 12px;
  background: var(--color-state-warning);
  color: var(--color-paper-canvas);
}
.badge-preorder + .img-wrap .badge-featured,
.img-wrap > .badge-featured + .badge-preorder {
  /* 同時 featured + preorder 時 preorder 往下移 */
  top: 42px;
}

.body {
  padding: 22px 22px 24px;
}

.num {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--color-accent-soft);
  margin-bottom: 10px;
}

.title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 20px;
  letter-spacing: 0.04em;
  color: var(--color-ink-strong);
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta {
  font-family: var(--font-body);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-bottom: 14px;
}

.price-row {
  padding-top: 14px;
  border-top: 1px solid var(--color-line-subtle);
}

.price-label {
  display: block;
  font-family: var(--font-body);
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-bottom: 4px;
}

.price {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--color-ink-strong);
  font-weight: 500;
  white-space: nowrap;
}
</style>
