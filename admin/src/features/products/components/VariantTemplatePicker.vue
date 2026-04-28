<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, Loader2 } from 'lucide-vue-next'

import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'

import { useVariantsQuery } from '../queries'
import type { Variant } from '../api'

const props = defineProps<{
  open: boolean
  productId: string
  /** single = 只能選一張（封面用）；multi = 多選（批次匯入圖片用）。 */
  mode: 'single' | 'multi'
}>()

const emit = defineEmits<{
  close: []
  /** mode=single 給單一 url；mode=multi 給陣列。 */
  pick: [urls: string[]]
}>()

const { data: variants, isLoading } = useVariantsQuery(() => props.productId)

const selected = ref<Set<string>>(new Set())

const candidates = computed(() =>
  (variants.value ?? [])
    .filter((v): v is Variant & { job_spec: NonNullable<Variant['job_spec']> } =>
      Boolean(v.job_spec?.filled_template_url),
    ),
)

function specSummary(v: Variant): string {
  if (!v.job_spec) return v.production_job_id.slice(0, 8) + '…'
  const s = v.job_spec
  return `${s.canvas_w_cm}×${s.canvas_h_cm}cm · ${s.detail} · ${s.difficulty}`
}

function toggle(url: string) {
  if (props.mode === 'single') {
    selected.value = new Set([url])
  } else {
    const next = new Set(selected.value)
    if (next.has(url)) next.delete(url)
    else next.add(url)
    selected.value = next
  }
}

function confirm() {
  emit('pick', Array.from(selected.value))
  emit('close')
}
</script>

<template>
  <Dialog
    :open="open"
    :title="mode === 'single' ? '從變體模板選封面' : '從變體模板批次匯入'"
    size="lg"
    @close="$emit('close')"
  >
    <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>

    <div v-else-if="candidates.length === 0" class="py-12 text-center text-ink-muted">
      <p class="text-[13px] mb-1">此商品的變體尚無可用的填色模板</p>
      <p class="text-[12px]">先到製作系統把 production_job 跑完並產出 filled_template</p>
    </div>

    <div v-else class="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-[500px] overflow-y-auto">
      <button
        v-for="v in candidates"
        :key="v.id"
        type="button"
        class="relative aspect-square rounded-[var(--radius-sm)] border-2 overflow-hidden bg-paper-canvas transition-colors text-left"
        :class="
          selected.has(v.job_spec.filled_template_url!)
            ? 'border-accent'
            : 'border-line-hairline hover:border-line-strong'
        "
        @click="toggle(v.job_spec.filled_template_url!)"
      >
        <img
          :src="v.job_spec.filled_template_url!"
          :alt="specSummary(v)"
          class="w-full h-full object-cover"
        />
        <span
          v-if="selected.has(v.job_spec.filled_template_url!)"
          class="absolute top-2 right-2 h-6 w-6 inline-flex items-center justify-center rounded-full bg-accent text-paper-surface"
        >
          <Check :size="14" :stroke-width="2.25" />
        </span>
        <span
          class="absolute bottom-0 inset-x-0 px-2 py-1 text-[11px] text-paper-surface bg-ink-strong/70"
        >
          {{ specSummary(v) }}
        </span>
      </button>
    </div>

    <template #footer>
      <Button variant="secondary" @click="$emit('close')">取消</Button>
      <Button variant="primary" :disabled="selected.size === 0" @click="confirm">
        套用 {{ selected.size > 0 ? `(${selected.size})` : '' }}
      </Button>
    </template>
  </Dialog>
</template>
