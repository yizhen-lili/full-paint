<script setup lang="ts">
import { computed, ref } from 'vue'
import { Loader2 } from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'

import { usePhotoPricesQuery, useUpdatePhotoPriceMutation } from '../queries'
import { DIFFICULTY_LABEL, type Difficulty } from '../api'

const { data, isLoading } = usePhotoPricesQuery()
const updateMut = useUpdatePhotoPriceMutation()

const editing = ref<string | null>(null)
const editValue = ref('')

const items = computed(() => data.value?.items ?? [])

const difficulties: Difficulty[] = ['beginner', 'elementary', 'intermediate', 'advanced']

// 把 list 轉成 matrix： {sizeKey: {difficulty: row}}
const matrix = computed(() => {
  const m: Record<string, Record<Difficulty, { id: string; price: number } | null>> = {}
  for (const r of items.value) {
    const sizeKey = `${r.canvas_w}x${r.canvas_h}`
    if (!m[sizeKey]) {
      m[sizeKey] = {
        beginner: null,
        elementary: null,
        intermediate: null,
        advanced: null,
      }
    }
    m[sizeKey][r.difficulty] = { id: r.id, price: Number(r.price) }
  }
  return m
})

const sizeKeys = computed(() =>
  Object.keys(matrix.value).sort((a, b) => {
    const [aw, ah] = a.split('x').map(Number)
    const [bw, bh] = b.split('x').map(Number)
    return aw * ah - bw * bh
  }),
)

function startEdit(id: string, currentPrice: number) {
  editing.value = id
  editValue.value = String(currentPrice)
}

async function commitEdit(id: string) {
  const n = Number(editValue.value)
  if (!Number.isFinite(n) || n < 0) {
    editing.value = null
    return
  }
  try {
    await updateMut.mutateAsync({ id, price: n })
  } catch {
    /* swallow — 失敗時保留 editing */
  }
  editing.value = null
}

function cancelEdit() {
  editing.value = null
}
</script>

<template>
  <Card>
    <h2 class="font-display text-ink-strong text-[18px] leading-[26px] mb-4">客製照片基礎定價表</h2>
    <p class="text-[12px] text-ink-muted mb-3">
      矩陣顯示：橫軸 = 難易度、縱軸 = 畫布尺寸。點選格子直接修改金額（Enter 儲存、Esc 取消）。
    </p>

    <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>

    <div v-else-if="items.length === 0" class="text-ink-muted text-[13px] text-center py-8">
      尚無定價資料，需先 seed。
    </div>

    <div v-else class="overflow-x-auto">
      <table class="w-full text-[13px]">
        <thead>
          <tr class="border-b border-line-hairline">
            <th class="text-left py-2 px-3 text-ink-strong">尺寸 (cm)</th>
            <th
              v-for="d in difficulties"
              :key="d"
              class="text-right py-2 px-3 text-ink-strong"
            >
              {{ DIFFICULTY_LABEL[d] }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="size in sizeKeys" :key="size" class="border-b border-line-hairline last:border-0">
            <td class="py-2 px-3 font-mono text-ink-default">{{ size.replace('x', ' × ') }}</td>
            <td
              v-for="d in difficulties"
              :key="d"
              class="text-right py-2 px-3"
            >
              <template v-if="matrix[size][d]">
                <input
                  v-if="editing === matrix[size][d]!.id"
                  v-model="editValue"
                  type="number"
                  class="w-24 px-2 h-7 rounded-[var(--radius-xs)] border border-accent text-right font-mono text-[13px]"
                  autofocus
                  @blur="commitEdit(matrix[size][d]!.id)"
                  @keydown.enter.prevent="commitEdit(matrix[size][d]!.id)"
                  @keydown.esc.prevent="cancelEdit"
                />
                <button
                  v-else
                  type="button"
                  class="px-2 h-7 inline-flex items-center justify-end font-mono text-ink-strong rounded-[var(--radius-xs)] hover:bg-paper-subtle"
                  @click="startEdit(matrix[size][d]!.id, matrix[size][d]!.price)"
                >
                  {{ matrix[size][d]!.price.toLocaleString('zh-TW') }}
                </button>
              </template>
              <span v-else class="text-ink-muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </Card>
</template>
