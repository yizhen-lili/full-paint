<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ChevronLeft, Plus, Minus, Loader2, Calculator, Send, AlertTriangle } from 'lucide-vue-next'

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
import type { CandidateInfo, PreviewResponse } from '../api'

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

const { data: candidatesData, isLoading: candidatesLoading } = useCandidatesQuery()
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

function fmtMoney(n: number): string {
  return `NT$ ${n.toLocaleString('zh-TW')}`
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
        從待處理的訂單 / 製作任務中選需要列印的數量。底下會列出所有可用 candidate，輸入需要的份數即可。
      </p>

      <div v-if="candidatesLoading" class="py-8 flex justify-center text-ink-muted">
        <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
      </div>
      <div v-else-if="candidates.length === 0" class="py-8 text-center text-ink-muted text-[13px]">
        目前沒有可列印的項目
      </div>
      <ul v-else class="divide-y divide-line-hairline">
        <li
          v-for="c in candidates"
          :key="c.production_job_id"
          class="py-3 flex items-center justify-between gap-3 flex-wrap"
        >
          <div class="flex-1 min-w-0">
            <p class="font-medium text-ink-strong">{{ c.product_title }}</p>
            <p class="text-[11px] text-ink-muted">
              {{ c.canvas_w_cm }} × {{ c.canvas_h_cm }} cm · 單份 {{ c.inch_per_unit }} 吋
            </p>
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
            <dd class="font-mono">{{ previewResult.required_inch_count }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">計費吋數</dt>
            <dd class="font-mono">{{ previewResult.billable_inch_count }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-ink-muted">浪費吋數</dt>
            <dd class="font-mono text-state-warning">{{ previewResult.waste_inch }}</dd>
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
        <h2 class="font-display text-ink-strong text-[18px] mb-3">湊單建議</h2>
        <ul class="text-[12px] text-ink-default space-y-1.5">
          <li v-for="(s, i) in previewResult.suggestions" :key="i" class="flex gap-2">
            <span class="text-accent shrink-0">•</span>
            <span>{{ s }}</span>
          </li>
        </ul>
        <p v-if="previewResult.available_candidates.length > 0" class="mt-3 text-[11px] text-ink-muted">
          系統建議可加入 {{ previewResult.available_candidates.length }} 個 candidate（回上一步調整）
        </p>
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
        <Button
          v-if="finalizedPdfUrl"
          variant="primary"
          @click="finalizedPdfUrl && window.open(finalizedPdfUrl, '_blank', 'noopener')"
        >
          下載 PDF
        </Button>
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
