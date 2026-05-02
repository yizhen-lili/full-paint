<script setup lang="ts">
/**
 * MaskCanvas — 圖片 + sam_points/polygons 標記 + mask overlay 渲染
 *
 * 規格：admin_production.md §1.3 + 04c_production_sam.md §C.2
 *
 * 互動：
 *   SAM 模式：左鍵 → 前景點 (label=1, 綠)，右鍵 → 背景點 (label=0, 紅)
 *   多邊形模式：左鍵 → currentPolygon 加頂點，右鍵 → ≥3 點則閉合並 push
 *
 * 顯示：
 *   1. 原圖（bottom layer，<img> 不變形）
 *   2. mask overlay（半透明綠，吃 mask_url PNG）
 *   3. sam_points 圓點（綠/紅）+ polygons 線（藍）+ currentPolygon 進行中（虛線）
 *
 * 座標：對外提供 image-natural 座標（送後端用），內部換算 displayed → natural。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import type { SamPoint } from '../api'
import type { MaskTool } from './MaskToolbar.vue'

const props = defineProps<{
  imageUrl: string                            // <img src> — 用 signed URL 顯示
  imageWidth: number                          // natural width (px)
  imageHeight: number                         // natural height (px)
  tool: MaskTool
  samPoints: SamPoint[]
  polygons: number[][][]                      // 已閉合的多邊形：[[[x,y],...], ...]
  currentPolygon: number[][]                  // 進行中：[[x,y],...]
  maskUrl: string | null                      // 後端回的 mask PNG signed URL
  isLocked: boolean
}>()

const emit = defineEmits<{
  'add-sam-point': [point: SamPoint]
  'add-polygon-vertex': [point: [number, number]]
  'close-polygon': []
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const imgRef = ref<HTMLImageElement | null>(null)

// ── 座標換算（displayed pixel → natural pixel）─────────────────────────
// container 顯示尺寸可能被 CSS 限制（max-width / max-height），跟 natural 不一樣。
// 後端 sam_points 要 natural 座標。

const displayedW = ref(0)
const displayedH = ref(0)

function recomputeSize() {
  if (!imgRef.value) return
  displayedW.value = imgRef.value.clientWidth
  displayedH.value = imgRef.value.clientHeight
}

let ro: ResizeObserver | null = null
onMounted(() => {
  recomputeSize()
  if (imgRef.value) {
    imgRef.value.onload = recomputeSize
  }
  if (window.ResizeObserver && imgRef.value) {
    ro = new ResizeObserver(recomputeSize)
    ro.observe(imgRef.value)
  }
})
onUnmounted(() => {
  if (ro) ro.disconnect()
})

watch(() => props.imageUrl, () => {
  // 換圖時 displayed 尺寸要重新量
  setTimeout(recomputeSize, 50)
})

const scaleX = computed(() => (displayedW.value > 0 ? props.imageWidth / displayedW.value : 1))
const scaleY = computed(() => (displayedH.value > 0 ? props.imageHeight / displayedH.value : 1))

// natural → displayed（用於畫 marker overlay）
function nx(naturalX: number): number {
  return scaleX.value > 0 ? naturalX / scaleX.value : naturalX
}
function ny(naturalY: number): number {
  return scaleY.value > 0 ? naturalY / scaleY.value : naturalY
}

// click event → natural 座標
function eventToNatural(e: MouseEvent): [number, number] {
  const rect = imgRef.value?.getBoundingClientRect()
  if (!rect) return [0, 0]
  const dx = e.clientX - rect.left
  const dy = e.clientY - rect.top
  const naturalX = Math.round(dx * scaleX.value)
  const naturalY = Math.round(dy * scaleY.value)
  return [naturalX, naturalY]
}

// ── 滑鼠事件 ─────────────────────────────────────────────────────────────

function onLeftClick(e: MouseEvent) {
  if (props.isLocked) return
  e.preventDefault()
  const [x, y] = eventToNatural(e)
  if (props.tool === 'sam') {
    emit('add-sam-point', { x, y, label: 1 })
  } else {
    emit('add-polygon-vertex', [x, y])
  }
}

function onRightClick(e: MouseEvent) {
  if (props.isLocked) return
  e.preventDefault()
  const [x, y] = eventToNatural(e)
  if (props.tool === 'sam') {
    emit('add-sam-point', { x, y, label: 0 })
  } else {
    // 多邊形：≥ 3 點才閉合
    if (props.currentPolygon.length >= 3) {
      emit('close-polygon')
    }
  }
}
</script>

<template>
  <div
    ref="containerRef"
    class="relative inline-block max-w-full select-none"
    @contextmenu.prevent
  >
    <!-- 1. 原圖（block，控制容器尺寸）-->
    <img
      ref="imgRef"
      :src="imageUrl"
      class="block max-w-full h-auto pointer-events-none rounded-[var(--radius-xs)]"
      alt="待標記圖"
      draggable="false"
    />

    <!-- 2. 透明點擊層（吸所有滑鼠事件，蓋滿圖 — 圖本身 pointer-events-none）-->
    <div
      class="absolute inset-0"
      :class="[isLocked ? 'cursor-not-allowed' : tool === 'sam' ? 'cursor-crosshair' : 'cursor-copy']"
      @click="onLeftClick"
      @contextmenu="onRightClick"
    />

    <!-- 3. Mask PNG overlay（半透明綠，後端產出）-->
    <img
      v-if="maskUrl"
      :src="maskUrl"
      class="absolute inset-0 w-full h-full object-contain pointer-events-none mix-blend-multiply opacity-50"
      style="filter: hue-rotate(80deg) saturate(2);"
      alt="mask overlay"
      draggable="false"
    />

    <!-- 4. SVG overlay：sam points + polygons -->
    <svg
      class="absolute inset-0 w-full h-full pointer-events-none"
      :width="displayedW || '100%'"
      :height="displayedH || '100%'"
    >
      <!-- 已閉合多邊形（藍色實線）-->
      <polygon
        v-for="(poly, i) in polygons"
        :key="`p-${i}`"
        :points="poly.map((pt) => `${nx(pt[0])},${ny(pt[1])}`).join(' ')"
        fill="rgba(56, 189, 248, 0.15)"
        stroke="#0284c7"
        stroke-width="2"
      />

      <!-- 進行中多邊形（虛線）-->
      <polyline
        v-if="currentPolygon.length > 0"
        :points="currentPolygon.map((pt) => `${nx(pt[0])},${ny(pt[1])}`).join(' ')"
        fill="none"
        stroke="#0284c7"
        stroke-width="2"
        stroke-dasharray="6,4"
      />
      <circle
        v-for="(pt, i) in currentPolygon"
        :key="`cp-${i}`"
        :cx="nx(pt[0])"
        :cy="ny(pt[1])"
        r="4"
        fill="#0284c7"
      />

      <!-- SAM 點：綠 = 前景，紅 = 背景 -->
      <g v-for="(p, i) in samPoints" :key="`s-${i}`">
        <circle
          :cx="nx(p.x)"
          :cy="ny(p.y)"
          r="7"
          :fill="p.label === 1 ? '#22c55e' : '#ef4444'"
          stroke="white"
          stroke-width="2"
        />
      </g>
    </svg>
  </div>
</template>
