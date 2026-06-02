<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Loader2, Search } from 'lucide-vue-next'

import Dialog from '@/shared/ui/Dialog.vue'
import Input from '@/shared/ui/Input.vue'
import Button from '@/shared/ui/Button.vue'

import { useProductsQuery } from '../queries'
import type { ProductListItem } from '../api'

const props = defineProps<{
  open: boolean
  /** 已置頂的 product_ids（會被排掉不列出） */
  excludeIds: string[]
  /** 已剩可加數量（== 12 - 目前置頂數）；0 時 dialog 不該開 */
  remainingSlots: number
}>()

const emit = defineEmits<{
  close: []
  pick: [item: ProductListItem]
}>()

const search = ref('')

// 每次開啟重置搜尋
watch(() => props.open, (v) => {
  if (v) search.value = ''
})

const queryParams = computed(() => ({
  search: search.value || undefined,
  status: 'on_sale' as const,
  exclude_ids: props.excludeIds.length ? props.excludeIds : undefined,
  page: 1,
  page_size: 50,
}))

const { data, isLoading } = useProductsQuery(queryParams)
const items = computed(() => data.value?.items ?? [])

function pick(item: ProductListItem) {
  emit('pick', item)
}
</script>

<template>
  <Dialog :open="open" title="加入首頁置頂商品" size="lg" @close="emit('close')">
    <div class="space-y-3">
      <div class="text-[12px] text-ink-muted">
        只列出 <span class="text-accent font-medium">已上架（on_sale）</span> 的商品。還可加 <span class="font-mono">{{ remainingSlots }}</span> 個（上限 12）。
      </div>

      <div class="relative">
        <Search
          :size="14"
          :stroke-width="1.5"
          class="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
        />
        <Input
          v-model="search"
          placeholder="搜尋商品名稱..."
          class="pl-9"
        />
      </div>

      <div v-if="isLoading" class="py-10 flex justify-center text-ink-muted">
        <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
      </div>

      <div
        v-else-if="items.length === 0"
        class="py-10 text-center text-ink-muted text-[13px]"
      >
        <span v-if="search">找不到符合「{{ search }}」的商品。</span>
        <span v-else>沒有可加入的商品（已上架商品都已置頂）。</span>
      </div>

      <ul v-else class="grid grid-cols-2 gap-2 max-h-[420px] overflow-y-auto">
        <li v-for="p in items" :key="p.id">
          <button
            type="button"
            class="w-full flex items-center gap-3 p-2 border border-line-hairline rounded-[var(--radius-sm)] text-left hover:border-accent hover:bg-paper-canvas transition-colors"
            @click="pick(p)"
          >
            <img
              v-if="p.cover_image_url"
              :src="p.cover_image_url"
              :alt="p.title"
              class="w-14 h-14 object-cover rounded-[var(--radius-xs)] flex-shrink-0"
              loading="lazy"
            />
            <div
              v-else
              class="w-14 h-14 bg-paper-canvas rounded-[var(--radius-xs)] flex-shrink-0"
            />
            <div class="flex-1 min-w-0">
              <div class="text-[13px] text-ink-strong truncate">{{ p.title }}</div>
              <div class="text-[11px] text-ink-muted font-mono mt-0.5">
                {{ p.variant_count }} 個變體
              </div>
            </div>
          </button>
        </li>
      </ul>
    </div>

    <template #footer>
      <Button variant="secondary" @click="emit('close')">關閉</Button>
    </template>
  </Dialog>
</template>
