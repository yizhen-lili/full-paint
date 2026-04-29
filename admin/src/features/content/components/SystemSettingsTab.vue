<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Loader2, Save } from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Textarea from '@/shared/ui/Textarea.vue'

import { useSettingsQuery, useUpsertSettingMutation } from '../queries'
import { SETTING_LABEL } from '../api'

const { data, isLoading } = useSettingsQuery()
const upsertMut = useUpsertSettingMutation()

const localValues = ref<Record<string, string>>({})
const saving = ref<string | null>(null)
const apiError = ref<string | null>(null)

watch(
  () => data.value?.items,
  (items) => {
    if (items) {
      const map: Record<string, string> = {}
      for (const s of items) map[s.key] = s.value
      localValues.value = map
    }
  },
  { immediate: true },
)

const grouped = computed(() => {
  const items = data.value?.items ?? []
  // 先用已知 key 排序，未知 key 排在最後
  const knownKeys = Object.keys(SETTING_LABEL)
  const known = items.filter((s) => knownKeys.includes(s.key)).sort(
    (a, b) => knownKeys.indexOf(a.key) - knownKeys.indexOf(b.key),
  )
  const unknown = items.filter((s) => !knownKeys.includes(s.key))
  return [...known, ...unknown]
})

async function saveOne(key: string) {
  apiError.value = null
  saving.value = key
  try {
    await upsertMut.mutateAsync({ key, value: localValues.value[key] ?? '' })
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '儲存失敗'
  } finally {
    saving.value = null
  }
}

function getMeta(key: string): { label: string; type: 'text' | 'textarea' | 'number' } {
  return SETTING_LABEL[key] ?? { label: key, type: 'text' }
}
</script>

<template>
  <Card>
    <p
      v-if="apiError"
      class="mb-3 px-3 py-2 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[12px] rounded-[var(--radius-xs)]"
    >{{ apiError }}</p>

    <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>

    <div v-else-if="grouped.length === 0" class="text-ink-muted text-[13px] text-center py-8">
      尚無系統設定。需先 seed 預設值。
    </div>

    <ul v-else class="divide-y divide-line-hairline">
      <li v-for="s in grouped" :key="s.key" class="py-4 first:pt-0 last:pb-0">
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div class="flex-1 min-w-0 max-w-2xl">
            <Label>
              {{ getMeta(s.key).label }}
              <span class="text-[10px] text-ink-muted font-mono ml-1">{{ s.key }}</span>
            </Label>
            <Input
              v-if="getMeta(s.key).type === 'text'"
              v-model="localValues[s.key]"
            />
            <Input
              v-else-if="getMeta(s.key).type === 'number'"
              v-model="localValues[s.key]"
              type="number"
            />
            <Textarea
              v-else
              v-model="localValues[s.key]"
              :rows="4"
              class="font-mono text-[13px]"
            />
            <p class="mt-1 text-[11px] text-ink-muted">最後更新 {{ new Date(s.updated_at).toLocaleString('zh-TW') }}</p>
          </div>
          <div class="shrink-0">
            <Button
              variant="secondary"
              :disabled="saving === s.key || localValues[s.key] === s.value"
              @click="saveOne(s.key)"
            >
              <Loader2 v-if="saving === s.key" :size="14" :stroke-width="1.5" class="animate-spin" />
              <Save v-else :size="14" :stroke-width="1.5" />
              儲存
            </Button>
          </div>
        </div>
      </li>
    </ul>
  </Card>
</template>
