/**
 * Paint Requirements API — F22 顏料準備清單查詢（admin）。
 *
 * 取得任意 production_job × N 件需要的物理顏料用量清單，
 * 支援三類來源：商品 variant / 客製訂單 / 試驗任務（standalone job）。
 */

const API = '/api/v1'

export interface ApiError {
  message: string
  code?: string
  status: number
  /** 未 finalize 時 backend 帶回 production_job_id 給前端跳轉 mapping 頁 */
  production_job_id?: string
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
      code: body.code,
      status: res.status,
      production_job_id: body.production_job_id,
    } as ApiError
  }
  return body
}

// ── Result schemas ───────────────────────────────────────────────────────

export interface PaintRequirementItem {
  physical_color_id: string
  output_label: number | null
  code: string
  name: string
  hex: string
  required_per_unit_ml: number
  total_required_ml: number
  stock_ml: number
  shortage_ml: number
  is_short: boolean
}

export interface PaintRequirementsSummary {
  total_colors: number
  short_count: number
  total_required_ml: number
}

export interface PaintRequirementsResponse {
  production_job_id: string
  quantity: number
  canvas_w_cm: number
  canvas_h_cm: number
  items: PaintRequirementItem[]
  summary: PaintRequirementsSummary
}

// ── Sources schemas（picker）────────────────────────────────────────────

export interface SourceVariantInfo {
  variant_id: string
  production_job_id: string
  canvas_w_cm: number
  canvas_h_cm: number
  price: number
  is_finalized: boolean
}

export interface SourceProductGroup {
  id: string
  title: string
  status: 'draft' | 'on_sale' | 'off_sale'
  variants: SourceVariantInfo[]
}

export interface SourceCustomRequest {
  custom_request_id: string
  production_job_id: string
  label: string
  status: string
  canvas_w_cm: number
  canvas_h_cm: number
  is_finalized: boolean
}

export interface SourceStandaloneJob {
  production_job_id: string
  label: string
  canvas_w_cm: number
  canvas_h_cm: number
  detail: string
  difficulty: string
  created_at: string
  is_finalized: boolean
}

export interface PaintRequirementSourcesResponse {
  products: SourceProductGroup[]
  custom_requests: SourceCustomRequest[]
  standalone_jobs: SourceStandaloneJob[]
}

// ── Endpoints ─────────────────────────────────────────────────────────

export function getPaintRequirements(productionJobId: string, quantity: number) {
  const q = new URLSearchParams()
  q.set('production_job_id', productionJobId)
  q.set('quantity', String(quantity))
  return request<PaintRequirementsResponse>(`/admin/paint-requirements?${q.toString()}`)
}

export function getPaintRequirementSources() {
  return request<PaintRequirementSourcesResponse>('/admin/paint-requirements/sources')
}
