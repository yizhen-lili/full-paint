<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Printer, Download, Loader2 } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import AppDataTable, { type Column } from '@/shared/components/AppDataTable.vue'
import AppPagination from '@/shared/components/AppPagination.vue'
import Button from '@/shared/ui/Button.vue'

import { useBatchesQuery } from '../queries'
import { STATUS_LABEL, type PrintBatchSummary } from '../api'

const router = useRouter()

const page = ref(1)
const pageSize = 20

const params = computed(() => ({ page: page.value, page_size: pageSize }))
const { data, isLoading, isError } = useBatchesQuery(params)
const items = computed(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)

const columns: Column<PrintBatchSummary>[] = [
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
</template>
