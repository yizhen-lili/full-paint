<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Pencil, Trash2, Loader2, Tag as TagIcon } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Button from '@/shared/ui/Button.vue'
import Dialog from '@/shared/ui/Dialog.vue'

import {
  useTagsQuery,
  useCreateTagMutation,
  useUpdateTagMutation,
  useDeleteTagMutation,
} from '../queries'
import type { Tag } from '../api'
import ProductsTabs from '../components/ProductsTabs.vue'

const { data: tags, isLoading } = useTagsQuery()
const createMut = useCreateTagMutation()
const updateMut = useUpdateTagMutation()
const deleteMut = useDeleteTagMutation()

const dialogOpen = ref(false)
const editing = ref<Tag | null>(null)
const formName = ref('')

function openCreate() {
  editing.value = null
  formName.value = ''
  dialogOpen.value = true
}

function openEdit(t: Tag) {
  editing.value = t
  formName.value = t.name
  dialogOpen.value = true
}

async function submit() {
  const name = formName.value.trim()
  if (!name) return
  try {
    if (editing.value) {
      await updateMut.mutateAsync({ id: editing.value.id, payload: { name } })
    } else {
      await createMut.mutateAsync({ name })
    }
    dialogOpen.value = false
  } catch (e) {
    alert((e as { message?: string }).message || '儲存失敗')
  }
}

async function handleDelete(t: Tag) {
  if (!confirm(`刪除標籤「${t.name}」？所有商品的此標籤關聯都會被一併移除。`)) return
  try {
    await deleteMut.mutateAsync(t.id)
  } catch (e) {
    alert((e as { message?: string }).message || '刪除失敗')
  }
}
</script>

<template>
  <PageHeader title="商品管理" subtitle="商品 / 系列 / 標籤">
    <template #actions>
      <Button variant="primary" @click="openCreate">
        <Plus :size="14" :stroke-width="1.75" />
        新增標籤
      </Button>
    </template>
  </PageHeader>

  <ProductsTabs class="mb-6" />

  <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
    <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
  </div>

  <div
    v-else-if="!tags || tags.length === 0"
    class="bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] py-16 flex flex-col items-center text-center"
  >
    <TagIcon :size="32" :stroke-width="1.25" class="text-aux-rice-mid mb-3" />
    <p class="text-[13px] text-ink-muted mb-1">尚無標籤</p>
    <Button variant="primary" class="mt-4" @click="openCreate">
      <Plus :size="14" :stroke-width="1.75" />
      建立第一個標籤
    </Button>
  </div>

  <Card v-else>
    <div class="flex flex-wrap gap-2">
      <div
        v-for="t in tags"
        :key="t.id"
        class="group inline-flex items-center gap-1 h-8 px-3 rounded-[var(--radius-xs)] bg-paper-subtle border border-line-strong text-[13px] text-ink-default"
      >
        <span>{{ t.name }}</span>
        <button
          type="button"
          class="ml-1 text-ink-muted hover:text-ink-strong opacity-0 group-hover:opacity-100 transition-opacity"
          @click="openEdit(t)"
        >
          <Pencil :size="12" :stroke-width="1.5" />
        </button>
        <button
          type="button"
          class="text-ink-muted hover:text-state-danger opacity-0 group-hover:opacity-100 transition-opacity"
          @click="handleDelete(t)"
        >
          <Trash2 :size="12" :stroke-width="1.5" />
        </button>
      </div>
    </div>
  </Card>

  <Dialog
    :open="dialogOpen"
    :title="editing ? '編輯標籤' : '新增標籤'"
    size="sm"
    @close="dialogOpen = false"
  >
    <div>
      <Label for="t-name">標籤名稱</Label>
      <Input id="t-name" v-model="formName" placeholder="例：療癒" autofocus />
    </div>
    <template #footer>
      <Button variant="secondary" @click="dialogOpen = false">取消</Button>
      <Button
        variant="primary"
        :disabled="!formName.trim() || createMut.isPending.value || updateMut.isPending.value"
        @click="submit"
      >
        儲存
      </Button>
    </template>
  </Dialog>
</template>
