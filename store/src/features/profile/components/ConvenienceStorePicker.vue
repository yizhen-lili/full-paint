<script setup lang="ts">
import { Store, MapPin, X } from 'lucide-vue-next'
import type { ShippingType } from '../api'
import { buildCvsMapUrl } from '../cvsRedirect'

const props = defineProps<{
  shippingType: ShippingType  // 'seven_eleven' | 'family_mart' (home 不會走這裡)
  storeId: string | null
  storeName: string | null
  /** 同分頁 redirect 流程 — 用 sessionStorage 還原時，已選店的地址 / 電話顯示用 */
  selectedAddress?: string | null
  selectedPhone?: string | null
}>()

const emit = defineEmits<{
  'update:storeId': [value: string]
  'update:storeName': [value: string]
  /** 即將 redirect 到 ECpay，父層需要把當前 form draft 寫進 sessionStorage */
  'before-redirect': []
}>()

function openPicker() {
  // 行動 Safari 在 cross-origin redirect 後會清掉 window.opener + 擋 window.close，
  // 所以舊版 popup + postMessage 流程行不通 → 全平台改成同分頁 redirect。
  const url = buildCvsMapUrl(props.shippingType, window.location.pathname)
  if (!url) {
    return
  }
  // 父層必須在這個事件裡同步 saveCvsRedirect()（寫 sessionStorage）
  emit('before-redirect')
  window.location.assign(url)
}

function clearStore() {
  emit('update:storeId', '')
  emit('update:storeName', '')
}
</script>

<template>
  <div class="cvs-picker">
    <template v-if="storeId && storeName">
      <div class="selected-card">
        <div class="selected-icon">
          <Store :size="14" />
        </div>
        <div class="selected-info">
          <div class="selected-name">{{ storeName }}</div>
          <div class="selected-meta">門市代碼 {{ storeId }}</div>
          <div v-if="selectedAddress" class="selected-addr">{{ selectedAddress }}</div>
          <div v-if="selectedPhone" class="selected-addr">{{ selectedPhone }}</div>
        </div>
        <button type="button" class="clear-btn" @click="clearStore" aria-label="清除門市">
          <X :size="14" />
        </button>
      </div>
      <button
        type="button"
        class="open-btn open-btn-secondary"
        @click="openPicker"
      >
        <MapPin :size="14" />
        <span>重新選擇門市</span>
      </button>
    </template>

    <button
      v-else
      type="button"
      class="open-btn"
      @click="openPicker"
    >
      <MapPin :size="14" />
      <span>選擇門市</span>
    </button>

    <p class="hint">
      將同分頁開啟 ECpay 選店畫面，挑好門市後會自動返回此頁面（已輸入的收件人 / 電話會保留）。
    </p>
  </div>
</template>

<style scoped>
.cvs-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.open-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  background: var(--color-paper-canvas);
  border: 1px dashed var(--color-accent);
  color: var(--color-accent);
  font-family: var(--font-body);
  font-size: 13px;
  letter-spacing: 0.04em;
  border-radius: var(--radius-xs);
  cursor: pointer;
  transition: background 150ms, border-color 150ms;
  align-self: flex-start;
}
.open-btn:hover {
  background: var(--color-accent-tint);
  border-color: var(--color-accent-deep);
}
.open-btn :deep(svg) { stroke: currentColor; stroke-width: 1.5; fill: none; }

/* 已選店時的「重新選擇」按鈕 — 較不搶眼，避免跟「已選門市」視覺衝突 */
.open-btn-secondary {
  border-style: solid;
  border-color: var(--color-line);
  background: transparent;
  color: var(--color-ink-default);
  padding: 8px 14px;
  font-size: 12px;
  margin-top: 8px;
}
.open-btn-secondary:hover {
  background: var(--color-paper-deep);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.selected-card {
  display: grid;
  grid-template-columns: 28px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
  background: var(--color-accent-tint);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-xs);
}

.selected-icon {
  width: 28px; height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-paper-canvas);
  border: 1px solid var(--color-line-subtle);
  color: var(--color-accent);
}
.selected-icon :deep(svg) { stroke: currentColor; stroke-width: 1.5; fill: none; }

.selected-info { min-width: 0; }
.selected-name {
  font-family: var(--font-cn-serif);
  font-size: 15px;
  color: var(--color-ink-strong);
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}
.selected-meta {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--color-ink-muted);
}
.selected-addr {
  font-size: 12px;
  color: var(--color-ink-muted);
  letter-spacing: 0.02em;
  margin-top: 2px;
  line-height: 1.5;
}

.clear-btn {
  width: 28px; height: 28px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  color: var(--color-ink-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 150ms, border-color 150ms;
}
.clear-btn:hover {
  color: var(--color-state-danger);
  border-color: var(--color-state-danger);
}
.clear-btn :deep(svg) { stroke: currentColor; stroke-width: 1.5; fill: none; }

.hint {
  font-size: 11px;
  color: var(--color-ink-muted);
  margin: 0;
  letter-spacing: 0.04em;
}
</style>
