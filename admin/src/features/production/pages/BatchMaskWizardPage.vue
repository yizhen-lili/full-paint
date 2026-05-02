<script setup lang="ts">
/**
 * BatchMaskWizardPage — 批次多筆 sam_* 任務逐筆編輯遮罩。
 *
 * 路由：/admin/production/batches/:batchId/mask?step=N
 *
 * 規格依據：04c_production_sam.md §C 待確認 4。
 *
 * 流程：
 *   1. 進頁面 → fetch batch 內所有 sam_* + status=pending 的 jobs（依 created_at asc 排）
 *   2. 顯示步驟指示器「第 K / N 張遮罩」+ 進度條
 *   3. 中間步驟用「儲存並下一張」前進；最後一步換成「儲存並啟動全批」觸發 batch start
 *   4. 步驟導航 = router.replace?step=K 維持 URL 同步（重整不丟）
 *
 * UX 重用：MaskCanvas / MaskToolbar / useMaskActions composable / 鍵盤快捷鍵
 * 與 MaskEditPage 一致（V/P/Esc/Ctrl+Z/H/+/-/0）。
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { ChevronLeft, AlertTriangle, Loader2, ChevronRight, Check } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'

import MaskCanvas from '../components/MaskCanvas.vue'
import MaskToolbar, { type MaskTool } from '../components/MaskToolbar.vue'
import { useMaskActions } from '../composables/useMaskActions'
import { useStartBatchMutation } from '../queries'
import {
  getJob,
  getJobSignedUrl,
  listJobs,
  updateSamMask,
  type JobDetail,
  type SamPoint,
} from '../api'

const route = useRoute()
const router = useRouter()

const batchId = computed(() => String(route.params.batchId))
const stepFromQuery = computed(() => {
  const raw = route.query.step
  const n = typeof raw === 'string' ? parseInt(raw, 10) : 1
  return Number.isFinite(n) && n > 0 ? n : 1
})
const currentStep = ref<number>(stepFromQuery.value)

// step 跟著 query 變（瀏覽器前進後退）
watch(stepFromQuery, (s) => { currentStep.value = s })

// ── 拉 batch 內所有 sam_* + pending 的 jobs（依 created_at asc）─────────
const batchJobsQuery = useQuery({
  queryKey: computed(() => ['admin', 'production', 'batch-mask-wizard', batchId.value]),
  queryFn: async () => {
    const r = await listJobs({ batch_id: batchId.value, status: 'pending', page: 1, page_size: 100 })
    // 過濾 sam_* + asc 排序
    return r.items
      .filter((j) => j.mode === 'sam_refine' || j.mode === 'sam_weighted')
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
  },
})

const totalSteps = computed(() => batchJobsQuery.data.value?.length ?? 0)
const currentJob = computed(() =>
  batchJobsQuery.data.value?.[currentStep.value - 1] ?? null
)
const currentJobId = computed(() => currentJob.value?.id ?? null)
const samMode = computed<'sam_refine' | 'sam_weighted' | null>(() => {
  const m = currentJob.value?.mode
  if (m === 'sam_refine' || m === 'sam_weighted') return m
  return null
})
const isLastStep = computed(() => currentStep.value >= totalSteps.value && totalSteps.value > 0)

// ── 當前 job 詳細資料（取 sam_points / polygons / mask_url 既有狀態）──
const currentJobDetail = ref<JobDetail | null>(null)
const apiError = ref<string | null>(null)

// ── 編輯狀態 ────────────────────────────────────────────────────────
const tool = ref<MaskTool>('sam')
const actions = useMaskActions({ onChange: () => triggerSamMask() })
const {
  samPoints, polygons, currentPolygon, canUndo,
  addSamPoint, addPolygonVertex, closePolygon,
  deleteSamPoint, deletePolygon, undo, cancelCurrentPolygon, hydrate,
} = actions

const imageDisplayUrl = ref<string | null>(null)
const imageWidth = ref<number>(0)
const imageHeight = ref<number>(0)
const maskUrl = ref<string | null>(null)
const samMaskInflight = ref(false)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const canConfirm = computed(() => {
  return (
    samPoints.value.length > 0 ||
    polygons.value.length > 0 ||
    currentPolygon.value.length > 0
  )
})

// ── 切到新 step 時：重新載入 image / hydrate 既有 mask state ────────
async function loadCurrentJob() {
  const id = currentJobId.value
  if (!id) return
  apiError.value = null
  imageDisplayUrl.value = null
  imageWidth.value = 0
  imageHeight.value = 0
  maskUrl.value = null
  // reset editing state（每張獨立）
  actions.clearAll()
  // pop 掉 clearAll 自己推進的 record（這個 reset 不該佔 undo stack）
  actions.actionStack.value.pop()

  try {
    const job = await getJob(id)
    currentJobDetail.value = job
    // hydrate sam_points / polygons / mask_url（型別目前沒這些欄位 → 用 any patch）
    const anyJ = job as unknown as { sam_points?: SamPoint[]; polygons?: number[][][]; mask_url?: string | null }
    hydrate({ samPoints: anyJ.sam_points, polygons: anyJ.polygons })
    if (anyJ.mask_url) maskUrl.value = anyJ.mask_url

    // 載原圖 signed URL + 量寬高
    const resp = await getJobSignedUrl(id, 'image')
    if (!resp.url) throw new Error('無法取得原圖 signed URL')
    imageDisplayUrl.value = resp.url
    await loadImageDims(resp.url)
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '載入任務失敗'
  }
}

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

watch([currentJobId], () => {
  if (currentJobId.value) loadCurrentJob()
})

// ── debounced sam-mask（同 MaskEditPage）──────────────────────────
function triggerSamMask() {
  if (!samMode.value || !currentJobId.value) return
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(async () => {
    if (samPoints.value.length === 0 && polygons.value.length === 0) {
      maskUrl.value = null
      return
    }
    samMaskInflight.value = true
    try {
      const resp = await updateSamMask(currentJobId.value!, {
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

async function flushAndSaveCurrentMask(): Promise<boolean> {
  if (!currentJobId.value || !samMode.value) return true
  if (currentPolygon.value.length > 0) {
    if (currentPolygon.value.length >= 3) {
      closePolygon()
    } else {
      apiError.value = `進行中的多邊形只有 ${currentPolygon.value.length} 點（需 ≥ 3 才能閉合）。請先 Esc 取消或繼續加點。`
      return false
    }
  }
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  if (samPoints.value.length === 0 && polygons.value.length === 0) {
    return true   // 沒選任何東西也允許繼續
  }
  try {
    await updateSamMask(currentJobId.value, {
      sam_points: samPoints.value.length ? samPoints.value : undefined,
      polygons: polygons.value.length ? polygons.value : undefined,
      mode: samMode.value!,
    })
    return true
  } catch (e) {
    apiError.value = `儲存 mask 失敗：${(e as { message?: string }).message || ''}`
    return false
  }
}

// ── 步驟導航 ─────────────────────────────────────────────────────
async function goToStep(n: number) {
  router.replace({ query: { ...route.query, step: String(n) } })
}

async function saveAndNext() {
  const ok = await flushAndSaveCurrentMask()
  if (!ok) return
  await goToStep(currentStep.value + 1)
}

async function goPrev() {
  // 上一張不強制儲存（已有 debounced 自動送）；但 flush pending 進行中 polygon
  if (currentPolygon.value.length >= 3) closePolygon()
  if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null }
  await goToStep(Math.max(1, currentStep.value - 1))
}

// ── 啟動全批 ─────────────────────────────────────────────────────
const startBatchMut = useStartBatchMutation()
async function saveAndStartBatch() {
  const ok = await flushAndSaveCurrentMask()
  if (!ok) return
  try {
    const result = await startBatchMut.mutateAsync(batchId.value)
    if (result.skipped.length > 0) {
      apiError.value = `部分 job 未啟動：${result.skipped.map((s) => s.reason).join('、')}`
      return
    }
    router.push(`/admin/production?batch_id=${batchId.value}`)
  } catch (e) {
    apiError.value = `啟動批次失敗：${(e as { message?: string }).message || ''}`
  }
}

// ── 隱藏遮罩 ─────────────────────────────────────────────────────
const hideMaskToggle = ref(false)
const hideMaskHold = ref(false)
const hideMask = computed(() => hideMaskToggle.value || hideMaskHold.value)

// ── canvas zoom helper ─────────────────────────────────────────
const canvasRef = ref<InstanceType<typeof MaskCanvas> | null>(null)
function onZoomIn() { canvasRef.value?.zoomIn() }
function onZoomOut() { canvasRef.value?.zoomOut() }
function onResetView() { canvasRef.value?.resetView() }

// 切清除：不需要清 maskUrl（每張 step 切換時 loadCurrentJob 會 reset）
function clearAll() { actions.clearAll(); maskUrl.value = null }

// ── 鍵盤快捷鍵（與 MaskEditPage 一致）────────────────────────────
function isInputFocused(): boolean {
  const el = document.activeElement as HTMLElement | null
  if (!el) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || el.isContentEditable
}
function onKeyDown(e: KeyboardEvent) {
  if (isInputFocused()) return
  if ((e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault()
    if (canUndo.value) undo()
    return
  }
  if (e.key === 'Escape') {
    if (currentPolygon.value.length > 0) {
      e.preventDefault()
      cancelCurrentPolygon()
    }
    return
  }
  if (e.key === 'h' || e.key === 'H') { hideMaskHold.value = true; return }
  if (e.key === 'v' || e.key === 'V') { tool.value = 'sam'; return }
  if (e.key === 'p' || e.key === 'P') { tool.value = 'polygon'; return }
  if (e.key === '0' || e.key === '1') { onResetView(); return }
  if (e.key === '+' || e.key === '=') { onZoomIn(); return }
  if (e.key === '-' || e.key === '_') { onZoomOut(); return }
}
function onKeyUp(e: KeyboardEvent) {
  if (e.key === 'h' || e.key === 'H') hideMaskHold.value = false
}
onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('keyup', onKeyUp)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('keyup', onKeyUp)
})
</script>

<template>
  <div class="flex items-center gap-2 mb-3">
    <button
      type="button"
      class="text-[13px] text-ink-muted hover:text-ink-strong inline-flex items-center gap-1 transition-colors"
      @click="router.push('/admin/production')"
    >
      <ChevronLeft :size="14" :stroke-width="1.5" />
      返回任務列表
    </button>
  </div>

  <PageHeader
    title="批次遮罩編輯"
    :subtitle="`批次 #${batchId.slice(0, 8)}｜逐筆編輯 SAM 遮罩`"
  />

  <!-- 進度條 + 步驟指示 -->
  <div v-if="totalSteps > 0" class="mb-5">
    <div class="flex items-center justify-between mb-1.5 text-[13px]">
      <span class="text-ink-default font-medium">
        第 {{ currentStep }} / {{ totalSteps }} 張遮罩
        <span v-if="currentJob" class="ml-2 text-ink-muted text-[12px]">
          ({{ samMode === 'sam_refine' ? 'SAM 細化' : 'SAM 加權' }} · #{{ currentJob.id.slice(0, 8) }})
        </span>
      </span>
      <span class="text-[12px] text-ink-muted">
        {{ Math.round((currentStep / totalSteps) * 100) }}%
      </span>
    </div>
    <div class="h-1.5 bg-paper-subtle rounded-full overflow-hidden">
      <div
        class="h-full bg-accent transition-all duration-200"
        :style="{ width: `${(currentStep / totalSteps) * 100}%` }"
      />
    </div>
  </div>

  <div
    v-if="apiError"
    class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)] flex items-start gap-2"
  >
    <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5" />
    <span class="flex-1">{{ apiError }}</span>
    <button class="text-[12px] underline" @click="apiError = null">關閉</button>
  </div>

  <Card>
    <div v-if="batchJobsQuery.isLoading.value" class="text-center text-ink-muted py-12">
      <Loader2 :size="20" :stroke-width="1.5" class="inline animate-spin mr-2" />
      載入批次資料 ...
    </div>

    <div v-else-if="batchJobsQuery.error.value" class="text-center text-state-danger py-12">
      載入失敗：{{ (batchJobsQuery.error.value as { message?: string }).message }}
    </div>

    <div v-else-if="totalSteps === 0" class="text-center text-ink-muted py-12">
      此批次無待編輯的 SAM 任務（皆已啟動或無 sam_* mode job）。
    </div>

    <div v-else-if="!currentJob" class="text-center text-ink-muted py-12">
      step={{ currentStep }} 超出範圍（共 {{ totalSteps }} 張）
    </div>

    <div v-else>
      <MaskToolbar
        v-model:tool="tool"
        :hide-mask="hideMask"
        :has-mask="!!maskUrl"
        :can-undo="canUndo"
        :can-confirm="canConfirm"
        :is-locked="startBatchMut.isPending.value"
        @undo="undo"
        @clear="clearAll"
        @confirm="isLastStep ? saveAndStartBatch() : saveAndNext()"
        @zoom-in="onZoomIn"
        @zoom-out="onZoomOut"
        @reset-view="onResetView"
        @update:hide-mask="(v) => (hideMaskToggle = v)"
      />

      <div>
        <div v-if="!imageDisplayUrl || imageWidth === 0" class="text-ink-muted py-12 text-center">
          <Loader2 :size="20" :stroke-width="1.5" class="inline animate-spin mr-2" />
          載入圖片 ...
        </div>
        <MaskCanvas
          v-else
          ref="canvasRef"
          :image-url="imageDisplayUrl"
          :image-width="imageWidth"
          :image-height="imageHeight"
          :tool="tool"
          :sam-points="samPoints"
          :polygons="polygons"
          :current-polygon="currentPolygon"
          :mask-url="maskUrl"
          :is-locked="false"
          :hide-mask="hideMask"
          :inflight="samMaskInflight"
          @add-sam-point="addSamPoint"
          @add-polygon-vertex="addPolygonVertex"
          @close-polygon="closePolygon"
          @delete-sam-point="deleteSamPoint"
          @delete-polygon="deletePolygon"
        />
      </div>

      <div class="mt-3 flex items-center gap-3 text-[12px] text-ink-muted flex-wrap">
        <span>SAM 點：{{ samPoints.length }}</span>
        <span class="text-line-strong">|</span>
        <span>多邊形：{{ polygons.length }}（進行中 {{ currentPolygon.length }} 點）</span>
        <span class="text-line-strong">|</span>
        <span v-if="maskUrl" class="text-state-success">已生成 mask</span>
        <span v-else class="text-ink-muted/70">尚未生成 mask</span>
      </div>

      <!-- 步驟導航：上一張 / 下一張 / 啟動全批 -->
      <div class="mt-5 pt-4 border-t border-line-hairline flex items-center justify-between gap-2">
        <Button
          variant="secondary"
          :disabled="currentStep <= 1 || startBatchMut.isPending.value"
          @click="goPrev"
        >
          <ChevronLeft :size="14" :stroke-width="1.5" />
          上一張
        </Button>
        <span class="text-[12px] text-ink-muted">
          進行中可隨時關頁面，已點選的內容會自動儲存。
        </span>
        <Button
          v-if="!isLastStep"
          variant="primary"
          :disabled="startBatchMut.isPending.value"
          @click="saveAndNext"
        >
          儲存並下一張
          <ChevronRight :size="14" :stroke-width="1.5" />
        </Button>
        <Button
          v-else
          variant="primary"
          :disabled="startBatchMut.isPending.value"
          @click="saveAndStartBatch"
        >
          <Loader2 v-if="startBatchMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
          <Check v-else :size="14" :stroke-width="1.5" />
          儲存並啟動全批
        </Button>
      </div>
    </div>
  </Card>
</template>
