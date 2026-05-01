<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft, Loader2, Download } from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'

import { useBatchQuery } from '../queries'
import { STATUS_LABEL } from '../api'

const route = useRoute()
const router = useRouter()

const id = computed(() => (typeof route.params.id === 'string' ? route.params.id : ''))

const { data: batch, isLoading, isError } = useBatchQuery(id)

function fmtDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fmtMoney(n: number): string {
  return `NT$ ${n.toLocaleString('zh-TW')}`
}

function fmtInch(n: number): string {
  return n.toFixed(2)
}
</script>

<template>
  <div class="flex items-center gap-2 mb-3">
    <button
      type="button"
      class="text-[13px] text-ink-muted hover:text-ink-strong inline-flex items-center gap-1 transition-colors"
      @click="router.push('/admin/print-batches')"
    >
      <ChevronLeft :size="14" :stroke-width="1.5" />
      返回批次列表
    </button>
  </div>

  <div v-if="isLoading" class="py-20 flex justify-center text-ink-muted">
    <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
  </div>

  <div
    v-else-if="isError"
    class="px-4 py-3 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)]"
  >載入失敗</div>

  <template v-else-if="batch">
    <header class="mb-7 pb-5 border-b border-line-hairline flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 flex-wrap">
          <h1 class="font-display text-ink-strong text-[24px] leading-[32px]">
            列印批次
            <span class="font-mono text-[20px] ml-1">#{{ batch.id.slice(0, 8) }}</span>
          </h1>
          <span
            class="inline-flex items-center px-2 h-[22px] text-[12px] tracking-[0.04em] rounded-[var(--radius-xs)]"
            :class="STATUS_LABEL[batch.status].cls"
          >
            {{ STATUS_LABEL[batch.status].label }}
          </span>
        </div>
        <p class="mt-1 text-[13px] text-ink-muted">
          建立於 {{ fmtDateTime(batch.created_at) }}
          <span v-if="batch.finalized_at"> · 完成於 {{ fmtDateTime(batch.finalized_at) }}</span>
        </p>
      </div>
      <div class="shrink-0">
        <a
          v-if="batch.pdf_url"
          :href="batch.pdf_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-[var(--radius-xs)] bg-accent text-paper-surface text-[13px] font-medium hover:opacity-90 transition-opacity"
        >
          <Download :size="14" :stroke-width="1.5" />
          下載 PDF
        </a>
      </div>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <!-- Main：明細 -->
      <div class="lg:col-span-2 space-y-5">
        <Card>
          <h2 class="font-display text-ink-strong text-[18px] mb-4">列印項目（{{ batch.items.length }}）</h2>
          <table class="w-full text-[13px]">
            <thead>
              <tr class="border-b border-line-hairline text-left text-ink-muted">
                <th class="py-2">job ID</th>
                <th class="py-2">尺寸</th>
                <th class="py-2 text-right">單份吋</th>
                <th class="py-2 text-right">數量</th>
                <th class="py-2">來源</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="i in batch.items" :key="i.id" class="border-b border-line-hairline last:border-0">
                <td class="py-2 font-mono text-[12px]">{{ i.production_job_id.slice(0, 8) }}</td>
                <td class="py-2 font-mono text-[12px]">{{ i.canvas_w_cm }} × {{ i.canvas_h_cm }} cm</td>
                <td class="py-2 text-right font-mono">{{ fmtInch(i.inch_per_unit) }}</td>
                <td class="py-2 text-right font-mono">{{ i.quantity }}</td>
                <td class="py-2 text-[12px] text-ink-muted">{{ i.source_type === 'order_item' ? '訂單' : '製作' }}</td>
              </tr>
            </tbody>
          </table>
        </Card>

        <Card v-if="batch.admin_notes">
          <h2 class="font-display text-ink-strong text-[18px] mb-3">內部備註</h2>
          <p class="text-[13px] text-ink-default whitespace-pre-line">{{ batch.admin_notes }}</p>
        </Card>
      </div>

      <!-- Side：成本 -->
      <div class="space-y-5">
        <Card>
          <h2 class="font-display text-ink-strong text-[16px] mb-3">成本明細</h2>
          <dl class="text-[13px] space-y-1.5">
            <div class="flex justify-between">
              <dt class="text-ink-muted">總吋數</dt>
              <dd class="font-mono">{{ fmtInch(batch.total_inch_count) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-ink-muted">計費吋數</dt>
              <dd class="font-mono">{{ fmtInch(batch.billable_inch_count) }}</dd>
            </div>
            <div class="flex justify-between pt-2 border-t border-line-hairline mt-2">
              <dt class="text-ink-muted">列印成本</dt>
              <dd class="font-mono">{{ fmtMoney(batch.print_cost) }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-ink-muted">裁切成本</dt>
              <dd class="font-mono">{{ fmtMoney(batch.cut_cost) }}</dd>
            </div>
            <div class="flex justify-between pt-2 border-t border-line-hairline mt-2">
              <dt class="text-ink-strong font-medium">總成本</dt>
              <dd class="font-mono text-ink-strong font-medium">{{ fmtMoney(batch.total_cost) }}</dd>
            </div>
          </dl>
        </Card>
      </div>
    </div>
  </template>
</template>
