/**
 * Admin Users API wrappers — F13 用戶管理。
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

export type UserRole = 'admin' | 'customer'

export interface AdminUser {
  id: string
  name: string
  email: string
  role: UserRole
  is_active: boolean
  is_email_verified: boolean
  created_at: string
}

export interface UsersListResponse {
  items: AdminUser[]
  total: number
  page: number
  page_size: number
}

export interface UsersListParams {
  search?: string
  role?: UserRole | ''
  is_active?: boolean | ''
  is_email_verified?: boolean | ''
  page?: number
  page_size?: number
}

export interface UpdateUserPayload {
  name?: string | null
  role?: UserRole | null
  is_active?: boolean | null
  password?: string | null
}

// ── Endpoints ─────────────────────────────────────────────────────────

export function listUsers(params: UsersListParams = {}) {
  const q = new URLSearchParams()
  if (params.search) q.set('search', params.search)
  if (params.role) q.set('role', params.role)
  if (params.is_active !== undefined && params.is_active !== '') {
    q.set('is_active', String(params.is_active))
  }
  if (params.is_email_verified !== undefined && params.is_email_verified !== '') {
    q.set('is_email_verified', String(params.is_email_verified))
  }
  q.set('page', String(params.page ?? 1))
  q.set('page_size', String(params.page_size ?? 20))
  return request<UsersListResponse>(`/admin/users?${q.toString()}`)
}

export function getUser(id: string) {
  return request<AdminUser>(`/admin/users/${id}`)
}

export function updateUser(id: string, payload: UpdateUserPayload) {
  return request<AdminUser>(`/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

/** Admin 替未驗證 user 重寄驗證信。 */
export function resendVerification(id: string) {
  return request<void>(`/admin/users/${id}/resend-verification`, { method: 'POST' })
}

/** Admin 強制標記 email 已驗證（跳過 email 流程）。 */
export function forceVerifyEmail(id: string) {
  return request<AdminUser>(`/admin/users/${id}/force-verify-email`, { method: 'POST' })
}
