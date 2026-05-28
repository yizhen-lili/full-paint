<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import {
  AlertTriangle,
  Beaker,
  CheckCircle2,
  Loader2,
  Search,
} from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Select from '@/shared/ui/Select.vue'

import { listProducts, listVariants } from '@/features/products/api'

import { usePaintRequirementsMutation } from '../queries'
import type { ApiError, PaintRequirementsResponse } from '../api'

const router = useRouter()

// ── Step 1: 商品搜尋 + 選擇 ──────────────────────────────────────────────
const searchTerm = ref('')
const selectedProductId = ref<string>('')

// 直接列前 50 個商品（含搜尋 server-side），數量大時可換 autocomplete
const productsQuery = useQuery({
  queryKey: ['admin', 'paint-requirements', 'products', searchTerm],
  queryFn: () => listProducts({ search: searchTerm.value || undefined, page: 1, page_size: 50 }),
  staleTime: 30_000,
})

const productOptions = computed(() => [
  { value: '', label: '— 請選商品 —' },
  ...(productsQuery.data.value?.items ?? []).map((p) => ({
    value: p.id,
    label: `${p.title}（${p.variant_count} 規格）`,
  })),
])

// 切商品時自動清掉所選規格與結果
watch(selectedProductId, () => {
  selectedVariantId.value = ''
  result.value = null
  failure.value = null
})

// ── Step 2: 從 product 拉 variants ──────────────────────────────────────
const selectedVariantId = ref<string>('')

const variantsQuery = useQuery({
  queryKey: ['admin', 'paint-requirements', 'variants', selectedProductId],
  queryFn: () => listVariants(selectedProductId.value),
  enabled: () => !!selectedProductId.value,
  staleTime: 30_000,
})

function fmtVariantLabel(v: { id: string; price: number; job_spec: { canvas_w_cm: number; canvas_h_cm: number } | null }): string {
  const size = v.job_spec
    ? `${v.job_spec.canvas_w_cm} × ${v.job_spec.canvas_h_cm} cm`
    : '尺寸未知'
  return `${size} · NT$ ${Number(v.price).toLocaleString()}`
}

const variantOptions = computed(() => [
  { value: '', label: '— 請選規格 —' },
  ...(variantsQuery.data.value ?? []).map((v) => ({
    value: v.id,
    label: fmtVariantLabel(v),
  })),
])

// ── Step 3: quantity + 查詢 ──────────────────────────────────────────────
const quantity = ref<number>(1)

const mut = usePaintRequirementsMutation()
const result = ref<PaintRequirementsResponse | null>(null)
const failure = ref<ApiError | null>(null)

const canSubmit = computed(
  () => !!selectedVariantId.value && quantity.value >= 1 && quantity.value <= 1000,
)

async function onSubmit() {
  if (!canSubmit.value) return
  result.value = null
  failure.value = null
  try {
    const data = await mut.mutateAsync({
      variantId: selectedVariantId.value,
      quantity: quantity.value,
    })
    result.value = data
  } catch (e) {
    failure.value = e as ApiError
  }
}

function goToColorMapping() {
  if (failure.value?.production_job_id) {
    router.push(`/admin/colors/mapping/${failure.value.production_job_id}`)
  }
}
</script>

<template>
  <PageHeader title="顏料準備清單" subtitle="查詢規格 × N 件的物理顏料用量、對比庫存" />

  <Card class="mb-5">
    <div class="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
      <!-- 商品搜尋 -->
      <div class="md:col-span-4">
        <Label>商品搜尋</Label>
        <Input
          v-model="searchTerm"
          placeholder="輸入商品名稱關鍵字…"
          class="mt-1"
        />
      </div>
      <!-- 商品 -->
      <div class="md:col-span-4">
        <Label>商品</Label>
        <Select
          v-model="selectedProductId"
          :options="productOptions"
          :disabled="productsQuery.isLoading.value"
          class="mt-1"
        />
      </div>
      <!-- 規格 -->
      <div class="md:col-span-4">
        <Label>規格</Label>
        <Select
          v-model="selectedVariantId"
          :options="variantOptions"
          :disabled="!selectedProductId || variantsQuery.isLoading.value"
          class="mt-1"
        />
      </div>
      <!-- quantity -->
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
      <!-- 查詢 -->
      <div class="md:col-span-3">
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
  </Card>

  <!-- 結果區 -->

  <!-- 未 finalize 提示 -->
  <Card
    v-if="failure && failure.code === 'VARIANT_NOT_FINALIZED'"
    class="border-state-warning/40 bg-[var(--color-state-warning)]/[0.06]"
  >
    <div class="flex items-start gap-3">
      <AlertTriangle :size="20" :stroke-width="1.5" class="text-state-warning mt-0.5 shrink-0" />
      <div class="flex-1">
        <p class="font-display text-ink-strong text-[16px] leading-[22px] mb-1">
          該規格尚未完成顏色對應
        </p>
        <p class="text-[13px] text-ink-default leading-[1.6] mb-3">
          請先到「顏色對應」工作台完成對應 + finalize 模板後，再回來查詢顏料需求。
        </p>
        <Button
          v-if="failure.production_job_id"
          variant="secondary"
          @click="goToColorMapping"
        >
          前往對應 →
        </Button>
      </div>
    </div>
  </Card>

  <!-- 其他錯誤（404 / 500 等） -->
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

  <!-- 成功：摘要 + 表格 -->
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
          此規格目前沒有顏料對應資料
        </div>
      </div>
    </Card>
  </template>

  <!-- 初始空狀態 -->
  <Card v-else class="text-center py-10">
    <Beaker :size="32" :stroke-width="1.25" class="mx-auto mb-3 text-aux-rice-mid" />
    <p class="text-[13px] text-ink-muted">
      選擇商品與規格、輸入製作件數，按「查詢顏料需求」即可看到該規格需要哪些物理顏料。
    </p>
  </Card>
</template>
