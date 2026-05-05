<script setup lang="ts">
import { ref } from 'vue'
import { Plus, X, Loader2 } from 'lucide-vue-next'

import Select from '@/shared/ui/Select.vue'
import Input from '@/shared/ui/Input.vue'

import { useSeriesQuery, useCreateSeriesMutation } from '../queries'

defineProps<{
  modelValue: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const { data: seriesList } = useSeriesQuery()
const create = useCreateSeriesMutation()

const inlineMode = ref(false)
const newName = ref('')

async function submitNew() {
  const name = newName.value.trim()
  if (!name) return
  try {
    const created = await create.mutateAsync({
      name,
      description: null,
      theme_id: null,
      is_featured: false,
    })
    emit('update:modelValue', created.id)
    newName.value = ''
    inlineMode.value = false
  } catch (e) {
    alert((e as { message?: string }).message || '建立失敗')
  }
}

function options() {
  const opts = [{ value: '', label: '無系列' }]
  for (const s of seriesList.value ?? []) {
    opts.push({ value: s.id, label: s.name })
  }
  return opts
}
</script>

<template>
  <div class="space-y-2">
    <div v-if="!inlineMode" class="flex gap-2">
      <div class="flex-1">
        <Select
          :model-value="modelValue ?? ''"
          :options="options()"
          @update:model-value="(v) => $emit('update:modelValue', v || null)"
        />
      </div>
      <button
        type="button"
        class="h-9 px-3 inline-flex items-center gap-1 rounded-[var(--radius-xs)] border border-line-strong text-ink-default text-[13px] hover:bg-paper-subtle transition-colors"
        @click="inlineMode = true"
      >
        <Plus :size="14" :stroke-width="1.5" />
        新增
      </button>
    </div>

    <div v-else class="flex gap-2">
      <Input
        v-model="newName"
        placeholder="新系列名稱"
        autofocus
        @keydown.enter.prevent="submitNew"
        @keydown.esc="inlineMode = false; newName = ''"
      />
      <button
        type="button"
        class="h-9 px-3 inline-flex items-center gap-1 rounded-[var(--radius-xs)] bg-accent text-paper-surface text-[13px] font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
        :disabled="create.isPending.value || !newName.trim()"
        @click="submitNew"
      >
        <Loader2 v-if="create.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
        建立
      </button>
      <button
        type="button"
        class="h-9 w-9 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:text-ink-strong hover:bg-paper-subtle transition-colors"
        @click="inlineMode = false; newName = ''"
      >
        <X :size="14" :stroke-width="1.5" />
      </button>
    </div>
  </div>
</template>
