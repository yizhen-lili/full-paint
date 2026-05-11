<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, Loader2, Plus, Trash2, Wrench, X as XIcon } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import AppDataTable, { type Column } from '@/shared/components/AppDataTable.vue'
import AppPagination from '@/shared/components/AppPagination.vue'
import Button from '@/shared/ui/Button.vue'
import Dialog from '@/shared/ui/Dialog.vue'
import Select from '@/shared/ui/Select.vue'
import Input from '@/shared/ui/Input.vue'

import JobStatusBadge from '../components/JobStatusBadge.vue'
import { useDeleteJobsBatchMutation, useJobsQuery } from '../queries'
import {
  type BatchDeleteJobResult,
  type JobListItem,
  type JobStatus,
  DETAIL_LABEL,
  DIFFICULTY_LABEL,
  MODE_LABEL,
} from '../api'

const router = useRouter()
const route = useRoute()

const status = ref<'' | JobStatus>(
  (typeof route.query.status === 'string' ? route.query.status : '') as '' | JobStatus,
)
const approvedFilter = ref<'' | 'true' | 'false'>(
  (typeof route.query.approved === 'string' ? route.query.approved : '') as '' | 'true' | 'false',
)
const batchId = ref<string>(typeof route.query.batch_id === 'string' ? route.query.batch_id : '')
const page = ref<number>(Number(route.query.page) > 0 ? Number(route.query.page) : 1)
const pageSize = 20

watch([status, approvedFilter, batchId], () => {
  page.value = 1
})

watch(
  [status, approvedFilter, batchId, page],
  () => {
    router.replace({
      query: {
        ...(status.value ? { status: status.value } : {}),
        ...(approvedFilter.value ? { approved: approvedFilter.value } : {}),
        ...(batchId.value ? { batch_id: batchId.value } : {}),
        ...(page.value > 1 ? { page: String(page.value) } : {}),
      },
    })
  },
  { flush: 'post' },
)

const params = computed(() => ({
  status: status.value || undefined,
  approved:
    approvedFilter.value === 'true'
      ? true
      : approvedFilter.value === 'false'
        ? false
        : undefined,
  batch_id: batchId.value || undefined,
  page: page.value,
  page_size: pageSize,
}))

const { data, isLoading, isError, error } = useJobsQuery(params)
const items = computed(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)

const statusOptions = [
  { value: '', label: '全部狀態' },
  { value: 'pending', label: '等待中' },
  { value: 'processing', label: '處理中' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失敗' },
  { value: 'cancelled', label: '已取消' },
]

const approvedOptions = [
  { value: '', label: '全部審核狀態' },
  { value: 'true', label: '已審核' },
  { value: 'false', label: '待審核' },
]

const columns: Column<JobListItem>[] = [
  { key: '__select', label: '', width: '40px' },
  { key: 'cover', label: '預覽', width: '64px' },
  { key: 'id_short', label: 'Job ID', width: '110px' },
  { key: 'source', label: '來源', width: '110px' },
  { key: 'spec', label: '規格' },
  { key: 'status', label: '狀態', width: '160px' },
  { key: 'created_at', label: '建立時間', width: '170px' },
]

function goNew() {
  router.push('/admin/production/new')
}

function goDetail(id: string) {
  router.push(`/admin/production/${id}`)
}

function fmtDateTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ── 批次刪除 ─────────────────────────────────────────────────────────────
// 允許多選任何 job；processing / 被引用的 job 由 backend 逐筆檢查並回報失敗
// （UI 不預先排除，partial success 結果 dialog 會顯示原因）。

const selectedIds = ref<Set<string>>(new Set())
const batchMut = useDeleteJobsBatchMutation()
const batchConfirmOpen = ref(false)
const batchResultsOpen = ref(false)
const batchResults = ref<BatchDeleteJobResult[]>([])
const forceDelete = ref(false)

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

// 換頁 / 換篩選 → 清空選取（避免跨頁誤刪）
watch([page, status, approvedFilter, batchId], () => clearSelection())

const successCount = computed(() => batchResults.value.filter((r) => r.ok).length)
const failedCount = computed(() => batchResults.value.filter((r) => !r.ok).length)

// 確認 dialog 顯示用的「將被刪除」清單（從 items 過濾出已勾選的 row）
const selectedJobsForDialog = computed(() =>
  items.value.filter((j) => selectedIds.value.has(j.id)),
)

async function doBatchDelete() {
  batchConfirmOpen.value = false
  try {
    const res = await batchMut.mutateAsync({
      jobIds: Array.from(selectedIds.value),
      force: forceDelete.value,
    })
    batchResults.value = res.results
    batchResultsOpen.value = true
    clearSelection()
    forceDelete.value = false
  } catch (e) {
    const err = e as { message?: string }
    alert(err.message || '批次刪除失敗')
  }
}
</script>

<template>
  <PageHeader title="製作系統" subtitle="圖片轉數字油畫模板的製作任務">
    <template #actions>
      <Button variant="primary" @click="goNew">
        <Plus :size="14" :stroke-width="1.75" />
        新增任務
      </Button>
    </template>
  </PageHeader>

  <section class="bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] p-4 mb-5">
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <Select v-model="status" :options="statusOptions" />
      <Select v-model="approvedFilter" :options="approvedOptions" />
      <Input v-model="batchId" placeholder="批次 ID（同批 jobs 共用 UUID）" />
    </div>
  </section>

  <div
    v-if="isError"
    class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)]"
  >
    載入失敗：{{ (error as { message?: string })?.message ?? '未知錯誤' }}
  </div>

  <!-- 批次工具列：勾選任何 row 後出現 -->
  <div
    v-if="selectedCount > 0"
    class="mb-3 px-4 py-3 bg-state-danger/[0.08] border border-state-danger/40 rounded-[var(--radius-xs)] flex items-center justify-between"
  >
    <div class="flex items-center gap-3 text-[13px] text-ink-strong">
      <Trash2 :size="16" :stroke-width="1.5" class="text-state-danger" />
      <span>已選取 <span class="font-mono">{{ selectedCount }}</span> 筆製作任務</span>
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
    empty-text="尚無製作任務"
    :empty-icon="Wrench"
    @row-click="(r) => goDetail(r.id)"
  >
    <template #header-__select>
      <input
        type="checkbox"
        class="cursor-pointer"
        :checked="allSelected"
        :disabled="items.length === 0"
        :title="allSelected ? '取消全選' : `全選本頁（${items.length} 筆）`"
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

    <template #cell-cover="{ row }">
      <!-- 已完成 job：filled_template；其他狀態 fallback 原圖 thumbnail -->
      <img
        v-if="row.filled_template_url"
        :src="row.filled_template_url"
        alt=""
        class="w-12 h-12 object-cover rounded-[var(--radius-xs)] border border-line-hairline"
      />
      <img
        v-else-if="row.image_preview_url"
        :src="row.image_preview_url"
        alt=""
        class="w-12 h-12 object-cover rounded-[var(--radius-xs)] border border-line-hairline opacity-70"
      />
      <div
        v-else
        class="w-12 h-12 bg-paper-subtle rounded-[var(--radius-xs)] border border-line-hairline"
      />
    </template>

    <template #cell-id_short="{ row }">
      <span class="font-mono text-[12px] text-ink-strong">{{ row.id.slice(0, 8) }}</span>
    </template>

    <template #cell-source="{ row }">
      <span
        v-if="row.custom_request_id"
        class="inline-flex items-center px-2 h-[20px] text-[11px] tracking-[0.04em] rounded-[var(--radius-xs)] bg-aux-rice-mid/40 text-ink-default"
      >客製</span>
      <span
        v-else-if="row.image_id"
        class="inline-flex items-center px-2 h-[20px] text-[11px] tracking-[0.04em] rounded-[var(--radius-xs)] bg-paper-subtle text-ink-default"
      >上傳</span>
      <span v-else class="text-[12px] text-ink-muted">—</span>
    </template>

    <template #cell-spec="{ row }">
      <div class="text-[12px] text-ink-default leading-snug">
        <div class="flex items-center gap-1.5 flex-wrap">
          <span>{{ row.canvas_w_cm }} × {{ row.canvas_h_cm }} cm</span>
          <span
            class="inline-flex items-center px-1.5 h-[18px] text-[10px] tracking-[0.04em] rounded-[var(--radius-xs)]"
            :class="row.mode === 'standard'
              ? 'bg-paper-subtle text-ink-muted'
              : 'bg-[var(--color-accent)]/[0.10] text-accent'"
          >{{ MODE_LABEL[row.mode] }}</span>
        </div>
        <div class="text-ink-muted">
          {{ DIFFICULTY_LABEL[row.difficulty] }} · {{ DETAIL_LABEL[row.detail] }}
          <span v-if="row.num_colors_used" class="ml-1">· {{ row.num_colors_used }} 色</span>
        </div>
      </div>
    </template>

    <template #cell-status="{ row }">
      <JobStatusBadge :status="row.status" :approved="row.approved" />
    </template>

    <template #cell-created_at="{ row }">
      <span class="text-ink-muted text-[12px] font-mono">{{ fmtDateTime(row.created_at) }}</span>
    </template>

    <template #empty-action>
      <Button variant="primary" class="mt-5" @click="goNew">
        <Plus :size="14" :stroke-width="1.75" />
        建立第一個任務
      </Button>
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
    title="批次刪除製作任務"
    @close="batchConfirmOpen = false"
  >
    <div class="text-[14px] text-ink-default leading-[1.7] space-y-3">
      <p>
        將永久刪除以下 <span class="font-mono text-ink-strong">{{ selectedCount }}</span> 筆製作任務：
      </p>
      <ul class="bg-paper-subtle border border-line-hairline rounded-[var(--radius-xs)] p-3 max-h-[280px] overflow-auto text-[12px] font-mono space-y-1">
        <li
          v-for="j in selectedJobsForDialog"
          :key="j.id"
          class="flex items-center justify-between"
        >
          <span class="text-ink-strong">{{ j.id.slice(0, 8) }}</span>
          <span class="text-ink-muted">
            {{ MODE_LABEL[j.mode] }} · {{ DIFFICULTY_LABEL[j.difficulty] }} · {{ DETAIL_LABEL[j.detail] }}
          </span>
        </li>
      </ul>
      <div class="text-[12px] text-ink-muted space-y-1">
        <p>• 連帶刪除 palette_color_mappings 子資料</p>
        <p>• Firebase 中 production_jobs/{job_id}/ 下的 svg / filled / snapped / mask 等檔案會被清除</p>
        <p>• 處理中（processing）或被商品 / 訂單 / 列印批次引用的 job 會在結果中標示失敗、不會被刪除</p>
      </div>
      <label class="flex items-center gap-2 text-[12px] text-ink-default cursor-pointer">
        <input v-model="forceDelete" type="checkbox" class="cursor-pointer" />
        <span>強制刪除（含處理中任務，可能產生 Firebase orphan 物件）</span>
      </label>
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
        <span class="text-ink-strong">總共 <span class="font-mono">{{ batchResults.length }}</span> 筆</span>
        <span class="text-state-success">
          <Check :size="13" :stroke-width="1.5" class="inline" />
          成功 <span class="font-mono">{{ successCount }}</span>
        </span>
        <span v-if="failedCount > 0" class="text-state-danger">
          <XIcon :size="13" :stroke-width="1.5" class="inline" />
          失敗 <span class="font-mono">{{ failedCount }}</span>
        </span>
      </div>
      <ul class="bg-paper-subtle border border-line-hairline rounded-[var(--radius-xs)] p-3 max-h-[400px] overflow-auto text-[12px] space-y-2">
        <li
          v-for="r in batchResults"
          :key="r.job_id"
          class="border-b border-line-hairline pb-2 last:border-b-0 last:pb-0"
        >
          <div class="flex items-center justify-between">
            <code class="text-ink-strong text-[11px]">{{ r.job_id.slice(0, 8) }}</code>
            <span v-if="r.ok" class="text-state-success font-mono text-[11px]">
              <Check :size="11" :stroke-width="1.5" class="inline" />
              已刪除
            </span>
            <span v-else class="text-state-danger text-[11px]">
              <XIcon :size="11" :stroke-width="1.5" class="inline" />
              失敗
            </span>
          </div>
          <p v-if="!r.ok && r.error" class="mt-1 text-ink-muted text-[11px] whitespace-pre-line">{{ r.error }}</p>
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
