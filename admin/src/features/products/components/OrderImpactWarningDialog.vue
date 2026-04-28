<script setup lang="ts">
import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'

defineProps<{
  open: boolean
  ongoingCount?: number
}>()

defineEmits<{
  close: []
  confirm: []
}>()
</script>

<template>
  <Dialog :open="open" title="此商品有進行中訂單" size="md" @close="$emit('close')">
    <p class="text-[13px] text-ink-default leading-relaxed">
      <span v-if="ongoingCount !== undefined">
        此商品有 <strong class="text-ink-strong">{{ ongoingCount }}</strong> 筆進行中訂單。
      </span>
      <span v-else>
        此商品有進行中訂單。
      </span>
    </p>
    <p class="text-[13px] text-ink-muted leading-relaxed mt-2">
      下架後不影響現有訂單，已成立訂單仍會正常製作出貨；新客戶將無法選購此商品。確定繼續？
    </p>

    <template #footer>
      <Button variant="secondary" @click="$emit('close')">取消</Button>
      <Button variant="danger" @click="$emit('confirm')">確認下架</Button>
    </template>
  </Dialog>
</template>
