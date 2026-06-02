<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { Loader2, Pin, Plus, Save, X } from 'lucide-vue-next'
import { VueDraggable } from 'vue-draggable-plus'

import PageHeader from '@/shared/components/PageHeader.vue'
import Button from '@/shared/ui/Button.vue'

import ProductsTabs from '../components/ProductsTabs.vue'
import PinProductPickerDialog from '../components/PinProductPickerDialog.vue'
import {
  useHomepagePinnedQuery,
  useSetHomepageOrderMutation,
} from '../queries'
import type { HomepagePinnedItem, ProductListItem } from '../api'

const MAX_PINNED = 12

const { data, isLoading } = useHomepagePinnedQuery()
const saveMut = useSetHomepageOrderMutation()

// 本地拖曳列表 — 與 server data 解耦讓 admin 可以未存就拖
const localList = ref<HomepagePinnedItem[]>([])

// server 端 data 變動 → reset 本地（除非 user 正在編輯中）
const isDirty = ref(false)
watch(
  () => data.value?.items,
  (items) => {
    if (!isDirty.value && items) {
      localList.value = items.map((it) => ({ ...it }))
    }
  },
  { immediate: true },
)

const pickerOpen = ref(false)
const remainingSlots = computed(() => MAX_PINNED - localList.value.length)
const isFull = computed(() => localList.value.length >= MAX_PINNED)

function onListMutated() {
  // VueDraggable 拖到原位也會觸發 update — 比對與 server data 的 id 順序，
  // 真正變動才標 dirty，避免「拖出再拖回」誤亮 Save / 跳離開警告。
  const serverIds = (data.value?.items ?? []).map((it) => it.id)
  const localIds = localList.value.map((it) => it.id)
  isDirty.value =
    localIds.length !== serverIds.length ||
    localIds.some((id, idx) => id !== serverIds[idx])
}

function removeItem(id: string) {
  localList.value = localList.value.filter((it) => it.id !== id)
  isDirty.value = true
}

function onPick(item: ProductListItem) {
  // 已達上限就不再加（理論上 picker 內部按鈕也會 disabled，這是雙保險）
  if (localList.value.length >= MAX_PINNED) {
    pickerOpen.value = false
    return
  }

  // 把 ProductListItem 轉 HomepagePinnedItem（homepage_order 暫時設成下一個位置，純顯示用）
  localList.value.push({
    id: item.id,
    title: item.title,
    cover_image_url: item.cover_image_url,
    status: item.status,
    homepage_order: localList.value.length + 1,
  })
  isDirty.value = true

  // 連續挑：dialog 保持開啟，picker 內已挑的會被 excludeIds 排掉、剩餘格數即時遞減；
  // 達到上限 12 才自動關閉。admin 也可以隨時手動按「關閉」結束。
  if (localList.value.length >= MAX_PINNED) {
    pickerOpen.value = false
  }
}

async function save() {
  try {
    await saveMut.mutateAsync(localList.value.map((it) => it.id))
    isDirty.value = false
  } catch (e) {
    alert((e as { message?: string }).message || '儲存失敗')
  }
}

// 離開頁面前確認（router beforeLeave + beforeunload）
onBeforeRouteLeave((_to, _from, next) => {
  if (isDirty.value && !confirm('排序尚未儲存，確定要離開？變更會遺失。')) {
    next(false)
  } else {
    next()
  }
})

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (isDirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

watch(isDirty, (v) => {
  if (typeof window === 'undefined') return
  if (v) window.addEventListener('beforeunload', onBeforeUnload)
  else window.removeEventListener('beforeunload', onBeforeUnload)
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('beforeunload', onBeforeUnload)
  }
})

const excludeIds = computed(() => localList.value.map((it) => it.id))
</script>

<template>
  <PageHeader title="商品管理" subtitle="首頁置頂排序 — 拖曳卡片調整 store 首頁顯示順序">
    <template #actions>
      <Button
        variant="ghost"
        :disabled="isFull"
        @click="pickerOpen = true"
      >
        <Plus :size="14" :stroke-width="1.75" />
        加入商品
        <span
          v-if="isFull"
          class="text-[11px] text-ink-muted ml-1 font-normal"
        >（已達上限 12）</span>
      </Button>
      <Button
        variant="primary"
        :disabled="!isDirty || saveMut.isPending.value"
        @click="save"
      >
        <Save :size="14" :stroke-width="1.75" />
        儲存排序
      </Button>
    </template>
  </PageHeader>

  <ProductsTabs class="mb-6" />

  <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
    <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
  </div>

  <div v-else-if="localList.length === 0" class="py-16 text-center">
    <div class="inline-flex w-12 h-12 items-center justify-center rounded-full bg-paper-canvas text-ink-muted mb-3">
      <Pin :size="18" :stroke-width="1.5" />
    </div>
    <p class="text-[14px] text-ink-strong mb-1">還沒有任何首頁置頂商品。</p>
    <p class="text-[12px] text-ink-muted">點上方「加入商品」按鈕從已上架商品中挑選，最多 12 個。</p>
  </div>

  <div v-else>
    <div class="mb-3 text-[12px] text-ink-muted">
      Top1 在最前；拖曳卡片可調整順序。<span v-if="isDirty" class="text-accent ml-1">（有未儲存變動）</span>
    </div>

    <VueDraggable
      v-model="localList"
      :animation="200"
      ghost-class="opacity-30"
      class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3"
      @update="onListMutated"
    >
      <div
        v-for="(item, idx) in localList"
        :key="item.id"
        class="group relative bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] overflow-hidden cursor-grab active:cursor-grabbing hover:border-accent transition-colors"
      >
        <div class="aspect-[4/3] bg-paper-canvas relative">
          <img
            v-if="item.cover_image_url"
            :src="item.cover_image_url"
            :alt="item.title"
            class="w-full h-full object-cover"
            loading="lazy"
          />
          <span class="absolute top-2 left-2 inline-flex items-center justify-center w-6 h-6 rounded-full bg-ink-strong text-paper-canvas text-[11px] font-mono font-medium">
            {{ idx + 1 }}
          </span>
          <button
            type="button"
            class="absolute top-2 right-2 w-6 h-6 inline-flex items-center justify-center rounded-full bg-ink-strong/80 text-paper-canvas opacity-0 group-hover:opacity-100 transition-opacity hover:bg-accent-wine"
            aria-label="移除"
            @click.stop="removeItem(item.id)"
          >
            <X :size="12" :stroke-width="2" />
          </button>
        </div>
        <div class="p-2.5">
          <div class="text-[13px] text-ink-strong truncate">{{ item.title }}</div>
          <div class="text-[11px] text-ink-muted font-mono mt-0.5">
            {{ item.status === 'on_sale' ? '已上架' : item.status }}
          </div>
        </div>
      </div>
    </VueDraggable>
  </div>

  <PinProductPickerDialog
    :open="pickerOpen"
    :exclude-ids="excludeIds"
    :remaining-slots="remainingSlots"
    @close="pickerOpen = false"
    @pick="onPick"
  />
</template>
