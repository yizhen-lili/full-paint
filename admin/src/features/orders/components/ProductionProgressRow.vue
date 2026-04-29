<script setup lang="ts">
import { computed } from 'vue'
import { Loader2, ChevronRight } from 'lucide-vue-next'
import type { OrderStatus, ProductionProgress, ProductionProgressStatus } from '../api'

const props = defineProps<{
  progress: ProductionProgress
  orderStatus: OrderStatus
  pending: boolean
}>()

const emit = defineEmits<{
  advance: [status: 'manufacturing' | 'packaging' | 'ready_to_ship']
}>()

interface Stage {
  status: ProductionProgressStatus
  label: string
  hint: string
  /** 是否可由管理員手動切換到這個 stage（pending/in_production/shipped 是自動的）。 */
  manual: boolean
}

const STAGES: Stage[] = [
  { status: 'pending', label: '等待開始', hint: '付款確認後自動建立', manual: false },
  { status: 'in_production', label: '製作中', hint: '客製訂單自動推進', manual: false },
  { status: 'manufacturing', label: '印製模板 / 備料', hint: '管理員手動', manual: true },
  { status: 'packaging', label: '打包中', hint: '管理員手動', manual: true },
  { status: 'ready_to_ship', label: '備貨完成', hint: '管理員手動', manual: true },
  { status: 'shipped', label: '已出貨', hint: '由「出貨」按鈕自動推進', manual: false },
]

const currentIndex = computed(() => STAGES.findIndex((s) => s.status === props.progress.status))

const allowJump = computed(
  () => props.orderStatus === 'paid' || props.orderStatus === 'processing',
)

function isManualStage(s: ProductionProgressStatus): s is 'manufacturing' | 'packaging' | 'ready_to_ship' {
  return s === 'manufacturing' || s === 'packaging' || s === 'ready_to_ship'
}

function clickable(stage: Stage): boolean {
  if (!allowJump.value) return false
  if (!stage.manual) return false
  if (stage.status === props.progress.status) return false
  return isManualStage(stage.status)
}

function onJump(stage: Stage) {
  if (clickable(stage) && isManualStage(stage.status)) {
    emit('advance', stage.status)
  }
}
</script>

<template>
  <div class="px-3 py-2.5 bg-paper-subtle rounded-[var(--radius-xs)]">
    <div class="flex items-center justify-between mb-2">
      <span class="text-[11px] tracking-[0.04em] text-ink-muted uppercase">生產進度</span>
      <Loader2 v-if="pending" :size="12" :stroke-width="1.5" class="animate-spin text-ink-muted" />
    </div>

    <ol class="flex items-center gap-0 flex-wrap">
      <li v-for="(stage, i) in STAGES" :key="stage.status" class="flex items-center">
        <button
          type="button"
          :disabled="!clickable(stage)"
          :title="stage.hint"
          class="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-[var(--radius-xs)] text-[12px] tracking-[0.02em] transition-colors duration-[120ms] disabled:cursor-default"
          :class="
            i === currentIndex
              ? 'bg-accent text-paper-surface font-medium shadow-sm'
              : i < currentIndex
                ? clickable(stage)
                  ? 'bg-paper-surface text-ink-default border border-line-hairline hover:bg-paper-canvas'
                  : 'bg-transparent text-ink-muted'
                : clickable(stage)
                  ? 'bg-paper-surface text-ink-default border border-line-hairline hover:bg-paper-canvas'
                  : 'bg-transparent text-ink-muted'
          "
          @click="onJump(stage)"
        >
          <span
            class="inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-mono"
            :class="
              i === currentIndex
                ? 'bg-paper-surface text-accent'
                : i < currentIndex
                  ? 'bg-state-success/20 text-state-success'
                  : 'bg-paper-canvas text-ink-muted'
            "
          >
            {{ i < currentIndex ? '✓' : i + 1 }}
          </span>
          {{ stage.label }}
        </button>
        <ChevronRight
          v-if="i < STAGES.length - 1"
          :size="12"
          :stroke-width="1.5"
          class="mx-0.5 text-line-strong"
        />
      </li>
    </ol>

    <p v-if="!allowJump" class="mt-2 text-[11px] text-ink-muted">
      （訂單目前狀態無法手動調整生產進度）
    </p>
    <p v-else class="mt-2 text-[11px] text-ink-muted">
      點任一手動階段即可切換（含返回上一階段）；前後與已出貨由系統自動處理。
    </p>
  </div>
</template>
