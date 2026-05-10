<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  FileText,
  Settings,
  DollarSign,
  Plus as PlusIcon,
  Sparkles,
  Tag,
  AlertTriangle,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const tabs = [
  { id: 'pages', label: '靜態頁面', icon: FileText },
  { id: 'settings', label: '系統設定', icon: Settings },
  { id: 'prices', label: '客製定價', icon: DollarSign },
  { id: 'surcharges', label: '加費項目', icon: PlusIcon },
  { id: 'cases', label: '完成案例', icon: Sparkles },
  { id: 'categories', label: '案例分類', icon: Tag },
  { id: 'danger', label: 'Danger Zone', icon: AlertTriangle },
] as const

const current = computed(() => {
  const t = route.query.tab
  if (typeof t === 'string' && tabs.find((x) => x.id === t)) return t
  return 'pages'
})

function selectTab(id: string) {
  router.replace({ query: { ...route.query, tab: id } })
}
</script>

<template>
  <nav class="flex items-center gap-1 mb-6 border-b border-line-hairline overflow-x-auto">
    <button
      v-for="t in tabs"
      :key="t.id"
      type="button"
      class="inline-flex items-center gap-1.5 h-10 px-4 text-[13px] border-b-2 -mb-px transition-colors whitespace-nowrap"
      :class="
        current === t.id
          ? 'border-accent text-ink-strong font-medium'
          : 'border-transparent text-ink-muted hover:text-ink-strong'
      "
      @click="selectTab(t.id)"
    >
      <component :is="t.icon" :size="14" :stroke-width="1.5" />
      {{ t.label }}
    </button>
  </nav>
</template>
