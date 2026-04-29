<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import { Loader2 } from 'lucide-vue-next'

import type { PhysicalColor } from '../api'

const props = defineProps<{
  open: boolean
  color: PhysicalColor | null
  pending: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: [add_ml: number]
}>()

const addMl = ref('')
const errors = ref<Record<string, string>>({})

watch(
  () => props.open,
  (v) => {
    if (v) {
      addMl.value = ''
      errors.value = {}
    }
  },
)

function submit() {
  const n = Number(addMl.value)
  if (!Number.isFinite(n) || n === 0) {
    errors.value.add_ml = '請輸入非 0 的數值'
    return
  }
  if (props.color && props.color.stock_ml + n < 0) {
    errors.value.add_ml = `扣減後庫存會 < 0（目前 ${props.color.stock_ml} + ${n} = ${props.color.stock_ml + n}）`
    return
  }
  emit('confirm', n)
}
</script>

<template>
  <Dialog
    :open="open"
    :title="color ? `更新庫存：${color.code} ${color.name}` : ''"
    size="md"
    @close="emit('close')"
  >
    <div v-if="color" class="space-y-4 text-[13px]">
      <p class="text-ink-default">
        目前庫存：<span class="font-mono text-ink-strong">{{ color.stock_ml }} ml</span>
      </p>

      <div>
        <Label>變動量（ml，正數 = 進貨、負數 = 扣減）</Label>
        <Input v-model="addMl" type="number" placeholder="例：150（5 罐 × 30ml）" />
        <p v-if="errors.add_ml" class="mt-1 text-[12px] text-state-danger">{{ errors.add_ml }}</p>
      </div>

      <p class="text-[11px] text-ink-muted">
        進貨後系統會自動掃描預購訂單，庫存足夠者立即升單並寄出貨通知 email 給客戶。
      </p>
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="pending" @click="emit('close')">取消</Button>
      <Button variant="primary" :disabled="pending" @click="submit">
        <Loader2 v-if="pending" :size="14" :stroke-width="1.5" class="animate-spin" />
        確認
      </Button>
    </template>
  </Dialog>
</template>
