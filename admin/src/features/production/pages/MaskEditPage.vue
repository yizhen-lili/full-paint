<script setup lang="ts">
/**
 * MaskEditPage — 路由 /admin/production/jobs/:id/mask
 *
 * 規格依據：
 *   admin_production.md §1.3（兩種選取模式 / 即時預覽 / 撤銷+清除+確認）
 *   04c_production_sam.md §C（debounce 300ms 即時送 sam-mask；確認 = 啟動批次）
 *
 * 流程：
 *   1. 進頁面 → useJobQuery 拉 job 資料 + image_id 對應的圖
 *   2. 使用者標 sam_points / polygons → debounce 300ms → POST /sam-mask → 拿 mask_url
 *   3. mask_url 變更 → MaskCanvas 顯示 overlay
 *   4. 「儲存並啟動批次」→ 最後送一次 sam-mask（確保最新狀態）→ POST /batches/{batch_id}/start
 *      → router.push 回 batch 列表
 *
 * 編輯時機：status=pending 才能編輯，其他狀態 isLocked=true（rendering 仍在，但禁用互動）。
 */
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft, AlertTriangle, Loader2 } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'

import MaskCanvas from '../components/MaskCanvas.vue'
import MaskToolbar, { type MaskTool } from '../components/MaskToolbar.vue'
import { useJobQuery, useSamMaskMutation, useStartBatchMutation } from '../queries'
import { getJobSignedUrl, type SamPoint } from '../api'

const route = useRoute()
const router = useRouter()

const jobId = computed(() => String(route.params.jobId))

// ── 拉 job 資料（含 image 寬高、status、batch_id、mode）─────────────────
const jobQuery = useJobQuery(jobId)
const job = computed(() => jobQuery.data.value)

const isLocked = computed(() => {
  const s = job.value?.status
  // pending 才可編輯；其他全鎖
  return s !== 'pending'
})

const samMode = computed<'sam_refine' | 'sam_weighted' | null>(() => {
  const m = job.value?.mode
  if (m === 'sam_refine' || m === 'sam_weighted') return m
  return null
})

// ── 圖片 URL（透過 signed-url endpoint 拿原圖；簡化：從 job.image_id 找；後端已綁好 image）
// 由於 JobDetailResponse 沒直接給 image 的 signed URL，採用：呼叫 /admin/images/:id
//（如果沒這 endpoint，改方案：從 image_id 拿 image，再用 image.original_url，已是 signed URL）
// MVP 階段先用 job.svg_url? 不對 — 那是結果。
// 暫用：image_id → 透過 /admin/images?image_id=X 列表式拿 — 但這 list endpoint 沒按 id 過濾。
// 簡化：呼叫 backend 提供的圖片資訊。先看 job.image_id 後再實作。
//
// 替代方案：sam-mask endpoint 內部會自己讀圖；前端只需要顯示一張圖。
// 用 /admin/production/jobs/:id/signed-url?file=image — 確認此 endpoint 是否支援 image。

const imageDisplayUrl = ref<string | null>(null)
const imageLoadError = ref<string | null>(null)
const imageWidth = ref<number>(0)
const imageHeight = ref<number>(0)

watch(job, async (j) => {
  if (!j || imageDisplayUrl.value) return
  try {
    // 嘗試走 signed-url endpoint 拿原圖（file=image）
    const resp = await getJobSignedUrl(j.id, 'image')
    if (resp.url) {
      imageDisplayUrl.value = resp.url
      // 讀寬高（natural）
      await loadImageDims(resp.url)
    } else {
      imageLoadError.value = '無法取得原圖（image signed URL 為空）'
    }
  } catch (e) {
    imageLoadError.value = (e as { message?: string }).message || '無法取得原圖'
  }
}, { immediate: true })

async function loadImageDims(url: string) {
  return new Promise<void>((resolve, reject) => {
    const img = new window.Image()
    img.onload = () => {
      imageWidth.value = img.naturalWidth
      imageHeight.value = img.naturalHeight
      resolve()
    }
    img.onerror = () => reject(new Error('圖片載入失敗'))
    img.src = url
  })
}

// ── 編輯狀態 ─────────────────────────────────────────────────────────────
const tool = ref<MaskTool>('sam')
const samPoints = ref<SamPoint[]>([])
const polygons = ref<number[][][]>([])
const currentPolygon = ref<number[][]>([])
// undo stack：記錄每個動作的種類，用於撤銷
type Action =
  | { type: 'sam'; point: SamPoint }
  | { type: 'poly_vertex'; vertex: [number, number] }
  | { type: 'poly_close'; polygon: number[][] }
const actionStack = ref<Action[]>([])

const canUndo = computed(() => actionStack.value.length > 0)
const canConfirm = computed(() => {
  if (isLocked.value) return false
  // 至少有一個 sam_point 或一個閉合 polygon
  return samPoints.value.length > 0 || polygons.value.length > 0
})

// 載入既有 sam_points / polygons（job 之前已編輯過）
watch(job, (j) => {
  if (!j) return
  // JobDetail 還沒把 sam_points / polygons 帶出來（schema 有，type 沒）
  // 暫時用 any — 之後補強型別
  const anyJ = j as unknown as { sam_points?: SamPoint[]; polygons?: number[][][] }
  if (anyJ.sam_points && samPoints.value.length === 0) samPoints.value = [...anyJ.sam_points]
  if (anyJ.polygons && polygons.value.length === 0) polygons.value = anyJ.polygons.map((p) => [...p])
}, { immediate: true })

// ── 互動 handler ────────────────────────────────────────────────────────
function addSamPoint(point: SamPoint) {
  samPoints.value.push(point)
  actionStack.value.push({ type: 'sam', point })
  triggerSamMask()
}

function addPolygonVertex(vertex: [number, number]) {
  currentPolygon.value.push(vertex)
  actionStack.value.push({ type: 'poly_vertex', vertex })
}

function closePolygon() {
  if (currentPolygon.value.length < 3) return
  const closed = [...currentPolygon.value]
  polygons.value.push(closed)
  actionStack.value.push({ type: 'poly_close', polygon: closed })
  currentPolygon.value = []
  triggerSamMask()
}

function undo() {
  const last = actionStack.value.pop()
  if (!last) return
  if (last.type === 'sam') {
    samPoints.value.pop()
  } else if (last.type === 'poly_vertex') {
    currentPolygon.value.pop()
  } else if (last.type === 'poly_close') {
    // 撤銷閉合 → 把那 polygon 變回 currentPolygon
    polygons.value.pop()
    currentPolygon.value = last.polygon
  }
  triggerSamMask()
}

function clearAll() {
  samPoints.value = []
  polygons.value = []
  currentPolygon.value = []
  actionStack.value = []
  // 後端 mask 也要清掉 — 送一次空狀態
  // 但後端 validator 至少要一個 → 不打 API，前端等使用者重新點
  maskUrl.value = null
}

// ── 送 sam-mask（debounce 300ms）─────────────────────────────────────────
const samMaskMut = useSamMaskMutation('') // 動態傳 jobId — 但 useMutation 需要先綁，改下面寫法
const maskUrl = ref<string | null>(null)
const samMaskInflight = ref(false)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function triggerSamMask() {
  if (!samMode.value) return
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(async () => {
    if (samPoints.value.length === 0 && polygons.value.length === 0) {
      // 沒任何標記，不送
      return
    }
    samMaskInflight.value = true
    try {
      // 直接呼叫 api（避開 useMutation 綁定 jobId 的麻煩）
      const { updateSamMask } = await import('../api')
      const resp = await updateSamMask(jobId.value, {
        sam_points: samPoints.value.length ? samPoints.value : undefined,
        polygons: polygons.value.length ? polygons.value : undefined,
        mode: samMode.value!,
      })
      maskUrl.value = resp.mask_url
    } catch (e) {
      apiError.value = `更新 mask 失敗：${(e as { message?: string }).message || ''}`
    } finally {
      samMaskInflight.value = false
    }
  }, 300)
}

// ── 啟動批次 ─────────────────────────────────────────────────────────────
const startBatchMut = useStartBatchMutation()
const apiError = ref<string | null>(null)

async function confirm() {
  if (!job.value?.batch_id) {
    apiError.value = '此 job 沒有 batch_id，無法啟動'
    return
  }
  // 先 flush debounce 確保最新 mask 已送
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  if (!isLocked.value && (samPoints.value.length > 0 || polygons.value.length > 0)) {
    try {
      const { updateSamMask } = await import('../api')
      await updateSamMask(jobId.value, {
        sam_points: samPoints.value.length ? samPoints.value : undefined,
        polygons: polygons.value.length ? polygons.value : undefined,
        mode: samMode.value!,
      })
    } catch (e) {
      apiError.value = `儲存 mask 失敗：${(e as { message?: string }).message || ''}`
      return
    }
  }
  // 啟動 batch
  try {
    const result = await startBatchMut.mutateAsync(job.value.batch_id)
    if (result.skipped.length > 0) {
      apiError.value = `部分 job 未啟動：${result.skipped.map((s) => s.reason).join('、')}`
    }
    router.push(`/admin/production?batch_id=${job.value.batch_id}`)
  } catch (e) {
    apiError.value = `啟動批次失敗：${(e as { message?: string }).message || ''}`
  }
}
</script>

<template>
  <div class="flex items-center gap-2 mb-3">
    <button
      type="button"
      class="text-[13px] text-ink-muted hover:text-ink-strong inline-flex items-center gap-1 transition-colors"
      @click="router.push(`/admin/production/${jobId}`)"
    >
      <ChevronLeft :size="14" :stroke-width="1.5" />
      返回任務詳情
    </button>
  </div>

  <PageHeader
    title="編輯遮罩"
    :subtitle="`mode = ${samMode || '—'}，${isLocked ? '已鎖定（status ≠ pending）' : '可編輯'}`"
  />

  <div
    v-if="apiError"
    class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)] flex items-start gap-2"
  >
    <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5" />
    <span class="flex-1">{{ apiError }}</span>
    <button class="text-[12px] underline" @click="apiError = null">關閉</button>
  </div>

  <Card>
    <div v-if="jobQuery.isLoading.value" class="text-center text-ink-muted py-12">
      <Loader2 :size="20" :stroke-width="1.5" class="inline animate-spin mr-2" />
      載入任務資料 ...
    </div>

    <div v-else-if="jobQuery.error.value" class="text-center text-state-danger py-12">
      載入失敗：{{ (jobQuery.error.value as { message?: string }).message }}
    </div>

    <div v-else-if="!samMode" class="text-center text-ink-muted py-12">
      此 job 不是 SAM 模式（mode = {{ job?.mode }}），無需編輯遮罩。
    </div>

    <div v-else>
      <MaskToolbar
        v-model:tool="tool"
        :can-undo="canUndo"
        :can-confirm="canConfirm"
        :is-locked="isLocked || startBatchMut.isPending.value"
        @undo="undo"
        @clear="clearAll"
        @confirm="confirm"
      />

      <div class="mt-4 flex justify-center">
        <div v-if="imageLoadError" class="text-state-danger py-12">
          {{ imageLoadError }}
        </div>
        <div v-else-if="!imageDisplayUrl || imageWidth === 0" class="text-ink-muted py-12">
          <Loader2 :size="20" :stroke-width="1.5" class="inline animate-spin mr-2" />
          載入圖片 ...
        </div>
        <MaskCanvas
          v-else
          :image-url="imageDisplayUrl"
          :image-width="imageWidth"
          :image-height="imageHeight"
          :tool="tool"
          :sam-points="samPoints"
          :polygons="polygons"
          :current-polygon="currentPolygon"
          :mask-url="maskUrl"
          :is-locked="isLocked"
          @add-sam-point="addSamPoint"
          @add-polygon-vertex="addPolygonVertex"
          @close-polygon="closePolygon"
        />
      </div>

      <div class="mt-3 flex items-center gap-3 text-[12px] text-ink-muted">
        <span>SAM 點：{{ samPoints.length }}</span>
        <span class="text-line-strong">|</span>
        <span>多邊形：{{ polygons.length }}（進行中 {{ currentPolygon.length }} 點）</span>
        <span class="text-line-strong">|</span>
        <span v-if="samMaskInflight" class="text-accent">
          <Loader2 :size="11" :stroke-width="1.5" class="inline animate-spin" />
          後端推論中 ...
        </span>
        <span v-else-if="maskUrl" class="text-state-success">已生成 mask</span>
      </div>
    </div>
  </Card>
</template>
