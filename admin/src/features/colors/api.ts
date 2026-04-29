/**
 * Colors API — F07-A 實體色管理（admin）。
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

export interface PhysicalColor {
  id: string
  code: string
  name: string
  color_family: string | null
  brand: string | null
  rgb: [number, number, number]
  stock_ml: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RgbHistoryItem {
  id: string
  rgb: [number, number, number]
  changed_by_user_id: string | null
  changed_by_name: string | null
  note: string
  created_at: string
}

export interface ShortageItem {
  color_id: string
  code: string
  name: string
  stock_ml: number
  required_ml: number
  shortage_ml: number
  waiting_orders: number
}

export interface CreateColorPayload {
  code: string
  name: string
  color_family?: string | null
  brand?: string | null
  rgb: [number, number, number]
  stock_ml: number
}

export interface UpdateColorPayload {
  code?: string | null
  name?: string | null
  color_family?: string | null
  brand?: string | null
  stock_ml?: number | null
}

export interface ColorsListParams {
  color_family?: string
  is_active?: boolean | ''
  search?: string
}

// ── Endpoints ─────────────────────────────────────────────────────────

export function listColors(params: ColorsListParams = {}) {
  const q = new URLSearchParams()
  if (params.color_family) q.set('color_family', params.color_family)
  if (params.is_active !== undefined && params.is_active !== '') {
    q.set('is_active', String(params.is_active))
  }
  if (params.search) q.set('search', params.search)
  const qs = q.toString()
  return request<{ items: PhysicalColor[] }>(`/admin/colors${qs ? '?' + qs : ''}`)
}

export function createColor(payload: CreateColorPayload) {
  return request<PhysicalColor>('/admin/colors', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateColor(id: string, payload: UpdateColorPayload) {
  return request<PhysicalColor>(`/admin/colors/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function toggleColorActive(id: string) {
  return request<PhysicalColor>(`/admin/colors/${id}/toggle-active`, { method: 'PATCH' })
}

export function updateColorRgb(
  id: string,
  payload: { hex?: string; rgb?: [number, number, number] },
) {
  return request<PhysicalColor>(`/admin/colors/${id}/rgb`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function getRgbHistory(id: string) {
  return request<{ items: RgbHistoryItem[] }>(`/admin/colors/${id}/rgb-history`)
}

export function revertRgb(id: string, history_id: string) {
  return request<PhysicalColor>(`/admin/colors/${id}/rgb-revert`, {
    method: 'POST',
    body: JSON.stringify({ history_id }),
  })
}

export function updateColorStock(id: string, add_ml: number) {
  return request<{ new_stock_ml: number; fulfilled_orders: number }>(
    `/admin/colors/${id}/stock`,
    {
      method: 'PATCH',
      body: JSON.stringify({ add_ml }),
    },
  )
}

export function getShortageDashboard() {
  return request<{ items: ShortageItem[] }>('/admin/colors/shortage-dashboard')
}

// ── Helpers ───────────────────────────────────────────────────────────

export function rgbToHex(rgb: [number, number, number]): string {
  return (
    '#' +
    rgb
      .map((v) =>
        Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0'),
      )
      .join('')
      .toUpperCase()
  )
}

export function hexToRgb(hex: string): [number, number, number] | null {
  const m = hex.replace(/^#/, '').match(/^[0-9a-f]{6}$/i)
  if (!m) return null
  const n = parseInt(m[0], 16)
  return [(n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff]
}
