<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Printer, Download, Loader2, Trash2, Check, X as XIcon } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import AppDataTable, { type Column } from '@/shared/components/AppDataTable.vue'
import AppPagination from '@/shared/components/AppPagination.vue'
import Button from '@/shared/ui/Button.vue'
import Dialog from '@/shared/ui/Dialog.vue'

import { useBatchesQuery, useDeleteBatchesBatchMutation } from '../queries'
import {
  STATUS_LABEL,
  type BatchDeleteBatchResult,
  type BatchReferenceGroup,
  type PrintBatchSummary,
} from '../api'

const router = useRouter()

const page = ref(1)
const pageSize = 20

const params = computed(() => ({ page: page.value, page_size: pageSize }))
const { data, isLoading, isError } = useBatchesQuery(params)
const items = computed(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)

const columns: Column<PrintBatchSummary>[] = [
  { key: '__select', label: '', width: '40px' },
  { key: 'id_short', label: '批次 ID', width: '120px' },
  { key: 'status', label: '狀態', width: '100px' },
  { key: 'item_count', label: '項目數', width: '70px', align: 'right' },
  { key: 'inch', label: '吋數', width: '80px', align: 'right' },
  { key: 'cost', label: '總成本', width: '120px', align: 'right' },
  { key: 'pdf', label: 'PDF', width: '100px', align: 'center' },
  { key: 'created_at', label: '建立時間', width: '170px' },
]

function fmtDateTime(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ── 批次刪除（沿用 ProductionListPage 模式）─────────────────────────────────
// 訂單引用永遠不可刪（金流稽核紅線）；其他批次無限制（draft / finalized 都可刪）

const selectedIds = ref<Set<string>>(new Set())
const batchMut = useDeleteBatchesBatchMutation()
const batchConfirmOpen = ref(false)
const batchResultsOpen = ref(false)
const batchResults = ref<BatchDeleteBatchResult[]>([])

function toggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

const allSelected = computed(
  () => items.value.length > 0 && items.value.every((r) => selectedIds.value.has(r.id)),
)

function toggleSelectAll() {
  if (allSelected.value) clearSelection()
  else selectedIds.value = new Set(items.value.map((r) => r.id))
}

const selectedCount = computed(() => selectedIds.value.size)
// 換頁清空選取
watch(page, () => clearSelection())

const selectedBatchesForDialog = computed(() =>
  items.value.filter((b) => selectedIds.value.has(b.id)),
)
const successCount = computed(() => batchResults.value.filter((r) => r.ok).length)
const failedCount = computed(() => batchResults.value.filter((r) => !r.ok).length)
const orderBlockedCount = computed(() =>
  batchResults.value.filter(
    (r) => !r.ok && r.references && r.references.some((g) => g.type === 'order_item'),
  ).length,
)

const REF_TYPE_BADGE: Record<BatchReferenceGroup['type'], string> = {
  order_item: 'bg-state-danger/[0.10] text-state-danger',
}

async function doBatchDelete() {
  batchConfirmOpen.value = false
  if (selectedCount.value === 0) return
  try {
    const res = await batchMut.mutateAsync(Array.from(selectedIds.value))
    batchResults.value = res.results
    batchResultsOpen.value = true
    clearSelection()
  } catch (e) {
    const err = e as { message?: string }
    alert(err.message || '批次刪除失敗')
  }
}
</script>

<template>
  <PageHeader title="列印批次" subtitle="集中列印多個製作模板，依吋數計算成本">
    <template #actions>
      <Button variant="primary" @click="router.push('/admin/print-batches/new')">
        <Plus :size="14" :stroke-width="1.75" />
        新增批次
      </Button>
    </template>
  </PageHeader>

  <div
    v-if="isError"
    class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)]"
  >載入失敗</div>

  <!-- 批次工具列：勾選後出現 -->
  <div
    v-if="selectedCount > 0"
    class="mb-3 px-4 py-3 bg-state-danger/[0.08] border border-state-danger/40 rounded-[var(--radius-xs)] flex items-center justify-between"
  >
    <div class="flex items-center gap-3 text-[13px] text-ink-strong">
      <Trash2 :size="16" :stroke-width="1.5" class="text-state-danger" />
      <span>已選取 <span class="font-mono">{{ selectedCount }}</span> 個批次</span>
      <button
        type="button"
        class="text-[12px] text-ink-muted hover:text-ink-strong transition-colors"
        @click="clearSelection"
      >
        清除選取
      </button>
    </div>
    <Button
      variant="primary"
      :disabled="batchMut.isPending.value"
      class="bg-state-danger hover:bg-state-danger/90"
      @click="batchConfirmOpen = true"
    >
      <Loader2 v-if="batchMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
      <Trash2 v-else :size="14" :stroke-width="1.5" />
      批次刪除
    </Button>
  </div>

  <AppDataTable
    :columns="columns"
    :rows="items"
    :loading="isLoading"
    :row-key="(r) => r.id"
    :row-clickable="true"
    empty-text="尚無批次"
    :empty-icon="Printer"
    @row-click="(r) => router.push(`/admin/print-batches/${r.id}`)"
  >
    <template #header-__select>
      <input
        type="checkbox"
        class="cursor-pointer"
        :checked="allSelected"
        :disabled="items.length === 0"
        :title="allSelected ? '取消全選' : `全選本頁（${items.length} 個）`"
        @click.stop="toggleSelectAll"
      />
    </template>

    <template #cell-__select="{ row }">
      <input
        type="checkbox"
        class="cursor-pointer"
        :checked="selectedIds.has(row.id)"
        @click.stop="toggleSelect(row.id)"
      />
    </template>

    <template #cell-id_short="{ row }">
      <span class="font-mono text-[12px] text-ink-strong">{{ row.id.slice(0, 8) }}</span>
    </template>
    <template #cell-status="{ row }">
      <span
        class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)]"
        :class="STATUS_LABEL[row.status].cls"
      >
        {{ STATUS_LABEL[row.status].label }}
      </span>
    </template>
    <template #cell-item_count="{ row }">
      <span class="font-mono text-[12px]">{{ row.item_count }}</span>
    </template>
    <template #cell-inch="{ row }">
      <span class="font-mono text-[12px]">{{ row.total_inch_count.toFixed(2) }}</span>
    </template>
    <template #cell-cost="{ row }">
      <span class="font-mono text-[12px] text-ink-strong">NT$ {{ row.total_cost.toLocaleString() }}</span>
    </template>
    <template #cell-pdf="{ row }">
      <a
        v-if="row.pdf_url"
        :href="row.pdf_url"
        target="_blank"
        rel="noopener"
        class="text-accent hover:text-accent-hover inline-flex items-center gap-1 text-[12px]"
        @click.stop
      >
        <Download :size="12" :stroke-width="1.5" />
        下載
      </a>
      <span v-else class="text-ink-muted text-[12px]">—</span>
    </template>
    <template #cell-created_at="{ row }">
      <span class="text-ink-muted text-[12px] font-mono">{{ fmtDateTime(row.created_at) }}</span>
    </template>
  </AppDataTable>

  <AppPagination
    v-if="total > pageSize"
    v-model:page="page"
    :page-size="pageSize"
    :total="total"
  />

  <!-- 批次刪除確認 dialog -->
  <Dialog
    :open="batchConfirmOpen"
    title="批次刪除列印批次"
    @close="batchConfirmOpen = false"
  >
    <div class="text-[14px] text-ink-default leading-[1.7] space-y-3">
      <p>
        將永久刪除以下 <span class="font-mono text-ink-strong">{{ selectedCount }}</span> 個列印批次：
      </p>
      <ul class="bg-paper-subtle border border-line-hairline rounded-[var(--radius-xs)] p-3 max-h-[280px] overflow-auto text-[12px] font-mono space-y-1">
        <li
          v-for="b in selectedBatchesForDialog"
          :key="b.id"
          class="flex items-center justify-between"
        >
          <span class="text-ink-strong">{{ b.id.slice(0, 8) }}</span>
          <span class="text-ink-muted">
            {{ STATUS_LABEL[b.status].label }} · {{ b.item_count }} 項 · NT$ {{ b.total_cost.toLocaleString() }}
          </span>
        </li>
      </ul>
      <div class="text-[12px] text-ink-muted space-y-1">
        <p>• 批次內項目（print_batch_items）依 FK CASCADE 連帶刪除</p>
        <p>• 已 finalize 的批次 PDF 檔（Firebase）會 best-effort 清除</p>
        <p>• 含訂單項目來源的批次會被擋下，結果中標示失敗</p>
      </div>
    </div>
    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <Button variant="secondary" @click="batchConfirmOpen = false">取消</Button>
        <Button
          variant="primary"
          :disabled="batchMut.isPending.value"
          class="bg-state-danger hover:bg-state-danger/90"
          @click="doBatchDelete"
        >
          <Loader2 v-if="batchMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
          <Trash2 v-else :size="14" :stroke-width="1.5" />
          確認刪除
        </Button>
      </div>
    </template>
  </Dialog>

  <!-- 批次刪除結果 dialog -->
  <Dialog
    :open="batchResultsOpen"
    title="批次刪除結果"
    @close="batchResultsOpen = false"
  >
    <div class="space-y-3">
      <div class="flex items-center gap-4 text-[13px]">
        <span class="text-ink-strong">總共 <span class="font-mono">{{ batchResults.length }}</span> 個</span>
        <span class="text-state-success">
          <Check :size="13" :stroke-width="1.5" class="inline" />
          成功 <span class="font-mono">{{ successCount }}</span>
        </span>
        <span v-if="failedCount > 0" class="text-state-danger">
          <XIcon :size="13" :stroke-width="1.5" class="inline" />
          失敗 <span class="font-mono">{{ failedCount }}</span>
        </span>
      </div>

      <div
        v-if="orderBlockedCount > 0"
        class="px-3 py-2 border border-state-danger/40 bg-state-danger/[0.06] text-state-danger text-[12px] rounded-[var(--radius-xs)] leading-[1.6]"
      >
        <p class="font-medium">
          有 <span class="font-mono">{{ orderBlockedCount }}</span> 個批次內含訂單項目，無法刪除。
        </p>
        <p class="text-state-danger/80 mt-0.5">
          訂單為金流稽核記錄，請先到「訂單管理」頁取消或退款相關訂單，再回來刪除批次。
        </p>
      </div>

      <ul class="bg-paper-subtle border border-line-hairline rounded-[var(--radius-xs)] p-3 max-h-[440px] overflow-auto text-[12px] space-y-3">
        <li
          v-for="r in batchResults"
          :key="r.batch_id"
          class="border-b border-line-hairline pb-3 last:border-b-0 last:pb-0"
        >
          <div class="flex items-center justify-between">
            <code class="text-ink-strong text-[11px]">{{ r.batch_id.slice(0, 8) }}</code>
            <span v-if="r.ok" class="text-state-success font-mono text-[11px]">
              <Check :size="11" :stroke-width="1.5" class="inline" />
              已刪除
            </span>
            <span v-else class="text-state-danger text-[11px]">
              <XIcon :size="11" :stroke-width="1.5" class="inline" />
              失敗
            </span>
          </div>
          <div v-if="!r.ok && r.references && r.references.length > 0" class="mt-2 space-y-2">
            <div
              v-for="group in r.references"
              :key="`${r.batch_id}-${group.type}`"
              class="border border-line-hairline rounded-[var(--radius-xs)] bg-paper-surface px-2.5 py-2"
            >
              <div class="flex items-center justify-between mb-1.5">
                <span
                  class="inline-flex items-center px-1.5 h-[18px] text-[10px] tracking-[0.04em] rounded-[var(--radius-xs)]"
                  :class="REF_TYPE_BADGE[group.type]"
                >{{ group.label }}（{{ group.items.length }} 筆）</span>
                <span class="text-[10px] text-state-danger">不可刪除</span>
              </div>
              <p
                v-if="group.blocking_reason"
                class="text-[11px] text-state-danger/80 mb-1.5 leading-[1.5]"
              >{{ group.blocking_reason }}</p>
              <ul class="space-y-0.5 text-[11px] text-ink-default">
                <li
                  v-for="item in group.items"
                  :key="item.id"
                  class="leading-[1.5]"
                >• {{ item.display }}</li>
              </ul>
            </div>
          </div>
          <p
            v-else-if="!r.ok && r.error"
            class="mt-1 text-ink-muted text-[11px] whitespace-pre-line"
          >{{ r.error }}</p>
        </li>
      </ul>
    </div>
    <template #footer>
      <div class="flex justify-end">
        <Button variant="primary" @click="batchResultsOpen = false">關閉</Button>
      </div>
    </template>
  </Dialog>
</template>
