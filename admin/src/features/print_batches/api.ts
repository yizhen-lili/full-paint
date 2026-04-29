/**
 * Print Batches API — F12 列印批次（admin）。
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

export type PrintBatchStatus = 'draft' | 'finalized' | 'failed'

export interface PrintBatchSummary {
  id: string
  status: PrintBatchStatus
  total_inch_count: number
  total_cost: number
  pdf_url: string | null
  item_count: number
  created_at: string
  finalized_at: string | null
}

export interface BatchItem {
  id: string
  source_type: 'order_item' | 'production_job'
  source_order_item_id: string | null
  production_job_id: string
  quantity: number
  inch_per_unit: number
  canvas_w_cm: number
  canvas_h_cm: number
}

export interface PrintBatchDetail {
  id: string
  status: PrintBatchStatus
  total_inch_count: number
  billable_inch_count: number
  print_cost: number
  cut_cost: number
  total_cost: number
  pdf_url: string | null
  admin_notes: string | null
  created_at: string
  finalized_at: string | null
  items: BatchItem[]
}

export interface CandidateInfo {
  production_job_id: string
  product_title: string
  canvas_w_cm: number
  canvas_h_cm: number
  inch_per_unit: number
}

export interface PreviewResponse {
  required_inch_count: number
  billable_inch_count: number
  waste_inch: number
  cost_breakdown: {
    print_cost: number
    cut_cost: number
    total_cost: number
  }
  suggestions: string[]
  available_candidates: CandidateInfo[]
}

export interface RequiredItem {
  production_job_id: string
  quantity: number
}

// ── Endpoints ─────────────────────────────────────────────────────────

export function listBatches(params: { page?: number; page_size?: number } = {}) {
  const q = new URLSearchParams()
  q.set('page', String(params.page ?? 1))
  q.set('page_size', String(params.page_size ?? 20))
  return request<{ items: PrintBatchSummary[]; total: number; page: number; page_size: number }>(
    `/admin/print-batches?${q.toString()}`,
  )
}

export function getCandidates() {
  return request<{ items: CandidateInfo[] }>('/admin/print-batches/candidates')
}

export function previewBatch(payload: { required: RequiredItem[]; candidates: RequiredItem[] }) {
  return request<PreviewResponse>('/admin/print-batches/preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createBatch(payload: {
  required: RequiredItem[]
  candidates: RequiredItem[]
  admin_notes?: string | null
}) {
  return request<PrintBatchDetail>('/admin/print-batches', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getBatch(id: string) {
  return request<PrintBatchDetail>(`/admin/print-batches/${id}`)
}

export function finalizeBatch(id: string) {
  return request<PrintBatchDetail>(`/admin/print-batches/${id}/finalize`, {
    method: 'POST',
  })
}

export const STATUS_LABEL: Record<PrintBatchStatus, { label: string; cls: string }> = {
  draft: { label: '草稿', cls: 'bg-paper-subtle text-ink-muted' },
  finalized: { label: '已完成', cls: 'bg-[var(--color-state-success)]/[0.10] text-state-success' },
  failed: { label: '失敗', cls: 'bg-[var(--color-state-danger)]/[0.10] text-state-danger' },
}
