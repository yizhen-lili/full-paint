<script setup lang="ts">
import { computed } from 'vue'
import { Check } from 'lucide-vue-next'
import type { RequestStatus } from '../api'

const props = defineProps<{
  status: RequestStatus
}>()

interface Step {
  key: 'submitted' | 'quoting' | 'sent' | 'confirmed'
  label: string
  caption: string
}

const STEPS: Step[] = [
  { key: 'submitted', label: '提交', caption: 'Submitted' },
  { key: 'quoting', label: '報價中', caption: 'Quoting' },
  { key: 'sent', label: '報價送達', caption: 'Quoted' },
  { key: 'confirmed', label: '已確認', caption: 'Confirmed' },
]

// 終態（rejected / expired）→ 整條 stepper 灰封存
const isArchived = computed(() => ['quote_rejected', 'quote_expired'].includes(props.status))

// 計算每個 step 的狀態：done / active / upcoming
function stepState(key: Step['key']): 'done' | 'active' | 'upcoming' {
  const s = props.status
  if (isArchived.value) return 'upcoming'

  switch (key) {
    case 'submitted':
      return 'done' // 進這頁 = 已提交
    case 'quoting':
      if (['quote_pending', 'negotiating', 'draft_revision'].includes(s)) return 'active'
      return 'done' // quote_sent 起 = quoting 完成
    case 'sent':
      if (s === 'quote_sent') return 'active'
      if (s === 'quote_confirmed') return 'done'
      return 'upcoming'
    case 'confirmed':
      if (s === 'quote_confirmed') return 'done'
      return 'upcoming'
  }
}
</script>

<template>
  <ol class="stepper" :class="{ 'is-archived': isArchived }" :aria-label="isArchived ? '此申請已封存' : '客製申請進度'">
    <li
      v-for="(step, idx) in STEPS"
      :key="step.key"
      class="step"
      :class="`step-${stepState(step.key)}`"
    >
      <div class="step-line" v-if="idx > 0" aria-hidden="true" />
      <div class="step-mark" aria-hidden="true">
        <Check v-if="stepState(step.key) === 'done'" :size="12" :stroke-width="2" />
        <span v-else-if="stepState(step.key) === 'active'" class="dot-pulse" />
        <span v-else class="dot-dim" />
      </div>
      <div class="step-text">
        <span class="step-no">{{ String(idx + 1).padStart(2, '0') }}</span>
        <span class="step-label">{{ step.label }}</span>
        <span class="step-caption">{{ step.caption }}</span>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.stepper {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  padding: 0;
  margin: 0;
  list-style: none;
}

.step {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 0 16px 0 0;
}

.step-line {
  position: absolute;
  top: 13px;
  left: 0;
  right: calc(100% - 28px);
  height: 1px;
  background: var(--color-line);
  transform: translateX(-100%);
}
.step-done .step-line,
.step-active .step-line {
  background: var(--color-accent);
}

.step-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid var(--color-line);
  background: var(--color-paper-canvas);
  color: var(--color-ink-muted);
  margin-bottom: 12px;
  position: relative;
  z-index: 1;
}
.step-done .step-mark {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-paper-canvas);
}
.step-active .step-mark {
  background: var(--color-paper-canvas);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.dot-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: pulse 1.6s ease-in-out infinite;
}
.dot-dim {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-line);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.6; }
}

.step-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.step-no {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.22em;
  color: var(--color-ink-muted);
}
.step-label {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
}
.step-active .step-label,
.step-done .step-label {
  color: var(--color-ink-strong);
}
.step-caption {
  font-family: var(--font-display);
  font-style: italic;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
}

/* 封存態：整條灰調 */
.stepper.is-archived .step-mark {
  background: var(--color-paper-deep);
  border-color: var(--color-line-subtle);
  color: var(--color-ink-disabled);
}
.stepper.is-archived .step-line {
  background: var(--color-line-subtle);
}
.stepper.is-archived .step-no,
.stepper.is-archived .step-label,
.stepper.is-archived .step-caption {
  color: var(--color-ink-disabled);
}

@media (max-width: 639px) {
  .stepper { grid-template-columns: repeat(4, 1fr); gap: 0; }
  .step { padding: 0 6px 0 0; }
  .step-no { display: none; }
  .step-caption { display: none; }
  .step-label { font-size: 12px; }
}
</style>
