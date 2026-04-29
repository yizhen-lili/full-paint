<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Plus,
  Pencil,
  Palette,
  Package,
  AlertTriangle,
  ToggleLeft,
  ToggleRight,
  Loader2,
} from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import AppSearchInput from '@/shared/components/AppSearchInput.vue'
import AppDataTable, { type Column } from '@/shared/components/AppDataTable.vue'
import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Select from '@/shared/ui/Select.vue'

import EditColorDialog from '../components/EditColorDialog.vue'
import RgbCalibrationDialog from '../components/RgbCalibrationDialog.vue'
import StockUpdateDialog from '../components/StockUpdateDialog.vue'

import {
  useColorsQuery,
  useCreateColorMutation,
  useRevertRgbMutation,
  useShortageDashboardQuery,
  useToggleActiveMutation,
  useUpdateColorMutation,
  useUpdateRgbMutation,
  useUpdateStockMutation,
} from '../queries'
import type { CreateColorPayload, PhysicalColor, UpdateColorPayload } from '../api'
import { rgbToHex } from '../api'

const route = useRoute()
const router = useRouter()

// ── Filters ───────────────────────────────────────────────────────────
const search = ref<string>(typeof route.query.search === 'string' ? route.query.search : '')
const family = ref<string>(typeof route.query.family === 'string' ? route.query.family : '')
const active = ref<'' | 'true' | 'false'>(
  (typeof route.query.is_active === 'string' ? route.query.is_active : '') as '' | 'true' | 'false',
)

const params = computed(() => ({
  search: search.value || undefined,
  color_family: family.value || undefined,
  is_active: active.value === 'true' ? true : active.value === 'false' ? false : undefined,
}))

const { data, isLoading } = useColorsQuery(params)
const items = computed(() => data.value?.items ?? [])

const familyOptions = computed(() => {
  const fams = new Set<string>()
  for (const c of items.value) {
    if (c.color_family) fams.add(c.color_family)
  }
  return [
    { value: '', label: '全部色系' },
    ...Array.from(fams)
      .sort()
      .map((f) => ({ value: f, label: f })),
  ]
})

const activeOptions = [
  { value: '', label: '全部狀態' },
  { value: 'true', label: '啟用中' },
  { value: 'false', label: '已停用' },
]

// ── Shortage dashboard ────────────────────────────────────────────────
const { data: shortageData } = useShortageDashboardQuery()
const shortageItems = computed(() => shortageData.value?.items ?? [])

// ── Mutations ─────────────────────────────────────────────────────────
const createMut = useCreateColorMutation()
const updateMut = useUpdateColorMutation()
const toggleMut = useToggleActiveMutation()
const updateRgbMut = useUpdateRgbMutation()
const revertRgbMut = useRevertRgbMutation()
const stockMut = useUpdateStockMutation()

// ── Dialogs ───────────────────────────────────────────────────────────
const editOpen = ref(false)
const editingColor = ref<PhysicalColor | null>(null)
const calOpen = ref(false)
const calColor = ref<PhysicalColor | null>(null)
const stockOpen = ref(false)
const stockColor = ref<PhysicalColor | null>(null)
const apiError = ref<string | null>(null)
const lastFulfilledMessage = ref<string | null>(null)

function openCreate() {
  editingColor.value = null
  editOpen.value = true
}

function openEdit(c: PhysicalColor) {
  editingColor.value = c
  editOpen.value = true
}

function openCalibrate(c: PhysicalColor) {
  calColor.value = c
  calOpen.value = true
}

function openStock(c: PhysicalColor) {
  stockColor.value = c
  stockOpen.value = true
}

async function onCreate(payload: CreateColorPayload) {
  apiError.value = null
  try {
    await createMut.mutateAsync(payload)
    editOpen.value = false
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '建立失敗'
  }
}

async function onUpdate(payload: UpdateColorPayload) {
  if (!editingColor.value) return
  apiError.value = null
  try {
    await updateMut.mutateAsync({ id: editingColor.value.id, payload })
    editOpen.value = false
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '儲存失敗'
  }
}

async function toggleActive(c: PhysicalColor) {
  try {
    await toggleMut.mutateAsync(c.id)
  } catch (e) {
    alert((e as { message?: string }).message || '切換失敗')
  }
}

async function onSaveRgb(hex: string) {
  if (!calColor.value) return
  try {
    await updateRgbMut.mutateAsync({ id: calColor.value.id, payload: { hex } })
  } catch (e) {
    alert((e as { message?: string }).message || 'RGB 校正失敗')
  }
}

async function onRevert(history_id: string) {
  if (!calColor.value) return
  try {
    await revertRgbMut.mutateAsync({ id: calColor.value.id, history_id })
  } catch (e) {
    alert((e as { message?: string }).message || '還原失敗')
  }
}

async function onConfirmStock(add_ml: number) {
  if (!stockColor.value) return
  apiError.value = null
  try {
    const r = await stockMut.mutateAsync({ id: stockColor.value.id, add_ml })
    if (r.fulfilled_orders > 0) {
      lastFulfilledMessage.value = `已自動為 ${r.fulfilled_orders} 筆預購訂單升單。`
    } else {
      lastFulfilledMessage.value = `庫存更新完成，目前 ${r.new_stock_ml} ml。`
    }
    stockOpen.value = false
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '更新庫存失敗'
  }
}

// ── Table ─────────────────────────────────────────────────────────────
const columns: Column<PhysicalColor>[] = [
  { key: 'swatch', label: '色票', width: '64px' },
  { key: 'code', label: '色號', width: '80px' },
  { key: 'name', label: '名稱' },
  { key: 'family', label: '色系', width: '120px' },
  { key: 'rgb', label: 'RGB', width: '160px' },
  { key: 'stock_ml', label: '庫存 (ml)', width: '110px', align: 'right' },
  { key: 'is_active', label: '狀態', width: '80px', align: 'center' },
  { key: 'actions', label: '', width: '160px', align: 'right' },
]
</script>

<template>
  <PageHeader title="實體色管理" subtitle="60 色色盤、RGB 校正、庫存進貨、預購備料">
    <template #actions>
      <Button variant="primary" @click="openCreate">
        <Plus :size="14" :stroke-width="1.75" />
        新增實體色
      </Button>
    </template>
  </PageHeader>

  <div
    v-if="apiError"
    class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)]"
  >
    {{ apiError }}
  </div>
  <div
    v-if="lastFulfilledMessage"
    class="mb-5 px-4 py-3 border border-state-success/40 bg-[var(--color-state-success)]/[0.06] text-state-success text-[13px] rounded-[var(--radius-xs)] flex items-start gap-2"
  >
    <span class="flex-1">{{ lastFulfilledMessage }}</span>
    <button class="text-[12px] underline" @click="lastFulfilledMessage = null">關閉</button>
  </div>

  <!-- Shortage dashboard -->
  <Card v-if="shortageItems.length > 0" class="mb-5">
    <h2 class="font-display text-ink-strong text-[18px] leading-[26px] mb-3 flex items-center gap-2">
      <AlertTriangle :size="16" :stroke-width="1.5" class="text-state-warning" />
      預購缺料
      <span class="text-[12px] text-ink-muted font-sans">{{ shortageItems.length }} 色待進貨</span>
    </h2>
    <table class="w-full text-[13px]">
      <thead>
        <tr class="border-b border-line-hairline text-left text-ink-muted">
          <th class="py-2">色號</th>
          <th class="py-2">名稱</th>
          <th class="py-2 text-right">現有 (ml)</th>
          <th class="py-2 text-right">待備 (ml)</th>
          <th class="py-2 text-right">缺口 (ml)</th>
          <th class="py-2 text-right">等待訂單</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in shortageItems" :key="s.color_id" class="border-b border-line-hairline last:border-0">
          <td class="py-2 font-mono text-[12px]">{{ s.code }}</td>
          <td class="py-2">{{ s.name }}</td>
          <td class="py-2 text-right font-mono">{{ s.stock_ml }}</td>
          <td class="py-2 text-right font-mono">{{ s.required_ml }}</td>
          <td class="py-2 text-right font-mono text-state-danger">-{{ s.shortage_ml }}</td>
          <td class="py-2 text-right font-mono">{{ s.waiting_orders }}</td>
        </tr>
      </tbody>
    </table>
  </Card>

  <!-- Filter bar -->
  <section class="bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] p-4 mb-5">
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <AppSearchInput v-model="search" placeholder="搜尋色號 / 名稱..." />
      <Select v-model="family" :options="familyOptions" />
      <Select v-model="active" :options="activeOptions" />
    </div>
  </section>

  <!-- Color table -->
  <AppDataTable
    :columns="columns"
    :rows="items"
    :loading="isLoading"
    :row-key="(r) => r.id"
    empty-text="尚無實體色"
    :empty-icon="Palette"
  >
    <template #cell-swatch="{ row }">
      <div
        class="w-10 h-10 rounded-[var(--radius-xs)] border border-line-hairline"
        :style="{ backgroundColor: rgbToHex(row.rgb) }"
      />
    </template>
    <template #cell-code="{ row }">
      <span class="font-mono text-[13px] text-ink-strong">{{ row.code }}</span>
    </template>
    <template #cell-name="{ row }">
      <span class="font-medium text-ink-strong">{{ row.name }}</span>
      <span v-if="row.brand" class="text-[11px] text-ink-muted ml-1">· {{ row.brand }}</span>
    </template>
    <template #cell-family="{ row }">
      <span class="text-[12px] text-ink-default">{{ row.color_family || '—' }}</span>
    </template>
    <template #cell-rgb="{ row }">
      <span class="font-mono text-[11px] text-ink-muted">{{ rgbToHex(row.rgb) }}</span>
    </template>
    <template #cell-stock_ml="{ row }">
      <span
        class="font-mono"
        :class="row.stock_ml === 0 ? 'text-state-danger' : 'text-ink-strong'"
      >{{ row.stock_ml.toLocaleString() }}</span>
    </template>
    <template #cell-is_active="{ row }">
      <button
        type="button"
        class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)]"
        :class="
          row.is_active
            ? 'bg-[var(--color-state-success)]/[0.10] text-state-success'
            : 'bg-paper-subtle text-ink-muted'
        "
        @click="toggleActive(row)"
      >
        {{ row.is_active ? '啟用' : '停用' }}
      </button>
    </template>
    <template #cell-actions="{ row }">
      <div class="flex items-center justify-end gap-1">
        <button
          type="button"
          class="h-8 px-2 inline-flex items-center gap-1 text-[12px] text-ink-muted hover:text-ink-strong hover:bg-paper-subtle rounded-[var(--radius-xs)] transition-colors"
          @click="openStock(row)"
        >
          <Package :size="12" :stroke-width="1.5" />
          進貨
        </button>
        <button
          type="button"
          class="h-8 px-2 inline-flex items-center gap-1 text-[12px] text-ink-muted hover:text-ink-strong hover:bg-paper-subtle rounded-[var(--radius-xs)] transition-colors"
          @click="openCalibrate(row)"
        >
          RGB
        </button>
        <button
          type="button"
          class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:text-ink-strong hover:bg-paper-subtle"
          @click="openEdit(row)"
        >
          <Pencil :size="14" :stroke-width="1.5" />
        </button>
      </div>
    </template>
  </AppDataTable>

  <EditColorDialog
    :open="editOpen"
    :color="editingColor"
    :pending="createMut.isPending.value || updateMut.isPending.value"
    @close="editOpen = false"
    @create="onCreate"
    @update="onUpdate"
  />
  <RgbCalibrationDialog
    :open="calOpen"
    :color="calColor"
    :pending="updateRgbMut.isPending.value || revertRgbMut.isPending.value"
    @close="calOpen = false"
    @save-rgb="onSaveRgb"
    @revert="onRevert"
  />
  <StockUpdateDialog
    :open="stockOpen"
    :color="stockColor"
    :pending="stockMut.isPending.value"
    @close="stockOpen = false"
    @confirm="onConfirmStock"
  />
</template>
