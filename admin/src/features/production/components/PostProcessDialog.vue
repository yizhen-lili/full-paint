<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'
import Label from '@/shared/ui/Label.vue'
import Select from '@/shared/ui/Select.vue'
import { Loader2, AlertTriangle, MousePointer } from 'lucide-vue-next'

import type { PaletteColor } from '../api'

type OperationType = 'merge_color' | 'eliminate_border'

const props = defineProps<{
  open: boolean
  type: OperationType | null
  palette: PaletteColor[]
  /** filled_template_url，可選；提供時 dialog 會多一個「點圖選色塊」面板 */
  imageUrl?: string | null
  pending: boolean
}>()

const emit = defineEmits<{
  close: []
  confirmMerge: [payload: { source_template_id: number; target_template_id: number }]
  confirmEliminate: [payload: { absorbed_template_id: number; surviving_template_id: number }]
}>()

const param1 = ref<string>('')  // first template_id
const param2 = ref<string>('')  // second template_id
const errors = ref<Record<string, string>>({})

// canvas pick：next click 填到哪個 param
const canvasMode = ref(false)
const canvasRef = ref<HTMLCanvasElement | null>(null)
let imgData: ImageData | null = null
const canvasError = ref<string | null>(null)
const canvasLoading = ref(false)

watch(
  [() => props.open, () => props.type],
  () => {
    if (props.open) {
      param1.value = ''
      param2.value = ''
      errors.value = {}
      canvasError.value = null
      // canvas 開啟時不自動進 mode；要等 user 點按鈕（避免每次開 dialog 都重畫）
      canvasMode.value = false
    }
  },
)

watch(
  [() => canvasMode.value, () => props.imageUrl],
  async () => {
    if (!canvasMode.value || !props.imageUrl) return
    canvasLoading.value = true
    canvasError.value = null
    try {
      // 等 next tick 讓 canvas DOM 渲染
      await new Promise((r) => setTimeout(r, 50))
      const c = canvasRef.value
      if (!c) return
      const img = new Image()
      img.crossOrigin = 'anonymous'
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve()
        img.onerror = () => reject(new Error('圖片載入失敗'))
        img.src = props.imageUrl!
      })
      const maxW = 600
      const ratio = img.width > maxW ? maxW / img.width : 1
      c.width = Math.round(img.width * ratio)
      c.height = Math.round(img.height * ratio)
      const ctx = c.getContext('2d')
      if (!ctx) return
      ctx.drawImage(img, 0, 0, c.width, c.height)
      imgData = ctx.getImageData(0, 0, c.width, c.height)
    } catch (e) {
      canvasError.value = (e as Error).message
    } finally {
      canvasLoading.value = false
    }
  },
)

function onCanvasClick(e: MouseEvent) {
  if (!canvasRef.value || !imgData) return
  const rect = canvasRef.value.getBoundingClientRect()
  const x = Math.floor((e.clientX - rect.left) * (canvasRef.value.width / rect.width))
  const y = Math.floor((e.clientY - rect.top) * (canvasRef.value.height / rect.height))
  const idx = (y * imgData.width + x) * 4
  const r = imgData.data[idx]
  const g = imgData.data[idx + 1]
  const b = imgData.data[idx + 2]
  // 找 palette 中最近的 RGB
  let best: { id: number; dist: number } | null = null
  for (const p of props.palette) {
    const [pr, pg, pb] = p.rgb
    const dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
    if (!best || dist < best.dist) best = { id: p.template_id, dist }
  }
  if (!best) return
  // 填到下一個空 slot（先 param1，再 param2）
  if (!param1.value) {
    param1.value = String(best.id)
  } else if (!param2.value) {
    param2.value = String(best.id)
  } else {
    // 兩個都滿了 → 重置 param1
    param1.value = String(best.id)
    param2.value = ''
  }
}

const titles: Record<OperationType, string> = {
  merge_color: '合併色塊',
  eliminate_border: '消除邊界線',
}
const labels: Record<OperationType, { p1: string; p2: string; hint: string; warn: string }> = {
  merge_color: {
    p1: '來源色塊（會被併掉）',
    p2: '目標色塊（保留）',
    hint: '把來源色塊的所有像素改成目標色塊的顏色，重新跑 SVG。',
    warn: '會把 approved 退回 false（需重新審核）。',
  },
  eliminate_border: {
    p1: '被吸收的色塊（消失）',
    p2: '存活的色塊（吃掉對方）',
    hint: '把兩色塊間的邊界消去，被吸收側的像素改成存活側的顏色。',
    warn: '會把 approved 退回 false。',
  },
}

const paletteOptions = computed(() => [
  { value: '', label: '— 請選 —' },
  ...props.palette.map((c) => ({
    value: String(c.template_id),
    label: `#${c.template_id} ${c.hex}`,
  })),
])

function validate(): boolean {
  const errs: Record<string, string> = {}
  const id1 = Number(param1.value)
  const id2 = Number(param2.value)
  if (!id1) errs.p1 = '必選'
  if (!id2) errs.p2 = '必選'
  if (id1 && id2 && id1 === id2) errs.p2 = '不可選同一個色塊'
  errors.value = errs
  return Object.keys(errs).length === 0
}

function submit() {
  if (!validate() || !props.type) return
  const id1 = Number(param1.value)
  const id2 = Number(param2.value)
  if (props.type === 'merge_color') {
    emit('confirmMerge', { source_template_id: id1, target_template_id: id2 })
  } else if (props.type === 'eliminate_border') {
    emit('confirmEliminate', { absorbed_template_id: id1, surviving_template_id: id2 })
  }
}
</script>

<template>
  <Dialog
    :open="open"
    :title="type ? titles[type] : ''"
    size="md"
    @close="emit('close')"
  >
    <div v-if="type" class="space-y-4 text-[13px]">
      <p class="text-ink-default">{{ labels[type].hint }}</p>
      <p class="text-[12px] text-state-warning flex items-start gap-1">
        <AlertTriangle :size="12" :stroke-width="1.5" class="mt-0.5 shrink-0" />
        <span>{{ labels[type].warn }}</span>
      </p>

      <!-- 點圖選色塊 toggle -->
      <div v-if="imageUrl">
        <button
          type="button"
          class="text-[12px] inline-flex items-center gap-1 text-ink-muted hover:text-accent transition-colors"
          @click="canvasMode = !canvasMode"
        >
          <MousePointer :size="12" :stroke-width="1.5" />
          {{ canvasMode ? '收起預覽圖' : '從預覽圖點選色塊' }}
        </button>
        <div
          v-if="canvasMode"
          class="mt-2 rounded-[var(--radius-sm)] border border-line-hairline bg-paper-canvas overflow-hidden relative"
        >
          <canvas
            ref="canvasRef"
            class="block max-w-full h-auto cursor-crosshair"
            @click="onCanvasClick"
          />
          <div
            v-if="canvasLoading"
            class="absolute inset-0 flex items-center justify-center bg-paper-canvas/80"
          >
            <Loader2 :size="20" :stroke-width="1.5" class="animate-spin text-ink-muted" />
          </div>
          <p v-if="canvasError" class="p-2 text-[11px] text-state-danger">{{ canvasError }}</p>
        </div>
        <p v-if="canvasMode" class="mt-1 text-[11px] text-ink-muted">
          點圖會依序填到下方第 1 / 第 2 欄；兩格都滿會從第 1 欄重新開始。
        </p>
      </div>

      <div>
        <Label>{{ labels[type].p1 }}</Label>
        <Select v-model="param1" :options="paletteOptions" />
        <p v-if="errors.p1" class="mt-1 text-[12px] text-state-danger">{{ errors.p1 }}</p>
      </div>
      <div>
        <Label>{{ labels[type].p2 }}</Label>
        <Select v-model="param2" :options="paletteOptions" />
        <p v-if="errors.p2" class="mt-1 text-[12px] text-state-danger">{{ errors.p2 }}</p>
      </div>

      <p class="text-[11px] text-ink-muted">
        色塊編號可從上方「調色盤」卡看到（每色 #N 標記）。
      </p>
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="pending" @click="emit('close')">取消</Button>
      <Button variant="primary" :disabled="pending" @click="submit">
        <Loader2 v-if="pending" :size="14" :stroke-width="1.5" class="animate-spin" />
        執行
      </Button>
    </template>
  </Dialog>
</template>
