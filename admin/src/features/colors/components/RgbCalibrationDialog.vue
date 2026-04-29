<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import { Loader2, History, RotateCcw } from 'lucide-vue-next'

import type { PhysicalColor, RgbHistoryItem } from '../api'
import { rgbToHex } from '../api'
import { useRgbHistoryQuery } from '../queries'

const props = defineProps<{
  open: boolean
  color: PhysicalColor | null
  pending: boolean
}>()

const emit = defineEmits<{
  close: []
  saveRgb: [hex: string]
  revert: [history_id: string]
}>()

const hex = ref('#000000')
const errors = ref<Record<string, string>>({})

watch(
  [() => props.open, () => props.color],
  () => {
    if (props.color) hex.value = rgbToHex(props.color.rgb)
    errors.value = {}
  },
  { immediate: true },
)

const colorId = computed(() => (props.open ? props.color?.id : undefined))
const { data: history, isLoading: historyLoading } = useRgbHistoryQuery(colorId)

function submit() {
  if (!/^#[0-9a-fA-F]{6}$/.test(hex.value)) {
    errors.value.hex = 'HEX 格式 #RRGGBB'
    return
  }
  emit('saveRgb', hex.value)
}

function fmtDateTime(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function rgbStr(rgb: [number, number, number]): string {
  return `${rgbToHex(rgb)} · rgb(${rgb.join(', ')})`
}

function noteLabel(note: string): string {
  if (note === 'initial') return '初始建色'
  if (note === 'manual') return '手動校正'
  if (note.startsWith('revert from ')) return `還原自 #${note.slice(12, 20)}`
  return note
}
</script>

<template>
  <Dialog
    :open="open"
    :title="color ? `校正 RGB：${color.code} ${color.name}` : ''"
    size="md"
    @close="emit('close')"
  >
    <div v-if="color" class="space-y-5 text-[13px]">
      <!-- 編輯 RGB -->
      <div>
        <Label>新 RGB（HEX）</Label>
        <div class="flex items-center gap-2">
          <input
            v-model="hex"
            type="color"
            class="w-12 h-9 rounded-[var(--radius-xs)] border border-line-strong cursor-pointer"
          />
          <Input v-model="hex" class="flex-1 font-mono" />
          <Button variant="primary" :disabled="pending" @click="submit">
            <Loader2 v-if="pending" :size="14" :stroke-width="1.5" class="animate-spin" />
            儲存校正
          </Button>
        </div>
        <p v-if="errors.hex" class="mt-1 text-[12px] text-state-danger">{{ errors.hex }}</p>
        <p class="mt-1 text-[11px] text-ink-muted">
          每次儲存都會寫入 history snapshot，不影響既有 palette mappings 的色票。
        </p>
      </div>

      <!-- History -->
      <div>
        <h3 class="text-[12px] tracking-[0.04em] text-ink-muted uppercase mb-2">
          <History :size="12" :stroke-width="1.5" class="inline mr-1" />
          歷史記錄
        </h3>
        <div v-if="historyLoading" class="py-6 flex justify-center text-ink-muted">
          <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
        </div>
        <ul v-else-if="(history?.items.length ?? 0) > 0" class="space-y-2 max-h-[300px] overflow-y-auto">
          <li
            v-for="(h, idx) in history!.items"
            :key="h.id"
            class="flex items-center gap-3 p-2.5 border border-line-hairline rounded-[var(--radius-xs)]"
          >
            <div
              class="w-8 h-8 rounded-[var(--radius-xs)] border border-line-hairline shrink-0"
              :style="{ backgroundColor: rgbToHex(h.rgb) }"
            />
            <div class="flex-1 min-w-0">
              <p class="text-[12px] text-ink-strong font-mono">{{ rgbStr(h.rgb) }}</p>
              <p class="text-[11px] text-ink-muted">
                {{ noteLabel(h.note) }}
                <span v-if="h.changed_by_name"> · {{ h.changed_by_name }}</span>
                · {{ fmtDateTime(h.created_at) }}
              </p>
            </div>
            <button
              v-if="idx > 0"
              type="button"
              class="text-[11px] text-ink-muted hover:text-accent inline-flex items-center gap-1 transition-colors"
              :disabled="pending"
              @click="emit('revert', h.id)"
            >
              <RotateCcw :size="10" :stroke-width="1.5" />
              還原此版
            </button>
            <span v-else class="text-[11px] text-state-success">當前</span>
          </li>
        </ul>
        <p v-else class="text-ink-muted text-[12px] text-center py-4">尚無歷史記錄</p>
      </div>
    </div>

    <template #footer>
      <Button variant="secondary" @click="emit('close')">關閉</Button>
    </template>
  </Dialog>
</template>
