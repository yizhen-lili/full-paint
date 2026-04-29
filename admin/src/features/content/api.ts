/**
 * Content API wrappers — F10 內容管理。
 * 涵蓋 6 個子模組：static_pages / system_settings / photo_prices / photo_surcharges / custom_cases / case_categories
 *
 * 注意：canvas_sizes endpoint 後端尚未實作（F06-A 留 backlog 中），
 * 前端 CANVAS_SIZES hardcode 17 種尺寸沿用。
 */

const API = '/api/v1'

interface ApiError {
  message: string
  code?: string
  status: number
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
    ...init,
  })

  if (res.status === 204) return null as unknown as T

  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err: ApiError = {
      message: body.message || body.detail || `HTTP ${res.status}`,
      code: body.code,
      status: res.status,
    }
    throw err
  }
  return body
}

// ── Types ─────────────────────────────────────────────────────────────

export type Difficulty = 'beginner' | 'elementary' | 'intermediate' | 'advanced'

export interface StaticPage {
  id: string
  slug: string
  title: string
  content: string
  updated_at: string
}

export interface SystemSetting {
  key: string
  value: string
  updated_at: string
}

export interface CustomPhotoPrice {
  id: string
  canvas_w: number
  canvas_h: number
  difficulty: Difficulty
  price: number
}

export interface CustomPhotoSurcharge {
  id: string
  category: string
  label: string
  amount: number
  is_active: boolean
  created_at: string
}

export interface CaseCategory {
  id: string
  name: string
  created_at: string
}

export interface CustomCase {
  id: string
  image_url: string
  title: string
  description: string | null
  category_id: string | null
  canvas_w_cm: number | null
  canvas_h_cm: number | null
  difficulty: Difficulty | null
  is_published: boolean
  created_at: string
}

// ── Endpoints ─────────────────────────────────────────────────────────

// static_pages
export function listPages() {
  return request<{ items: StaticPage[] }>('/admin/pages')
}
export function upsertPage(slug: string, payload: { title: string; content: string }) {
  return request<StaticPage>(`/admin/pages/${slug}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

// system_settings
export function listSettings() {
  return request<{ items: SystemSetting[] }>('/admin/system-settings')
}
export function upsertSetting(payload: { key: string; value: string }) {
  return request<SystemSetting>('/admin/system-settings', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

// photo_prices
export function listPhotoPrices() {
  return request<{ items: CustomPhotoPrice[] }>('/admin/custom-photo-prices')
}
export function updatePhotoPrice(id: string, price: number) {
  return request<CustomPhotoPrice>(`/admin/custom-photo-prices/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ price }),
  })
}

// photo_surcharges
export function listSurcharges() {
  return request<{ items: CustomPhotoSurcharge[] }>('/admin/custom-photo-surcharges')
}
export function createSurcharge(payload: {
  category: string
  label: string
  amount: number
  is_active: boolean
}) {
  return request<CustomPhotoSurcharge>('/admin/custom-photo-surcharges', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
export function updateSurcharge(
  id: string,
  payload: { category: string; label: string; amount: number; is_active: boolean },
) {
  return request<CustomPhotoSurcharge>(`/admin/custom-photo-surcharges/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
export function toggleSurchargeActive(id: string) {
  return request<CustomPhotoSurcharge>(`/admin/custom-photo-surcharges/${id}/toggle-active`, {
    method: 'PATCH',
  })
}
export function deleteSurcharge(id: string) {
  return request<void>(`/admin/custom-photo-surcharges/${id}`, { method: 'DELETE' })
}

// case_categories
export function listCaseCategories() {
  return request<{ items: CaseCategory[] }>('/admin/case-categories')
}
export function createCaseCategory(name: string) {
  return request<CaseCategory>('/admin/case-categories', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}
export function updateCaseCategory(id: string, name: string) {
  return request<CaseCategory>(`/admin/case-categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ name }),
  })
}
export function deleteCaseCategory(id: string) {
  return request<void>(`/admin/case-categories/${id}`, { method: 'DELETE' })
}

// custom_cases
export function listCustomCases(params: { page?: number; page_size?: number } = {}) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('page_size', String(params.page_size ?? 50))
  return request<{ items: CustomCase[]; total: number; page: number; page_size: number }>(
    `/admin/custom-cases?${q.toString()}`,
  )
}
export function createCustomCase(payload: Omit<CustomCase, 'id' | 'created_at'>) {
  return request<CustomCase>('/admin/custom-cases', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
export function updateCustomCase(id: string, payload: Omit<CustomCase, 'id' | 'created_at'>) {
  return request<CustomCase>(`/admin/custom-cases/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
export function toggleCustomCasePublish(id: string) {
  return request<CustomCase>(`/admin/custom-cases/${id}/toggle-publish`, { method: 'PATCH' })
}
export function deleteCustomCase(id: string) {
  return request<void>(`/admin/custom-cases/${id}`, { method: 'DELETE' })
}

// ── Labels ────────────────────────────────────────────────────────────

export const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  beginner: '入門',
  elementary: '初級',
  intermediate: '中級',
  advanced: '進階',
}

export const SETTING_LABEL: Record<string, { label: string; type: 'text' | 'textarea' | 'number' }> = {
  bank_account_number: { label: '銀行帳號', type: 'text' },
  bank_name: { label: '銀行名稱', type: 'text' },
  bank_account_name: { label: '匯款戶名', type: 'text' },
  quote_reply_days: { label: '客製預計回覆天數', type: 'number' },
  product_info_tools: { label: '畫具內容物說明', type: 'textarea' },
  product_info_material: { label: '畫布材質說明', type: 'textarea' },
  product_info_tips: { label: '使用建議', type: 'textarea' },
  product_info_notes: { label: '注意事項', type: 'textarea' },
  paint_ml_per_cm2: { label: '顏料塗佈係數（ml/cm²）', type: 'number' },
  paint_min_ml: { label: '顏料最低配給量（ml）', type: 'number' },
  paint_buffer_ratio: { label: '顏料緩衝係數', type: 'number' },
  custom_photo_price_multiplier: { label: '客製服務費率倍數', type: 'number' },
  payment_absolute_deadline_hours: { label: '付款絕對期限（小時）', type: 'number' },
}

export const PAGE_LABEL: Record<string, string> = {
  size_guide: '尺寸指南',
  shipping: '出貨流程',
  custom_process: '訂製流程',
  pricing_reference: '報價參考',
  refund_policy: '退款退貨政策',
}
