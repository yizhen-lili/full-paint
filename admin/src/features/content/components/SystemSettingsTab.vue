<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Loader2, Save } from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Textarea from '@/shared/ui/Textarea.vue'

import { useSettingsQuery, useUpsertSettingMutation } from '../queries'
import { SETTING_LABEL, SETTING_GROUP_LABEL, type SettingMeta } from '../api'

const { data, isLoading } = useSettingsQuery()
const upsertMut = useUpsertSettingMutation()

// 已從 server 拿到的「實際值」snapshot（用來算 dirty）
const savedValues = ref<Record<string, string>>({})
// 用戶在輸入框裡的值（編輯狀態）
const localValues = ref<Record<string, string>>({})
const saving = ref(false)
const apiError = ref<string | null>(null)

watch(
  () => data.value?.items,
  (items) => {
    if (!items) return
    const next: Record<string, string> = {}
    for (const s of items) next[s.key] = s.value
    // 已知但 DB 還沒值的 key → 空字串
    for (const key of Object.keys(SETTING_LABEL)) {
      if (!(key in next)) next[key] = ''
    }
    savedValues.value = next

    // 只更新「沒被使用者改過」的 key — 已被改過的保留當前值不洗掉
    const newLocal: Record<string, string> = { ...localValues.value }
    for (const key of Object.keys(next)) {
      const current = localValues.value[key]
      const saved = next[key]
      // 從未在 localValues 裡 → 用 server 值初始化
      // 已在 localValues 裡，但等於 server 舊值 → 同步成 server 新值
      // 已被改過（!= server 舊值）→ 保留不動
      if (current === undefined) {
        newLocal[key] = saved
      } else if (!isDirty(key)) {
        newLocal[key] = saved
      }
    }
    localValues.value = newLocal
  },
  { immediate: true },
)

function isDirty(key: string): boolean {
  return (localValues.value[key] ?? '') !== (savedValues.value[key] ?? '')
}

const dirtyKeys = computed(() =>
  Object.keys(localValues.value).filter((k) => isDirty(k)),
)

interface Row {
  key: string
  meta: SettingMeta
  saved: boolean
  updatedAt: string | null
}

const allRows = computed<Row[]>(() => {
  const items = data.value?.items ?? []
  const itemMap: Record<string, { value: string; updated_at: string }> = {}
  for (const s of items) itemMap[s.key] = { value: s.value, updated_at: s.updated_at }

  const rows: Row[] = []
  for (const [key, meta] of Object.entries(SETTING_LABEL)) {
    const persisted = itemMap[key]
    rows.push({
      key,
      meta,
      saved: !!persisted,
      updatedAt: persisted?.updated_at ?? null,
    })
  }
  for (const s of items) {
    if (!(s.key in SETTING_LABEL)) {
      rows.push({
        key: s.key,
        meta: { label: s.key, type: 'text', group: 'misc' },
        saved: true,
        updatedAt: s.updated_at,
      })
    }
  }
  return rows
})

type Group = SettingMeta['group']
const grouped = computed<Array<{ group: Group; label: string; rows: Row[] }>>(() => {
  const map = new Map<Group, Row[]>()
  for (const r of allRows.value) {
    const list = map.get(r.meta.group) ?? []
    list.push(r)
    map.set(r.meta.group, list)
  }
  const order: Group[] = ['payment', 'ecpay_sender', 'product_info', 'paint', 'custom', 'misc']
  return order
    .filter((g) => map.has(g))
    .map((g) => ({ group: g, label: SETTING_GROUP_LABEL[g], rows: map.get(g) ?? [] }))
})

async function saveAll() {
  if (dirtyKeys.value.length === 0) return
  apiError.value = null
  saving.value = true
  const failed: string[] = []
  try {
    // 依序送 PATCH（後端 upsert，每筆獨立 transaction）— 並發會造成 commit 衝突
    for (const key of dirtyKeys.value) {
      try {
        await upsertMut.mutateAsync({ key, value: localValues.value[key] ?? '' })
      } catch (e) {
        failed.push(`${key}: ${(e as { message?: string }).message || '失敗'}`)
      }
    }
    if (failed.length > 0) {
      apiError.value = `部分欄位儲存失敗：\n${failed.join('\n')}`
    }
  } finally {
    saving.value = false
  }
}

function discardAll() {
  // 把 localValues 還原為 savedValues
  localValues.value = { ...savedValues.value }
}
</script>

<template>
  <div class="space-y-5">
    <!-- 頂部 sticky 工具列 -->
    <div
      v-if="dirtyKeys.length > 0"
      class="sticky top-0 z-10 mb-2 px-4 py-3 bg-accent/[0.10] border border-accent/40 rounded-[var(--radius-xs)] flex items-center justify-between"
    >
      <div class="text-[13px] text-ink-strong">
        有 <span class="font-mono font-bold">{{ dirtyKeys.length }}</span> 個欄位未儲存
      </div>
      <div class="flex items-center gap-2">
        <Button variant="secondary" :disabled="saving" @click="discardAll">
          放棄變更
        </Button>
        <Button variant="primary" :disabled="saving" @click="saveAll">
          <Loader2 v-if="saving" :size="14" :stroke-width="1.5" class="animate-spin" />
          <Save v-else :size="14" :stroke-width="1.5" />
          儲存全部變更
        </Button>
      </div>
    </div>

    <p
      v-if="apiError"
      class="px-3 py-2 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[12px] rounded-[var(--radius-xs)] whitespace-pre-line"
    >{{ apiError }}</p>

    <div v-if="isLoading" class="py-12 flex justify-center text-ink-muted">
      <Loader2 :size="20" :stroke-width="1.5" class="animate-spin" />
    </div>

    <template v-else>
      <Card v-for="g in grouped" :key="g.group">
        <h2 class="font-display text-ink-strong text-[16px] leading-[24px] mb-4 pb-3 border-b border-line-hairline">
          {{ g.label }}
        </h2>

        <ul class="divide-y divide-line-hairline">
          <li v-for="row in g.rows" :key="row.key" class="py-4 first:pt-0 last:pb-0">
            <div class="max-w-2xl">
              <Label>
                {{ row.meta.label }}
                <span class="text-[10px] text-ink-muted font-mono ml-1">{{ row.key }}</span>
                <span
                  v-if="!row.saved"
                  class="ml-2 inline-flex items-center px-1.5 h-[16px] text-[9px] tracking-[0.18em] uppercase rounded-[var(--radius-xs)] bg-[var(--color-state-warning)]/[0.18] text-state-warning"
                >未設定</span>
                <span
                  v-if="isDirty(row.key)"
                  class="ml-2 inline-flex items-center px-1.5 h-[16px] text-[9px] tracking-[0.18em] uppercase rounded-[var(--radius-xs)] bg-accent/[0.18] text-accent"
                >已修改</span>
              </Label>
              <Input
                v-if="row.meta.type === 'text'"
                v-model="localValues[row.key]"
              />
              <Input
                v-else-if="row.meta.type === 'number'"
                v-model="localValues[row.key]"
                type="number"
              />
              <Textarea
                v-else
                v-model="localValues[row.key]"
                :rows="4"
                class="font-mono text-[13px]"
              />
              <p v-if="row.meta.hint" class="mt-1 text-[11px] text-ink-muted">{{ row.meta.hint }}</p>
              <p v-if="row.updatedAt" class="mt-1 text-[11px] text-ink-muted">
                最後更新 {{ new Date(row.updatedAt).toLocaleString('zh-TW') }}
              </p>
            </div>
          </li>
        </ul>
      </Card>
    </template>
  </div>
</template>
