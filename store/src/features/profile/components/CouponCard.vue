<script setup lang="ts">
import { computed } from 'vue'
import { Truck, Tag, Gift, Users } from 'lucide-vue-next'
import type { UserCoupon } from '../api'

const props = defineProps<{
  coupon: UserCoupon
  /** 'available' | 'used' | 'expired'：影響灰調 + chip 文字 */
  state: 'available' | 'used' | 'expired'
}>()

const COUPON_TYPE_LABEL: Record<string, string> = {
  new_user: '新用戶歡迎',
  promo: '推廣碼',
  shipping: '運費優惠',
  reward: '回購禮',
}

const COUPON_TYPE_ICON: Record<string, typeof Truck> = {
  new_user: Users,
  promo: Tag,
  shipping: Truck,
  reward: Gift,
}

const stateLabel = computed(() => ({
  available: '可使用',
  used: '已使用',
  expired: '已過期',
}[props.state]))

const discountText = computed(() => {
  const c = props.coupon
  if (c.discount_type === 'free_shipping') return '免運'
  if (c.discount_type === 'percentage') {
    return `${Math.round((1 - c.discount_value) * 100)}% OFF`
  }
  return `NT$ ${c.discount_value.toLocaleString()} OFF`
})

const expiresAtText = computed(() => {
  const c = props.coupon
  if (!c.expires_at) return '無使用期限'
  const d = new Date(c.expires_at)
  const fmt = d.toLocaleDateString('zh-TW', {
    year: 'numeric', month: 'long', day: 'numeric',
  })
  return `${fmt} 到期`
})

const daysLeft = computed(() => {
  const c = props.coupon
  if (!c.expires_at) return null
  const ms = new Date(c.expires_at).getTime() - Date.now()
  if (ms <= 0) return 0
  return Math.ceil(ms / 86400000)
})
const isExpiringSoon = computed(() =>
  props.state === 'available' && daysLeft.value !== null && daysLeft.value <= 3,
)
</script>

<template>
  <article class="card" :class="`is-${state}`">
    <div class="card-head">
      <component :is="COUPON_TYPE_ICON[coupon.coupon_type ?? 'promo']" :size="14" :stroke-width="1.5" class="type-icon" />
      <span class="type-label">{{ COUPON_TYPE_LABEL[coupon.coupon_type ?? 'promo'] || '優惠券' }}</span>
      <span class="state-chip">{{ stateLabel }}</span>
    </div>

    <p class="discount">{{ discountText }}</p>

    <p v-if="coupon.min_purchase" class="min-purchase">
      滿 NT$ {{ coupon.min_purchase.toLocaleString() }} 可用
    </p>
    <p v-else class="min-purchase no-min">不限金額</p>

    <p class="expires" :class="{ 'is-soon': isExpiringSoon }">
      {{ expiresAtText }}
      <span v-if="isExpiringSoon" class="days-left">（剩 {{ daysLeft }} 天）</span>
    </p>
  </article>
</template>

<style scoped>
.card {
  position: relative;
  background: var(--color-paper-surface);
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-sm);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: filter 200ms, border-color 200ms;
}

.card-head {
  display: flex; align-items: center; gap: 8px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--color-line-subtle);
}
.type-icon { color: var(--color-accent-deep); }
.type-label {
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.22em;
  text-transform: uppercase; color: var(--color-ink-muted);
}
.state-chip {
  margin-left: auto;
  padding: 1px 8px; height: 20px;
  display: inline-flex; align-items: center;
  font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.18em;
  text-transform: uppercase;
  border-radius: var(--radius-xs);
  border: 1px solid var(--color-fresh-soft);
  color: var(--color-fresh);
  background: var(--color-fresh-tint);
}

.is-used .state-chip {
  color: var(--color-ink-muted);
  border-color: var(--color-line);
  background: var(--color-paper-deep);
}
.is-expired .state-chip {
  color: var(--color-state-danger);
  border-color: var(--color-state-danger);
  background: var(--color-paper-canvas);
  opacity: 0.7;
}

.discount {
  margin: 8px 0 4px;
  font-family: var(--font-mono);
  font-size: 28px;
  letter-spacing: 0.04em;
  color: var(--color-ink-strong);
  font-weight: 500;
}

.min-purchase {
  margin: 0;
  font-size: 12px;
  color: var(--color-ink-default);
  letter-spacing: 0.04em;
}
.min-purchase.no-min { color: var(--color-ink-muted); font-style: italic; }

.expires {
  margin: 8px 0 0;
  padding-top: 12px;
  border-top: 1px solid var(--color-line-subtle);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.16em;
  color: var(--color-ink-muted);
}
.expires.is-soon { color: var(--color-state-warning); }
.days-left { font-weight: 500; }

/* Used / expired 視覺：sepia + saturate */
.is-used { filter: sepia(0.2) saturate(0.6); }
.is-expired { filter: sepia(0.3) saturate(0.4); opacity: 0.85; }
</style>
