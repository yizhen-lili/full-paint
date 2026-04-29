<script setup lang="ts">
import type { JobStatus } from '../api'

defineProps<{ status: JobStatus; approved?: boolean }>()

const statusLabel: Record<JobStatus, { label: string; cls: string }> = {
  pending: { label: '等待中', cls: 'bg-[var(--color-state-warning)]/[0.12] text-state-warning' },
  processing: { label: '處理中', cls: 'bg-[var(--color-state-info)]/[0.12] text-state-info animate-pulse' },
  completed: { label: '已完成', cls: 'bg-[var(--color-state-success)]/[0.12] text-state-success' },
  failed: { label: '失敗', cls: 'bg-[var(--color-state-danger)]/[0.12] text-state-danger' },
  cancelled: { label: '已取消', cls: 'bg-paper-subtle text-ink-muted' },
}
</script>

<template>
  <span class="inline-flex items-center gap-1.5">
    <span
      class="inline-flex items-center px-2 h-[22px] text-[11px] tracking-[0.04em] rounded-[var(--radius-xs)]"
      :class="statusLabel[status].cls"
    >
      {{ statusLabel[status].label }}
    </span>
    <span
      v-if="status === 'completed'"
      class="inline-flex items-center px-2 h-[22px] text-[11px] tracking-[0.04em] rounded-[var(--radius-xs)]"
      :class="
        approved
          ? 'bg-[var(--color-accent)]/[0.10] text-accent'
          : 'border border-line-strong text-ink-muted'
      "
    >
      {{ approved ? '已審核' : '待審核' }}
    </span>
  </span>
</template>
