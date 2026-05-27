<script setup lang="ts">
import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'

import PostProcessPanel from './PostProcessPanel.vue'
import type { BatchOperation, PaletteColor } from '../api'

type OperationType = 'merge_color' | 'eliminate_border'

defineProps<{
  open: boolean
  type: OperationType | null
  palette: PaletteColor[]
  /** template.svg 的 signed URL；點選格子用 */
  svgUrl?: string | null
  pending: boolean
}>()

const emit = defineEmits<{
  close: []
  confirmBatch: [payload: BatchOperation[]]
}>()

const titles: Record<OperationType, string> = {
  merge_color: '合併色塊',
  eliminate_border: '消除邊界線',
}
</script>

<template>
  <Dialog
    :open="open"
    :title="type ? titles[type] : ''"
    size="lg"
    @close="emit('close')"
  >
    <!-- v-if="open" 確保 Dialog 重開時 Panel 被 remount → 自動清空 queue/選擇 -->
    <PostProcessPanel
      v-if="open && type"
      :palette="palette"
      :svg-url="svgUrl"
      :pending="pending"
      :type-filter="type"
      @confirm-batch="(ops) => emit('confirmBatch', ops)"
    />

    <template #footer>
      <Button variant="secondary" :disabled="pending" @click="emit('close')">關閉</Button>
    </template>
  </Dialog>
</template>
