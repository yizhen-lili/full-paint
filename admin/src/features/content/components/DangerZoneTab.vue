<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { AlertTriangle, Trash2, Loader2, RefreshCw } from 'lucide-vue-next'
import Card from '@/shared/ui/Card.vue'
import Input from '@/shared/ui/Input.vue'
import Button from '@/shared/ui/Button.vue'
import Label from '@/shared/ui/Label.vue'

const API = '/api/v1'

interface PreviewData {
  counts: Record<string, number>
  coupons_to_release: number
  order_items_to_restore_stock: number
}

interface ClearSummary {
  ok: boolean
  summary: Record<string, number>
}

const preview = ref<PreviewData | null>(null)
const previewLoading = ref(false)
const previewError = ref<string | null>(null)

const confirmPhrase = ref('')
const submitting = ref(false)
const result = ref<ClearSummary | null>(null)
const apiError = ref<string | null>(null)

const REQUIRED_PHRASE = 'CLEAR-ALL-TEST-DATA'

// 通知中心清除
const clearNotifSubmitting = ref(false)
const clearNotifResult = ref<{ before: number; deleted: number } | null>(null)
const clearNotifError = ref<string | null>(null)

async function clearAllNotifications() {
  if (!confirm('確定要清空整個通知中心嗎？此動作不可復原。')) return
  clearNotifSubmitting.value = true
  clearNotifError.value = null
  clearNotifResult.value = null
  try {
    const res = await fetch(`${API}/admin/system/clear-all-notifications`, {
      method: 'POST',
      credentials: 'include',
    })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`)
    clearNotifResult.value = body as { before: number; deleted: number }
  } catch (e) {
    clearNotifError.value = (e as Error).message || '清除失敗'
  } finally {
    clearNotifSubmitting.value = false
  }
}

async function loadPreview() {
  previewLoading.value = true
  previewError.value = null
  try {
    const res = await fetch(`${API}/admin/system/clear-test-data/preview`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${res.status}`)
    }
    preview.value = await res.json()
  } catch (e) {
    previewError.value = (e as Error).message || '載入失敗'
  } finally {
    previewLoading.value = false
  }
}

async function executeClear() {
  if (confirmPhrase.value !== REQUIRED_PHRASE) {
    apiError.value = `確認字串必須輸入 ${REQUIRED_PHRASE}`
    return
  }
  if (!confirm('真的要清除所有訂單 / 購物車 / 客製申請嗎？此動作不可復原。')) {
    return
  }
  submitting.value = true
  apiError.value = null
  result.value = null
  try {
    const res = await fetch(`${API}/admin/system/clear-test-data`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm_phrase: confirmPhrase.value }),
    })
    const body = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(body.detail || `HTTP ${res.status}`)
    result.value = body as ClearSummary
    confirmPhrase.value = ''
    // 重新載入預覽（應該全變 0）
    await loadPreview()
  } catch (e) {
    apiError.value = (e as Error).message || '清除失敗'
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadPreview()
})
</script>

<template>
  <div class="space-y-5">
    <!-- 警告 banner -->
    <Card>
      <div class="flex items-start gap-3">
        <AlertTriangle :size="20" class="text-state-danger flex-shrink-0 mt-0.5" />
        <div>
          <h2 class="font-display text-state-danger text-[16px] leading-[24px] mb-1">
            ⚠️ 危險操作區
          </h2>
          <p class="text-[12px] leading-[1.7] text-ink-default">
            這裡的操作會<strong>不可復原地修改資料庫內容</strong>。僅限上線前測試資料清理使用。
            動作前會雙重確認（按鈕 + confirm phrase）。
          </p>
        </div>
      </div>
    </Card>

    <!-- Clear test data -->
    <Card>
      <div class="flex items-baseline justify-between mb-4">
        <h3 class="font-display text-ink-strong text-[16px] leading-[24px]">
          清除測試訂單 / 購物車 / 客製申請
        </h3>
        <Button variant="ghost" size="sm" :loading="previewLoading" @click="loadPreview">
          <RefreshCw :size="13" :stroke-width="1.5" />
          重新計算
        </Button>
      </div>

      <p class="text-[12px] leading-[1.7] text-ink-muted mb-4">
        清除所有 orders / order_items / cart_items / custom_requests / shipments
        / payment_submissions / production_progress / 相關通知與訊息。
        同時還原 physical_colors.stock_ml + 釋放 user_coupons（is_used 重置）。
        <br>
        <strong>不會動：</strong>users / products / variants / themes / series / tags
        / production_jobs / canvas_sizes / coupon_configs。
      </p>

      <!-- 預覽 -->
      <div
        v-if="previewError"
        class="px-3 py-2.5 mb-4 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[12px] rounded-[var(--radius-xs)]"
      >
        預覽載入失敗：{{ previewError }}
      </div>

      <div v-else-if="previewLoading" class="text-[13px] text-ink-muted py-4 flex items-center gap-2">
        <Loader2 :size="14" class="animate-spin" />
        載入預覽…
      </div>

      <div v-else-if="preview" class="bg-paper-deep border border-line-hairline rounded-[var(--radius-xs)] p-4 mb-4">
        <p class="text-[11px] tracking-[0.06em] uppercase text-ink-muted mb-2">將清除</p>
        <ul class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px] mb-3">
          <li v-for="(n, key) in preview.counts" :key="key" class="flex justify-between">
            <span class="text-ink-default">{{ key }}</span>
            <span class="font-mono text-ink-strong">{{ n }} 筆</span>
          </li>
        </ul>
        <div class="pt-2 border-t border-line-hairline space-y-1 text-[11px] text-ink-muted">
          <p>釋放 user_coupons：<span class="font-mono text-ink-default">{{ preview.coupons_to_release }} 筆</span></p>
          <p>還原 stock 之 order_item：<span class="font-mono text-ink-default">{{ preview.order_items_to_restore_stock }} 筆</span></p>
        </div>
      </div>

      <!-- 結果 -->
      <div
        v-if="result"
        class="px-3 py-2.5 mb-4 border border-state-success/40 bg-[var(--color-state-success)]/[0.06] text-state-success rounded-[var(--radius-xs)]"
      >
        <p class="font-medium mb-2 text-[13px]">✅ 清除完成</p>
        <ul class="text-[11px] grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono">
          <li v-for="(n, key) in result.summary" :key="key" class="flex justify-between">
            <span>{{ key }}</span>
            <span>{{ n }}</span>
          </li>
        </ul>
      </div>

      <!-- Confirm phrase + 按鈕 -->
      <div class="border-t border-line-hairline pt-4 space-y-3">
        <div>
          <Label for="confirm-phrase">輸入確認字串：<code class="text-accent-wine">{{ REQUIRED_PHRASE }}</code></Label>
          <Input
            id="confirm-phrase"
            v-model="confirmPhrase"
            type="text"
            placeholder="CLEAR-ALL-TEST-DATA"
            class="font-mono"
          />
        </div>

        <div
          v-if="apiError"
          class="px-3 py-2 text-[12px] text-state-danger bg-[var(--color-state-danger)]/[0.06] border border-state-danger/40 rounded-[var(--radius-xs)]"
        >
          {{ apiError }}
        </div>

        <Button
          variant="primary"
          :disabled="confirmPhrase !== REQUIRED_PHRASE || submitting"
          :loading="submitting"
          class="!bg-state-danger hover:!bg-state-danger/90 !border-state-danger"
          @click="executeClear"
        >
          <Trash2 :size="14" :stroke-width="1.5" />
          確認清除
        </Button>
      </div>
    </Card>

    <!-- 通知中心清空 -->
    <Card>
      <div class="flex items-baseline justify-between mb-3">
        <h3 class="font-display text-ink-strong text-[16px] leading-[24px]">
          清空通知中心
        </h3>
      </div>

      <p class="text-[12px] leading-[1.7] text-ink-muted mb-4">
        刪除所有 admin_notifications（含 production_failed / stock_shortage / order / custom_request 等所有類型）。
        適用於 maintenance 清空累積通知。<strong class="text-ink-default">不會動到任何業務資料</strong>。
      </p>

      <div
        v-if="clearNotifResult"
        class="px-3 py-2.5 mb-3 border border-state-success/40 bg-[var(--color-state-success)]/[0.06] text-state-success text-[12px] rounded-[var(--radius-xs)]"
      >
        ✅ 已清除 {{ clearNotifResult.deleted }} 筆通知（原 {{ clearNotifResult.before }} 筆）
      </div>

      <div
        v-if="clearNotifError"
        class="px-3 py-2 mb-3 text-[12px] text-state-danger bg-[var(--color-state-danger)]/[0.06] border border-state-danger/40 rounded-[var(--radius-xs)]"
      >
        {{ clearNotifError }}
      </div>

      <Button
        variant="secondary"
        :loading="clearNotifSubmitting"
        @click="clearAllNotifications"
      >
        <Trash2 :size="14" :stroke-width="1.5" />
        清空通知中心
      </Button>
    </Card>
  </div>
</template>
