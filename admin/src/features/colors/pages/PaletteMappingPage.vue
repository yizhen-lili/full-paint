<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQueryClient } from '@tanstack/vue-query'
import {
  ChevronLeft,
  ChevronDown,
  Loader2,
  CheckCircle2,
  Copy,
  AlertTriangle,
  Archive,
  FileImage,
  Sparkles,
  Pipette,
  Wrench,
} from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'

import {
  PM_KEYS,
  useCompleteMappingsMutation,
  useConfirmPendingMergesMutation,
  useCopyMappingsMutation,
  usePaletteMappingsQuery,
  useRejectPendingMergesMutation,
  useUpdateMappingMutation,
} from '../queries_mapping'
import { useRevertRgbMutation, useUpdateRgbMutation } from '../queries'
import { rgbToHex, type PhysicalColor } from '../api'
import type { PaletteMapping } from '../api_mapping'

import PhysicalColorPickerDialog from '../components/PhysicalColorPickerDialog.vue'
import CopyMappingsDialog from '../components/CopyMappingsDialog.vue'
import PalettePreviewCanvas from '../components/PalettePreviewCanvas.vue'
import RgbCalibrationDialog from '../components/RgbCalibrationDialog.vue'

import { PJ_KEYS, useBatchPostProcessMutation, useJobQuery } from '@/features/production/queries'
import { getJobSignedUrl, type BatchOperation } from '@/features/production/api'
import PostProcessPanel from '@/features/production/components/PostProcessPanel.vue'

const route = useRoute()
const router = useRouter()

const jobId = computed(() => (typeof route.params.jobId === 'string' ? route.params.jobId : ''))

const { data, isLoading, isError, error } = usePaletteMappingsQuery(jobId)
const updateMut = useUpdateMappingMutation(jobId.value)
const copyMut = useCopyMappingsMutation(jobId.value)
const completeMut = useCompleteMappingsMutation(jobId.value)
const confirmMergesMut = useConfirmPendingMergesMutation(jobId.value)
const rejectMergesMut = useRejectPendingMergesMutation(jobId.value)

async function confirmAutoMerges() {
  apiError.value = null
  try {
    await confirmMergesMut.mutateAsync()
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '確認合併失敗'
  }
}

async function rejectAutoMerges() {
  apiError.value = null
  try {
    await rejectMergesMut.mutateAsync()
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '拒絕合併失敗'
  }
}

// 自動合併建議按 tiny_template_id 分組（每個 template 可能有 N 個 polygon 各別合併）
interface MergeGroup {
  tiny_template_id: number
  count: number
  total_area: number
  // 每個 target 各有幾個 polygon 指向；按 polygon 數降序
  targets: { tid: number; count: number }[]
  dominant_target: number
  has_polygon_id: boolean   // 舊資料缺 polygon_id → 提示 admin 重按完成對應
}

const groupedMerges = computed<MergeGroup[]>(() => {
  const map = new Map<number, {
    count: number
    total_area: number
    targets: Map<number, number>
    has_polygon_id: boolean
  }>()
  for (const m of jobData.value?.pending_auto_merges ?? []) {
    const e = map.get(m.tiny_template_id) ?? {
      count: 0, total_area: 0, targets: new Map(), has_polygon_id: false,
    }
    e.count++
    e.total_area += m.tiny_area
    e.targets.set(
      m.target_template_id,
      (e.targets.get(m.target_template_id) ?? 0) + 1,
    )
    if (m.polygon_id) e.has_polygon_id = true
    map.set(m.tiny_template_id, e)
  }
  return Array.from(map.entries())
    .map(([tid, e]) => {
      const targets = Array.from(e.targets.entries())
        .map(([t, c]) => ({ tid: t, count: c }))
        .sort((a, b) => b.count - a.count)
      return {
        tiny_template_id: tid,
        count: e.count,
        total_area: e.total_area,
        targets,
        dominant_target: targets[0]?.tid ?? -1,
        has_polygon_id: e.has_polygon_id,
      }
    })
    .sort((a, b) => b.count - a.count)
})

const hasLegacyPendingData = computed(() =>
  groupedMerges.value.length > 0
    && groupedMerges.value.some((g) => !g.has_polygon_id),
)

const mappings = computed(() => data.value?.mappings ?? [])

// 抓 job 細節給 canvas 預覽 + finalize 後的最終模板 preview 用
const { data: jobData } = useJobQuery(jobId)

// finalize 之後若又做過 post-process（按「更新模板」），filled_template_final_url
// 是舊模板的快照，admin 看到會誤以為自己沒更新成功。判斷方式：post-process 完成
// 時間 > finalize 時間 → final 過期 → 改顯示算法量化版 filled_template_url（新模板）
const isFinalStale = computed<boolean>(() => {
  const finAt = jobData.value?.finalized_at
  const ppAt = jobData.value?.post_processed_at
  if (!finAt) return false      // 從未 finalize → 沒 stale 問題
  if (!ppAt) return false       // 從未 post-process → final 仍 fresh
  return new Date(ppAt) > new Date(finAt)
})

// post-finalize 優先顯示「實體色版」(filled_template_final.png：同色合併、實物色 RGB)
// 但 final 過期時（post-process 比 finalize 新）必須顯示新算法版，避免 admin 看舊圖
// fallback 到演算法版 filled_template_url（未 finalize / 生成失敗時）
const filledTemplateUrl = computed(() => {
  if (isFinalStale.value) {
    return jobData.value?.filled_template_url ?? null
  }
  return jobData.value?.filled_template_final_url
    ?? jobData.value?.filled_template_url
    ?? null
})

// finalize 後合併編號 (output_label) 的「不重複數量」— 給 helper text 顯示「1 ~ N 號」
const uniqueOutputLabelCount = computed<number>(() => {
  const labels = new Set<number>()
  for (const m of mappings.value) {
    if (m.output_label != null) labels.add(m.output_label)
  }
  return labels.size
})

function onCanvasPick(templateId: number) {
  const m = mappings.value.find((x) => x.template_id === templateId)
  if (m) openPicker(m)
}

const apiError = ref<string | null>(null)
const completeResult = ref<{
  all_stocked: boolean
  shortage_colors: { template_id: number; physical_color_id: string; code: string; name: string }[]
} | null>(null)

// ── Picker dialog ─────────────────────────────────────────────────────
const pickerOpen = ref(false)
const pickerMapping = ref<PaletteMapping | null>(null)

function openPicker(m: PaletteMapping) {
  pickerMapping.value = m
  pickerOpen.value = true
}

async function onPickPhysicalColor(physicalColorId: string) {
  if (!pickerMapping.value) return
  apiError.value = null
  try {
    await updateMut.mutateAsync({
      templateId: pickerMapping.value.template_id,
      physicalColorId,
    })
    pickerOpen.value = false
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '更新對應失敗'
  }
}

// ── RGB 校正 dialog（內嵌，免跳轉「實體色管理」頁面）─────────────────────
// 在對應 row 或 picker 內任一色項點 Pipette icon 都進這裡。
// 校正成功後依賴 useUpdateRgbMutation invalidate COL_KEYS.all → mappings query
// 自動 refetch，使用該實體色的所有 row（含 picker 內）色票同步刷新。
const rgbDialogOpen = ref(false)
const rgbDialogColor = ref<PhysicalColor | null>(null)
const updateRgbMut = useUpdateRgbMutation()
const revertRgbMut = useRevertRgbMutation()

function openRgbDialog(color: PhysicalColor) {
  rgbDialogColor.value = color
  rgbDialogOpen.value = true
}

const qc = useQueryClient()

// 校正成功後額外 invalidate 本頁的 palette-mappings query
// （useUpdateRgbMutation 預設只 invalidate ['admin','colors']，跟 mappings 的
//  ['admin','palette-mappings',jobId] 不同 prefix → 不會自動 refetch）
function refreshMappings() {
  if (jobId.value) qc.invalidateQueries({ queryKey: PM_KEYS.mappings(jobId.value) })
}

async function onSaveRgb(hex: string) {
  if (!rgbDialogColor.value) return
  apiError.value = null
  try {
    await updateRgbMut.mutateAsync({ id: rgbDialogColor.value.id, payload: { hex } })
    refreshMappings()
  } catch (e) {
    apiError.value = (e as { message?: string }).message || 'RGB 校正失敗'
  }
}

async function onRevertRgb(history_id: string) {
  if (!rgbDialogColor.value) return
  apiError.value = null
  try {
    await revertRgbMut.mutateAsync({ id: rgbDialogColor.value.id, history_id })
    refreshMappings()
  } catch (e) {
    apiError.value = (e as { message?: string }).message || 'RGB 還原失敗'
  }
}

// ── Copy dialog ───────────────────────────────────────────────────────
const copyOpen = ref(false)

async function onConfirmCopy(sourceJobId: string) {
  apiError.value = null
  try {
    await copyMut.mutateAsync(sourceJobId)
    copyOpen.value = false
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '複製失敗'
  }
}

// ── Complete ──────────────────────────────────────────────────────────
const allMapped = computed(
  () => mappings.value.length > 0 && mappings.value.every((m) => m.physical_color),
)

// finalize 改 Celery 背景跑：完成對應回來時 template_final.svg 還沒產好，
// 且 job status 維持 completed（不會觸發既有的 pending/processing 輪詢），
// 所以這裡自己輪詢 job 直到 finalized_at 更新成新值（或逾時）。
const finalizing = ref(false)
let finalizeTimer: ReturnType<typeof setInterval> | null = null

function stopFinalizePoll() {
  if (finalizeTimer) {
    clearInterval(finalizeTimer)
    finalizeTimer = null
  }
  finalizing.value = false
}

function pollFinalize(prevFinalizedAt: string | null) {
  stopFinalizePoll()
  finalizing.value = true
  const started = Date.now()
  finalizeTimer = setInterval(() => {
    const finAt = jobData.value?.finalized_at ?? null
    const done = !!finAt && finAt !== prevFinalizedAt
    if (done || Date.now() - started > 120_000) {
      stopFinalizePoll()
      return
    }
    qc.invalidateQueries({ queryKey: PJ_KEYS.detail(jobId.value) })
  }, 4000)
}

async function complete() {
  apiError.value = null
  completeResult.value = null
  const prevFinalizedAt = jobData.value?.finalized_at ?? null
  try {
    const r = await completeMut.mutateAsync()
    completeResult.value = r
    pollFinalize(prevFinalizedAt)
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '完成對應失敗'
  }
}

onUnmounted(stopFinalizePoll)

// 「stale finalize」偵測：曾 finalize 過（有 template_final_url）但 mapping 後來
// 變動使 backend 清掉 finalized_at → 即時 banner 提示 admin 重按完成對應
const isFinalizeStale = computed(
  () => !!jobData.value
    && !!jobData.value.template_final_url
    && jobData.value.finalized_at === null,
)

// 「實體色版最終模板」內聯預覽收合（finalize 完成後才出現）
const finalSvgExpanded = ref(false)

function fmtDateTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ── 模板格子調整（合併色塊 / 消邊界）────────────────────────────────────
// 整合 PostProcessPanel：admin 不必跳回 production detail 即可微調模板，
// Celery 完成後 jobQuery 自動刷新 → mappings query 同步 invalidate。
const postProcessExpanded = ref(false)
const batchPostProcessMut = useBatchPostProcessMutation(jobId.value)
const svgUrl = ref<string | null>(null)
const svgUrlLoading = ref(false)

async function fetchSvgUrl() {
  if (!jobId.value || !jobData.value || jobData.value.status !== 'completed') return
  svgUrlLoading.value = true
  try {
    const r = await getJobSignedUrl(jobId.value, 'svg')
    svgUrl.value = r.url
  } catch {
    svgUrl.value = null
  } finally {
    svgUrlLoading.value = false
  }
}

// PostProcessPanel「手動重抓」用 — 比 fetchSvgUrl 更徹底：
//   1. invalidate jobData 強制 refetch（更新 post_processed_at 等時間戳）
//   2. invalidate palette-mappings 強制 refetch
//   3. 再呼叫 fetchSvgUrl 拿最新 signed URL
// 等 jobData refetch 完，watch(post_processed_at) 也會被觸發、做為 backup。
async function forceRefreshSvg() {
  if (!jobId.value) return
  await qc.invalidateQueries({ queryKey: PJ_KEYS.detail(jobId.value) })
  qc.invalidateQueries({ queryKey: PM_KEYS.mappings(jobId.value) })
  await fetchSvgUrl()
}

// 進入頁面 / status 變回 completed（post-process 跑完）→ 重抓新 SVG signed URL
watch(
  () => jobData.value?.status,
  (s, prev) => {
    if (s === 'completed') {
      fetchSvgUrl()
      // 從 processing 變回 completed = Celery 完成；mapping query 也需 refresh
      // （post-process 重產 palette/svg → 部分 template_id 可能被合併消失）
      if (prev === 'processing' && jobId.value) {
        qc.invalidateQueries({ queryKey: PM_KEYS.mappings(jobId.value) })
      }
    }
  },
  { immediate: true },
)

// 保險：每次 post_processed_at 變動（必然有新值）→ 重抓 SVG + invalidate mappings
// 既有 status watch 可能因 polling 太快、completed→processing→completed 中間時刻
// 被 skip 而漏 fire；改用時間戳更可靠。
watch(
  () => jobData.value?.post_processed_at,
  (newVal, oldVal) => {
    if (newVal && newVal !== oldVal && jobData.value?.status === 'completed') {
      fetchSvgUrl()
      if (jobId.value) {
        qc.invalidateQueries({ queryKey: PM_KEYS.mappings(jobId.value) })
      }
    }
  },
)

async function onPostProcessSubmit(operations: BatchOperation[]) {
  apiError.value = null
  try {
    await batchPostProcessMut.mutateAsync({ operations })
    postProcessExpanded.value = false  // 送出後自動收合，admin 等 Celery 完成
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '模板調整送出失敗'
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
      返回製作詳情
    </button>
  </div>

  <header class="mb-7 pb-5 border-b border-line-hairline flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
    <div>
      <h1 class="font-display text-ink-strong text-[24px] leading-[32px]">
        顏色對應工作台
        <span class="ml-2 font-mono text-[18px] text-ink-muted">#{{ jobId.slice(0, 8) }}</span>
      </h1>
      <p class="mt-1 text-[13px] text-ink-muted">
        把演算法產出的調色盤對應到實體色（60 色色盤）
      </p>
    </div>
    <div class="flex flex-wrap items-center gap-2 shrink-0">
      <Button variant="secondary" @click="copyOpen = true">
        <Copy :size="14" :stroke-width="1.5" />
        從其他 job 複製
      </Button>
      <Button
        variant="primary"
        :disabled="completeMut.isPending.value || !allMapped"
        @click="complete"
      >
        <Loader2 v-if="completeMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
        <CheckCircle2 v-else :size="14" :stroke-width="1.5" />
        完成對應（{{ mappings.filter((m) => m.physical_color).length }} / {{ mappings.length }}）
      </Button>
    </div>
  </header>

  <div
    v-if="apiError"
    class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)] flex items-start gap-2"
  >
    <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5" />
    <span class="flex-1">{{ apiError }}</span>
    <button class="text-[12px] underline" @click="apiError = null">關閉</button>
  </div>

  <!-- stale finalize 提示：曾 finalize 過、但 mapping 已變動 -->
  <div
    v-if="isFinalizeStale"
    class="mb-5 p-4 border border-state-warning/40 bg-[var(--color-state-warning)]/[0.06]
           text-state-warning text-[13px] rounded-[var(--radius-xs)]
           flex items-start gap-2"
  >
    <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5 shrink-0" />
    <div class="flex-1">
      <p class="font-medium mb-0.5">最終模板已過期</p>
      <p class="text-state-warning/80 leading-[1.5]">
        你修改了顏色對應，但「最終模板」（template_final.svg）與色號編號
        尚未更新到最新狀態。請按頁面右上方的「完成對應」重新產出 —
        系統會重新計算用量、重排色號、覆蓋最終模板檔。
      </p>
    </div>
  </div>

  <div
    v-if="completeResult"
    class="mb-5 p-4 border rounded-[var(--radius-xs)]"
    :class="
      completeResult.all_stocked
        ? 'border-state-success/40 bg-[var(--color-state-success)]/[0.06] text-state-success'
        : 'border-state-warning/40 bg-[var(--color-state-warning)]/[0.06] text-state-warning'
    "
  >
    <p v-if="completeResult.all_stocked" class="text-[13px] flex items-center gap-2">
      <CheckCircle2 :size="14" :stroke-width="1.5" />
      <span>對應完成、所有顏色庫存充足，可進入商品上架流程。</span>
    </p>
    <div v-else>
      <p class="text-[13px] flex items-center gap-2">
        <AlertTriangle :size="14" :stroke-width="1.5" />
        <span>
          對應完成，但 {{ completeResult.shortage_colors.length }} 色庫存不足。
          商品可上架，前台會顯示「預購」狀態。詳細缺料色號請至「顏料準備清單」查詢。
        </span>
      </p>
    </div>
    <!-- finalize 背景產生中（密集模板數十秒）：產好後自動換成下方連結 -->
    <p
      v-if="finalizing && !jobData?.template_final_url"
      class="mt-3 pt-3 border-t border-current/20 text-[12px] flex items-center gap-2"
    >
      <Loader2 :size="12" :stroke-width="1.5" class="animate-spin" />
      實體色版最終模板產生中…（密集模板需數十秒，產好會自動出現連結）
    </p>
    <!-- finalize 完成後給 admin 看最終模板的連結 -->
    <p
      v-if="jobData?.template_final_url"
      class="mt-3 pt-3 border-t border-current/20 text-[12px] flex items-center gap-2"
    >
      <CheckCircle2 :size="12" :stroke-width="1.5" />
      已產出「實體色版最終模板」（重編號 + PDF 含色號對照表）：
      <a
        :href="jobData.template_final_url"
        target="_blank"
        rel="noopener"
        class="underline font-medium"
      >查看 SVG</a>
    </p>
  </div>

  <div v-if="isLoading" class="py-20 flex justify-center text-ink-muted">
    <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
  </div>

  <div
    v-else-if="isError"
    class="px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)]"
  >
    載入失敗：{{ (error as { message?: string })?.message ?? '未知錯誤' }}
  </div>

  <Card v-else-if="mappings.length === 0" class="text-center py-12">
    <Sparkles :size="32" :stroke-width="1.25" class="mx-auto mb-3 text-aux-rice-mid" />
    <p class="text-[13px] text-ink-muted">此 job 尚無調色盤資料（製作未完成？）</p>
  </Card>

  <template v-else>
    <!-- 模板更新後實體色版過期警告：admin 在 finalize 之後又做 post-process，
         目前 canvas 顯示的是新算法版（最新模板），但實體色版還是舊模板的 → 提醒重新 finalize -->
    <div
      v-if="isFinalStale"
      class="mb-4 rounded-md border border-aux-rice-mid bg-aux-rice-light/40 p-3 text-[13px] text-ink-strong"
    >
      ⚠️ 模板已重新製作，目前顯示的是「演算法量化版」（最新模板）。
      原本的實體色版已不對應新模板，請按下方「完成顏色對應」重新 finalize 取得新的實體色版。
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
    <!-- 左：canvas 預覽 -->
    <Card>
      <h2 class="font-display text-ink-strong text-[18px] leading-[26px] mb-1">即時預覽</h2>
      <p class="text-[11px] text-ink-muted mb-3 leading-relaxed">
        填色預覽 — finalize 完顯示「實體色版」（同色合併），未 finalize 或模板剛更新顯示「演算法量化版」。
      </p>
      <PalettePreviewCanvas
        :image-url="filledTemplateUrl"
        :mappings="mappings"
        @pick-template="onCanvasPick"
      />
    </Card>

    <!-- 右：調色盤對應表 -->
    <Card>
      <h2 class="font-display text-ink-strong text-[18px] leading-[26px] mb-4">
        調色盤
        <span class="ml-2 text-[12px] text-ink-muted font-sans">{{ mappings.length }} 色</span>
      </h2>
      <div class="space-y-2 max-h-[600px] overflow-y-auto">
        <div
          v-for="m in mappings"
          :key="m.template_id"
          class="p-3 border border-line-hairline rounded-[var(--radius-xs)] flex items-center gap-3 cursor-pointer hover:bg-paper-subtle transition-colors"
          @click="openPicker(m)"
        >
          <div class="text-center shrink-0">
            <div
              class="w-10 h-10 rounded-[var(--radius-xs)] border border-line-hairline"
              :style="{ backgroundColor: rgbToHex(m.algorithm_rgb) }"
            />
            <p class="mt-1 text-[10px] text-ink-muted">#{{ m.template_id }}</p>
          </div>

          <span class="text-ink-muted text-[12px] shrink-0">→</span>

          <div v-if="m.physical_color" class="flex-1 min-w-0 flex items-center gap-2">
            <div
              class="w-10 h-10 rounded-[var(--radius-xs)] border border-line-hairline shrink-0"
              :style="{ backgroundColor: rgbToHex(m.physical_color.rgb) }"
            />
            <div class="flex-1 min-w-0">
              <p class="text-[12px] font-mono text-ink-strong flex items-center gap-1.5 flex-wrap">
                <span>{{ m.physical_color.code }}</span>
                <!-- 對應完成後的「實體色版編號」（多個 template 對到同色 → 同 label） -->
                <span
                  v-if="m.output_label != null"
                  class="inline-flex items-center px-1.5 h-[16px] text-[10px] tracking-[0.04em] rounded-[var(--radius-xs)] bg-accent/[0.12] text-accent"
                  title="塗色模板上顯示的編號（已 finalize）"
                >模板 #{{ m.output_label }}</span>
                <span
                  v-if="m.mapped_by === 'system'"
                  class="text-[10px] text-ink-muted"
                >（自動）</span>
              </p>
              <p class="text-[12px] text-ink-default truncate">{{ m.physical_color.name }}</p>
              <p class="text-[10px]" :class="m.physical_color.stock_ml === 0 ? 'text-state-danger' : 'text-ink-muted'">
                庫存 {{ m.physical_color.stock_ml }} ml
                <span v-if="m.required_ml"> · 需 {{ m.required_ml }} ml</span>
              </p>
            </div>
            <!-- RGB 校正：免跳「實體色管理」頁也能即時改 -->
            <button
              type="button"
              class="shrink-0 p-1.5 rounded-[var(--radius-xs)] hover:bg-paper-subtle text-ink-muted hover:text-ink-strong transition-colors"
              title="校正此實體色 RGB"
              @click.stop="openRgbDialog(m.physical_color!)"
            >
              <Pipette :size="14" :stroke-width="1.5" />
            </button>
          </div>
          <div v-else class="flex-1 text-[12px] text-state-warning">尚未對應</div>
        </div>
      </div>
    </Card>
    </div>
  </template>

  <!-- 實體色版最終模板（finalize 後才出現；點開內聯看合併編號 + 物理色填色）-->
  <section
    v-if="jobData?.template_final_url"
    class="mt-6"
  >
    <button
      type="button"
      class="w-full flex items-center gap-2 px-4 py-3 border border-line-hairline rounded-[var(--radius-sm)] bg-paper-surface hover:bg-paper-subtle transition-colors"
      @click="finalSvgExpanded = !finalSvgExpanded"
    >
      <ChevronDown
        :size="16" :stroke-width="1.5"
        class="transition-transform text-ink-muted"
        :class="finalSvgExpanded ? '' : '-rotate-90'"
      />
      <FileImage :size="14" :stroke-width="1.5" class="text-ink-muted" />
      <h2 class="font-display text-ink-strong text-[16px] leading-[22px]">實體色版最終模板</h2>
      <span class="ml-auto text-[11px] text-ink-muted hidden sm:inline">
        同色合併、output_label 重編號 — finalize 完成後產出
      </span>
    </button>

    <p v-if="finalSvgExpanded" class="text-[12px] text-ink-muted px-1 mt-3 leading-relaxed">
      👤 這是 <strong class="text-ink-default">客戶印出來會看到的線圖</strong>。
      數字是「<strong class="text-ink-default">合併後的物理色編號</strong>」（共 {{ uniqueOutputLabelCount }} 號）—
      同一個物理色的所有區塊都標相同數字，方便客戶按色號上色。
      <br />
      跟下方「合併色塊 / 消除邊界線」面板顯示的<strong>演算法原始編號 template_id</strong>
      （數量會多很多）是不同概念。
    </p>

    <div
      v-if="finalSvgExpanded"
      class="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-4"
    >
      <!-- 左：原始版（第二次 finalize 起才有）-->
      <div class="space-y-2">
        <div class="flex items-center gap-2 px-1">
          <Archive :size="14" :stroke-width="1.5" class="text-ink-muted" />
          <h3 class="text-[14px] font-medium text-ink-strong">原始版</h3>
          <span
            v-if="jobData.original_finalized_at"
            class="text-[11px] text-ink-muted font-normal"
          >
            {{ fmtDateTime(jobData.original_finalized_at) }} 第一次完成對應
          </span>
        </div>

        <template v-if="jobData.original_template_final_url">
          <Card>
            <div class="flex items-center justify-between mb-2">
              <span class="text-[12px] text-ink-muted">線圖（output_label 合併編號 · 客戶印出來看到的）</span>
              <a
                :href="jobData.original_template_final_url"
                target="_blank" rel="noopener"
                class="text-[11px] text-accent hover:text-accent-hover underline"
              >另開分頁</a>
            </div>
            <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-auto flex items-center justify-center">
              <img
                :src="jobData.original_template_final_url"
                alt="原始版 template_final.svg"
                class="max-w-full max-h-full object-contain"
              />
            </div>
          </Card>
          <Card v-if="jobData.original_filled_template_final_url">
            <span class="text-[12px] text-ink-muted block mb-2">實體色填色預覽</span>
            <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-hidden flex items-center justify-center">
              <img
                :src="jobData.original_filled_template_final_url"
                alt="原始版 filled_template_final.png"
                class="max-w-full max-h-full object-contain"
              />
            </div>
          </Card>
        </template>
        <div
          v-else
          class="p-4 border border-dashed border-line-hairline rounded-[var(--radius-xs)] text-[12px] text-ink-muted leading-[1.6]"
        >
          目前還沒有原始版備份 — 這是這個任務第一次完成對應的結果。
          下次再按「完成對應」時，此處會自動保留現在的版本當「原始版」、新版顯示在右邊。
        </div>
      </div>

      <!-- 右：最新版 -->
      <div class="space-y-2">
        <div class="flex items-center gap-2 px-1">
          <Sparkles :size="14" :stroke-width="1.5" class="text-accent" />
          <h3 class="text-[14px] font-medium text-ink-strong">最新版</h3>
          <span
            v-if="jobData.finalized_at"
            class="text-[11px] text-ink-muted font-normal"
          >
            {{ fmtDateTime(jobData.finalized_at) }} 完成對應
          </span>
        </div>

        <Card>
          <div class="flex items-center justify-between mb-2">
            <span class="text-[12px] text-ink-muted">線圖（output_label 合併編號 · 客戶印出來看到的）</span>
            <a
              :href="jobData.template_final_url"
              target="_blank" rel="noopener"
              class="text-[11px] text-accent hover:text-accent-hover underline"
            >另開分頁</a>
          </div>
          <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-auto flex items-center justify-center">
            <img
              :src="jobData.template_final_url"
              alt="最新版 template_final.svg"
              class="max-w-full max-h-full object-contain"
            />
          </div>
        </Card>
        <Card v-if="jobData.filled_template_final_url">
          <span class="text-[12px] text-ink-muted block mb-2">實體色填色預覽</span>
          <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-hidden flex items-center justify-center">
            <img
              :src="jobData.filled_template_final_url"
              alt="最新版 filled_template_final.png"
              class="max-w-full max-h-full object-contain"
            />
          </div>
        </Card>
      </div>
    </div>
  </section>

  <!-- 自動合併建議（finalize 偵測到微小色塊建議合進相近鄰居；待 admin 確認）-->
  <section
    v-if="jobData?.pending_auto_merges?.length"
    class="mt-6"
  >
    <div class="p-4 border border-state-info/40 bg-state-info/[0.04] rounded-[var(--radius-sm)]">
      <div class="flex items-start gap-3">
        <Sparkles :size="18" :stroke-width="1.5" class="text-state-info mt-0.5 shrink-0" />
        <div class="flex-1 min-w-0">
          <h3 class="font-display text-ink-strong text-[15px] leading-[22px] mb-1">
            自動合併建議（{{ jobData.pending_auto_merges.length }} 個小色塊 · 涵蓋 {{ groupedMerges.length }} 個 template）
          </h3>
          <p class="text-[12px] text-ink-muted leading-[1.6]">
            系統偵測到一些太小、難以辨識色號的色塊。上方「最新版」模板<b>保留</b>所有原本色塊
            （即你看到的細緻版）；下方「合併後預覽」展示<b>若按下「確認合併」</b>之後會變成的樣子。
            <br />
            點「確認合併寫入 DB」會用 <b>per-polygon</b> 方式處理 —
            只把這些小色塊精準改成鄰居色，<b>不會動原 template 的大色塊</b>，
            並重 finalize 一次（會 archive 當前版為「原始版」）。
          </p>
          <div
            v-if="hasLegacyPendingData"
            class="mt-2 px-3 py-2 border border-state-warning/40 bg-[var(--color-state-warning)]/[0.06] text-state-warning text-[11px] rounded-[var(--radius-xs)] leading-[1.5]"
          >
            ⚠ 部分舊資料沒有 polygon_id 欄位（之前的 bug 版本產生的），無法精準
            per-polygon 合併。請按「放棄這次建議」清掉、再重按「完成對應」即可重新偵測。
          </div>

          <!-- 左右對比：當前未合併 vs 合併後預覽 -->
          <div
            v-if="jobData.template_final_merged_preview_url"
            class="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-3"
          >
            <div class="space-y-1">
              <div class="flex items-center gap-2 px-1">
                <Archive :size="13" :stroke-width="1.5" class="text-ink-muted" />
                <span class="text-[12px] font-medium text-ink-strong">目前模板（未套用建議）</span>
              </div>
              <Card class="!p-2">
                <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-auto flex items-center justify-center">
                  <img
                    :src="jobData.template_final_url"
                    alt="未合併 template_final.svg"
                    class="max-w-full max-h-full object-contain"
                  />
                </div>
                <p class="text-[10px] text-ink-muted mt-1.5 px-0.5 leading-[1.5]">
                  保留所有原色塊。按「放棄這次建議」可保持這個版本。
                </p>
              </Card>
            </div>
            <div class="space-y-1">
              <div class="flex items-center gap-2 px-1">
                <Sparkles :size="13" :stroke-width="1.5" class="text-accent" />
                <span class="text-[12px] font-medium text-ink-strong">合併後預覽（套用建議）</span>
              </div>
              <Card class="!p-2">
                <div class="aspect-square rounded-[var(--radius-xs)] border border-accent/40 bg-paper-canvas overflow-auto flex items-center justify-center">
                  <img
                    :src="jobData.template_final_merged_preview_url"
                    alt="合併版 template_final_merged_preview.svg"
                    class="max-w-full max-h-full object-contain"
                  />
                </div>
                <p class="text-[10px] text-ink-muted mt-1.5 px-0.5 leading-[1.5]">
                  小色塊已合進鄰居。按「確認合併」會把「最新版」變成這個樣子。
                </p>
              </Card>
            </div>
          </div>
          <ul class="mt-2 text-[12px] space-y-1 max-h-[200px] overflow-y-auto pr-1">
            <li
              v-for="g in groupedMerges"
              :key="g.tiny_template_id"
              class="text-ink-default leading-[1.5]"
            >
              • template <span class="font-mono">#{{ g.tiny_template_id }}</span>
              的 <span class="font-mono">{{ g.count }}</span> 個小色塊
              <span class="text-ink-muted">（總面積 {{ g.total_area.toFixed(1) }}）</span>
              → 主要合進到 <span class="font-mono">#{{ g.dominant_target }}</span>
              <span
                v-if="g.targets.length > 1"
                class="text-ink-muted"
              >
                （另含 {{ g.targets.slice(1).map((t) => `#${t.tid}(${t.count})`).join(', ') }}）
              </span>
            </li>
          </ul>
          <div class="mt-3 flex gap-2 flex-wrap">
            <Button
              variant="primary"
              :disabled="confirmMergesMut.isPending.value || rejectMergesMut.isPending.value || hasLegacyPendingData"
              @click="confirmAutoMerges"
            >
              <Loader2 v-if="confirmMergesMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
              <CheckCircle2 v-else :size="14" :stroke-width="1.5" />
              確認合併（per-polygon 精準改色）
            </Button>
            <Button
              variant="secondary"
              :disabled="confirmMergesMut.isPending.value || rejectMergesMut.isPending.value"
              @click="rejectAutoMerges"
            >
              <Loader2 v-if="rejectMergesMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
              放棄這次建議
            </Button>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- 模板格子調整（合併色塊 / 消邊界）-->
  <section
    v-if="mappings.length > 0"
    class="mt-6"
  >
    <button
      type="button"
      class="w-full flex items-center gap-2 px-4 py-3 border border-line-hairline rounded-[var(--radius-sm)] bg-paper-surface hover:bg-paper-subtle transition-colors"
      @click="postProcessExpanded = !postProcessExpanded"
    >
      <ChevronDown
        :size="16"
        :stroke-width="1.5"
        class="transition-transform text-ink-muted"
        :class="postProcessExpanded ? '' : '-rotate-90'"
      />
      <Wrench :size="14" :stroke-width="1.5" class="text-ink-muted" />
      <h2 class="font-display text-ink-strong text-[16px] leading-[22px]">模板格子調整</h2>
      <span class="ml-auto text-[11px] text-ink-muted hidden sm:inline">
        合併色塊 / 消邊界 — 微調後預覽與對應表會自動更新
      </span>
    </button>

    <div
      v-if="postProcessExpanded"
      class="mt-3 p-4 border border-line-hairline rounded-[var(--radius-sm)] bg-paper-surface"
    >
      <!-- 執行前警告 -->
      <div class="px-3 py-2 mb-3 border border-state-warning/40 bg-[var(--color-state-warning)]/[0.06] text-state-warning text-[12px] rounded-[var(--radius-xs)] flex items-start gap-2 leading-[1.5]">
        <AlertTriangle :size="12" :stroke-width="1.5" class="mt-0.5 shrink-0" />
        <span>
          模板格子調整會把 job 退回 processing 狀態、重新產出 SVG 與調色盤；
          原本已對應的色號可能因色塊合併而消失。
          建議完成後再檢查對應表一次。
        </span>
      </div>

      <!-- 處理中 banner -->
      <div
        v-if="jobData?.status === 'processing'"
        class="px-3 py-2 mb-3 border border-state-info/40 bg-[var(--color-state-info)]/[0.06] text-state-info text-[12px] rounded-[var(--radius-xs)] flex items-center gap-2"
      >
        <Loader2 :size="12" :stroke-width="1.5" class="animate-spin" />
        模板處理中（Celery）— 5-15 秒內完成，自動刷新預覽與對應表。
      </div>

      <!-- Job 不在 completed 狀態 → 不能編輯 -->
      <div
        v-if="jobData && jobData.status !== 'completed'"
        class="p-3 text-[12px] text-ink-muted bg-paper-subtle rounded-[var(--radius-xs)]"
      >
        Job 當前狀態為 <span class="font-mono">{{ jobData.status }}</span>，僅 completed 狀態可調整模板。
      </div>

      <!-- SVG 簽章 URL 載入中 -->
      <div
        v-else-if="svgUrlLoading"
        class="py-6 flex items-center justify-center text-ink-muted"
      >
        <Loader2 :size="16" :stroke-width="1.5" class="animate-spin" />
      </div>

      <!-- Panel -->
      <PostProcessPanel
        v-else-if="jobData && svgUrl"
        :palette="jobData.palette_json ?? []"
        :svg-url="svgUrl"
        :pending="batchPostProcessMut.isPending.value"
        :type-filter="null"
        :last-updated-at="jobData.post_processed_at ?? jobData.created_at"
        :has-post-processed="!!jobData.post_processed_at"
        @confirm-batch="onPostProcessSubmit"
        @refresh="forceRefreshSvg"
      />
    </div>
  </section>

  <!-- Dialogs -->
  <PhysicalColorPickerDialog
    v-if="pickerMapping"
    :open="pickerOpen"
    :algorithm-rgb="pickerMapping.algorithm_rgb"
    :current-id="pickerMapping.physical_color?.id ?? null"
    @close="pickerOpen = false"
    @pick="onPickPhysicalColor"
    @calibrate="openRgbDialog"
  />

  <CopyMappingsDialog
    :open="copyOpen"
    :job-id="jobId"
    :pending="copyMut.isPending.value"
    @close="copyOpen = false"
    @confirm="onConfirmCopy"
  />

  <RgbCalibrationDialog
    :open="rgbDialogOpen"
    :color="rgbDialogColor"
    :pending="updateRgbMut.isPending.value || revertRgbMut.isPending.value"
    @close="rgbDialogOpen = false"
    @save-rgb="onSaveRgb"
    @revert="onRevertRgb"
  />
</template>
