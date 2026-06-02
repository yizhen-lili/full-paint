<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ChevronLeft } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    /** 文字 label；預設「回上一頁」 */
    label?: string
    /** history 為空（直連進來）時的 fallback 路徑；預設 / 首頁 */
    fallback?: string
  }>(),
  {
    label: '回上一頁',
    fallback: '/',
  },
)

const router = useRouter()

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push(props.fallback)
  }
}
</script>

<template>
  <button type="button" class="back-link" @click="goBack">
    <ChevronLeft :size="14" :stroke-width="1.5" />
    {{ label }}
  </button>
</template>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 16px;
  padding: 4px 8px 4px 4px;
  background: transparent;
  border: none;
  border-radius: var(--radius-xs);
  font-size: 13px;
  color: var(--color-ink-muted);
  cursor: pointer;
  transition: color 120ms;
  font-family: inherit;
}
.back-link:hover {
  color: var(--color-ink-strong);
}
</style>
