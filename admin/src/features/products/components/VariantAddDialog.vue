<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loader2 } from 'lucide-vue-next'

import Dialog from '@/shared/ui/Dialog.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Button from '@/shared/ui/Button.vue'

import { useAddVariantMutation } from '../queries'

const props = defineProps<{
  open: boolean
  productId: string
}>()

const emit = defineEmits<{
  close: []
  added: []
}>()

const productionJobId = ref('')
const price = ref<number | ''>('')
const apiError = ref<string | null>(null)

watch(() => props.open, (v) => {
  if (v) {
    productionJobId.value = ''
    price.value = ''
    apiError.value = null
  }
})

const add = useAddVariantMutation(props.productId)

async function submit() {
  apiError.value = null
  const id = productionJobId.value.trim()
  const p = typeof price.value === 'number' ? price.value : Number(price.value)
  if (!id || !p || p < 1) {
    apiError.value = '請填入合法的 production_job_id 與售價'
    return
  }
  try {
    await add.mutateAsync({ production_job_id: id, price: p })
    emit('added')
    emit('close')
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '加入失敗'
  }
}
</script>

<template>
  <Dialog :open="open" title="新增變體" size="md" @close="$emit('close')">
    <div class="space-y-4">
      <p class="text-[12px] text-ink-muted">
        F06 製作系統完成後，這裡會改成下拉選 production_job。<br/>
        現在先用 UUID 直填（可從製作系統的 job 詳情頁複製）。
      </p>

      <div>
        <Label for="vd-job">Production Job ID</Label>
        <Input
          id="vd-job"
          v-model="productionJobId"
          placeholder="UUID"
        />
      </div>

      <div>
        <Label for="vd-price">售價（NTD）</Label>
        <Input
          id="vd-price"
          :model-value="String(price)"
          type="number"
          placeholder="例：397"
          @update:model-value="(v) => price = v === '' ? '' : Number(v)"
        />
      </div>

      <div
        v-if="apiError"
        class="px-3 py-2 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[13px] rounded-[var(--radius-xs)]"
      >
        {{ apiError }}
      </div>
    </div>

    <template #footer>
      <Button variant="secondary" @click="$emit('close')">取消</Button>
      <Button variant="primary" :disabled="add.isPending.value" @click="submit">
        <Loader2 v-if="add.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
        加入變體
      </Button>
    </template>
  </Dialog>
</template>
