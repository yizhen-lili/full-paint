/**
 * Notifications API — F09 通知中心（admin）。
 */

const API = '/api/v1'

interface ApiError {
  message: string
  status: number
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
    ...init,
  })
  if (res.status === 204) return null as unknown as T
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw {
      message: body.message || body.detail || `HTTP ${res.status}`,
      status: res.status,
    } as ApiError
  }
  return body
}

// ── Types ─────────────────────────────────────────────────────────────

export type NotificationStatus = 'unhandled' | 'in_progress' | 'completed'

export interface AdminNotification {
  id: string
  type: string
  message: string
  requires_action: boolean
  status: NotificationStatus
  reference_type: string | null
  reference_id: string | null
  created_at: string
  updated_at: string
}

export interface NotificationsListResponse {
  items: AdminNotification[]
  total: number
  page: number
  page_size: number
}

export interface NotificationsParams {
  status?: NotificationStatus | ''
  requires_action?: boolean | ''
  page?: number
  page_size?: number
}

// ── Endpoints ─────────────────────────────────────────────────────────

export function listNotifications(params: NotificationsParams = {}) {
  const q = new URLSearchParams()
  if (params.status) q.set('status', params.status)
  if (params.requires_action !== undefined && params.requires_action !== '') {
    q.set('requires_action', String(params.requires_action))
  }
  q.set('page', String(params.page ?? 1))
  q.set('page_size', String(params.page_size ?? 20))
  return request<NotificationsListResponse>(`/admin/notifications?${q.toString()}`)
}

export function updateNotificationStatus(id: string, status: NotificationStatus) {
  return request<AdminNotification>(`/admin/notifications/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

export function bulkCompleteNotifications(ids: string[]) {
  return request<{ updated_count: number }>('/admin/notifications/bulk-complete', {
    method: 'PATCH',
    body: JSON.stringify({ ids }),
  })
}

// ── Labels ────────────────────────────────────────────────────────────

export const STATUS_LABEL: Record<NotificationStatus, { label: string; cls: string }> = {
  unhandled: { label: '未處理', cls: 'bg-[var(--color-state-warning)]/[0.12] text-state-warning' },
  in_progress: { label: '處理中', cls: 'bg-[var(--color-state-info)]/[0.12] text-state-info' },
  completed: { label: '已完成', cls: 'bg-paper-subtle text-ink-muted' },
}

// 已知 type 的中文 label（未列出的會原樣顯示）
export const TYPE_LABEL: Record<string, string> = {
  quote_pending: '客製申請待回覆',
  payment_submitted: '客戶填了付款資訊',
  payment_resubmitted: '客戶重填付款資訊',
  custom_order_paid: '客製訂單已付款',
  new_message: '客製對話新訊息',
  draft_revision_requested: '客戶要求修改初稿',
  quote_confirmed: '客戶確認報價',
  quote_rejected: '客戶拒絕報價',
  order_cancelled: '訂單被取消',
  order_completed_by_customer: '客戶確認收貨',
  shipment_overdue: '出貨後 5 天無回應',
  ecpay_status: 'ECpay 物流狀態變化',
  batch_completed: '批次處理完畢',
  production_failed: '製作任務失敗',
  stock_shortage: '顏料庫存不足',
}

export function buildNotificationLink(n: AdminNotification): string | null {
  const t = n.reference_type
  const id = n.reference_id
  if (!t || !id) return null
  if (t === 'order') return `/admin/orders/${id}`
  if (t === 'custom_request') return `/admin/custom-requests/${id}`
  if (t === 'production_job') return `/admin/production/${id}`
  if (t === 'batch') return `/admin/print-batches/${id}`
  return null
}
