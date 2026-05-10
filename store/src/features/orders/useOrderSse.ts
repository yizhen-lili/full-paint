// SSE composable — 訂閱單一訂單的 status / shipment 事件
//
// 後端 endpoint: GET /api/v1/orders/{id}/sse
// 事件類型：
//   - status_changed：訂單狀態變動（paid / shipped / completed / cancelled / refunded）
//   - shipment_created：admin 建出貨（含 tracking）
//   - shipment_status_changed：ECpay webhook 狀態（在途 / 到店 / 已取貨）

import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'

export interface OrderSseHandlers {
  onStatusChanged?: (data: OrderStatusPayload) => void
  onShipmentCreated?: (data: ShipmentCreatedPayload) => void
  onShipmentStatusChanged?: (data: ShipmentStatusPayload) => void
  onError?: (e: Event) => void
}

export interface OrderStatusPayload {
  order_id: string
  status: string
  paid_at: string | null
  completed_at: string | null
  refunded_at: string | null
}

export interface ShipmentCreatedPayload {
  order_id: string
  status: string
  tracking_number: string
  shipment_id: string
}

export interface ShipmentStatusPayload {
  order_id: string
  shipment_id: string
  shipment_status: string
  rtn_code: string
  rtn_msg: string
}

export function useOrderSse(
  orderId: Ref<string | null | undefined> | (() => string | null | undefined),
  handlers: OrderSseHandlers = {},
) {
  const queryClient = useQueryClient()
  const connected = ref(false)
  let es: EventSource | null = null

  const close = () => {
    if (es) {
      es.close()
      es = null
    }
    connected.value = false
  }

  const open = (id: string) => {
    close()
    es = new EventSource(`/api/v1/orders/${encodeURIComponent(id)}/sse`)

    es.addEventListener('open', () => { connected.value = true })

    es.addEventListener('error', (e) => {
      connected.value = false
      handlers.onError?.(e)
      // EventSource 內建會自動重連（後端送了 retry: 5000）
    })

    const refreshOrder = () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] })
      queryClient.invalidateQueries({ queryKey: ['order-detail', id] })
    }

    es.addEventListener('status_changed', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as OrderStatusPayload
        handlers.onStatusChanged?.(data)
      } catch { /* ignore parse */ }
      refreshOrder()
    })

    es.addEventListener('shipment_created', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as ShipmentCreatedPayload
        handlers.onShipmentCreated?.(data)
      } catch { /* ignore */ }
      refreshOrder()
    })

    es.addEventListener('shipment_status_changed', (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as ShipmentStatusPayload
        handlers.onShipmentStatusChanged?.(data)
      } catch { /* ignore */ }
      refreshOrder()
    })
  }

  const source = typeof orderId === 'function' ? orderId : () => orderId.value
  watch(
    source,
    (id) => {
      if (id) open(id)
      else close()
    },
    { immediate: true },
  )

  onBeforeUnmount(close)

  return { connected }
}
