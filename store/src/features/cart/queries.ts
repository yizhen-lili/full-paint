import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import * as cartApi from './api'
import type { CheckoutPreviewRequest, ShippingType } from './api'
import { useAuthStore } from '@/features/auth/store'

const STALE_30S = 30 * 1000

export const cartQueryKey = ['cart'] as const

/** GET /cart — 只在登入後才打 */
export function useCartQuery() {
  const auth = useAuthStore()
  return useQuery({
    queryKey: cartQueryKey,
    queryFn: cartApi.getCart,
    staleTime: STALE_30S,
    enabled: computed(() => auth.isLoggedIn),
  })
}

export function useAddCartItemMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ variantId, quantity }: { variantId: string; quantity: number }) =>
      cartApi.addCartItem(variantId, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cartQueryKey })
    },
  })
}

export function useUpdateCartItemMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId, quantity }: { itemId: string; quantity: number }) =>
      cartApi.updateCartItem(itemId, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cartQueryKey })
    },
  })
}

export function useDeleteCartItemMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => cartApi.deleteCartItem(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cartQueryKey })
    },
  })
}

/** Reactive checkout-preview — 隨運送類型 / 折扣碼變動自動 refetch */
export function useCheckoutPreviewQuery(
  body: MaybeRefOrGetter<CheckoutPreviewRequest>,
  options?: { enabled?: MaybeRefOrGetter<boolean> },
) {
  return useQuery({
    queryKey: computed(() => ['checkout-preview', toValue(body)] as const),
    queryFn: () => cartApi.checkoutPreview(toValue(body)),
    staleTime: 0,
    enabled: computed(() => options?.enabled ? toValue(options.enabled) : true),
  })
}

export function useCreateOrderMutation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: cartApi.createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cartQueryKey })
      queryClient.invalidateQueries({ queryKey: ['orders'] })
    },
  })
}

/** 用 useCartQuery 派生：購物車件數（用於 Header 角標） */
export function useCartItemCount(): import('vue').ComputedRef<number> {
  const cart = useCartQuery()
  return computed(() =>
    (cart.data.value?.items ?? []).reduce((sum, i) => sum + i.quantity, 0),
  )
}

// 雜項：把 ShippingType 轉成中文標籤
export const SHIPPING_LABEL: Record<ShippingType, string> = {
  home: '宅配到府',
  convenience: '超商取貨',
}
