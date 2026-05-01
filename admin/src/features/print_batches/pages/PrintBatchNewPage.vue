<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, Plus, Minus, Loader2, Calculator, Send, AlertTriangle, ImageOff, Download } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Textarea from '@/shared/ui/Textarea.vue'

import {
  useCandidatesQuery,
  useCreateBatchMutation,
  useFinalizeBatchMutation,
  usePreviewBatchMutation,
} from '../queries'
import { CANDIDATE_KIND_BADGE } from '../api'
import type { CandidateInfo, PreviewResponse, SuggestedCombo } from '../api'

const router = useRouter()

// ── Step state ────────────────────────────────────────────────────────
type Step = 1 | 2 | 3
const step = ref<Step>(1)

// requiredQty[production_job_id] = quantity（必印的）
// optionalQty 是預覽後 backend 給的建議湊單，前端再放回 candidates
const requiredQty = ref<Record<string, number>>({})
const optionalQty = ref<Record<string, number>>({})
const adminNotes = ref('')

const apiError = ref<string | null>(null)
const previewResult = ref<PreviewResponse | null>(null)
const finalizedBatchId = ref<string | null>(null)
const finalizedPdfUrl = ref<string | null>(null)

const {
  data: candidatesData,
  isLoading: candidatesLoading,
  isError: candidatesError,
  error: candidatesErrorObj,
  refetch: refetchCandidates,
} = useCandidatesQuery()
const candidates = computed(() => candidatesData.value?.items ?? [])

const previewMut = usePreviewBatchMutation()
const createMut = useCreateBatchMutation()
const finalizeMut = useFinalizeBatchMutation()

// ── Helpers ───────────────────────────────────────────────────────────
function adjQty(target: 'required' | 'optional', jobId: string, delta: number) {
  const map = target === 'required' ? requiredQty : optionalQty
  const cur = map.value[jobId] ?? 0
  const next = Math.max(0, cur + delta)
  if (next === 0) {
    delete map.value[jobId]
  } else {
    map.value[jobId] = next
  }
}

function setQty(target: 'required' | 'optional', jobId: string, qty: number) {
  const map = target === 'required' ? requiredQty : optionalQty
  if (qty <= 0) delete map.value[jobId]
  else map.value[jobId] = qty
}

const totalRequired = computed(() =>
  Object.values(requiredQty.value).reduce((a, b) => a + b, 0),
)
const totalOptional = computed(() =>
  Object.values(optionalQty.value).reduce((a, b) => a + b, 0),
)

const requiredItems = computed(() =>
  Object.entries(requiredQty.value).map(([production_job_id, quantity]) => ({
    production_job_id,
    quantity,
  })),
)
const optionalItems = computed(() =>
  Object.entries(optionalQty.value).map(([production_job_id, quantity]) => ({
    production_job_id,
    quantity,
  })),
)

const candidateById = computed(() => {
  const m: Record<string, CandidateInfo> = {}
  for (const c of candidates.value) m[c.production_job_id] = c
  return m
})

// ── Step transitions ──────────────────────────────────────────────────
async function goPreview() {
  if (totalRequired.value === 0) {
    apiError.value = '至少選 1 個必印項目'
    return
  }
  apiError.value = null
  try {
    const r = await previewMut.mutateAsync({
      required: requiredItems.value,
      candidates: optionalItems.value,
    })
    previewResult.value = r
    step.value = 2
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '預覽失敗'
  }
}

async function goFinalize() {
  apiError.value = null
  try {
    const created = await createMut.mutateAsync({
      required: requiredItems.value,
      candidates: optionalItems.value,
      admin_notes: adminNotes.value || null,
    })
    const finalized = await finalizeMut.mutateAsync(created.id)
    finalizedBatchId.value = finalized.id
    finalizedPdfUrl.value = finalized.pdf_url
    step.value = 3
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '建立批次失敗'
  }
}

function backToStep(s: Step) {
  step.value = s
}

/** 套用湊單建議：把 combo items 寫進 optionalQty，回 Step 1 並重新預覽 */
async function applySuggestion(combo: SuggestedCombo) {
  optionalQty.value = {}
  for (const it of combo.items) {
    optionalQty.value[it.production_job_id] = it.quantity
  }
  // 直接重新預覽，不退回 Step 1（admin 已看到效果即可）
  await goPreview()
}

function fmtMoney(n: number): string {
  return `NT$ ${n.toLocaleString('zh-TW')}`
}

function fmtInch(n: number): string {
  return n.toFixed(2)
}
</script>

<template>
  <div class="flex items-center gap-2 mb-3">
    <button
      type="button"
      class="text-[13px] text-ink-muted hover:text-ink-strong inline-flex items-center gap-1 transition-colors"
      @click="router.push('/admin/print-batches')"
    >
      <ChevronLeft :size="14" :stroke-width="1.5" />
      返回批次列表
    </button>
  </div>

  <PageHeader title="新增列印批次" subtitle="3 步驟：選項目 → 預覽成本 → 確認列印" />

  <!-- Stepper -->
  <nav class="flex items-center gap-2 mb-6 text-[13px]">
    <span
      v-for="s in [1, 2, 3]"
      :key="s"
      class="flex items-center gap-2"
    >
      <span
        class="inline-flex items-center justify-center w-7 h-7 rounded-full text-[12px] font-medium"
        :class="
          step === s
            ? 'bg-accent text-paper-surface'
            : step > s
              ? 'bg-state-success/20 text-state-success'
              : 'bg-paper-subtle text-ink-muted'
        "
      >{{ step > s ? '✓' : s }}</span>
      <span :class="step >= s ? 'text-ink-strong' : 'text-ink-muted'">
        {{ s === 1 ? '選擇項目' : s === 2 ? '預覽成本' : '完成' }}
      </span>
      <span v-if="s < 3" class="text-line-strong">→</span>
    </span>
  </nav>

  <div
    v-if="apiError"
    class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)] flex items-start gap-2"
  >
    <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5" />
    <span class="flex-1">{{ apiError }}</span>
  </div>

  <!-- Step 1：選項目 -->
  <template v-if="step === 1">
    <Card class="mb-5">
      <h2 class="font-display text-ink-strong text-[18px] mb-2">必印項目</h2>
      <p class="text-[12px] text-ink-muted mb-4">
        所有「已通過審核」的製作任務都會列出（含未上架商品與客製訂單），輸入需要的份數即可。
      </p>

      <div v-if="candidatesLoading" class="py-8 flex justify-center text-ink-muted">
        <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
      </div>
      <div
        v-else-if="candidatesError"
        class="py-6 px-4 text-[13px] text-state-danger border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] rounded-[var(--radius-xs)] flex items-start gap-2"
      >
        <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5 shrink-0" />
        <div class="flex-1">
          <p class="font-medium">載入候選清單失敗</p>
          <p class="text-[12px] text-ink-muted mt-1">
            {{ (candidatesErrorObj as { message?: string })?.message || '請確認後端是否運作中' }}
          </p>
        </div>
        <button
          type="button"
          class="text-[12px] underline shrink-0"
          @click="refetchCandidates()"
        >重試</button>
      </div>
      <div v-else-if="candidates.length === 0" class="py-8 text-center text-ink-muted text-[13px]">
        目前沒有可列印的項目（需要 approved=true 且 status=completed 的製作任務）
      </div>
      <ul v-else class="divide-y divide-line-hairline">
        <li
          v-for="c in candidates"
          :key="c.production_job_id"
          class="py-3 flex items-center justify-between gap-3 flex-wrap"
        >
          <div class="flex-1 min-w-0 flex items-center gap-3">
            <div class="w-16 h-16 shrink-0 rounded border border-line-hairline overflow-hidden bg-paper-canvas flex items-center justify-center">
              <img
                v-if="c.preview_url"
                :src="c.preview_url"
                alt="預覽"
                class="w-full h-full object-cover"
              />
              <ImageOff v-else :size="18" :stroke-width="1.25" class="text-ink-muted" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-medium text-ink-strong flex items-center gap-2">
                <span
                  class="text-[10px] px-1.5 py-0.5 rounded shrink-0"
                  :class="CANDIDATE_KIND_BADGE[c.kind].cls"
                >{{ CANDIDATE_KIND_BADGE[c.kind].label }}</span>
                <span class="truncate">{{ c.product_title }}</span>
              </p>
              <p class="text-[11px] text-ink-muted">
                {{ c.canvas_w_cm }} × {{ c.canvas_h_cm }} cm · 單份 {{ fmtInch(c.inch_per_unit) }} 吋
              </p>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <button
              type="button"
              class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] border border-line-strong text-ink-muted hover:bg-paper-subtle"
              @click="adjQty('required', c.production_job_id, -1)"
            >
              <Minus :size="14" :stroke-width="1.5" />
            </button>
            <input
              :value="requiredQty[c.production_job_id] ?? 0"
              type="number"
              min="0"
              class="w-16 h-8 px-2 text-center font-mono text-[13px] border border-line-hairline rounded-[var(--radius-xs)]"
              @input="setQty('required', c.production_job_id, Number(($event.target as HTMLInputElement).value))"
            />
            <button
              type="button"
              class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] border border-line-strong text-ink-muted hover:bg-paper-subtle"
              @click="adjQty('required', c.production_job_id, 1)"
            >
              <Plus :size="14" :stroke-width="1.5" />
            </button>
          </div>
        </li>
      </ul>

      <p class="mt-4 text-[12px] text-ink-muted">
        已選 {{ totalRequired }} 份（{{ Object.keys(requiredQty).length }} 種）
      </p>
    </Card>

    <div class="flex justify-end">
      <Button variant="primary" :disabled="previewMut.isPending.value" @click="goPreview">
        <Loader2 v-if="previewMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
        <Calculator v-else :size="14" :stroke-width="1.5" />
        計算成本
      </Button>
    </div>
  </template>

  <!-- Step 2：預覽成本 -->
  <template v-else-if="step === 2 && previewResult">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
      <Card>
        <h2 class="font-display text-ink-strong text-[18px] mb-3">成本明細</h2>
        <dl class="text-[13px] space-y-1.5">
          <div class="flex justify-between">
            <dt class="text-ink-muted">所需吋數</dt>
            <dd class="font-mono">{{ fmtInch(previewResult.required_inch_count) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">計費吋數</dt>
            <dd class="font-mono">{{ fmtInch(previewResult.billable_inch_count) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">浪費吋數</dt>
            <dd class="font-mono text-state-warning">{{ fmtInch(previewResult.waste_inch) }}</dd>
          </div>
          <div class="flex justify-between pt-2 border-t border-line-hairline mt-2">
            <dt class="text-ink-muted">列印成本</dt>
            <dd class="font-mono">{{ fmtMoney(previewResult.cost_breakdown.print_cost) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">裁切成本</dt>
            <dd class="font-mono">{{ fmtMoney(previewResult.cost_breakdown.cut_cost) }}</dd>
          </div>
          <div class="flex justify-between pt-2 border-t border-line-hairline mt-2">
            <dt class="text-ink-strong font-medium">總成本</dt>
            <dd class="font-mono text-ink-strong font-medium">{{ fmtMoney(previewResult.cost_breakdown.total_cost) }}</dd>
          </div>
        </dl>
      </Card>

      <Card v-if="previewResult.suggestions.length > 0">
        <h2 class="font-display text-ink-strong text-[18px] mb-1">湊單建議</h2>
        <p class="text-[11px] text-ink-muted mb-4">
          目前未達 20 吋免下限門檻，建議湊單以避免 100 元裁切下限浪費。
        </p>
        <div class="space-y-3">
          <div
            v-for="(s, i) in previewResult.suggestions"
            :key="i"
            class="rounded-[var(--radius-sm)] border border-line-hairline p-3 hover:border-accent/40 transition-colors"
          >
            <div class="flex items-center justify-between gap-3 mb-2">
              <div>
                <p class="font-medium text-ink-strong text-[13px]">{{ s.label }}</p>
                <p class="text-[11px] text-ink-muted mt-0.5">
                  總 {{ fmtInch(s.billable_inch_count) }} 吋
                  · 浪費 <span :class="s.waste_inch === 0 ? 'text-state-success' : 'text-state-warning'">{{ fmtInch(s.waste_inch) }}</span> 吋
                  · {{ fmtMoney(s.cost_breakdown.total_cost) }}
                </p>
              </div>
              <Button
                variant="secondary"
                :disabled="previewMut.isPending.value"
                @click="applySuggestion(s)"
              >
                <Plus :size="12" :stroke-width="1.5" />
                套用
              </Button>
            </div>
            <ul class="space-y-2">
              <li
                v-for="it in s.items"
                :key="it.production_job_id"
                class="flex items-center gap-2.5 text-[12px]"
              >
                <div class="w-10 h-10 shrink-0 rounded border border-line-hairline overflow-hidden bg-paper-canvas flex items-center justify-center">
                  <img
                    v-if="it.preview_url"
                    :src="it.preview_url"
                    alt="預覽"
                    class="w-full h-full object-cover"
                  />
                  <ImageOff v-else :size="14" :stroke-width="1.25" class="text-ink-muted" />
                </div>
                <div class="flex-1 min-w-0 flex items-center gap-1.5">
                  <span
                    class="text-[10px] px-1 py-0.5 rounded shrink-0"
                    :class="CANDIDATE_KIND_BADGE[it.kind].cls"
                  >{{ CANDIDATE_KIND_BADGE[it.kind].label }}</span>
                  <span class="truncate text-ink-default">{{ it.product_title }}</span>
                </div>
                <span class="font-mono text-ink-muted shrink-0">×{{ it.quantity }}</span>
              </li>
            </ul>
          </div>
        </div>
      </Card>
    </div>

    <Card class="mb-5">
      <h2 class="font-display text-ink-strong text-[18px] mb-3">內部備註（選填）</h2>
      <Textarea v-model="adminNotes" :rows="3" placeholder="例：本批優先處理逾期 3 天的訂單" />
    </Card>

    <div class="flex justify-between">
      <Button variant="secondary" @click="backToStep(1)">回上一步</Button>
      <Button
        variant="primary"
        :disabled="createMut.isPending.value || finalizeMut.isPending.value"
        @click="goFinalize"
      >
        <Loader2
          v-if="createMut.isPending.value || finalizeMut.isPending.value"
          :size="14" :stroke-width="1.5" class="animate-spin"
        />
        <Send v-else :size="14" :stroke-width="1.5" />
        確認建立批次
      </Button>
    </div>
  </template>

  <!-- Step 3：完成 -->
  <template v-else-if="step === 3">
    <Card class="text-center py-8">
      <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-state-success/20 text-state-success mb-4">
        ✓
      </div>
      <h2 class="font-display text-ink-strong text-[20px] mb-2">批次已建立</h2>
      <p class="text-ink-muted text-[13px] mb-5">PDF 已產出，可立即下載或之後從列表頁取用。</p>

      <div class="flex justify-center gap-3">
        <a
          v-if="finalizedPdfUrl"
          :href="finalizedPdfUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-[var(--radius-xs)] bg-accent text-paper-surface text-[13px] font-medium hover:opacity-90 transition-opacity"
        >
          <Download :size="14" :stroke-width="1.5" />
          下載 PDF
        </a>
        <Button
          variant="secondary"
          @click="finalizedBatchId && router.push(`/admin/print-batches/${finalizedBatchId}`)"
        >
          查看批次詳情
        </Button>
        <Button variant="secondary" @click="router.push('/admin/print-batches')">回列表</Button>
      </div>
    </Card>
  </template>
</template>
