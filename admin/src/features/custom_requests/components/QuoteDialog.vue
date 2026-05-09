<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Textarea from '@/shared/ui/Textarea.vue'
import Select from '@/shared/ui/Select.vue'
import { Loader2, Eye, ChevronLeft, ImageOff, AlertTriangle, Check } from 'lucide-vue-next'

import {
  useCustomPhotoPricesQuery,
  useCustomPhotoSurchargesQuery,
} from '../queries'
import type { CustomRequestDetail, Detail, Difficulty, QuotePayload } from '../api'
import { listJobs, getJobSignedUrl, type JobListItem } from '@/features/production/api'

const props = defineProps<{
  open: boolean
  request: CustomRequestDetail
  pending: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: [payload: QuotePayload]
}>()

const detail = ref<Detail>('standard')
// admin 必選一個 completed job 作為報價基準；selectedJob 的 canvas / difficulty / detail
// 自動帶到下方試算欄位（client 可後再覆蓋）。報價提交會帶 production_job_id 到後端，
// 客戶看到的預覽圖、最終規格 = 該 job。
const selectedJobId = ref<string | null>(null)
const priceCanvasW = ref<number | null>(null)
const priceCanvasH = ref<number | null>(null)
const priceDifficulty = ref<Difficulty>('intermediate')
const surchargeIds = ref<Set<string>>(new Set())
const overrideStr = ref('')
const note = ref('')
const errors = ref<Record<string, string>>({})

// 兩步驟：1=填寫報價、2=預覽客戶會看到的內容（確認後才真的送出）
const step = ref<1 | 2>(1)
const previewImageError = ref(false)
const previewImageLoading = ref(false)

const { data: prices, isLoading: pricesLoading } = useCustomPhotoPricesQuery()
const { data: surcharges, isLoading: surLoading } = useCustomPhotoSurchargesQuery()

// 拉這個 custom_request 的 production_jobs（只列 completed 給選）
const jobsQuery = useQuery({
  queryKey: computed(() => ['custom-jobs', props.request.id]),
  queryFn: () =>
    listJobs({ custom_request_id: props.request.id, page_size: 50 }),
  enabled: computed(() => props.open),
  staleTime: 10_000,
})
const completedJobs = computed<JobListItem[]>(() =>
  (jobsQuery.data.value?.items ?? []).filter((j) => j.status === 'completed'),
)
const selectedJob = computed(() =>
  completedJobs.value.find((j) => j.id === selectedJobId.value),
)

// 批次 fetch jobs 的 filled signed URL（每張縮圖 15 分鐘有效；同一個 job 不重複拿）
const jobThumbnails = ref<Map<string, string>>(new Map())
watch(
  completedJobs,
  async (jobs) => {
    const tasks = jobs
      .filter((j) => !jobThumbnails.value.has(j.id))
      .map(async (j) => {
        try {
          const r = await getJobSignedUrl(j.id, 'filled')
          if (r.url) jobThumbnails.value.set(j.id, r.url)
        } catch (_e) {
          // 忽略單張失敗（顯示 fallback icon）
        }
      })
    await Promise.all(tasks)
    // 觸發 reactivity（Map 不是 reactive proxy，用 trigger 重設）
    jobThumbnails.value = new Map(jobThumbnails.value)
  },
  { immediate: true },
)

// 從 prices 表推所有可選的 canvas 尺寸（去重）
const availableCanvasSizes = computed(() => {
  if (!prices.value) return [] as Array<{ w: number; h: number; label: string }>
  const seen = new Set<string>()
  const out: Array<{ w: number; h: number; label: string }> = []
  for (const p of prices.value.items) {
    const key = `${p.canvas_w}x${p.canvas_h}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push({ w: p.canvas_w, h: p.canvas_h, label: `${p.canvas_w} × ${p.canvas_h} cm` })
  }
  return out.sort((a, b) => a.w * a.h - b.w * b.h)
})
const canvasSizeOptions = computed(() =>
  availableCanvasSizes.value.map((s) => ({ value: `${s.w}x${s.h}`, label: s.label })),
)
const priceCanvasKey = computed({
  get: () => (priceCanvasW.value && priceCanvasH.value
    ? `${priceCanvasW.value}x${priceCanvasH.value}` : ''),
  set: (v: string) => {
    const [w, h] = v.split('x').map(Number)
    priceCanvasW.value = w || null
    priceCanvasH.value = h || null
  },
})

const difficultyOptions: Array<{ value: Difficulty; label: string }> = [
  { value: 'beginner', label: '入門 beginner' },
  { value: 'elementary', label: '初級 elementary' },
  { value: 'intermediate', label: '中級 intermediate' },
  { value: 'advanced', label: '進階 advanced' },
]

watch(
  () => props.open,
  (v) => {
    if (v) {
      detail.value = (props.request.detail as Detail) || 'standard'
      selectedJobId.value = null  // 等 completedJobs 載入後 watcher 會自動選最佳
      // 預設帶客戶填的；客戶 null 則用合理 default（之後選 job 會覆蓋）
      priceCanvasW.value = props.request.canvas_w_cm ?? 30
      priceCanvasH.value = props.request.canvas_h_cm ?? 40
      priceDifficulty.value = (props.request.difficulty as Difficulty) ?? 'intermediate'
      surchargeIds.value = new Set()
      overrideStr.value = ''
      note.value = ''
      errors.value = {}
      step.value = 1
      previewImageError.value = false
    }
  },
)

// jobs 載入完後，預設選一個：優先 approved 中最新一筆，否則最新一筆 completed
watch(
  completedJobs,
  (jobs) => {
    if (selectedJobId.value || jobs.length === 0) return
    const approved = jobs.find((j) => j.approved)
    selectedJobId.value = approved?.id ?? jobs[0].id
  },
)

// 選了 job → 用 job 的規格覆蓋試算欄位
watch(
  selectedJob,
  (job) => {
    if (!job) return
    if (job.canvas_w_cm) priceCanvasW.value = Number(job.canvas_w_cm)
    if (job.canvas_h_cm) priceCanvasH.value = Number(job.canvas_h_cm)
    if (job.difficulty) priceDifficulty.value = job.difficulty as Difficulty
    if (job.detail) detail.value = job.detail as Detail
  },
)

const PRICE_MULTIPLIER = 2.0

const basePrice = computed(() => {
  if (!prices.value || !priceCanvasW.value || !priceCanvasH.value) return null
  const match = prices.value.items.find(
    (p) =>
      p.canvas_w === priceCanvasW.value &&
      p.canvas_h === priceCanvasH.value &&
      p.difficulty === priceDifficulty.value,
  )
  return match ? Number(match.price) : null
})

const customerSpecsHint = computed(() => {
  const r = props.request
  const cv = r.canvas_w_cm ? `${r.canvas_w_cm}×${r.canvas_h_cm}cm` : '讓我們建議'
  const df = r.difficulty || '讓我們建議'
  return `客戶填：畫布 ${cv}、難易度 ${df}`
})

// 試算規格是否還是「所選 job 帶過來的」(true) 還是 admin 又手動改了 (false)
const usingJobSpec = computed(() => {
  const j = selectedJob.value
  if (!j) return false
  return (
    Number(j.canvas_w_cm) === priceCanvasW.value
    && Number(j.canvas_h_cm) === priceCanvasH.value
    && j.difficulty === priceDifficulty.value
  )
})

const activeSurcharges = computed(() => surcharges.value?.items.filter((s) => s.is_active) ?? [])

const surchargeTotal = computed(() => {
  let sum = 0
  for (const s of activeSurcharges.value) {
    if (surchargeIds.value.has(s.id)) sum += Number(s.amount)
  }
  return sum
})

const suggestedPrice = computed(() => {
  if (basePrice.value == null) return null
  return Math.round((basePrice.value + surchargeTotal.value) * PRICE_MULTIPLIER)
})

const finalPrice = computed(() => {
  const o = Number(overrideStr.value)
  if (overrideStr.value.trim() && Number.isFinite(o) && o > 0) return Math.round(o)
  return suggestedPrice.value
})

function toggleSurcharge(id: string) {
  const next = new Set(surchargeIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  surchargeIds.value = next
}

const detailOptions = [
  { value: 'rough', label: '粗 rough' },
  { value: 'standard', label: '標準 standard' },
  { value: 'detailed', label: '細緻 detailed' },
  { value: 'premium', label: '高級 premium' },
]

function fmtMoney(n: number | null): string {
  if (n == null) return '—'
  return `NT$ ${n.toLocaleString('zh-TW')}`
}

function validate(): boolean {
  const errs: Record<string, string> = {}
  if (!selectedJobId.value) {
    errs.job = '請選擇一個製作版本作為報價基準'
  }
  if (finalPrice.value == null || finalPrice.value <= 0) {
    errs.price = '報價金額必須大於 0'
  }
  errors.value = errs
  return Object.keys(errs).length === 0
}

function goPreview() {
  if (!validate()) return
  step.value = 2
}

function submit() {
  if (!validate()) return
  emit('confirm', {
    quoted_price: finalPrice.value!,
    production_job_id: selectedJobId.value!,
    detail: detail.value,
    surcharge_ids: Array.from(surchargeIds.value),
    quote_note: note.value.trim() || null,
  })
}

// admin preview 端點：渲染客戶會看到的浮水印圖（不消耗 view_count）
const previewImageSrc = computed(
  () => `/api/v1/admin/custom-requests/${props.request.id}/preview-watermark`,
)
</script>

<template>
  <Dialog :open="open" :title="step === 1 ? '送出報價' : '確認客戶會看到的內容'" size="lg" @close="emit('close')">
    <div v-if="pricesLoading || surLoading" class="py-12 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>

    <!-- Step 1: 報價設定 -->
    <div v-else-if="step === 1" class="space-y-5 text-[13px]">
      <!-- Spec preview -->
      <div class="p-3 border border-line-hairline rounded-[var(--radius-xs)] bg-paper-subtle">
        <p class="text-ink-strong font-medium">客戶申請內容</p>
        <p class="text-ink-muted text-[12px] mt-1">{{ customerSpecsHint }}</p>
      </div>

      <!-- 製作版本選擇器 — 必填，admin 跑了多版本時選一個給客戶 -->
      <div>
        <label class="block text-[13px] text-ink-strong mb-2">
          選擇製作版本
          <span class="text-state-danger">*</span>
          <span class="text-[11px] text-ink-muted ml-1 font-normal">客戶會看到這個版本的預覽圖；規格也以此為準</span>
        </label>
        <div v-if="jobsQuery.isLoading.value" class="py-6 flex justify-center text-ink-muted">
          <Loader2 :size="16" :stroke-width="1.5" class="animate-spin" />
        </div>
        <div
          v-else-if="completedJobs.length === 0"
          class="p-4 border border-state-warning/40 bg-[var(--color-state-warning)]/[0.06] rounded-[var(--radius-xs)] text-[12px]"
        >
          <AlertTriangle :size="14" :stroke-width="1.5" class="inline mr-1 text-state-warning" />
          尚無 completed 製作 — 請先「前往製作」跑出至少一個 job 才能報價。
        </div>
        <div v-else class="grid grid-cols-2 md:grid-cols-3 gap-2.5">
          <button
            v-for="(j, idx) in completedJobs"
            :key="j.id"
            type="button"
            class="relative aspect-[4/3] rounded-[var(--radius-xs)] border-2 overflow-hidden bg-paper-canvas hover:border-accent transition-colors text-left"
            :class="
              selectedJobId === j.id
                ? 'border-accent'
                : 'border-line-hairline'
            "
            @click="selectedJobId = j.id"
          >
            <img
              v-if="jobThumbnails.get(j.id)"
              :src="jobThumbnails.get(j.id)"
              :alt="`版本 ${idx + 1}`"
              class="w-full h-full object-contain"
            />
            <div v-else class="absolute inset-0 flex items-center justify-center text-ink-muted">
              <ImageOff :size="20" :stroke-width="1.25" />
            </div>
            <!-- meta overlay -->
            <div class="absolute bottom-0 left-0 right-0 px-2 py-1 bg-paper-canvas/90 border-t border-line-hairline">
              <p class="text-[11px] font-mono leading-tight text-ink-strong truncate">
                #{{ idx + 1 }} · {{ j.canvas_w_cm }}×{{ j.canvas_h_cm }}cm
              </p>
              <p class="text-[10px] text-ink-muted leading-tight truncate">
                {{ j.difficulty || '—' }} · {{ j.mode === 'standard' ? '標準' : j.mode }}
              </p>
            </div>
            <!-- selected check -->
            <div
              v-if="selectedJobId === j.id"
              class="absolute top-1 right-1 w-5 h-5 rounded-full bg-accent flex items-center justify-center"
            >
              <Check :size="12" :stroke-width="2" class="text-paper-canvas" />
            </div>
            <!-- approved chip -->
            <span
              v-if="j.approved"
              class="absolute top-1 left-1 px-1.5 h-4 inline-flex items-center text-[9px] tracking-[0.04em] rounded-[2px] bg-fresh-tint text-fresh font-medium"
            >已 APPROVED</span>
          </button>
        </div>
        <p v-if="errors.job" class="mt-2 text-[12px] text-state-danger">{{ errors.job }}</p>
      </div>

      <!-- 試算規格 — admin 敲定報價基準 -->
      <div class="p-3 border border-aux-rice-mid/40 bg-aux-rice-mid/[0.06] rounded-[var(--radius-xs)] space-y-3">
        <p class="text-[12px] text-ink-default">
          報價試算規格
          <span v-if="usingJobSpec" class="text-ink-muted">（沿用所選製作版本）</span>
          <span v-else-if="selectedJob" class="text-state-warning">（你已手動調整，與所選版本不同 — 報價試算用此欄位，但客戶看到的預覽仍是上方所選版本）</span>
        </p>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[12px] text-ink-muted mb-1">畫布尺寸</label>
            <Select v-model="priceCanvasKey" :options="canvasSizeOptions" />
          </div>
          <div>
            <label class="block text-[12px] text-ink-muted mb-1">難易度</label>
            <Select v-model="priceDifficulty" :options="difficultyOptions" />
          </div>
        </div>
      </div>

      <!-- Detail picker -->
      <div>
        <label class="block text-[13px] text-ink-strong mb-1.5">細緻度（影響報價）</label>
        <Select v-model="detail" :options="detailOptions" />
      </div>

      <!-- Surcharges -->
      <div>
        <label class="block text-[13px] text-ink-strong mb-2">加費項目</label>
        <div v-if="activeSurcharges.length === 0" class="text-ink-muted text-[12px]">
          目前無啟用中加費項目
        </div>
        <div v-else class="space-y-1.5">
          <label
            v-for="s in activeSurcharges"
            :key="s.id"
            class="flex items-center gap-3 p-2.5 border border-line-hairline rounded-[var(--radius-xs)] cursor-pointer hover:bg-paper-subtle"
            :class="surchargeIds.has(s.id) ? 'border-accent bg-[var(--color-accent)]/[0.04]' : ''"
          >
            <input
              type="checkbox"
              :checked="surchargeIds.has(s.id)"
              @change="toggleSurcharge(s.id)"
            />
            <div class="flex-1">
              <span class="text-ink-default">{{ s.label }}</span>
              <span class="text-[11px] text-ink-muted ml-1">（{{ s.category }}）</span>
            </div>
            <span class="font-mono text-ink-strong">+{{ fmtMoney(Number(s.amount)) }}</span>
          </label>
        </div>
      </div>

      <!-- Calculation breakdown -->
      <div class="p-3 border border-line-hairline rounded-[var(--radius-xs)] bg-paper-subtle">
        <p class="text-[12px] text-ink-muted mb-2">系統建議價格（公式 × {{ PRICE_MULTIPLIER }}）</p>
        <dl class="text-[12px] space-y-1">
          <div class="flex justify-between">
            <dt>基礎價（{{ priceCanvasW }}×{{ priceCanvasH }} · {{ priceDifficulty }}）</dt>
            <dd class="font-mono">{{ fmtMoney(basePrice) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt>加費小計</dt>
            <dd class="font-mono">{{ fmtMoney(surchargeTotal) }}</dd>
          </div>
          <div class="flex justify-between pt-1.5 border-t border-line-hairline mt-1.5">
            <dt class="text-ink-strong">建議報價</dt>
            <dd class="font-mono text-ink-strong">{{ fmtMoney(suggestedPrice) }}</dd>
          </div>
        </dl>
        <p v-if="basePrice == null" class="mt-2 text-[11px] text-state-warning">
          ⚠ 找不到對應價格表 — 請確認 prices 表已 seed 此 (尺寸 × 難度) 組合
        </p>
      </div>

      <!-- Override -->
      <div>
        <label class="block text-[13px] text-ink-strong mb-1.5">
          管理員確認報價（NT$，留空則用建議價）
        </label>
        <Input v-model="overrideStr" type="number" :placeholder="suggestedPrice ? String(suggestedPrice) : ''" />
        <p class="mt-1 text-[12px] text-ink-default">
          將使用：<span class="font-mono text-ink-strong">{{ fmtMoney(finalPrice) }}</span>
        </p>
        <p v-if="errors.price" class="mt-1 text-[12px] text-state-danger">{{ errors.price }}</p>
      </div>

      <!-- Note -->
      <div>
        <label class="block text-[13px] text-ink-strong mb-1.5">報價備註（會放進訊息流）</label>
        <Textarea v-model="note" :rows="3" :maxlength="1000" placeholder="可選：報價說明、製作期、備註..." />
      </div>

      <p class="text-[12px] text-ink-muted">
        送出後系統會：寄純文字 email + 連結（不附圖）；客戶在連結頁看浮水印降解析度預覽圖；報價有效 24 小時、最多查看 10 次。
      </p>
    </div>

    <!-- Step 2: 預覽客戶看到的內容 -->
    <div v-else class="space-y-4 text-[13px]">
      <div class="p-3 border border-aux-rice-mid/40 bg-aux-rice-mid/[0.06] rounded-[var(--radius-xs)] flex items-start gap-2">
        <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5 shrink-0 text-aux-rice-deep" />
        <div class="flex-1 text-[12px] leading-relaxed">
          以下是<strong class="text-ink-strong">客戶會看到的完整內容</strong>，請確認預覽圖品質、報價金額、備註無誤後再送出。
          送出後狀態變「報價已寄出」、客戶會收到 email。
        </div>
      </div>

      <!-- 客戶看到的浮水印預覽 -->
      <div>
        <p class="text-[11px] text-ink-muted tracking-[0.04em] uppercase mb-1.5">
          客戶看到的預覽圖（800px 寬 + 浮水印追溯印）
        </p>
        <div
          class="rounded-[var(--radius-sm)] border border-line-hairline overflow-hidden bg-paper-canvas"
          :class="previewImageError ? 'p-6 text-center' : ''"
        >
          <div v-if="previewImageError" class="text-ink-muted">
            <ImageOff :size="32" :stroke-width="1.25" class="mx-auto mb-2" />
            <p class="text-[12px]">尚未有可預覽的製作圖</p>
            <p class="text-[11px] mt-1">請先「前往製作」跑出 production_job 並 approve，才能用浮水印預覽。</p>
          </div>
          <img
            v-else
            :src="previewImageSrc"
            alt="客戶看到的預覽圖"
            class="w-full h-auto"
            @error="previewImageError = true"
            @load="previewImageError = false"
          />
        </div>
      </div>

      <!-- 客戶看到的 email 內容 -->
      <div>
        <p class="text-[11px] text-ink-muted tracking-[0.04em] uppercase mb-1.5">客戶會收到的 email</p>
        <div class="p-4 border border-line-hairline rounded-[var(--radius-sm)] bg-paper-surface text-[13px] leading-relaxed">
          <p class="text-ink-muted text-[11px] mb-3 pb-3 border-b border-line-hairline">
            主旨：【YIIMUI】客製報價已送出
          </p>
          <p class="mb-2">您的客製申請 #{{ request.id.slice(0, 8) }} 已完成報價。</p>
          <p class="mb-2"><strong>報價金額：{{ fmtMoney(finalPrice) }}</strong></p>
          <p v-if="note.trim()" class="mb-2">備註：{{ note.trim() }}</p>
          <p class="mb-2">請於 24 小時內確認：<span class="text-accent underline">查看報價</span></p>
        </div>
      </div>

      <!-- 客戶看到的報價摘要 -->
      <div class="p-4 border border-line-hairline rounded-[var(--radius-sm)] bg-paper-surface">
        <p class="text-[11px] text-ink-muted tracking-[0.04em] uppercase mb-2">客戶在 viewer 頁看到</p>
        <dl class="text-[13px] space-y-1.5">
          <div class="flex justify-between">
            <dt class="text-ink-muted">報價金額</dt>
            <dd class="font-display text-ink-strong text-[18px]">{{ fmtMoney(finalPrice) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">畫布尺寸</dt>
            <dd>{{ priceCanvasW }}×{{ priceCanvasH }}cm</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">難易度</dt>
            <dd>{{ priceDifficulty }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">細緻度</dt>
            <dd>{{ detail }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">查看限制</dt>
            <dd class="text-state-warning">10 次內必須決定 / 24 小時有效</dd>
          </div>
        </dl>
      </div>

      <p class="text-[11px] text-ink-muted">
        浮水印追溯印格式：<code class="font-mono bg-paper-subtle px-1">YIIMUI PREVIEW #{客戶 email 縮寫}-{申請 id 前 8 碼}</code>
        — 流到競品時可從浮水印反推來源。
      </p>
    </div>

    <template #footer>
      <template v-if="step === 1">
        <Button variant="secondary" :disabled="pending" @click="emit('close')">取消</Button>
        <Button variant="primary" :disabled="pending" @click="goPreview">
          <Eye :size="14" :stroke-width="1.5" />
          預覽客戶會看到的內容
        </Button>
      </template>
      <template v-else>
        <Button variant="secondary" :disabled="pending" @click="step = 1">
          <ChevronLeft :size="14" :stroke-width="1.5" />
          回上一步修改
        </Button>
        <Button variant="primary" :disabled="pending" @click="submit">
          <Loader2 v-if="pending" :size="14" :stroke-width="1.5" class="animate-spin" />
          確認無誤、送出報價
        </Button>
      </template>
    </template>
  </Dialog>
</template>
