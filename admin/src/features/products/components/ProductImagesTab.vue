<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { Plus, X, Image as ImageIcon, Loader2, GripVertical } from 'lucide-vue-next'

import { uploadFile } from '../api'
import {
  useImagesQuery,
  useAddImageMutation,
  useDeleteImageMutation,
  useReorderImagesMutation,
} from '../queries'
import type { ProductImage } from '../api'

const props = defineProps<{
  productId: string
}>()

const { data: serverImages, isLoading } = useImagesQuery(() => props.productId)
const addImage = useAddImageMutation(props.productId)
const deleteImage = useDeleteImageMutation(props.productId)
const reorderImages = useReorderImagesMutation(props.productId)

// Local copy for drag re-ordering (mirrors server data)
const localImages = ref<ProductImage[]>([])

watch(serverImages, (next) => {
  localImages.value = next ? [...next] : []
}, { immediate: true })

const fileInput = ref<HTMLInputElement | null>(null)
const isUploading = ref(false)
const error = ref<string | null>(null)

const sortedImages = computed(() => localImages.value)

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 20 * 1024 * 1024) { error.value = '檔案超過 20MB'; return }
  if (file.type !== 'image/jpeg' && file.type !== 'image/png') {
    error.value = '只接受 JPEG / PNG'
    return
  }
  error.value = null
  isUploading.value = true
  try {
    const url = await uploadFile(file)
    const nextOrder = (localImages.value.length > 0
      ? Math.max(...localImages.value.map((i) => i.sort_order)) + 1
      : 0)
    await addImage.mutateAsync({ image_url: url, sort_order: nextOrder })
  } catch (e) {
    error.value = (e as { message?: string }).message || '上傳失敗'
  } finally {
    isUploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function handleDelete(img: ProductImage) {
  if (!confirm('確定移除此圖？')) return
  try {
    await deleteImage.mutateAsync(img.id)
  } catch (e) {
    alert((e as { message?: string }).message || '刪除失敗')
  }
}

async function onDragEnd() {
  const order = localImages.value.map((i) => i.id)
  try {
    await reorderImages.mutateAsync(order)
  } catch (e) {
    alert((e as { message?: string }).message || '排序更新失敗')
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="font-display text-ink-strong text-[18px] leading-[26px]">商品圖片</h2>
        <p class="text-[12px] text-ink-muted mt-0.5">拖曳排序、第一張為前台主圖</p>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="image/jpeg,image/png"
        class="hidden"
        @change="onFileChange"
      />
      <button
        type="button"
        class="h-9 px-3 inline-flex items-center gap-1 rounded-[var(--radius-xs)] bg-accent text-paper-surface text-[13px] font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
        :disabled="isUploading"
        @click="fileInput?.click()"
      >
        <Loader2 v-if="isUploading" :size="14" :stroke-width="1.5" class="animate-spin" />
        <Plus v-else :size="14" :stroke-width="1.75" />
        加圖
      </button>
    </div>

    <p v-if="error" class="mb-3 text-[12px] text-state-danger">{{ error }}</p>

    <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>

    <div
      v-else-if="sortedImages.length === 0"
      class="bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] py-16 flex flex-col items-center text-center"
    >
      <ImageIcon :size="32" :stroke-width="1.25" class="text-aux-rice-mid mb-3" />
      <p class="text-[13px] text-ink-muted">尚無商品圖片</p>
    </div>

    <VueDraggable
      v-else
      v-model="localImages"
      :animation="150"
      handle=".drag-handle"
      item-key="id"
      class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3"
      @end="onDragEnd"
    >
      <div
        v-for="img in sortedImages"
        :key="img.id"
        class="relative group aspect-square rounded-[var(--radius-sm)] border border-line-hairline overflow-hidden bg-paper-canvas"
      >
        <img :src="img.image_url" alt="" class="w-full h-full object-cover" />
        <button
          type="button"
          class="drag-handle absolute top-2 left-2 h-7 w-7 inline-flex items-center justify-center rounded-[var(--radius-xs)] bg-paper-surface/90 text-ink-muted opacity-0 group-hover:opacity-100 cursor-grab active:cursor-grabbing transition-opacity"
          aria-label="拖曳排序"
        >
          <GripVertical :size="14" :stroke-width="1.5" />
        </button>
        <button
          type="button"
          class="absolute top-2 right-2 h-7 w-7 inline-flex items-center justify-center rounded-[var(--radius-xs)] bg-paper-surface/90 text-state-danger opacity-0 group-hover:opacity-100 transition-opacity"
          aria-label="刪除"
          @click="handleDelete(img)"
        >
          <X :size="14" :stroke-width="1.5" />
        </button>
      </div>
    </VueDraggable>
  </div>
</template>
