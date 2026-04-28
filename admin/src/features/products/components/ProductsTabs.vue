<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Box, Layers, Sparkles, Tag as TagIcon } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const tabs = [
  { id: '', label: '商品', icon: Box, path: '/admin/products' },
  { id: 'themes', label: '主題', icon: Sparkles, path: '/admin/products/themes' },
  { id: 'series', label: '系列', icon: Layers, path: '/admin/products/series' },
  { id: 'tags', label: '標籤', icon: TagIcon, path: '/admin/products/tags' },
] as const

const currentId = computed(() => {
  if (route.path === '/admin/products/themes') return 'themes'
  if (route.path === '/admin/products/series') return 'series'
  if (route.path === '/admin/products/tags') return 'tags'
  return ''
})

function goto(path: string) {
  router.push(path)
}
</script>

<template>
  <nav class="flex items-center gap-1 border-b border-line-hairline">
    <button
      v-for="t in tabs"
      :key="t.id"
      type="button"
      class="inline-flex items-center gap-1.5 h-10 px-4 text-[13px] border-b-2 -mb-px transition-colors"
      :class="
        currentId === t.id
          ? 'border-accent text-ink-strong font-medium'
          : 'border-transparent text-ink-muted hover:text-ink-strong'
      "
      @click="goto(t.path)"
    >
      <component :is="t.icon" :size="14" :stroke-width="1.5" />
      {{ t.label }}
    </button>
  </nav>
</template>
