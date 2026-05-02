<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, Wrench } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import AppDataTable, { type Column } from '@/shared/components/AppDataTable.vue'
import AppPagination from '@/shared/components/AppPagination.vue'
import Button from '@/shared/ui/Button.vue'
import Select from '@/shared/ui/Select.vue'
import Input from '@/shared/ui/Input.vue'

import JobStatusBadge from '../components/JobStatusBadge.vue'
import { useJobsQuery } from '../queries'
import {
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
</template>
