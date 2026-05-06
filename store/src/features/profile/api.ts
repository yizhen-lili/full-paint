// User profile + shipping profile API
// Source: backend/users/router.py

const API_BASE = '/api/v1'

export interface ShippingProfile {
  id: string
  shipping_type: 'home' | 'convenience'
  recipient_name: string
  phone: string
  email: string | null
  city: string | null
  district: string | null
  address_detail: string | null
  store_id: string | null
  store_name: string | null
  is_default: boolean
}

export interface ApiError extends Error {
  status: number
  detail: string
}

async function jsonRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  })
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b) => b?.detail ?? b?.message ?? `${res.status}`)
      .catch(() => `${res.status}`)
    const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)) as ApiError
    err.status = res.status
    err.detail = typeof detail === 'string' ? detail : JSON.stringify(detail)
    throw err
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export async function listShippingProfiles(): Promise<ShippingProfile[]> {
  return jsonRequest<ShippingProfile[]>('/users/me/shipping-profiles')
}

export async function createShippingProfile(data: Partial<ShippingProfile>): Promise<ShippingProfile> {
  return jsonRequest<ShippingProfile>('/users/me/shipping-profiles', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
