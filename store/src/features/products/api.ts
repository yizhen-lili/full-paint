// Products public API
// Source: backend/product/router.py:53-105

const API_BASE = '/api/v1'

// ── Types ────────────────────────────────────────────────────────────────────

export type Difficulty = 'beginner' | 'elementary' | 'intermediate' | 'advanced'
export type Detail = 'rough' | 'standard' | 'detailed' | 'premium'
export type SortMode = 'latest' | 'popular' | 'price_asc' | 'price_desc'

export interface ProductBrief {
  id: string
  title: string
  cover_image_url: string
  difficulty_range: [Difficulty, Difficulty] | null
  price_min: number
  price_max: number
  is_preorder: boolean
  is_featured?: boolean
}

export interface ProductListResponse {
  items: ProductBrief[]
  total: number
  page: number
  page_size: number
}

export interface ProductsListParams {
  difficulty?: Difficulty
  detail?: Detail
  canvas_size?: string
  tag_id?: string
  series_id?: string
  theme_id?: string
  featured?: boolean
  sort?: SortMode
  page?: number
  page_size?: number
}

export interface ProductImage {
  id: string
  image_url: string
  sort_order: number
  created_at: string
}

export interface ProductTagBrief {
  id: string
  name: string
}

export interface ProductVariant {
  id: string
  canvas_w_cm: number
  canvas_h_cm: number
  difficulty: Difficulty
  detail: Detail
  color_count: number | null
  price: number
  is_active: boolean
  is_preorder: boolean
  filled_template_url: string | null
}

export interface ProductSeriesProductBrief {
  id: string
  title: string
  cover_image_url: string
  price_min: number
  is_preorder: boolean
}

export interface ProductSeriesWithProducts {
  id: string
  name: string
  products: ProductSeriesProductBrief[]
}

export interface ProductDetail {
  id: string
  title: string
  description: string | null
  cover_image_url: string
  is_featured?: boolean
  images: { items: ProductImage[] } | ProductImage[]
  series: ProductSeriesWithProducts | null
  tags: ProductTagBrief[]
  variants: ProductVariant[]
}

export interface RelatedProductsResponse {
  series: { id: string; name: string } | null
  items: ProductSeriesProductBrief[]
}

// ── Endpoints ────────────────────────────────────────────────────────────────

/** GET /products — 商品列表（含 filter / sort / pagination）*/
export async function listProducts(params: ProductsListParams = {}): Promise<ProductListResponse> {
  const q = new URLSearchParams()
  if (params.difficulty) q.set('difficulty', params.difficulty)
  if (params.detail) q.set('detail', params.detail)
  if (params.canvas_size) q.set('canvas_size', params.canvas_size)
  if (params.tag_id) q.set('tag_id', params.tag_id)
  if (params.series_id) q.set('series_id', params.series_id)
  if (params.theme_id) q.set('theme_id', params.theme_id)
  if (params.featured !== undefined) q.set('featured', String(params.featured))
  if (params.sort) q.set('sort', params.sort)
  q.set('page', String(params.page ?? 1))
  q.set('page_size', String(params.page_size ?? 24))

  const res = await fetch(`${API_BASE}/products?${q.toString()}`, { credentials: 'include' })
  if (!res.ok) throw new Error(`listProducts failed: ${res.status}`)
  return (await res.json()) as ProductListResponse
}

/** GET /products/search — 全文搜尋 */
export async function searchProducts(
  q: string,
  page = 1,
  page_size = 24,
): Promise<ProductListResponse> {
  const params = new URLSearchParams({ q, page: String(page), page_size: String(page_size) })
  const res = await fetch(`${API_BASE}/products/search?${params.toString()}`, {
    credentials: 'include',
  })
  if (!res.ok) throw new Error(`searchProducts failed: ${res.status}`)
  return (await res.json()) as ProductListResponse
}

/** GET /products/:id — 詳情 */
export async function getProduct(id: string): Promise<ProductDetail> {
  const res = await fetch(`${API_BASE}/products/${id}`, { credentials: 'include' })
  if (!res.ok) throw new Error(`getProduct failed: ${res.status}`)
  return (await res.json()) as ProductDetail
}

/** GET /products/:id/related — 同系列推薦 */
export async function getRelatedProducts(id: string): Promise<RelatedProductsResponse> {
  const res = await fetch(`${API_BASE}/products/${id}/related`, { credentials: 'include' })
  if (!res.ok) throw new Error(`getRelatedProducts failed: ${res.status}`)
  return (await res.json()) as RelatedProductsResponse
}
