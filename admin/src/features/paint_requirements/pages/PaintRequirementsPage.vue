<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  Beaker,
  CheckCircle2,
  Loader2,
  Package,
  Search,
  Sparkles,
  Wrench,
} from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Select from '@/shared/ui/Select.vue'

import { usePaintRequirementsMutation, useSourcesQuery } from '../queries'
import type {
  ApiError,
  PaintRequirementsResponse,
  SourceCustomRequest,
  SourceProductGroup,
  SourceStandaloneJob,
} from '../api'

const router = useRouter()

// ── 來源 picker：三 tab ──────────────────────────────────────────────
type TabType = 'products' | 'custom_requests' | 'standalone_jobs'
const activeTab = ref<TabType>('products')

const sourcesQuery = useSourcesQuery()
const sources = computed(() => sourcesQuery.data.value)

const tabs: { key: TabType; label: string; icon: typeof Package }[] = [
  { key: 'products', label: '商品', icon: Package },
  { key: 'custom_requests', label: '客製訂單', icon: Sparkles },
  { key: 'standalone_jobs', label: '試驗任務', icon: Wrench },
]

const tabCounts = computed(() => ({
  products: sources.value?.products.length ?? 0,
  custom_requests: sources.value?.custom_requests.length ?? 0,
  standalone_jobs: sources.value?.standalone_jobs.length ?? 0,
}))

// ── Tab 1: 商品 → variant ───────────────────────────────────────────
const selectedProductId = ref<string>('')
const selectedProductVariantId = ref<string>('')

const productOptions = computed(() => {
  const items = sources.value?.products ?? []
  return [
    { value: '', label: '— 請選商品 —' },
    ...items.map((p: SourceProductGroup) => ({
      value: p.id,
      label: `${p.title}（${p.variants.length} 規格${p.status === 'draft' ? ' · 草稿' : p.status === 'off_sale' ? ' · 下架' : ''}）`,
    })),
  ]
})

const selectedProduct = computed(() =>
  sources.value?.products.find((p) => p.id === selectedProductId.value) ?? null,
)

const productVariantOptions = computed(() => {
  if (!selectedProduct.value) return [{ value: '', label: '— 先選商品 —' }]
  return [
    { value: '', label: '— 請選規格 —' },
    ...selectedProduct.value.variants.map((v) => ({
      value: v.variant_id,
      label: `${v.canvas_w_cm} × ${v.canvas_h_cm} cm · NT$ ${v.price.toLocaleString()}${v.is_finalized ? '' : ' · 未對應'}`,
    })),
  ]
})

// ── Tab 2: 客製訂單 ────────────────────────────────────────────────
const selectedCustomRequestId = ref<string>('')

const customOptions = computed(() => {
  const items = sources.value?.custom_requests ?? []
  return [
    { value: '', label: '— 請選客製訂單 —' },
    ...items.map((c: SourceCustomRequest) => ({
      value: c.custom_request_id,
      label: `${c.label} · ${c.canvas_w_cm} × ${c.canvas_h_cm} cm${c.is_finalized ? '' : ' · 未對應'}`,
    })),
  ]
})

// ── Tab 3: 試驗任務 ────────────────────────────────────────────────
const selectedStandaloneJobId = ref<string>('')

function fmtDate(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const standaloneOptions = computed(() => {
  const items = sources.value?.standalone_jobs ?? []
  return [
    { value: '', label: '— 請選試驗任務 —' },
    ...items.map((j: SourceStandaloneJob) => ({
      value: j.production_job_id,
      label: `${j.label} · ${j.canvas_w_cm} × ${j.canvas_h_cm} cm · ${fmtDate(j.created_at)}${j.is_finalized ? '' : ' · 未對應'}`,
    })),
  ]
})

// ── 共用：解析當前 tab 選到的 job_id + finalized 狀態 ───────────────
const selectedJob = computed<{ jobId: string; isFinalized: boolean } | null>(() => {
  if (activeTab.value === 'products') {
    if (!selectedProduct.value || !selectedProductVariantId.value) return null
    const v = selectedProduct.value.variants.find(
      (vv) => vv.variant_id === selectedProductVariantId.value,
    )
    return v ? { jobId: v.production_job_id, isFinalized: v.is_finalized } : null
  }
  if (activeTab.value === 'custom_requests') {
    if (!selectedCustomRequestId.value) return null
    const c = sources.value?.custom_requests.find(
      (cc) => cc.custom_request_id === selectedCustomRequestId.value,
    )
    return c ? { jobId: c.production_job_id, isFinalized: c.is_finalized } : null
  }
  // standalone_jobs
  if (!selectedStandaloneJobId.value) return null
  const j = sources.value?.standalone_jobs.find(
    (jj) => jj.production_job_id === selectedStandaloneJobId.value,
  )
  return j ? { jobId: j.production_job_id, isFinalized: j.is_finalized } : null
})

// ── quantity + 查詢 ──────────────────────────────────────────────────
const quantity = ref<number>(1)

const mut = usePaintRequirementsMutation()
const result = ref<PaintRequirementsResponse | null>(null)
const failure = ref<ApiError | null>(null)

const canSubmit = computed(
  () => !!selectedJob.value
    && selectedJob.value.isFinalized
    && quantity.value >= 1
    && quantity.value <= 1000,
)

async function onSubmit() {
  if (!selectedJob.value) return
  result.value = null
  failure.value = null
  try {
    const data = await mut.mutateAsync({
      productionJobId: selectedJob.value.jobId,
      quantity: quantity.value,
    })
    result.value = data
  } catch (e) {
    failure.value = e as ApiError
  }
}

function goToColorMapping() {
  const jobId = failure.value?.production_job_id ?? selectedJob.value?.jobId
  if (jobId) router.push(`/admin/colors/mapping/${jobId}`)
}

// 切 tab 時清掉當前 tab 之外的選擇 + 結果（避免狀態混淆）
function setTab(t: TabType) {
  activeTab.value = t
  result.value = null
  failure.value = null
}
</script>

<template>
  <PageHeader title="顏料準備清單" subtitle="查詢任務 × N 件的物理顏料用量、對比庫存" />

  <Card class="mb-5">
    <!-- 三 tab 切換 -->
    <div class="flex gap-1 border-b border-line-hairline mb-4 -mx-5 px-5">
      <button
        v-for="t in tabs"
        :key="t.key"
        type="button"
        class="px-3 py-2 text-[13px] border-b-2 transition-colors -mb-px inline-flex items-center gap-1.5"
        :class="activeTab === t.key
          ? 'border-accent text-accent font-medium'
          : 'border-transparent text-ink-muted hover:text-ink-default'"
        @click="setTab(t.key)"
      >
        <component :is="t.icon" :size="14" :stroke-width="1.5" />
        {{ t.label }}
        <span
          class="text-[11px] px-1 font-mono"
          :class="activeTab === t.key ? 'text-accent' : 'text-ink-muted'"
        >{{ tabCounts[t.key] }}</span>
      </button>
    </div>

    <div v-if="sourcesQuery.isLoading.value" class="py-6 flex justify-center text-ink-muted">
      <Loader2 :size="16" :stroke-width="1.5" class="animate-spin" />
    </div>

    <template v-else>
      <!-- Tab 1: 商品 → variant cascade -->
      <div v-if="activeTab === 'products'" class="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
        <div class="md:col-span-5">
          <Label>商品</Label>
          <Select
            v-model="selectedProductId"
            :options="productOptions"
            class="mt-1"
          />
        </div>
        <div class="md:col-span-5">
          <Label>規格</Label>
          <Select
            v-model="selectedProductVariantId"
            :options="productVariantOptions"
            :disabled="!selectedProductId"
            class="mt-1"
          />
        </div>
        <div class="md:col-span-2 text-[11px] text-ink-muted">
          <p v-if="!sources?.products.length" class="text-state-warning">
            尚無商品 — 請先到「商品管理」建立
          </p>
        </div>
      </div>

      <!-- Tab 2: 客製訂單 -->
      <div v-else-if="activeTab === 'custom_requests'" class="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
        <div class="md:col-span-10">
          <Label>客製訂單</Label>
          <Select
            v-model="selectedCustomRequestId"
            :options="customOptions"
            class="mt-1"
          />
        </div>
        <div class="md:col-span-2 text-[11px] text-ink-muted">
          <p v-if="!sources?.custom_requests.length" class="text-state-warning">
            尚無已建任務的客製訂單
          </p>
        </div>
      </div>

      <!-- Tab 3: 試驗任務 -->
      <div v-else class="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
        <div class="md:col-span-10">
          <Label>試驗任務（未綁商品、未綁客製單）</Label>
          <Select
            v-model="selectedStandaloneJobId"
            :options="standaloneOptions"
            class="mt-1"
          />
        </div>
        <div class="md:col-span-2 text-[11px] text-ink-muted">
          <p v-if="!sources?.standalone_jobs.length" class="text-state-warning">
            尚無 standalone job
          </p>
        </div>
      </div>

      <!-- 共用 quantity + 查詢 -->
      <div class="grid grid-cols-1 md:grid-cols-12 gap-3 items-end mt-3 pt-3 border-t border-line-hairline">
        <div class="md:col-span-3">
          <Label>製作件數</Label>
          <Input
            v-model.number="quantity"
            type="number"
            min="1"
            max="1000"
            class="mt-1"
          />
        </div>
        <div class="md:col-span-3 md:col-start-10">
          <Button
            variant="primary"
            :disabled="!canSubmit || mut.isPending.value"
            class="w-full"
            @click="onSubmit"
          >
            <Loader2 v-if="mut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
            <Search v-else :size="14" :stroke-width="1.5" />
            查詢顏料需求
          </Button>
        </div>
      </div>

      <!-- 選到「未對應」項目時的提示 -->
      <p
        v-if="selectedJob && !selectedJob.isFinalized"
        class="mt-3 text-[12px] text-state-warning inline-flex items-center gap-1"
      >
        <AlertTriangle :size="12" :stroke-width="1.5" />
        該項目尚未完成顏色對應，無法查詢。
        <button
          class="underline ml-1"
          @click="goToColorMapping"
        >前往對應 →</button>
      </p>
    </template>
  </Card>

  <!-- 結果 / 錯誤展示 -->

  <Card
    v-if="failure && (failure.code === 'JOB_NOT_FINALIZED' || failure.code === 'VARIANT_NOT_FINALIZED')"
    class="border-state-warning/40 bg-[var(--color-state-warning)]/[0.06]"
  >
    <div class="flex items-start gap-3">
      <AlertTriangle :size="20" :stroke-width="1.5" class="text-state-warning mt-0.5 shrink-0" />
      <div class="flex-1">
        <p class="font-display text-ink-strong text-[16px] leading-[22px] mb-1">
          該任務尚未完成顏色對應
        </p>
        <p class="text-[13px] text-ink-default leading-[1.6] mb-3">
          請先到「顏色對應」工作台完成對應 + finalize 模板後，再回來查詢顏料需求。
        </p>
        <Button variant="secondary" @click="goToColorMapping">
          前往對應 →
        </Button>
      </div>
    </div>
  </Card>

  <Card
    v-else-if="failure"
    class="border-state-danger/40 bg-[var(--color-state-danger)]/[0.06]"
  >
    <div class="flex items-start gap-3">
      <AlertTriangle :size="20" :stroke-width="1.5" class="text-state-danger mt-0.5 shrink-0" />
      <div class="flex-1">
        <p class="font-display text-ink-strong text-[16px] leading-[22px] mb-1">查詢失敗</p>
        <p class="text-[13px] text-ink-default">{{ failure.message }}</p>
      </div>
    </div>
  </Card>

  <template v-else-if="result">
    <Card class="mb-4">
      <div class="flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px]">
        <div class="flex items-center gap-2">
          <Beaker :size="16" :stroke-width="1.5" class="text-accent" />
          <span class="font-display text-ink-strong text-[15px]">
            {{ result.canvas_w_cm }} × {{ result.canvas_h_cm }} cm × {{ result.quantity }} 件
          </span>
        </div>
        <span class="text-ink-muted">
          共 <span class="font-mono text-ink-strong">{{ result.summary.total_colors }}</span> 色 ·
          總需 <span class="font-mono text-ink-strong">{{ result.summary.total_required_ml.toFixed(2) }}</span> ml
        </span>
        <span
          v-if="result.summary.short_count > 0"
          class="text-state-danger inline-flex items-center gap-1"
        >
          <AlertTriangle :size="13" :stroke-width="1.5" />
          庫存不足 <span class="font-mono">{{ result.summary.short_count }}</span> 色
        </span>
        <span
          v-else
          class="text-state-success inline-flex items-center gap-1"
        >
          <CheckCircle2 :size="13" :stroke-width="1.5" />
          庫存充足
        </span>
      </div>
    </Card>

    <Card>
      <div class="overflow-x-auto">
        <table class="w-full text-[13px]">
          <thead>
            <tr class="border-b border-line-hairline text-ink-muted text-[12px]">
              <th class="text-left py-2 px-2 font-normal w-[60px]">模板色號</th>
              <th class="text-left py-2 px-2 font-normal w-[60px]">色票</th>
              <th class="text-left py-2 px-2 font-normal">色號 / 名稱</th>
              <th class="text-right py-2 px-2 font-normal w-[100px]">單件需 (ml)</th>
              <th class="text-right py-2 px-2 font-normal w-[100px]">總需 (ml)</th>
              <th class="text-right py-2 px-2 font-normal w-[100px]">庫存 (ml)</th>
              <th class="text-right py-2 px-2 font-normal w-[100px]">缺料 (ml)</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="it in result.items"
              :key="it.physical_color_id"
              class="border-b border-line-hairline last:border-b-0"
              :class="it.is_short ? 'bg-state-danger/[0.04]' : ''"
            >
              <td class="py-2 px-2 font-mono">
                <span
                  v-if="it.output_label !== null"
                  class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-accent/[0.12] text-accent text-[11px]"
                >#{{ it.output_label }}</span>
                <span v-else class="text-ink-muted">—</span>
              </td>
              <td class="py-2 px-2">
                <div
                  class="w-7 h-7 rounded-[var(--radius-xs)] border border-line-hairline"
                  :style="{ backgroundColor: it.hex }"
                  :title="it.hex"
                />
              </td>
              <td class="py-2 px-2">
                <div class="font-mono text-ink-strong">{{ it.code }}</div>
                <div class="text-[12px] text-ink-muted">{{ it.name }}</div>
              </td>
              <td class="py-2 px-2 text-right font-mono">
                {{ it.required_per_unit_ml.toFixed(2) }}
              </td>
              <td class="py-2 px-2 text-right font-mono font-medium">
                {{ it.total_required_ml.toFixed(2) }}
              </td>
              <td
                class="py-2 px-2 text-right font-mono"
                :class="it.is_short ? 'text-state-danger' : 'text-ink-default'"
              >
                {{ it.stock_ml.toFixed(2) }}
              </td>
              <td class="py-2 px-2 text-right font-mono">
                <span
                  v-if="it.is_short"
                  class="text-state-danger font-medium inline-flex items-center gap-1"
                >
                  <AlertTriangle :size="12" :stroke-width="1.5" />
                  {{ it.shortage_ml.toFixed(2) }}
                </span>
                <span v-else class="text-ink-muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div
          v-if="result.items.length === 0"
          class="py-8 text-center text-ink-muted text-[13px]"
        >
          此任務目前沒有顏料對應資料
        </div>
      </div>
    </Card>
  </template>

  <Card v-else class="text-center py-10">
    <Beaker :size="32" :stroke-width="1.25" class="mx-auto mb-3 text-aux-rice-mid" />
    <p class="text-[13px] text-ink-muted">
      切到對應 tab、選來源（商品 / 客製訂單 / 試驗任務）、輸入製作件數，按「查詢顏料需求」即可看到該任務需要哪些物理顏料。
    </p>
  </Card>
</template>
