<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Users } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import AppSearchInput from '@/shared/components/AppSearchInput.vue'
import AppDataTable, { type Column } from '@/shared/components/AppDataTable.vue'
import AppPagination from '@/shared/components/AppPagination.vue'
import Select from '@/shared/ui/Select.vue'

import { useUsersQuery } from '../queries'
import type { AdminUser, UserRole } from '../api'

const router = useRouter()
const route = useRoute()

const search = ref<string>(typeof route.query.search === 'string' ? route.query.search : '')
const role = ref<'' | UserRole>(
  (typeof route.query.role === 'string' ? route.query.role : '') as '' | UserRole,
)
const isActive = ref<'' | 'true' | 'false'>(
  (typeof route.query.is_active === 'string' ? route.query.is_active : '') as '' | 'true' | 'false',
)
const page = ref<number>(Number(route.query.page) > 0 ? Number(route.query.page) : 1)
const pageSize = 20

watch([search, role, isActive], () => {
  page.value = 1
})

watch(
  [search, role, isActive, page],
  () => {
    router.replace({
      query: {
        ...(search.value ? { search: search.value } : {}),
        ...(role.value ? { role: role.value } : {}),
        ...(isActive.value ? { is_active: isActive.value } : {}),
        ...(page.value > 1 ? { page: String(page.value) } : {}),
      },
    })
  },
  { flush: 'post' },
)

const params = computed(() => ({
  search: search.value || undefined,
  role: role.value || undefined,
  is_active:
    isActive.value === 'true' ? true : isActive.value === 'false' ? false : undefined,
  page: page.value,
  page_size: pageSize,
}))

const { data, isLoading, isError, error } = useUsersQuery(params)
const items = computed(() => data.value?.items ?? [])
const total = computed(() => data.value?.total ?? 0)

const roleOptions = [
  { value: '', label: '全部角色' },
  { value: 'admin', label: '管理員 admin' },
  { value: 'customer', label: '一般用戶 customer' },
]

const activeOptions = [
  { value: '', label: '全部狀態' },
  { value: 'true', label: '啟用中' },
  { value: 'false', label: '已停用' },
]

const columns: Column<AdminUser>[] = [
  { key: 'avatar', label: '', width: '50px' },
  { key: 'name', label: '名稱' },
  { key: 'email', label: 'Email' },
  { key: 'role', label: '角色', width: '90px' },
  { key: 'status', label: '狀態', width: '100px' },
  { key: 'created_at', label: '註冊時間', width: '160px' },
]

function goDetail(id: string) {
  router.push(`/admin/users/${id}`)
}

function initials(name: string): string {
  return (name || '?').slice(0, 2).toUpperCase()
}

function fmtDateTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<template>
  <PageHeader title="用戶管理" subtitle="客戶與管理員帳號維護" />

  <section class="bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] p-4 mb-5">
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <AppSearchInput v-model="search" placeholder="搜尋名稱 / email..." />
      <Select v-model="role" :options="roleOptions" />
      <Select v-model="isActive" :options="activeOptions" />
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
    empty-text="尚無用戶"
    :empty-icon="Users"
    @row-click="(r) => goDetail(r.id)"
  >
    <template #cell-avatar="{ row }">
      <div
        class="w-9 h-9 rounded-full flex items-center justify-center text-[12px] font-medium tracking-[0.04em]"
        :class="row.role === 'admin' ? 'bg-accent text-paper-surface' : 'bg-aux-rice-mid/40 text-ink-default'"
      >
        {{ initials(row.name) }}
      </div>
    </template>

    <template #cell-name="{ row }">
      <span class="font-medium text-ink-strong">{{ row.name }}</span>
    </template>

    <template #cell-email="{ row }">
      <span class="text-[12px] text-ink-default">{{ row.email }}</span>
      <span
        v-if="!row.is_email_verified"
        class="ml-1 inline-flex items-center px-1.5 h-[16px] text-[10px] tracking-[0.04em] rounded-[var(--radius-xs)] bg-paper-subtle text-ink-muted"
      >未驗證</span>
    </template>

    <template #cell-role="{ row }">
      <span
        class="inline-flex items-center px-2 h-[20px] text-[11px] tracking-[0.04em] rounded-[var(--radius-xs)]"
        :class="
          row.role === 'admin'
            ? 'bg-[var(--color-accent)]/[0.10] text-accent'
            : 'bg-paper-subtle text-ink-default'
        "
      >
        {{ row.role === 'admin' ? '管理員' : '客戶' }}
      </span>
    </template>

    <template #cell-status="{ row }">
      <span
        class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)]"
        :class="
          row.is_active
            ? 'bg-[var(--color-state-success)]/[0.10] text-state-success'
            : 'bg-[var(--color-state-danger)]/[0.10] text-state-danger'
        "
      >
        {{ row.is_active ? '啟用中' : '已停用' }}
      </span>
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
