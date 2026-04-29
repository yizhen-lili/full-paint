<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bell,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ExternalLink,
  CheckCheck,
} from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Select from '@/shared/ui/Select.vue'
import AppPagination from '@/shared/components/AppPagination.vue'

import {
  useBulkCompleteMutation,
  useNotificationsQuery,
  useUpdateStatusMutation,
} from '../queries'
import {
  STATUS_LABEL,
  TYPE_LABEL,
  buildNotificationLink,
  type AdminNotification,
  type NotificationStatus,
} from '../api'

const route = useRoute()
const router = useRouter()

// ── Tab：用 status 切換 ──────────────────────────────────────────────────
type TabId = 'unhandled' | 'in_progress' | 'completed'
const tab = ref<TabId>(
  ['unhandled', 'in_progress', 'completed'].includes(route.query.tab as string)
    ? (route.query.tab as TabId)
    : 'unhandled',
)

const requiresAction = ref<'' | 'true' | 'false'>(
  (typeof route.query.requires_action === 'string' ? route.query.requires_action : '') as
    | ''
    | 'true'
    | 'false',
)
const page = ref<number>(Number(route.query.page) > 0 ? Number(route.query.page) : 1)
const pageSize = 20

watch([tab, requiresAction], () => {
  page.value = 1
  selectedIds.value.clear()
})

watch(
  [tab, requiresAction, page],
  () => {
    router.replace({
      query: {
        tab: tab.value,
        ...(requiresAction.value ? { requires_action: requiresAction.value } : {}),
        ...(page.value > 1 ? { page: String(page.value) } : {}),
      },
    })
  },
  { flush: 'post' },
)

const params = computed(() => ({
  status: tab.value as NotificationStatus,
  requires_action:
    requiresAction.value === 'true'
      ? true
      : requiresAction.value === 'false'
        ? false
        : undefined,
  page: page.value,
  page_size: pageSize,
}))

const { data, isLoading, isFetching, isError } = useNotificationsQuery(params)
const items = computed(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)

// ── Mutations ─────────────────────────────────────────────────────────
const updateMut = useUpdateStatusMutation()
const bulkMut = useBulkCompleteMutation()

const apiError = ref<string | null>(null)

async function setStatus(n: AdminNotification, target: NotificationStatus) {
  apiError.value = null
  try {
    await updateMut.mutateAsync({ id: n.id, status: target })
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '更新失敗'
  }
}

// ── 多選 + 批次完成 ────────────────────────────────────────────────────
const selectedIds = ref<Set<string>>(new Set())

function toggleSelect(id: string) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function selectAll() {
  if (selectedIds.value.size === items.value.length) {
    selectedIds.value = new Set()
  } else {
    selectedIds.value = new Set(items.value.map((i) => i.id))
  }
}

async function bulkComplete() {
  if (selectedIds.value.size === 0) return
  apiError.value = null
  try {
    await bulkMut.mutateAsync(Array.from(selectedIds.value))
    selectedIds.value = new Set()
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '批次完成失敗'
  }
}

// ── Helpers ───────────────────────────────────────────────────────────
const requiresActionOptions = [
  { value: '', label: '全部' },
  { value: 'true', label: '需處理' },
  { value: 'false', label: '無需處理' },
]

function fmtDateTime(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function gotoRef(n: AdminNotification) {
  const url = buildNotificationLink(n)
  if (url) router.push(url)
}
</script>

<template>
  <PageHeader title="通知中心" subtitle="待處理事件、訊息、系統通知">
    <template #actions>
      <span class="inline-flex items-center text-[12px] text-ink-muted gap-1">
        <Loader2 v-if="isFetching" :size="12" :stroke-width="1.5" class="animate-spin" />
        每 30 秒自動更新
      </span>
    </template>
  </PageHeader>

  <!-- Tabs -->
  <nav class="flex items-center gap-1 mb-6 border-b border-line-hairline">
    <button
      v-for="t in [
        { id: 'unhandled', label: '未處理', icon: AlertTriangle },
        { id: 'in_progress', label: '處理中', icon: Loader2 },
        { id: 'completed', label: '已完成', icon: CheckCircle2 },
      ]"
      :key="t.id"
      type="button"
      class="inline-flex items-center gap-1.5 h-10 px-4 text-[13px] border-b-2 -mb-px transition-colors"
      :class="
        tab === t.id
          ? 'border-accent text-ink-strong font-medium'
          : 'border-transparent text-ink-muted hover:text-ink-strong'
      "
      @click="tab = t.id as TabId"
    >
      <component :is="t.icon" :size="14" :stroke-width="1.5" />
      {{ t.label }}
    </button>
  </nav>

  <div
    v-if="apiError"
    class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)] flex items-start gap-2"
  >
    <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5" />
    <span class="flex-1">{{ apiError }}</span>
    <button class="text-[12px] underline" @click="apiError = null">關閉</button>
  </div>

  <!-- Filter + bulk action -->
  <div class="flex items-center justify-between mb-4 gap-3 flex-wrap">
    <div class="w-48">
      <Select v-model="requiresAction" :options="requiresActionOptions" />
    </div>
    <div v-if="tab !== 'completed' && selectedIds.size > 0" class="flex items-center gap-2">
      <span class="text-[12px] text-ink-muted">已選 {{ selectedIds.size }} 筆</span>
      <Button variant="primary" :disabled="bulkMut.isPending.value" @click="bulkComplete">
        <Loader2 v-if="bulkMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
        <CheckCheck v-else :size="14" :stroke-width="1.5" />
        批次標記完成
      </Button>
    </div>
  </div>

  <!-- List -->
  <Card v-if="isLoading">
    <div class="py-10 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>
  </Card>

  <Card
    v-else-if="isError"
    class="text-state-danger text-[13px] text-center py-8"
  >
    載入失敗
  </Card>

  <Card v-else-if="items.length === 0" class="text-center py-12">
    <Bell :size="32" :stroke-width="1.25" class="mx-auto mb-3 text-aux-rice-mid" />
    <p class="text-[13px] text-ink-muted">{{ STATUS_LABEL[tab].label }}的通知 0 筆</p>
  </Card>

  <Card v-else>
    <!-- Select all bar (only for non-completed tabs) -->
    <div
      v-if="tab !== 'completed'"
      class="flex items-center gap-2 pb-3 border-b border-line-hairline mb-3"
    >
      <input
        type="checkbox"
        :checked="selectedIds.size === items.length && items.length > 0"
        :indeterminate="selectedIds.size > 0 && selectedIds.size < items.length"
        @change="selectAll"
      />
      <span class="text-[12px] text-ink-muted">全選本頁</span>
    </div>

    <ul class="divide-y divide-line-hairline">
      <li
        v-for="n in items"
        :key="n.id"
        class="py-3 flex items-start gap-3"
      >
        <input
          v-if="tab !== 'completed'"
          type="checkbox"
          class="mt-1.5"
          :checked="selectedIds.has(n.id)"
          @change="toggleSelect(n.id)"
        />

        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-[12px] font-medium text-ink-strong">{{ TYPE_LABEL[n.type] || n.type }}</span>
            <span
              v-if="n.requires_action"
              class="inline-flex items-center px-1.5 h-[18px] text-[10px] tracking-[0.04em] rounded-[var(--radius-xs)] bg-[var(--color-state-warning)]/[0.18] text-state-warning"
            >需處理</span>
            <span
              class="inline-flex items-center px-1.5 h-[18px] text-[10px] tracking-[0.04em] rounded-[var(--radius-xs)]"
              :class="STATUS_LABEL[n.status].cls"
            >{{ STATUS_LABEL[n.status].label }}</span>
          </div>
          <p class="mt-1 text-[13px] text-ink-default whitespace-pre-line">{{ n.message }}</p>
          <p class="mt-1 text-[11px] text-ink-muted font-mono">
            {{ fmtDateTime(n.created_at) }}
            <span v-if="n.updated_at !== n.created_at"> · 更新 {{ fmtDateTime(n.updated_at) }}</span>
          </p>
        </div>

        <div class="flex items-center gap-1 shrink-0">
          <button
            v-if="buildNotificationLink(n)"
            type="button"
            class="h-8 px-2 inline-flex items-center gap-1 text-[12px] text-ink-muted hover:text-accent rounded-[var(--radius-xs)] hover:bg-paper-subtle"
            @click="gotoRef(n)"
          >
            <ExternalLink :size="12" :stroke-width="1.5" />
            前往
          </button>
          <button
            v-if="n.status === 'unhandled'"
            type="button"
            class="h-8 px-2 inline-flex items-center gap-1 text-[12px] text-ink-muted hover:text-state-info rounded-[var(--radius-xs)] hover:bg-paper-subtle"
            :disabled="updateMut.isPending.value"
            @click="setStatus(n, 'in_progress')"
          >處理中</button>
          <button
            v-if="n.status !== 'completed'"
            type="button"
            class="h-8 px-2 inline-flex items-center gap-1 text-[12px] text-ink-muted hover:text-state-success rounded-[var(--radius-xs)] hover:bg-paper-subtle"
            :disabled="updateMut.isPending.value"
            @click="setStatus(n, 'completed')"
          >完成</button>
          <button
            v-if="n.status === 'completed'"
            type="button"
            class="h-8 px-2 inline-flex items-center gap-1 text-[12px] text-ink-muted hover:text-ink-strong rounded-[var(--radius-xs)] hover:bg-paper-subtle"
            :disabled="updateMut.isPending.value"
            @click="setStatus(n, 'unhandled')"
          >退回未處理</button>
        </div>
      </li>
    </ul>
  </Card>

  <AppPagination
    v-if="total > pageSize"
    v-model:page="page"
    :page-size="pageSize"
    :total="total"
  />
</template>
