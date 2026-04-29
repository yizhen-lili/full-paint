<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ShoppingBag, Wallet, Loader2, AlertTriangle } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Button from '@/shared/ui/Button.vue'

import { useSalesReportQuery } from '../queries'

const route = useRoute()
const router = useRouter()

// 預設區間：本月 1 號 → 今天
function defaultDateFrom(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}
function todayStr(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

const dateFrom = ref<string>(
  typeof route.query.date_from === 'string' ? route.query.date_from : defaultDateFrom(),
)
const dateTo = ref<string>(
  typeof route.query.date_to === 'string' ? route.query.date_to : todayStr(),
)

function syncQuery() {
  router.replace({
    query: {
      ...(dateFrom.value ? { date_from: dateFrom.value } : {}),
      ...(dateTo.value ? { date_to: dateTo.value } : {}),
    },
  })
}

function setPreset(preset: 'today' | 'this_month' | 'last_month' | 'last_30') {
  const today = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const fmt = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

  if (preset === 'today') {
    dateFrom.value = fmt(today)
    dateTo.value = fmt(today)
  } else if (preset === 'this_month') {
    dateFrom.value = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-01`
    dateTo.value = fmt(today)
  } else if (preset === 'last_month') {
    const last = new Date(today.getFullYear(), today.getMonth() - 1, 1)
    const end = new Date(today.getFullYear(), today.getMonth(), 0)
    dateFrom.value = fmt(last)
    dateTo.value = fmt(end)
  } else if (preset === 'last_30') {
    const start = new Date(today)
    start.setDate(start.getDate() - 29)
    dateFrom.value = fmt(start)
    dateTo.value = fmt(today)
  }
  syncQuery()
}

const params = computed(() => ({
  date_from: dateFrom.value || undefined,
  date_to: dateTo.value || undefined,
}))

const { data, isLoading, isError, error } = useSalesReportQuery(params)

function fmtMoney(n: number): string {
  return `NT$ ${n.toLocaleString('zh-TW')}`
}

const avgOrderValue = computed(() => {
  if (!data.value || data.value.total_orders === 0) return 0
  return data.value.total_revenue / data.value.total_orders
})
</script>

<template>
  <PageHeader title="銷售報表" subtitle="訂單與營收概覽" />

  <!-- 篩選 -->
  <Card class="mb-5">
    <div class="flex flex-wrap items-end gap-3">
      <div>
        <Label>從</Label>
        <Input v-model="dateFrom" type="date" @change="syncQuery" />
      </div>
      <div>
        <Label>至</Label>
        <Input v-model="dateTo" type="date" @change="syncQuery" />
      </div>
      <div class="flex flex-wrap items-center gap-2 ml-auto">
        <Button variant="secondary" @click="setPreset('today')">今天</Button>
        <Button variant="secondary" @click="setPreset('this_month')">本月</Button>
        <Button variant="secondary" @click="setPreset('last_month')">上個月</Button>
        <Button variant="secondary" @click="setPreset('last_30')">近 30 天</Button>
      </div>
    </div>
  </Card>

  <!-- Loading -->
  <div v-if="isLoading" class="py-20 flex justify-center text-ink-muted">
    <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
  </div>

  <!-- Error -->
  <div
    v-else-if="isError"
    class="px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)] flex items-start gap-2"
  >
    <AlertTriangle :size="14" :stroke-width="1.5" class="mt-0.5" />
    {{ (error as { message?: string })?.message ?? '載入失敗' }}
  </div>

  <!-- Metrics -->
  <template v-else-if="data">
    <p class="text-[12px] text-ink-muted mb-3">區間：{{ data.period }}</p>

    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
      <Card>
        <div class="flex items-center justify-between">
          <p class="text-[12px] text-ink-muted tracking-[0.04em] uppercase">已完成訂單數</p>
          <ShoppingBag :size="16" :stroke-width="1.5" class="text-ink-muted" />
        </div>
        <p class="font-display text-ink-strong text-[28px] mt-2">{{ data.total_orders.toLocaleString() }}</p>
      </Card>

      <Card>
        <div class="flex items-center justify-between">
          <p class="text-[12px] text-ink-muted tracking-[0.04em] uppercase">總營收</p>
          <Wallet :size="16" :stroke-width="1.5" class="text-ink-muted" />
        </div>
        <p class="font-display text-ink-strong text-[28px] mt-2 font-mono">{{ fmtMoney(data.total_revenue) }}</p>
      </Card>

      <Card>
        <p class="text-[12px] text-ink-muted tracking-[0.04em] uppercase">平均訂單金額</p>
        <p class="font-display text-ink-strong text-[28px] mt-2 font-mono">{{ fmtMoney(Math.round(avgOrderValue)) }}</p>
        <p v-if="data.total_orders === 0" class="text-[11px] text-ink-muted mt-1">區間內無訂單</p>
      </Card>
    </div>

    <Card v-if="data.note">
      <p class="text-[12px] text-ink-muted tracking-[0.04em] uppercase mb-2">備註</p>
      <p class="text-[13px] text-ink-default whitespace-pre-line">{{ data.note }}</p>
    </Card>

    <Card class="mt-5">
      <p class="text-[12px] text-ink-muted">
        🚧 細部圖表（每日 / 每月趨勢、商品銷售排行、客戶分布）— 等後端補
        <code class="font-mono">GET /admin/reports/sales/by-day</code> 與
        <code class="font-mono">/by-product</code> 端點後再整合 echarts。
      </p>
    </Card>
  </template>
</template>
