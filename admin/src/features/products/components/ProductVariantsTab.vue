<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Trash2, Wrench, Loader2 } from 'lucide-vue-next'

import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import VariantAddDialog from './VariantAddDialog.vue'

import {
  useVariantsQuery,
  useUpdateVariantMutation,
  useDeleteVariantMutation,
} from '../queries'
import type { Variant } from '../api'

const props = defineProps<{
  productId: string
}>()

const { data: variants, isLoading } = useVariantsQuery(() => props.productId)
const updateVariant = useUpdateVariantMutation(props.productId)
const deleteVariant = useDeleteVariantMutation(props.productId)

const dialogOpen = ref(false)
const editingPriceId = ref<string | null>(null)
const editingPriceValue = ref('')

function startEditPrice(v: Variant) {
  editingPriceId.value = v.id
  editingPriceValue.value = String(v.price)
}

async function commitPrice(v: Variant) {
  const newPrice = Number(editingPriceValue.value)
  if (!newPrice || newPrice < 1 || newPrice === v.price) {
    editingPriceId.value = null
    return
  }
  try {
    await updateVariant.mutateAsync({ variantId: v.id, payload: { price: newPrice } })
  } catch (e) {
    alert((e as { message?: string }).message || '更新失敗')
  } finally {
    editingPriceId.value = null
  }
}

async function toggleActive(v: Variant) {
  try {
    await updateVariant.mutateAsync({ variantId: v.id, payload: { is_active: !v.is_active } })
  } catch (e) {
    alert((e as { message?: string }).message || '切換失敗')
  }
}

async function handleDelete(v: Variant) {
  if (!confirm('確定刪除這個變體？')) return
  try {
    await deleteVariant.mutateAsync(v.id)
  } catch (e) {
    alert((e as { message?: string }).message || '刪除失敗')
  }
}

function specSummary(v: Variant): string {
  if (!v.production_job_snapshot) return v.production_job_id.slice(0, 8) + '…'
  const s = v.production_job_snapshot
  return `${s.canvas_w_cm}×${s.canvas_h_cm}cm · ${s.detail} · ${s.difficulty}`
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <div>
        <h2 class="font-display text-ink-strong text-[18px] leading-[26px]">變體管理</h2>
        <p class="text-[12px] text-ink-muted mt-0.5">每個變體對應一個製作 job 與獨立售價</p>
      </div>
      <Button variant="primary" @click="dialogOpen = true">
        <Plus :size="14" :stroke-width="1.75" />
        新增變體
      </Button>
    </div>

    <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>

    <div
      v-else-if="!variants || variants.length === 0"
      class="bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] py-16 flex flex-col items-center text-center"
    >
      <Wrench :size="32" :stroke-width="1.25" class="text-aux-rice-mid mb-3" />
      <p class="text-[13px] text-ink-muted mb-1">尚無變體</p>
      <p class="text-[12px] text-ink-muted">先到製作系統建立 production job，再回來加變體</p>
    </div>

    <div v-else class="bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] overflow-hidden">
      <table class="w-full text-left">
        <thead>
          <tr class="bg-paper-subtle border-b border-line-hairline">
            <th class="h-10 px-4 text-[13px] font-semibold text-ink-strong">規格</th>
            <th class="h-10 px-4 text-[13px] font-semibold text-ink-strong text-right" style="width: 120px;">公式底價</th>
            <th class="h-10 px-4 text-[13px] font-semibold text-ink-strong text-right" style="width: 140px;">售價</th>
            <th class="h-10 px-4 text-[13px] font-semibold text-ink-strong text-center" style="width: 100px;">上架</th>
            <th class="h-10 px-4" style="width: 60px;"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="v in variants"
            :key="v.id"
            class="border-b border-line-hairline last:border-0"
          >
            <td class="h-12 px-4 text-[13px] text-ink-default">{{ specSummary(v) }}</td>
            <td class="h-12 px-4 text-right font-mono text-[13px] text-ink-muted">{{ v.price_formula_base }}</td>
            <td class="h-12 px-4 text-right">
              <div v-if="editingPriceId === v.id" class="inline-block w-24">
                <Input
                  v-model="editingPriceValue"
                  type="number"
                  autofocus
                  @blur="commitPrice(v)"
                  @keydown.enter="commitPrice(v)"
                  @keydown.esc="editingPriceId = null"
                />
              </div>
              <button
                v-else
                type="button"
                class="font-mono text-[14px] text-ink-strong hover:bg-paper-subtle px-2 py-1 -my-1 rounded-[var(--radius-xs)] transition-colors"
                @click="startEditPrice(v)"
              >
                {{ v.price }}
              </button>
            </td>
            <td class="h-12 px-4 text-center">
              <button
                type="button"
                class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                :class="v.is_active ? 'bg-accent' : 'bg-line-strong'"
                @click="toggleActive(v)"
              >
                <span
                  class="inline-block h-4 w-4 transform rounded-full bg-paper-surface transition-transform"
                  :class="v.is_active ? 'translate-x-4' : 'translate-x-0.5'"
                />
              </button>
            </td>
            <td class="h-12 px-4 text-right">
              <button
                type="button"
                class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:bg-[var(--color-state-danger)]/[0.10] hover:text-state-danger transition-colors"
                @click="handleDelete(v)"
              >
                <Trash2 :size="14" :stroke-width="1.5" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <VariantAddDialog
      :open="dialogOpen"
      :product-id="productId"
      @close="dialogOpen = false"
      @added="dialogOpen = false"
    />
  </div>
</template>
