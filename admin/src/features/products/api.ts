/**
 * Products API wrappers — all endpoints for F03 (products / variants / images / series / tags).
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

export type ProductStatus = 'draft' | 'on_sale' | 'off_sale'

export interface ProductListItem {
  id: string
  title: string
  cover_image_url: string
  status: ProductStatus
  series_id: string | null
  series_name: string | null
  variant_count: number
  updated_at: string
}

export interface ProductsListResponse {
  items: ProductListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductsListParams {
  search?: string
  status?: ProductStatus | ''
  page?: number
  page_size?: number
}

export interface ProductDetail {
  id: string
  title: string
  description: string
  cover_image_url: string
  series_id: string | null
  series_order: number
  status: ProductStatus
  tag_ids: string[]
  created_at: string
  updated_at: string
}

export interface ProductPayload {
  title: string
  description: string
  cover_image_url: string
  series_id: string | null
  series_order: number
  status: ProductStatus
  tag_ids: string[]
}

export interface Variant {
  id: string
  product_id: string
  production_job_id: string
  price: number
  price_formula_base: number
  is_active: boolean
  production_job_snapshot?: {
    canvas_w_cm: number
    canvas_h_cm: number
    detail: string
    difficulty: string
    mode: string
  }
  created_at: string
}

export interface ProductImage {
  id: string
  product_id: string
  image_url: string
  sort_order: number
}

export interface Series {
  id: string
  name: string
  description: string | null
  product_count?: number
}

export interface Tag {
  id: string
  name: string
}

export interface UploadSignedUrl {
  upload_url: string
  public_url: string
  expires_at: string
}

// ── Products ──────────────────────────────────────────────────────────

export function listProducts(params: ProductsListParams) {
  const q = new URLSearchParams()
  if (params.search) q.set('search', params.search)
  if (params.status) q.set('status', params.status)
  q.set('page', String(params.page ?? 1))
  q.set('page_size', String(params.page_size ?? 20))
  return request<ProductsListResponse>(`/admin/products?${q.toString()}`)
}

export function getProduct(id: string) {
  return request<ProductDetail>(`/admin/products/${id}`)
}

export function createProduct(payload: ProductPayload) {
  return request<ProductDetail>('/admin/products', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateProduct(id: string, payload: ProductPayload) {
  return request<ProductDetail>(`/admin/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteProduct(id: string) {
  return request<void>(`/admin/products/${id}`, { method: 'DELETE' })
}

// ── Variants ──────────────────────────────────────────────────────────

export async function listVariants(productId: string): Promise<Variant[]> {
  const res = await request<Variant[] | { items: Variant[] }>(`/admin/products/${productId}/variants`)
  return Array.isArray(res) ? res : res.items
}

export function addVariant(productId: string, payload: { production_job_id: string; price: number }) {
  return request<Variant>(`/admin/products/${productId}/variants`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateVariant(
  productId: string,
  variantId: string,
  payload: { price?: number; is_active?: boolean },
) {
  return request<Variant>(`/admin/products/${productId}/variants/${variantId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteVariant(productId: string, variantId: string) {
  return request<void>(`/admin/products/${productId}/variants/${variantId}`, {
    method: 'DELETE',
  })
}

// ── Images ────────────────────────────────────────────────────────────

export async function listImages(productId: string): Promise<ProductImage[]> {
  const res = await request<ProductImage[] | { items: ProductImage[] }>(`/admin/products/${productId}/images`)
  return Array.isArray(res) ? res : res.items
}

export function addImage(productId: string, payload: { image_url: string; sort_order: number }) {
  return request<ProductImage>(`/admin/products/${productId}/images`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteImage(productId: string, imageId: string) {
  return request<void>(`/admin/products/${productId}/images/${imageId}`, {
    method: 'DELETE',
  })
}

export function reorderImages(productId: string, order: string[]) {
  return request<void>(`/admin/products/${productId}/images/reorder`, {
    method: 'PATCH',
    body: JSON.stringify({ order }),
  })
}

// ── Series ────────────────────────────────────────────────────────────

export async function listSeries(): Promise<Series[]> {
  const res = await request<Series[] | { items: Series[] }>('/admin/series')
  return Array.isArray(res) ? res : res.items
}

export function createSeries(payload: { name: string; description: string | null }) {
  return request<Series>('/admin/series', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSeries(id: string, payload: { name: string; description: string | null }) {
  return request<Series>(`/admin/series/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteSeries(id: string) {
  return request<void>(`/admin/series/${id}`, { method: 'DELETE' })
}

// ── Tags ──────────────────────────────────────────────────────────────

export async function listTags(): Promise<Tag[]> {
  const res = await request<Tag[] | { items: Tag[] }>('/admin/tags')
  return Array.isArray(res) ? res : res.items
}

export function createTag(payload: { name: string }) {
  return request<Tag>('/admin/tags', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateTag(id: string, payload: { name: string }) {
  return request<Tag>(`/admin/tags/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteTag(id: string) {
  return request<void>(`/admin/tags/${id}`, { method: 'DELETE' })
}

// ── Upload (signed URL) ───────────────────────────────────────────────

export function getUploadUrl(payload: {
  filename: string
  content_type: 'image/jpeg' | 'image/png'
  size: number
}) {
  return request<UploadSignedUrl>('/upload/product-image', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function uploadFile(file: File): Promise<string> {
  const contentType = file.type === 'image/png' ? 'image/png' : 'image/jpeg'
  const signed = await getUploadUrl({
    filename: file.name,
    content_type: contentType,
    size: file.size,
  })

  // Direct PUT to Firebase signed URL
  const putRes = await fetch(signed.upload_url, {
    method: 'PUT',
    headers: { 'Content-Type': contentType },
    body: file,
  })
  if (!putRes.ok && !signed.upload_url.startsWith('https://stub.firebase')) {
    throw new Error(`上傳失敗 HTTP ${putRes.status}`)
  }
  return signed.public_url
}
