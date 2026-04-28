<script setup lang="ts">
import Select from '@/shared/ui/Select.vue'

import { useThemesQuery } from '../queries'

defineProps<{
  modelValue: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const { data } = useThemesQuery()

function options() {
  const opts = [{ value: '', label: '無主題' }]
  for (const t of data.value?.items ?? []) {
    opts.push({ value: t.id, label: t.name })
  }
  return opts
}
</script>

<template>
  <Select
    :model-value="modelValue ?? ''"
    :options="options()"
    @update:model-value="(v) => emit('update:modelValue', v || null)"
  />
</template>
