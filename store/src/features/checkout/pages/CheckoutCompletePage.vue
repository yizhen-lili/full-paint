<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useQuery } from '@tanstack/vue-query'
import { Loader2, Check, Copy, AlertCircle } from 'lucide-vue-next'
import * as ordersApi from '@/features/orders/api'

const route = useRoute()
const orderId = computed(() => String(route.query.order || ''))

const orderQuery = useQuery({
  queryKey: computed(() => ['order', orderId.value] as const),
  queryFn: () => ordersApi.getOrder(orderId.value),
  enabled: computed(() => !!orderId.value),
})

const order = computed(() => orderQuery.data.value ?? null)

// 24h 倒數
const now = ref(Date.now())
let tickHandle: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  tickHandle = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})
onUnmounted(() => {
  if (tickHandle) clearInterval(tickHandle)
})

const deadline = computed(() => {
  if (!order.value?.payment_deadline) return null
  return new Date(order.value.payment_deadline).getTime()
})

const remainingMs = computed(() => {
  if (!deadline.value) return 0
  return Math.max(0, deadline.value - now.value)
})

const expired = computed(() => deadline.value !== null && remainingMs.value === 0)

function pad(n: number): string {
  return String(n).padStart(2, '0')
}
const countdown = computed(() => {
  const ms = remainingMs.value
  const totalSec = Math.floor(ms / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  return { h: pad(h), m: pad(m), s: pad(s) }
})

// payment_info 從 backend 的 service.py settings 來，可能在 shipping_snapshot 或別處
// 這裡先嘗試從 shipping_snapshot 找；後端如果改放別處再調整
const paymentInfo = computed(() => {
  // backend create_order response 的 payment_info 並未存到 OrderDetail
  // 這裡 fallback 寫死從 system_settings 預期欄位（admin 可改）
  // TODO: 將 payment_info 加到 OrderDetail 或新加 endpoint
  return {
    bank_name: '中華郵政',
    branch: '永康分行',
    account_name: 'YIIMUI 易木工作室',
    account_no: '700-0042312-345-678',
    note: '匯款後請至「我的訂單」上傳付款核對表單',
  }
})

const copyMsg = ref<string | null>(null)
async function copyAccount() {
  try {
    await navigator.clipboard.writeText(paymentInfo.value.account_no)
    copyMsg.value = '已複製'
    setTimeout(() => (copyMsg.value = null), 1500)
  } catch {
    copyMsg.value = '複製失敗'
    setTimeout(() => (copyMsg.value = null), 1500)
  }
}
</script>

<template>
  <main class="page">
    <div v-if="orderQuery.isPending.value" class="loading">
      <Loader2 :size="22" />
    </div>

    <section v-else-if="orderQuery.isError.value || !order" class="errored">
      <AlertCircle class="errored-icon" />
      <h1 class="errored-title">找不到訂單</h1>
      <p class="errored-hint">訂單 id 缺失或讀取失敗。</p>
      <RouterLink to="/orders" class="errored-cta">回我的訂單 →</RouterLink>
    </section>

    <template v-else>
      <!-- 成功標頭 -->
      <header class="head">
        <div class="success-icon">
          <Check />
        </div>
        <span class="eyebrow">— Order Placed —</span>
        <h1 class="title">訂單已建立</h1>
        <p class="lede">
          訂單編號 <strong>{{ order.order_number }}</strong> ·
          應付 <strong>NT$ {{ order.total.toLocaleString() }}</strong>
        </p>
      </header>

      <!-- 倒數 + 付款資訊 -->
      <section class="payment">
        <div class="left">
          <div class="block-eyebrow">
            <span class="block-no">01</span>
            <span class="block-cap">Payment Window</span>
          </div>
          <h2 class="block-title">24 小時付款期限</h2>

          <div v-if="deadline" class="countdown" :class="{ expired }">
            <div class="cd-cell">
              <span class="cd-num">{{ countdown.h }}</span>
              <span class="cd-label">時</span>
            </div>
            <span class="cd-sep">:</span>
            <div class="cd-cell">
              <span class="cd-num">{{ countdown.m }}</span>
              <span class="cd-label">分</span>
            </div>
            <span class="cd-sep">:</span>
            <div class="cd-cell">
              <span class="cd-num">{{ countdown.s }}</span>
              <span class="cd-label">秒</span>
            </div>
          </div>
          <p v-else class="cd-meta">
            無付款期限資訊
          </p>

          <p v-if="!expired" class="hint">
            請於上方倒數結束前完成轉帳；逾期未付款訂單將自動取消。
          </p>
          <p v-else class="hint hint-expired">
            付款期限已過，訂單已自動取消。
          </p>
        </div>

        <div class="right">
          <div class="block-eyebrow">
            <span class="block-no">02</span>
            <span class="block-cap">Bank Transfer</span>
          </div>
          <h2 class="block-title">匯款資訊</h2>

          <dl class="bank">
            <div class="bank-row">
              <dt>銀行</dt>
              <dd>{{ paymentInfo.bank_name }}<span v-if="paymentInfo.branch"> · {{ paymentInfo.branch }}</span></dd>
            </div>
            <div class="bank-row">
              <dt>戶名</dt>
              <dd>{{ paymentInfo.account_name }}</dd>
            </div>
            <div class="bank-row bank-row-account">
              <dt>帳號</dt>
              <dd>
                <span class="acc">{{ paymentInfo.account_no }}</span>
                <button type="button" class="copy" @click="copyAccount">
                  <Copy :size="12" />
                  <span>{{ copyMsg ?? '複製' }}</span>
                </button>
              </dd>
            </div>
            <div class="bank-row bank-row-amt">
              <dt>金額</dt>
              <dd class="amt">NT$ {{ order.total.toLocaleString() }}</dd>
            </div>
          </dl>

          <p class="bank-note">
            {{ paymentInfo.note }}
          </p>
        </div>
      </section>

      <!-- 下一步引導 -->
      <section class="next">
        <div class="next-card">
          <div class="next-no">→</div>
          <div class="next-body">
            <h3 class="next-title">下一步：上傳付款核對表單</h3>
            <p class="next-desc">
              完成轉帳後，到訂單詳情頁上傳轉帳金額 / 日期 / 帳號末五碼，加快人工核對。
            </p>
          </div>
          <RouterLink :to="`/orders/${order.id}`" class="next-cta">
            前往訂單詳情 →
          </RouterLink>
        </div>
        <div class="next-card next-card-secondary">
          <div class="next-no">↩</div>
          <div class="next-body">
            <h3 class="next-title">繼續逛逛</h3>
            <p class="next-desc">看看其他商品，多買滿 NT$ 800 享免運。</p>
          </div>
          <RouterLink to="/products" class="next-cta next-cta-ghost">
            看商品 →
          </RouterLink>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 56px 56px 96px;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 96px 0;
  color: var(--color-ink-muted);
}
.loading :deep(svg) {
  animation: spin 1s linear infinite;
  stroke: currentColor;
  stroke-width: 1.5;
  fill: none;
}
@keyframes spin { to { transform: rotate(360deg); } }

.errored {
  text-align: center;
  padding: 96px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.errored-icon {
  width: 40px; height: 40px;
  stroke: var(--color-state-danger);
  stroke-width: 1.25;
  fill: none;
  margin-bottom: 16px;
}
.errored-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 28px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0 0 12px;
}
.errored-hint {
  font-size: 14px;
  color: var(--color-ink-muted);
  margin: 0 0 28px;
}
.errored-cta {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
  border-bottom: 1px solid var(--color-accent);
  padding-bottom: 4px;
}

/* Head */
.head {
  text-align: center;
  margin-bottom: 64px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.success-icon {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: var(--color-fresh-tint);
  border: 1px solid var(--color-fresh);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}
.success-icon :deep(svg) {
  width: 32px; height: 32px;
  stroke: var(--color-fresh);
  stroke-width: 2;
  fill: none;
}
.eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-fresh);
}
.title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 44px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 12px 0 12px;
}
.lede {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 15px;
  line-height: 1.95;
  color: var(--color-ink-default);
  margin: 0;
  letter-spacing: 0.04em;
}
.lede strong {
  color: var(--color-ink-strong);
  font-weight: 500;
  font-family: var(--font-mono);
  font-size: 14px;
  margin: 0 4px;
}

/* Payment */
.payment {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  margin-bottom: 56px;
  background: var(--color-paper-deep);
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.payment .left,
.payment .right {
  padding: 36px 40px 40px;
}
.payment .left {
  border-right: 1px solid var(--color-line-subtle);
  background: var(--color-paper-surface);
}

.block-eyebrow {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.block-no {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--color-fresh);
  font-weight: 500;
}
.block-cap {
  font-family: var(--font-display);
  font-style: italic;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--color-accent);
}

.block-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 22px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0 0 24px;
}

/* Countdown */
.countdown {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 16px 18px;
  background: var(--color-paper-canvas);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xs);
  margin-bottom: 16px;
}
.countdown.expired {
  border-color: var(--color-state-danger);
  opacity: 0.6;
}
.cd-cell {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  min-width: 56px;
}
.cd-num {
  font-family: var(--font-mono);
  font-size: 36px;
  font-weight: 500;
  color: var(--color-ink-strong);
  line-height: 1;
  letter-spacing: 0;
}
.cd-label {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-top: 6px;
}
.cd-sep {
  font-family: var(--font-mono);
  font-size: 28px;
  color: var(--color-ink-muted);
  align-self: flex-start;
  margin-top: 4px;
}

.cd-meta {
  font-size: 14px;
  color: var(--color-ink-muted);
  margin: 0 0 16px;
}

.hint {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 13px;
  line-height: 1.85;
  color: var(--color-ink-default);
  letter-spacing: 0.04em;
  margin: 0;
  max-width: 380px;
}
.hint-expired { color: var(--color-state-danger); }

/* Bank info */
.bank {
  margin: 0 0 18px;
}
.bank-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-line-subtle);
}
.bank-row:last-child { border-bottom: none; }
.bank-row dt {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin: 0;
  flex-shrink: 0;
}
.bank-row dd {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 14px;
  color: var(--color-ink-strong);
  letter-spacing: 0.04em;
  margin: 0;
  text-align: right;
}
.bank-row-account dd {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.acc {
  font-family: var(--font-mono);
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
}
.copy {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xs);
  padding: 4px 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-accent);
  cursor: pointer;
  transition: border-color 150ms, color 150ms;
}
.copy:hover {
  border-color: var(--color-accent);
}
.copy :deep(svg) {
  stroke: currentColor; stroke-width: 1.5; fill: none;
}

.amt {
  font-family: var(--font-mono);
  font-size: 18px !important;
  font-weight: 500;
  color: var(--color-accent-wine) !important;
}

.bank-note {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 12px;
  line-height: 1.85;
  color: var(--color-ink-muted);
  margin: 12px 0 0;
  letter-spacing: 0.04em;
}

/* Next steps */
.next {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.next-card {
  display: grid;
  grid-template-columns: 32px 1fr auto;
  gap: 18px;
  align-items: center;
  padding: 24px 28px;
  background: var(--color-paper-surface);
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-sm);
}
.next-no {
  font-family: var(--font-display);
  font-weight: 300;
  font-size: 32px;
  line-height: 1;
  color: var(--color-accent);
  text-align: center;
}
.next-body { min-width: 0; }
.next-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 16px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0 0 4px;
}
.next-desc {
  font-size: 12px;
  line-height: 1.7;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
  margin: 0;
}
.next-cta {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  padding: 10px 16px;
  border: 1px solid var(--color-ink-strong);
  background: var(--color-ink-strong);
  color: var(--color-paper-canvas);
  text-decoration: none;
  white-space: nowrap;
  transition: all 200ms;
}
.next-cta:hover {
  background: var(--color-accent-deep);
  border-color: var(--color-accent-deep);
}
.next-cta-ghost {
  background: transparent;
  color: var(--color-ink-strong);
}
.next-cta-ghost:hover {
  background: var(--color-ink-strong);
  color: var(--color-paper-canvas);
}

@media (max-width: 1023px) {
  .page { padding: 40px 32px 64px; }
  .payment { grid-template-columns: 1fr; }
  .payment .left { border-right: none; border-bottom: 1px solid var(--color-line-subtle); }
  .next { grid-template-columns: 1fr; }
}
@media (max-width: 767px) {
  .page { padding: 32px 24px 48px; }
  .payment .left,
  .payment .right { padding: 28px 24px 32px; }
  .cd-cell { min-width: 48px; }
  .cd-num { font-size: 30px; }
  .next-card { grid-template-columns: 1fr; gap: 12px; padding: 20px 22px; }
  .next-cta { justify-self: flex-start; }
}
</style>
