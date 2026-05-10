<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ChevronLeft,
  Loader2,
  Pencil,
  ShoppingBag,
  Sparkles,
  Tag,
  AlertTriangle,
} from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import { useAuthStore } from '@/features/auth/store'

import EditUserDialog from '../components/EditUserDialog.vue'
import {
  useForceVerifyEmailMutation,
  useResendVerificationMutation,
  useUpdateUserMutation,
  useUserQuery,
} from '../queries'
import type { UpdateUserPayload } from '../api'

import { useOrdersQuery } from '@/features/orders/queries'
import { useCustomRequestsQuery } from '@/features/custom_requests/queries'
import { useUserCouponsQuery } from '@/features/discounts/queries'

const route = useRoute()
const router = useRouter()

const userId = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''))

const authStore = useAuthStore()
const isSelf = computed(() => authStore.user?.id === userId.value)

const { data: user, isLoading, isError, error } = useUserQuery(userId)
const updateMut = useUpdateUserMutation(userId.value)

const apiError = ref<string | null>(null)
const editOpen = ref(false)

async function onConfirmEdit(payload: UpdateUserPayload) {
  apiError.value = null
  try {
    await updateMut.mutateAsync(payload)
    editOpen.value = false
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '儲存失敗'
  }
}

// ── 救援動作（未驗證 user 救援）────────────────────────────────────────
const resendMut = useResendVerificationMutation(userId)
const forceVerifyMut = useForceVerifyEmailMutation(userId)
const recoveryMsg = ref<{ kind: 'success' | 'error'; text: string } | null>(null)

async function doResendVerification() {
  recoveryMsg.value = null
  try {
    await resendMut.mutateAsync()
    recoveryMsg.value = {
      kind: 'success',
      text: `驗證信已重寄到 ${user.value?.email ?? ''}`,
    }
  } catch (e) {
    recoveryMsg.value = {
      kind: 'error',
      text: (e as { message?: string }).message || '寄送失敗',
    }
  }
}

async function doForceVerify() {
  if (!confirm(
    `確定要強制標記此帳號 email 為已驗證嗎？\n\n`
    + `此動作會跳過 email 驗證流程，user 立刻可以登入。\n`
    + `僅在 user 真的收不到驗證信時使用。`,
  )) return
  recoveryMsg.value = null
  try {
    await forceVerifyMut.mutateAsync()
    recoveryMsg.value = { kind: 'success', text: '已強制標記為已驗證' }
  } catch (e) {
    recoveryMsg.value = {
      kind: 'error',
      text: (e as { message?: string }).message || '操作失敗',
    }
  }
}

// ── Tabs（client filter by user_id / email）──────────────────────────
const tab = ref<'orders' | 'custom' | 'coupons'>('orders')

// 訂單：用 search=email 過濾（後端的 search 欄位涵蓋 email）
const ordersParams = computed(() => ({
  search: user.value?.email,
  page: 1,
  page_size: 50,
}))
const ordersQuery = useOrdersQuery(ordersParams)

// 客製：list 全部後 client filter user_id
const customParams = computed(() => ({ page: 1, page_size: 100 }))
const customQuery = useCustomRequestsQuery(customParams)
const userCustomRequests = computed(
  () => customQuery.data.value?.items.filter((c) => c.user_id === userId.value) ?? [],
)

// 持有券
const couponsParams = computed(() => ({ user_id: userId.value }))
const couponsQuery = useUserCouponsQuery(couponsParams)

// ── helpers ───────────────────────────────────────────────────────────
function initials(name: string): string {
  return (name || '?').slice(0, 2).toUpperCase()
}

function fmtDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fmtMoney(n: number | string): string {
  const v = typeof n === 'string' ? Number(n) : n
  if (!Number.isFinite(v)) return '—'
  return `NT$ ${v.toLocaleString('zh-TW')}`
}
</script>

<template>
  <div class="flex items-center gap-2 mb-3">
    <button
      type="button"
      class="text-[13px] text-ink-muted hover:text-ink-strong inline-flex items-center gap-1 transition-colors"
      @click="router.push('/admin/users')"
    >
      <ChevronLeft :size="14" :stroke-width="1.5" />
      返回用戶列表
    </button>
  </div>

  <div v-if="isLoading" class="flex items-center justify-center py-20 text-ink-muted">
    <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    <span class="ml-2 text-[13px]">載入中...</span>
  </div>

  <div
    v-else-if="isError"
    class="px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)]"
  >
    載入失敗：{{ (error as { message?: string })?.message ?? '用戶不存在' }}
  </div>

  <template v-else-if="user">
    <header class="mb-7 pb-5 border-b border-line-hairline flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
      <div class="flex items-center gap-3">
        <div
          class="w-12 h-12 rounded-full flex items-center justify-center text-[14px] font-medium tracking-[0.04em] shrink-0"
          :class="user.role === 'admin' ? 'bg-accent text-paper-surface' : 'bg-aux-rice-mid/40 text-ink-default'"
        >
          {{ initials(user.name) }}
        </div>
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <h1 class="font-display text-ink-strong text-[22px] leading-[30px]">{{ user.name }}</h1>
            <span
              class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)]"
              :class="
                user.role === 'admin'
                  ? 'bg-[var(--color-accent)]/[0.10] text-accent'
                  : 'bg-paper-subtle text-ink-default'
              "
            >
              {{ user.role === 'admin' ? '管理員' : '客戶' }}
            </span>
            <span
              class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)]"
              :class="
                user.is_active
                  ? 'bg-[var(--color-state-success)]/[0.10] text-state-success'
                  : 'bg-[var(--color-state-danger)]/[0.10] text-state-danger'
              "
            >
              {{ user.is_active ? '啟用中' : '已停用' }}
            </span>
            <span
              v-if="isSelf"
              class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)] bg-paper-subtle text-ink-muted"
            >你自己</span>
          </div>
          <p class="mt-1 text-[13px] text-ink-muted">{{ user.email }}</p>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2 shrink-0">
        <Button variant="primary" @click="editOpen = true">
          <Pencil :size="14" :stroke-width="1.5" />
          編輯
        </Button>
      </div>
    </header>

    <div
      v-if="apiError"
      class="mb-5 px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)] flex items-start gap-2"
    >
      <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5" />
      <span class="flex-1">{{ apiError }}</span>
      <button class="text-[12px] underline" @click="apiError = null">關閉</button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <!-- Side：個人資料 -->
      <div class="space-y-5">
        <Card>
          <h2 class="font-display text-ink-strong text-[16px] leading-[24px] mb-3">基本資料</h2>
          <dl class="text-[13px] space-y-1.5">
            <div class="flex justify-between"><dt class="text-ink-muted">名稱</dt><dd>{{ user.name }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-muted">Email</dt><dd class="text-[12px]">{{ user.email }}</dd></div>
            <div class="flex justify-between"><dt class="text-ink-muted">Email 驗證</dt>
              <dd>
                <span
                  class="inline-flex items-center px-1.5 h-[18px] text-[10px] rounded-[var(--radius-xs)]"
                  :class="
                    user.is_email_verified
                      ? 'bg-[var(--color-state-success)]/[0.10] text-state-success'
                      : 'border border-[var(--color-accent-wine)]/40 bg-[var(--color-accent-wine)]/[0.08] text-accent-wine font-medium'
                  "
                >
                  {{ user.is_email_verified ? '已驗證' : '未驗證' }}
                </span>
              </dd>
            </div>
            <div class="flex justify-between"><dt class="text-ink-muted">註冊</dt><dd class="font-mono text-[12px]">{{ fmtDateTime(user.created_at) }}</dd></div>
          </dl>

          <!-- 救援動作（僅未驗證 user 顯示）-->
          <div
            v-if="!user.is_email_verified"
            class="mt-4 pt-4 border-t border-line-hairline"
          >
            <p class="text-[11px] text-ink-muted mb-2 leading-[1.7]">
              此帳號尚未完成 email 驗證，無法登入。
            </p>
            <div class="flex flex-col gap-2">
              <Button
                variant="secondary"
                size="sm"
                :loading="resendMut.isPending.value"
                @click="doResendVerification"
              >
                重寄驗證信
              </Button>
              <Button
                variant="ghost"
                size="sm"
                :loading="forceVerifyMut.isPending.value"
                @click="doForceVerify"
              >
                強制標為已驗證（跳過 email）
              </Button>
            </div>
            <div
              v-if="recoveryMsg"
              class="mt-2 px-2 py-1.5 text-[11px] rounded-[var(--radius-xs)]"
              :class="
                recoveryMsg.kind === 'success'
                  ? 'bg-[var(--color-state-success)]/[0.08] text-state-success'
                  : 'bg-[var(--color-state-danger)]/[0.08] text-state-danger'
              "
            >
              {{ recoveryMsg.text }}
            </div>
          </div>
        </Card>
      </div>

      <!-- Main：tabs -->
      <div class="lg:col-span-2">
        <nav class="flex items-center gap-1 mb-5 border-b border-line-hairline">
          <button
            v-for="t in [
              { id: 'orders', label: '訂單', icon: ShoppingBag },
              { id: 'custom', label: '客製申請', icon: Sparkles },
              { id: 'coupons', label: '持有券', icon: Tag },
            ]"
            :key="t.id"
            type="button"
            class="inline-flex items-center gap-1.5 h-10 px-4 text-[13px] border-b-2 -mb-px transition-colors"
            :class="
              tab === t.id
                ? 'border-accent text-ink-strong font-medium'
                : 'border-transparent text-ink-muted hover:text-ink-strong'
            "
            @click="tab = t.id as 'orders' | 'custom' | 'coupons'"
          >
            <component :is="t.icon" :size="14" :stroke-width="1.5" />
            {{ t.label }}
          </button>
        </nav>

        <!-- Tab: orders -->
        <Card v-if="tab === 'orders'">
          <div v-if="ordersQuery.isLoading.value" class="py-8 flex justify-center text-ink-muted">
            <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
          </div>
          <div
            v-else-if="(ordersQuery.data.value?.items.length ?? 0) === 0"
            class="text-center py-8 text-ink-muted text-[13px]"
          >
            此用戶尚無訂單
          </div>
          <ul v-else class="divide-y divide-line-hairline">
            <li
              v-for="o in ordersQuery.data.value?.items"
              :key="o.id"
              class="py-3 flex items-center justify-between gap-3 cursor-pointer hover:bg-paper-subtle px-2 -mx-2 rounded-[var(--radius-xs)]"
              @click="router.push(`/admin/orders/${o.id}`)"
            >
              <div>
                <p class="font-mono text-[13px] text-ink-strong">{{ o.order_number }}</p>
                <p class="text-[11px] text-ink-muted">{{ fmtDateTime(o.created_at) }}</p>
              </div>
              <div class="text-right">
                <p class="font-mono text-[13px] text-ink-strong">{{ fmtMoney(o.total) }}</p>
                <p class="text-[11px] text-ink-muted">{{ o.status }}</p>
              </div>
            </li>
          </ul>
        </Card>

        <!-- Tab: custom -->
        <Card v-else-if="tab === 'custom'">
          <div v-if="customQuery.isLoading.value" class="py-8 flex justify-center text-ink-muted">
            <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
          </div>
          <div v-else-if="userCustomRequests.length === 0" class="text-center py-8 text-ink-muted text-[13px]">
            此用戶尚無客製申請
          </div>
          <ul v-else class="divide-y divide-line-hairline">
            <li
              v-for="c in userCustomRequests"
              :key="c.id"
              class="py-3 flex items-center justify-between gap-3 cursor-pointer hover:bg-paper-subtle px-2 -mx-2 rounded-[var(--radius-xs)]"
              @click="router.push(`/admin/custom-requests/${c.id}`)"
            >
              <div>
                <p class="font-mono text-[12px]">#{{ c.id.slice(0, 8) }}</p>
                <p class="text-[11px] text-ink-muted">{{ fmtDateTime(c.created_at) }}</p>
              </div>
              <div class="text-right">
                <p class="text-[12px]">{{ c.status }}</p>
                <p v-if="c.quoted_price" class="font-mono text-[12px] text-ink-strong">{{ fmtMoney(c.quoted_price) }}</p>
              </div>
            </li>
          </ul>
        </Card>

        <!-- Tab: coupons -->
        <Card v-else-if="tab === 'coupons'">
          <div v-if="couponsQuery.isLoading.value" class="py-8 flex justify-center text-ink-muted">
            <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
          </div>
          <div
            v-else-if="(couponsQuery.data.value?.items.length ?? 0) === 0"
            class="text-center py-8 text-ink-muted text-[13px]"
          >
            此用戶持有 0 張券
          </div>
          <ul v-else class="space-y-2">
            <li
              v-for="c in couponsQuery.data.value?.items"
              :key="c.id"
              class="p-3 border border-line-hairline rounded-[var(--radius-xs)] text-[13px]"
            >
              <div class="flex items-center justify-between gap-2">
                <span class="text-ink-strong">{{ c.coupon_type ?? 'public_code' }}</span>
                <span
                  class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)]"
                  :class="
                    c.is_used
                      ? 'bg-paper-subtle text-ink-muted'
                      : 'bg-[var(--color-state-success)]/[0.10] text-state-success'
                  "
                >
                  {{ c.is_used ? '已使用' : '可用' }}
                </span>
              </div>
              <p class="mt-1 text-[12px] text-ink-muted">
                {{ c.discount_type === 'percentage' ? `折扣 ${c.discount_value}%` : `折 NT$ ${c.discount_value}` }}
                <span v-if="c.min_purchase">· 滿 {{ c.min_purchase }}</span>
                <span v-if="c.expires_at">· 到期 {{ fmtDateTime(c.expires_at) }}</span>
              </p>
            </li>
          </ul>
        </Card>
      </div>
    </div>

    <EditUserDialog
      :open="editOpen"
      :user="user"
      :is-self="isSelf"
      :pending="updateMut.isPending.value"
      @close="editOpen = false"
      @confirm="onConfirmEdit"
    />
  </template>
</template>
