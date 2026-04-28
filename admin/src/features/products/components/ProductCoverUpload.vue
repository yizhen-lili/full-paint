<script setup lang="ts">
import { ref } from 'vue'
import { Image as ImageIcon, Loader2, Upload, X } from 'lucide-vue-next'

import { uploadFile } from '../api'

const props = defineProps<{
  modelValue: string
  invalid?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [url: string]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isUploading = ref(false)
const error = ref<string | null>(null)

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 20 * 1024 * 1024) {
    error.value = '檔案超過 20MB'
    return
  }
  if (file.type !== 'image/jpeg' && file.type !== 'image/png') {
    error.value = '只接受 JPEG / PNG'
    return
  }
  error.value = null
  isUploading.value = true
  try {
    const url = await uploadFile(file)
    emit('update:modelValue', url)
  } catch (e) {
    error.value = (e as { message?: string }).message || '上傳失敗'
  } finally {
    isUploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

function trigger() {
  fileInput.value?.click()
}

function clear() {
  emit('update:modelValue', '')
}
</script>

<template>
  <div class="space-y-2">
    <input
      ref="fileInput"
      type="file"
      accept="image/jpeg,image/png"
      class="hidden"
      @change="onFileChange"
    />

    <!-- Empty state -->
    <button
      v-if="!modelValue && !isUploading"
      type="button"
      class="w-full aspect-[4/3] flex flex-col items-center justify-center gap-2 border-2 border-dashed rounded-[var(--radius-sm)] bg-paper-surface hover:bg-paper-subtle transition-colors text-ink-muted"
      :class="invalid ? 'border-state-danger' : 'border-line-strong'"
      @click="trigger"
    >
      <ImageIcon :size="32" :stroke-width="1.25" class="text-aux-rice-mid" />
      <span class="text-[13px]">點擊上傳封面（JPEG / PNG, ≤ 20MB）</span>
    </button>

    <!-- Uploading -->
    <div
      v-else-if="isUploading"
      class="w-full aspect-[4/3] flex flex-col items-center justify-center gap-2 border border-line-hairline rounded-[var(--radius-sm)] bg-paper-subtle"
    >
      <Loader2 :size="24" :stroke-width="1.5" class="animate-spin text-ink-muted" />
      <span class="text-[13px] text-ink-muted">上傳中...</span>
    </div>

    <!-- Has image -->
    <div
      v-else
      class="relative group w-full aspect-[4/3] rounded-[var(--radius-sm)] border border-line-hairline overflow-hidden bg-paper-canvas"
    >
      <img :src="modelValue" alt="封面" class="w-full h-full object-cover" />
      <div
        class="absolute inset-0 bg-ink-strong/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2"
      >
        <button
          type="button"
          class="h-9 px-3 rounded-[var(--radius-xs)] bg-paper-surface text-ink-strong text-[13px] font-medium hover:bg-paper-subtle transition-colors flex items-center gap-1.5"
          @click="trigger"
        >
          <Upload :size="14" :stroke-width="1.5" />
          替換
        </button>
        <button
          type="button"
          class="h-9 px-3 rounded-[var(--radius-xs)] bg-paper-surface text-state-danger text-[13px] font-medium hover:bg-paper-subtle transition-colors flex items-center gap-1.5"
          @click="clear"
        >
          <X :size="14" :stroke-width="1.5" />
          移除
        </button>
      </div>
    </div>

    <p v-if="error" class="text-[12px] text-state-danger">{{ error }}</p>
  </div>
</template>
