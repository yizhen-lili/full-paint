<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, Pencil, Trash2, Check, X, Loader2 } from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'

import {
  useCaseCategoriesQuery,
  useCreateCategoryMutation,
  useDeleteCategoryMutation,
  useUpdateCategoryMutation,
} from '../queries'

const { data, isLoading } = useCaseCategoriesQuery()
const createMut = useCreateCategoryMutation()
const updateMut = useUpdateCategoryMutation()
const deleteMut = useDeleteCategoryMutation()

const items = computed(() => data.value?.items ?? [])

const newName = ref('')
const editingId = ref<string | null>(null)
const editingName = ref('')
const apiError = ref<string | null>(null)

async function add() {
  const name = newName.value.trim()
  if (!name) return
  apiError.value = null
  try {
    await createMut.mutateAsync(name)
    newName.value = ''
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '建立失敗'
  }
}

function startEdit(id: string, name: string) {
  editingId.value = id
  editingName.value = name
}
async function saveEdit() {
  if (!editingId.value) return
  const name = editingName.value.trim()
  if (!name) {
    editingId.value = null
    return
  }
  try {
    await updateMut.mutateAsync({ id: editingId.value, name })
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '更新失敗'
  } finally {
    editingId.value = null
  }
}
function cancelEdit() {
  editingId.value = null
}

async function remove(id: string, name: string) {
  if (!confirm(`刪除「${name}」？該分類下的案例會變成「未分類」（不會被刪）。`)) return
  try {
    await deleteMut.mutateAsync(id)
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '刪除失敗'
  }
}
</script>

<template>
  <Card>
    <h2 class="font-display text-ink-strong text-[18px] leading-[26px] mb-4">案例分類</h2>

    <p
      v-if="apiError"
      class="mb-3 px-3 py-2 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[12px] rounded-[var(--radius-xs)]"
    >{{ apiError }}</p>

    <!-- 新增 -->
    <div class="flex gap-2 mb-4">
      <Input
        v-model="newName"
        placeholder="新分類名稱（例：人像 / 寵物 / 風景）"
        @keydown.enter.prevent="add"
      />
      <Button variant="primary" :disabled="createMut.isPending.value || !newName.trim()" @click="add">
        <Loader2 v-if="createMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
        <Plus v-else :size="14" :stroke-width="1.5" />
        新增
      </Button>
    </div>

    <!-- 列表 -->
    <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>
    <div v-else-if="items.length === 0" class="text-ink-muted text-[13px] text-center py-8">
      尚無分類
    </div>
    <ul v-else class="divide-y divide-line-hairline">
      <li
        v-for="c in items"
        :key="c.id"
        class="py-3 flex items-center justify-between gap-2"
      >
        <template v-if="editingId === c.id">
          <Input
            v-model="editingName"
            class="flex-1"
            @keydown.enter.prevent="saveEdit"
            @keydown.esc.prevent="cancelEdit"
          />
          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-state-success hover:bg-paper-subtle"
            @click="saveEdit"
          >
            <Check :size="14" :stroke-width="1.5" />
          </button>
          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:bg-paper-subtle"
            @click="cancelEdit"
          >
            <X :size="14" :stroke-width="1.5" />
          </button>
        </template>
        <template v-else>
          <span class="flex-1 text-ink-strong">{{ c.name }}</span>
          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:text-ink-strong hover:bg-paper-subtle"
            @click="startEdit(c.id, c.name)"
          >
            <Pencil :size="14" :stroke-width="1.5" />
          </button>
          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:text-state-danger hover:bg-[var(--color-state-danger)]/[0.10]"
            @click="remove(c.id, c.name)"
          >
            <Trash2 :size="14" :stroke-width="1.5" />
          </button>
        </template>
      </li>
    </ul>
  </Card>
</template>
