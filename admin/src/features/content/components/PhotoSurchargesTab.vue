<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Plus, Pencil, Trash2, Loader2 } from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Dialog from '@/shared/ui/Dialog.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import AppDataTable, { type Column } from '@/shared/components/AppDataTable.vue'

import {
  useCreateSurchargeMutation,
  useDeleteSurchargeMutation,
  useSurchargesQuery,
  useToggleSurchargeActiveMutation,
  useUpdateSurchargeMutation,
} from '../queries'
import type { CustomPhotoSurcharge } from '../api'

const { data, isLoading } = useSurchargesQuery()
const createMut = useCreateSurchargeMutation()
const updateMut = useUpdateSurchargeMutation()
const toggleMut = useToggleSurchargeActiveMutation()
const deleteMut = useDeleteSurchargeMutation()

const items = computed(() => data.value?.items ?? [])

const dialogOpen = ref(false)
const editing = ref<CustomPhotoSurcharge | null>(null)
const fCategory = ref('')
const fLabel = ref('')
const fAmount = ref('')
const fActive = ref(true)
const apiError = ref<string | null>(null)

watch(
  [() => dialogOpen.value, () => editing.value],
  () => {
    if (dialogOpen.value) {
      const e = editing.value
      fCategory.value = e?.category ?? ''
      fLabel.value = e?.label ?? ''
      fAmount.value = e ? String(e.amount) : ''
      fActive.value = e?.is_active ?? true
      apiError.value = null
    }
  },
)

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(s: CustomPhotoSurcharge) {
  editing.value = s
  dialogOpen.value = true
}

async function submit() {
  apiError.value = null
  const payload = {
    category: fCategory.value.trim(),
    label: fLabel.value.trim(),
    amount: Number(fAmount.value),
    is_active: fActive.value,
  }
  if (!payload.category || !payload.label || !Number.isFinite(payload.amount) || payload.amount < 0) {
    apiError.value = '請完整填寫；金額必須 ≥ 0'
    return
  }
  try {
    if (editing.value) {
      await updateMut.mutateAsync({ id: editing.value.id, payload })
    } else {
      await createMut.mutateAsync(payload)
    }
    dialogOpen.value = false
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '儲存失敗'
  }
}

async function toggleActive(s: CustomPhotoSurcharge) {
  try {
    await toggleMut.mutateAsync(s.id)
  } catch (e) {
    alert((e as { message?: string }).message || '切換失敗')
  }
}

async function remove(s: CustomPhotoSurcharge) {
  if (!confirm(`確定刪除「${s.label}」？已套用此加費的歷史報價不受影響。`)) return
  try {
    await deleteMut.mutateAsync(s.id)
  } catch (e) {
    alert((e as { message?: string }).message || '刪除失敗')
  }
}

const columns: Column<CustomPhotoSurcharge>[] = [
  { key: 'category', label: '類別', width: '140px' },
  { key: 'label', label: '名稱' },
  { key: 'amount', label: '金額', width: '110px', align: 'right' },
  { key: 'is_active', label: '啟用', width: '80px', align: 'center' },
  { key: 'actions', label: '', width: '120px', align: 'right' },
]
</script>

<template>
  <div class="flex items-center justify-end mb-3">
    <Button variant="primary" @click="openCreate">
      <Plus :size="14" :stroke-width="1.75" />
      新增加費項目
    </Button>
  </div>

  <AppDataTable
    :columns="columns"
    :rows="items"
    :loading="isLoading"
    :row-key="(r) => r.id"
    empty-text="尚無加費項目"
  >
    <template #cell-category="{ row }">
      <span class="text-[13px] text-ink-default">{{ row.category }}</span>
    </template>
    <template #cell-label="{ row }">
      <span class="font-medium text-ink-strong">{{ row.label }}</span>
    </template>
    <template #cell-amount="{ row }">
      <span class="font-mono text-ink-strong">+NT$ {{ row.amount.toLocaleString('zh-TW') }}</span>
    </template>
    <template #cell-is_active="{ row }">
      <button
        type="button"
        class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)]"
        :class="
          row.is_active
            ? 'bg-[var(--color-state-success)]/[0.10] text-state-success'
            : 'bg-paper-subtle text-ink-muted'
        "
        @click="toggleActive(row)"
      >
        {{ row.is_active ? '啟用' : '停用' }}
      </button>
    </template>
    <template #cell-actions="{ row }">
      <div class="flex items-center justify-end gap-1">
        <button
          type="button"
          class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:text-ink-strong hover:bg-paper-subtle"
          @click="openEdit(row)"
        >
          <Pencil :size="14" :stroke-width="1.5" />
        </button>
        <button
          type="button"
          class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:text-state-danger hover:bg-[var(--color-state-danger)]/[0.10]"
          @click="remove(row)"
        >
          <Trash2 :size="14" :stroke-width="1.5" />
        </button>
      </div>
    </template>
  </AppDataTable>

  <Dialog
    :open="dialogOpen"
    :title="editing ? '編輯加費項目' : '新增加費項目'"
    size="md"
    @close="dialogOpen = false"
  >
    <div class="space-y-4 text-[13px]">
      <p
        v-if="apiError"
        class="px-3 py-2 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[12px] rounded-[var(--radius-xs)]"
      >{{ apiError }}</p>

      <div>
        <Label>類別</Label>
        <Input v-model="fCategory" placeholder="例：人物數量 / 背景複雜度 / 特殊處理" />
      </div>
      <div>
        <Label>名稱</Label>
        <Input v-model="fLabel" placeholder="例：2 人 / 細節豐富" />
      </div>
      <div>
        <Label>金額（NT$）</Label>
        <Input v-model="fAmount" type="number" min="0" />
      </div>
      <label class="flex items-center gap-2">
        <input v-model="fActive" type="checkbox" />
        <span class="text-ink-strong">啟用此加費（不啟用則報價時不顯示）</span>
      </label>
    </div>
    <template #footer>
      <Button
        variant="secondary"
        :disabled="createMut.isPending.value || updateMut.isPending.value"
        @click="dialogOpen = false"
      >取消</Button>
      <Button
        variant="primary"
        :disabled="createMut.isPending.value || updateMut.isPending.value"
        @click="submit"
      >
        <Loader2
          v-if="createMut.isPending.value || updateMut.isPending.value"
          :size="14" :stroke-width="1.5" class="animate-spin"
        />
        {{ editing ? '儲存' : '建立' }}
      </Button>
    </template>
  </Dialog>
</template>
