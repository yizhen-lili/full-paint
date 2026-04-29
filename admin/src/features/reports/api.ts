/**
 * Reports API — F11 銷售報表（admin）。
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
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw {
      message: body.message || body.detail || `HTTP ${res.status}`,
      status: res.status,
    } as ApiError
  }
  return body
}

export interface SalesReport {
  period: string
  total_orders: number
  total_revenue: number
  note: string | null
}

export function getSalesReport(params: { date_from?: string; date_to?: string } = {}) {
  const q = new URLSearchParams()
  if (params.date_from) q.set('date_from', params.date_from)
  if (params.date_to) q.set('date_to', params.date_to)
  const qs = q.toString()
  return request<SalesReport>(`/admin/reports/sales${qs ? '?' + qs : ''}`)
}
