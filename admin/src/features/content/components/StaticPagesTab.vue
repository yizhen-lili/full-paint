<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Loader2, Save, Eye } from 'lucide-vue-next'

import Card from '@/shared/ui/Card.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Textarea from '@/shared/ui/Textarea.vue'

import { usePagesQuery, useUpsertPageMutation } from '../queries'
import { PAGE_LABEL } from '../api'

const { data, isLoading } = usePagesQuery()
const upsertMut = useUpsertPageMutation()

const selectedSlug = ref<string>('')
const title = ref('')
const content = ref('')
const showPreview = ref(false)
const apiError = ref<string | null>(null)

const pages = computed(() => data.value?.items ?? [])

watch(
  pages,
  (list) => {
    if (list.length > 0 && !selectedSlug.value) {
      selectPage(list[0].slug)
    }
  },
  { immediate: true },
)

function selectPage(slug: string) {
  const p = pages.value.find((x) => x.slug === slug)
  if (!p) return
  selectedSlug.value = slug
  title.value = p.title
  content.value = p.content
  showPreview.value = false
}

async function save() {
  apiError.value = null
  try {
    await upsertMut.mutateAsync({
      slug: selectedSlug.value,
      payload: { title: title.value, content: content.value },
    })
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '儲存失敗'
  }
}

// 簡易 markdown 預覽（標題 / 段落 / 粗體 / 斜體 / 列表 / 連結）— full markdown 留 future polish
function renderMarkdown(md: string): string {
  return md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/^### (.*)$/gm, '<h3>$1</h3>')
    .replace(/^## (.*)$/gm, '<h2>$1</h2>')
    .replace(/^# (.*)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/^- (.*)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>')
}
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-5">
    <!-- 頁面清單 -->
    <Card>
      <h3 class="text-[12px] tracking-[0.04em] text-ink-muted uppercase mb-3">頁面清單</h3>
      <div v-if="isLoading" class="text-ink-muted text-[12px]">載入中...</div>
      <ul v-else class="space-y-1">
        <li v-for="p in pages" :key="p.slug">
          <button
            type="button"
            class="w-full text-left px-3 py-2 text-[13px] rounded-[var(--radius-xs)] transition-colors"
            :class="
              selectedSlug === p.slug
                ? 'bg-[var(--color-accent)]/[0.10] text-accent font-medium'
                : 'text-ink-default hover:bg-paper-subtle'
            "
            @click="selectPage(p.slug)"
          >
            {{ PAGE_LABEL[p.slug] || p.slug }}
            <span class="block text-[10px] text-ink-muted font-mono">{{ p.slug }}</span>
          </button>
        </li>
      </ul>
    </Card>

    <!-- 編輯器 -->
    <Card>
      <div v-if="!selectedSlug" class="text-ink-muted text-[13px]">請從左側選擇一個頁面</div>
      <template v-else>
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-display text-ink-strong text-[18px]">
            編輯：{{ PAGE_LABEL[selectedSlug] || selectedSlug }}
          </h2>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="text-[12px] text-ink-muted hover:text-ink-strong inline-flex items-center gap-1 transition-colors"
              @click="showPreview = !showPreview"
            >
              <Eye :size="12" :stroke-width="1.5" />
              {{ showPreview ? '回到編輯' : '預覽' }}
            </button>
          </div>
        </div>

        <div
          v-if="apiError"
          class="mb-3 px-3 py-2 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[12px] rounded-[var(--radius-xs)]"
        >
          {{ apiError }}
        </div>

        <div v-if="!showPreview" class="space-y-4">
          <div>
            <Label>頁面標題</Label>
            <Input v-model="title" />
          </div>
          <div>
            <Label>內容（Markdown 格式）</Label>
            <Textarea
              v-model="content"
              :rows="20"
              placeholder="支援 # 標題 / **粗體** / *斜體* / - 列表 / [連結](url)"
              class="font-mono text-[13px]"
            />
            <p class="mt-1 text-[11px] text-ink-muted">
              客戶端渲染時會自動轉成 HTML。換行兩次 = 新段落。
            </p>
          </div>
          <div class="flex justify-end">
            <Button variant="primary" :disabled="upsertMut.isPending.value" @click="save">
              <Loader2 v-if="upsertMut.isPending.value" :size="14" :stroke-width="1.5" class="animate-spin" />
              <Save v-else :size="14" :stroke-width="1.5" />
              儲存
            </Button>
          </div>
        </div>

        <div v-else class="prose-yiimui text-[14px] leading-[24px]" v-html="renderMarkdown(content)" />
      </template>
    </Card>
  </div>
</template>

<style scoped>
.prose-yiimui :deep(h1) { font-size: 22px; font-weight: 600; margin: 1em 0 0.5em; }
.prose-yiimui :deep(h2) { font-size: 18px; font-weight: 600; margin: 1em 0 0.5em; }
.prose-yiimui :deep(h3) { font-size: 16px; font-weight: 600; margin: 1em 0 0.5em; }
.prose-yiimui :deep(p) { margin: 0.5em 0; }
.prose-yiimui :deep(ul) { padding-left: 20px; margin: 0.5em 0; }
.prose-yiimui :deep(li) { margin: 0.2em 0; }
.prose-yiimui :deep(a) { color: var(--color-accent); text-decoration: underline; }
</style>
