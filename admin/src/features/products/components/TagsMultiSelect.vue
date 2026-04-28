<script setup lang="ts">
import { ref } from 'vue'
import { Check, Plus, X, Loader2 } from 'lucide-vue-next'

import Input from '@/shared/ui/Input.vue'

import { useTagsQuery, useCreateTagMutation } from '../queries'

const props = defineProps<{
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const { data: tagsList } = useTagsQuery()
const create = useCreateTagMutation()

const inlineMode = ref(false)
const newName = ref('')

function toggle(tagId: string) {
  const set = new Set(props.modelValue)
  if (set.has(tagId)) set.delete(tagId)
  else set.add(tagId)
  emit('update:modelValue', Array.from(set))
}

async function submitNew() {
  const name = newName.value.trim()
  if (!name) return
  try {
    const created = await create.mutateAsync({ name })
    emit('update:modelValue', [...props.modelValue, created.id])
    newName.value = ''
    inlineMode.value = false
  } catch (e) {
    alert((e as { message?: string }).message || '建立失敗')
  }
}
</script>

<template>
  <div class="space-y-2">
    <div class="flex flex-wrap gap-1.5">
      <button
        v-for="tag in tagsList ?? []"
        :key="tag.id"
        type="button"
        class="h-7 px-2.5 inline-flex items-center gap-1 text-[12px] rounded-[var(--radius-xs)] border transition-colors"
        :class="
          modelValue.includes(tag.id)
            ? 'bg-accent-tint border-accent text-ink-strong'
            : 'bg-paper-surface border-line-strong text-ink-muted hover:bg-paper-subtle'
        "
        @click="toggle(tag.id)"
      >
        <Check
          v-if="modelValue.includes(tag.id)"
          :size="12"
          :stroke-width="2"
          class="text-accent"
        />
        {{ tag.name }}
      </button>

      <button
        v-if="!inlineMode"
        type="button"
        class="h-7 px-2.5 inline-flex items-center gap-1 text-[12px] rounded-[var(--radius-xs)] border border-dashed border-line-strong text-ink-muted hover:bg-paper-subtle transition-colors"
        @click="inlineMode = true"
      >
        <Plus :size="12" :stroke-width="1.75" />
        新增標籤
      </button>
    </div>

    <div v-if="inlineMode" class="flex gap-2">
      <Input
        v-model="newName"
        placeholder="標籤名稱"
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
