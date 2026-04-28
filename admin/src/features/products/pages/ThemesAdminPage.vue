<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Pencil, Trash2, Loader2, Sparkles } from 'lucide-vue-next'

import PageHeader from '@/shared/components/PageHeader.vue'
import Card from '@/shared/ui/Card.vue'
import Input from '@/shared/ui/Input.vue'
import Textarea from '@/shared/ui/Textarea.vue'
import Label from '@/shared/ui/Label.vue'
import Button from '@/shared/ui/Button.vue'
import Dialog from '@/shared/ui/Dialog.vue'

import {
  useThemesQuery,
  useCreateThemeMutation,
  useUpdateThemeMutation,
  useDeleteThemeMutation,
} from '../queries'
import type { Theme } from '../api'
import ProductsTabs from '../components/ProductsTabs.vue'
import ProductCoverUpload from '../components/ProductCoverUpload.vue'

const { data, isLoading } = useThemesQuery()
const createMut = useCreateThemeMutation()
const updateMut = useUpdateThemeMutation()
const deleteMut = useDeleteThemeMutation()

const dialogOpen = ref(false)
const editing = ref<Theme | null>(null)
const formName = ref('')
const formDesc = ref('')
const formCover = ref('')
const formSortOrder = ref(0)

function openCreate() {
  editing.value = null
  formName.value = ''
  formDesc.value = ''
  formCover.value = ''
  formSortOrder.value = 0
  dialogOpen.value = true
}

function openEdit(t: Theme) {
  editing.value = t
  formName.value = t.name
  formDesc.value = t.description ?? ''
  formCover.value = t.cover_image_url ?? ''
  formSortOrder.value = t.sort_order
  dialogOpen.value = true
}

async function submit() {
  const name = formName.value.trim()
  if (!name) return
  const payload = {
    name,
    description: formDesc.value.trim() || null,
    cover_image_url: formCover.value.trim() || null,
    sort_order: Number(formSortOrder.value) || 0,
  }
  try {
    if (editing.value) {
      await updateMut.mutateAsync({ id: editing.value.id, payload })
    } else {
      await createMut.mutateAsync(payload)
    }
    dialogOpen.value = false
  } catch (e) {
    const err = e as { status?: number; message?: string }
    if (err.status === 409) alert('主題名稱已存在')
    else alert(err.message || '儲存失敗')
  }
}

async function handleDelete(t: Theme) {
  if (
    !confirm(
      `刪除主題「${t.name}」？` +
        (t.series_count > 0
          ? `\n此主題下有 ${t.series_count} 個系列，刪除後系列會變為「未分類」（系列本身不會被刪除）。`
          : ''),
    )
  )
    return
  try {
    await deleteMut.mutateAsync(t.id)
  } catch (e) {
    alert((e as { message?: string }).message || '刪除失敗')
  }
}
</script>

<template>
  <PageHeader title="商品管理" subtitle="商品 / 主題 / 系列 / 標籤">
    <template #actions>
      <Button variant="primary" @click="openCreate">
        <Plus :size="14" :stroke-width="1.75" />
        新增主題
      </Button>
    </template>
  </PageHeader>

  <ProductsTabs class="mb-6" />

  <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
    <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
  </div>

  <div
    v-else-if="!data || data.items.length === 0"
    class="bg-paper-surface border border-line-hairline rounded-[var(--radius-sm)] py-16 flex flex-col items-center text-center"
  >
    <Sparkles :size="32" :stroke-width="1.25" class="text-aux-rice-mid mb-3" />
    <p class="text-[13px] text-ink-muted mb-1">尚無主題</p>
    <p class="text-[12px] text-ink-muted mb-4 max-w-sm">
      主題用來歸類系列，例如「萌寵」主題下可以有「貓咪系列」、「狗狗系列」
    </p>
    <Button variant="primary" @click="openCreate">
      <Plus :size="14" :stroke-width="1.75" />
      建立第一個主題
    </Button>
  </div>

  <Card v-else :padded="false">
    <ul>
      <li
        v-for="t in data.items"
        :key="t.id"
        class="flex items-start gap-4 px-6 py-4 border-b border-line-hairline last:border-0 hover:bg-paper-subtle transition-colors"
      >
        <div
          v-if="t.cover_image_url"
          class="w-14 h-14 rounded-[var(--radius-xs)] border border-line-hairline overflow-hidden shrink-0 bg-paper-canvas"
        >
          <img :src="t.cover_image_url" alt="" class="w-full h-full object-cover" />
        </div>
        <div
          v-else
          class="w-14 h-14 rounded-[var(--radius-xs)] border border-line-hairline bg-paper-subtle shrink-0 flex items-center justify-center"
        >
          <Sparkles :size="18" :stroke-width="1.5" class="text-aux-rice-mid" />
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-baseline gap-2">
            <p class="text-[14px] font-medium text-ink-strong">{{ t.name }}</p>
            <span class="text-[11px] text-ink-muted font-mono">#{{ t.sort_order }}</span>
          </div>
          <p v-if="t.description" class="text-[12px] text-ink-muted mt-1">{{ t.description }}</p>
        </div>

        <span class="text-[12px] text-ink-muted font-mono whitespace-nowrap shrink-0">
          {{ t.series_count }} 系列
        </span>
        <div class="flex items-center gap-1 shrink-0">
          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:bg-paper-subtle hover:text-ink-strong transition-colors"
            @click="openEdit(t)"
          >
            <Pencil :size="14" :stroke-width="1.5" />
          </button>
          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:bg-[var(--color-state-danger)]/[0.10] hover:text-state-danger transition-colors"
            @click="handleDelete(t)"
          >
            <Trash2 :size="14" :stroke-width="1.5" />
          </button>
        </div>
      </li>
    </ul>
  </Card>

  <Dialog
    :open="dialogOpen"
    :title="editing ? '編輯主題' : '新增主題'"
    size="md"
    @close="dialogOpen = false"
  >
    <div class="space-y-4">
      <div>
        <Label for="th-name">主題名稱</Label>
        <Input id="th-name" v-model="formName" placeholder="例：萌寵 / 風景 / 人物" />
      </div>
      <div>
        <Label for="th-desc">說明（選填）</Label>
        <Textarea id="th-desc" v-model="formDesc" :rows="3" placeholder="主題簡介" />
      </div>
      <div>
        <Label for="th-sort">排序（數字小越靠前）</Label>
        <Input
          id="th-sort"
          :model-value="String(formSortOrder)"
          type="number"
          @update:model-value="(v) => formSortOrder = Number(v) || 0"
        />
      </div>
      <div>
        <Label>主題封面（選填）</Label>
        <ProductCoverUpload v-model="formCover" />
      </div>
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
