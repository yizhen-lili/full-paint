<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  Beaker,
  CheckCircle2,
  ImageOff,
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

import { usePaintRequirementsMutation, useSourcesQuery } from '../queries'
import type {
  ApiError,
  PaintRequirementsResponse,
  SourceCustomRequest,
  SourceProductGroup,
  SourceStandaloneJob,
  SourceVariantInfo,
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

// ── 各 tab 的選中項（用 production_job_id 統一表達）──────────────────
// 商品 tab 需額外記 variant_id 以便顯示；客製 / 試驗只用 job_id
const selectedProductId = ref<string>('')  // 用來篩變體；不直接用於送 API
const selectedVariantId = ref<string>('')
const selectedCustomJobId = ref<string>('')
const selectedStandaloneJobId = ref<string>('')

const selectedProduct = computed(() =>
  sources.value?.products.find((p) => p.id === selectedProductId.value) ?? null,
)

// 解析當前 tab 選到的 job_id + finalized 狀態（送 API 用）
const selectedJob = computed<{ jobId: string; isFinalized: boolean } | null>(() => {
  if (activeTab.value === 'products') {
    if (!selectedProduct.value || !selectedVariantId.value) return null
    const v = selectedProduct.value.variants.find((x) => x.variant_id === selectedVariantId.value)
    return v ? { jobId: v.production_job_id, isFinalized: v.is_finalized } : null
  }
  if (activeTab.value === 'custom_requests') {
    if (!selectedCustomJobId.value) return null
    const c = sources.value?.custom_requests.find((x) => x.production_job_id === selectedCustomJobId.value)
    return c ? { jobId: c.production_job_id, isFinalized: c.is_finalized } : null
  }
  if (!selectedStandaloneJobId.value) return null
  const j = sources.value?.standalone_jobs.find((x) => x.production_job_id === selectedStandaloneJobId.value)
  return j ? { jobId: j.production_job_id, isFinalized: j.is_finalized } : null
})

function fmtDate(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function setTab(t: TabType) {
  activeTab.value = t
  result.value = null
  failure.value = null
}

function pickProduct(p: SourceProductGroup) {
  if (selectedProductId.value === p.id) return  // 已選不變
  selectedProductId.value = p.id
  selectedVariantId.value = ''  // 換商品要重選變體
}

function pickVariant(v: SourceVariantInfo) {
  selectedVariantId.value = v.variant_id
}

function pickCustom(c: SourceCustomRequest) {
  selectedCustomJobId.value = c.production_job_id
}

function pickStandalone(j: SourceStandaloneJob) {
  selectedStandaloneJobId.value = j.production_job_id
}

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
      <!-- Tab 1: 商品 → variant cascade（卡片式）-->
      <div v-if="activeTab === 'products'">
        <p
          v-if="!sources?.products.length"
          class="py-8 text-center text-[13px] text-ink-muted"
        >
          尚無商品 — 請先到「商品管理」建立
        </p>
        <template v-else>
          <Label>商品</Label>
          <div class="mt-2 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-[280px] overflow-y-auto pr-1">
            <button
              v-for="p in sources.products"
              :key="p.id"
              type="button"
              class="relative text-left rounded-[var(--radius-sm)] border bg-paper-surface p-2 transition-all hover:shadow-sm"
              :class="selectedProductId === p.id
                ? 'border-accent ring-2 ring-accent/30'
                : 'border-line-hairline hover:border-ink-muted'"
              @click="pickProduct(p)"
            >
              <!-- 第一個 variant 縮圖代表整個商品（多 variants 才在下方選具體規格）-->
              <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-hidden flex items-center justify-center mb-1.5">
                <img
                  v-if="p.variants[0]?.preview_url"
                  :src="p.variants[0].preview_url"
                  :alt="p.title"
                  class="w-full h-full object-cover"
                />
                <ImageOff v-else :size="20" :stroke-width="1.5" class="text-ink-muted" />
              </div>
              <p class="text-[12px] text-ink-strong font-medium leading-tight truncate" :title="p.title">
                {{ p.title }}
              </p>
              <p class="text-[10px] text-ink-muted mt-0.5">
                {{ p.variants.length }} 規格<span v-if="p.status === 'draft'"> · 草稿</span><span v-else-if="p.status === 'off_sale'"> · 下架</span>
              </p>
            </button>
          </div>

          <!-- 變體選擇（選了商品才出現）-->
          <template v-if="selectedProduct">
            <Label class="mt-4 block">規格</Label>
            <div class="mt-2 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              <button
                v-for="v in selectedProduct.variants"
                :key="v.variant_id"
                type="button"
                class="relative text-left rounded-[var(--radius-sm)] border bg-paper-surface p-2 transition-all hover:shadow-sm"
                :class="selectedVariantId === v.variant_id
                  ? 'border-accent ring-2 ring-accent/30'
                  : 'border-line-hairline hover:border-ink-muted'"
                @click="pickVariant(v)"
              >
                <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-hidden flex items-center justify-center mb-1.5">
                  <img
                    v-if="v.preview_url"
                    :src="v.preview_url"
                    :alt="`${v.canvas_w_cm}x${v.canvas_h_cm}`"
                    class="w-full h-full object-cover"
                  />
                  <ImageOff v-else :size="20" :stroke-width="1.5" class="text-ink-muted" />
                </div>
                <p class="text-[12px] text-ink-strong font-medium">
                  {{ v.canvas_w_cm }} × {{ v.canvas_h_cm }} cm
                </p>
                <p class="text-[10px] text-ink-muted mt-0.5">
                  NT$ {{ v.price.toLocaleString() }}
                </p>
                <span
                  v-if="!v.is_finalized"
                  class="absolute top-1 right-1 px-1.5 py-0.5 text-[9px] rounded bg-state-warning/[0.15] text-state-warning"
                >未對應</span>
              </button>
            </div>
          </template>
        </template>
      </div>

      <!-- Tab 2: 客製訂單 -->
      <div v-else-if="activeTab === 'custom_requests'">
        <p
          v-if="!sources?.custom_requests.length"
          class="py-8 text-center text-[13px] text-ink-muted"
        >
          尚無已建任務的客製訂單
        </p>
        <div
          v-else
          class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-[420px] overflow-y-auto pr-1"
        >
          <button
            v-for="c in sources.custom_requests"
            :key="c.custom_request_id"
            type="button"
            class="relative text-left rounded-[var(--radius-sm)] border bg-paper-surface p-2 transition-all hover:shadow-sm"
            :class="selectedCustomJobId === c.production_job_id
              ? 'border-accent ring-2 ring-accent/30'
              : 'border-line-hairline hover:border-ink-muted'"
            @click="pickCustom(c)"
          >
            <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-hidden flex items-center justify-center mb-1.5">
              <img
                v-if="c.preview_url"
                :src="c.preview_url"
                :alt="c.label"
                class="w-full h-full object-cover"
              />
              <ImageOff v-else :size="20" :stroke-width="1.5" class="text-ink-muted" />
            </div>
            <p class="text-[12px] text-ink-strong font-medium leading-tight truncate" :title="c.label">
              {{ c.label }}
            </p>
            <p class="text-[10px] text-ink-muted mt-0.5">
              {{ c.canvas_w_cm }} × {{ c.canvas_h_cm }} cm
            </p>
            <span
              v-if="!c.is_finalized"
              class="absolute top-1 right-1 px-1.5 py-0.5 text-[9px] rounded bg-state-warning/[0.15] text-state-warning"
            >未對應</span>
          </button>
        </div>
      </div>

      <!-- Tab 3: 試驗任務 -->
      <div v-else>
        <p
          v-if="!sources?.standalone_jobs.length"
          class="py-8 text-center text-[13px] text-ink-muted"
        >
          尚無 standalone job（未綁商品、未綁客製單）
        </p>
        <div
          v-else
          class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-[420px] overflow-y-auto pr-1"
        >
          <button
            v-for="j in sources.standalone_jobs"
            :key="j.production_job_id"
            type="button"
            class="relative text-left rounded-[var(--radius-sm)] border bg-paper-surface p-2 transition-all hover:shadow-sm"
            :class="selectedStandaloneJobId === j.production_job_id
              ? 'border-accent ring-2 ring-accent/30'
              : 'border-line-hairline hover:border-ink-muted'"
            @click="pickStandalone(j)"
          >
            <div class="aspect-square rounded-[var(--radius-xs)] border border-line-hairline bg-paper-canvas overflow-hidden flex items-center justify-center mb-1.5">
              <img
                v-if="j.preview_url"
                :src="j.preview_url"
                :alt="j.label"
                class="w-full h-full object-cover"
              />
              <ImageOff v-else :size="20" :stroke-width="1.5" class="text-ink-muted" />
            </div>
            <p class="text-[12px] text-ink-strong font-medium font-mono leading-tight truncate" :title="j.label">
              {{ j.label }}
            </p>
            <p class="text-[10px] text-ink-muted mt-0.5">
              {{ j.canvas_w_cm }} × {{ j.canvas_h_cm }} cm · {{ fmtDate(j.created_at) }}
            </p>
            <span
              v-if="!j.is_finalized"
              class="absolute top-1 right-1 px-1.5 py-0.5 text-[9px] rounded bg-state-warning/[0.15] text-state-warning"
            >未對應</span>
          </button>
        </div>
      </div>

      <!-- 共用 quantity + 查詢 -->
      <div class="grid grid-cols-1 md:grid-cols-12 gap-3 items-end mt-4 pt-4 border-t border-line-hairline">
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

      <p
        v-if="selectedJob && !selectedJob.isFinalized"
        class="mt-3 text-[12px] text-state-warning inline-flex items-center gap-1"
      >
        <AlertTriangle :size="12" :stroke-width="1.5" />
        該項目尚未完成顏色對應，無法查詢。
        <button class="underline ml-1" @click="goToColorMapping">前往對應 →</button>
      </p>
    </template>
  </Card>

  <!-- 結果 / 錯誤展示 -->

  <Card
    v-if="failure && failure.code === 'JOB_NOT_FINALIZED'"
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
      切到對應 tab、點縮圖選來源、輸入製作件數，按「查詢顏料需求」即可看到該任務需要哪些物理顏料。
    </p>
  </Card>
</template>
