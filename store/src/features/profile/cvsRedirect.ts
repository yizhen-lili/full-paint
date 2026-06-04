// CVS Map 同分頁 redirect 流程的 helper —— 集中 3 個職責：
//   1. 出發前：把 form draft + edit context + returnTo 寫進 sessionStorage
//   2. 回來後：讀回 sessionStorage + 解析 URL 的 cvs_* params，傳給呼叫端後一次清掉
//   3. 組去 ECpay 的 URL（含 ?return=<path>）
//
// 改動原因：行動 Safari 在 cross-origin redirect 後會清掉 window.opener 並擋
// window.close()，所以舊的 popup + postMessage 機制壞掉。改成同分頁 redirect，
// 用 sessionStorage 暫存 user 已輸入的表單內容（同 origin 才存得回得來）。
import type { ShippingProfileInput, ShippingType } from './api'

const STORAGE_KEY = 'cvs-redirect-pending'
const TTL_MS = 30 * 60 * 1000 // 30 min

// shipping_type → ECpay LogisticsSubType (C2C 店到店)
const SUB_TYPE_MAP: Record<string, string> = {
  seven_eleven: 'UNIMARTC2C',
  family_mart: 'FAMIC2C',
}

export interface CvsEditContext {
  /** 'shipping-profiles' / 'checkout' / 'order-detail' — 給呼叫端決定要開哪個 form */
  page: 'shipping-profiles' | 'checkout' | 'order-detail'
  /** ShippingProfilesPage 用：'new' 或既有 profile uuid */
  editingId?: string | null
  /** OrderDetailPage 用：哪張訂單在改寄送 */
  orderId?: string | null
}

export interface CvsPendingPayload {
  formDraft: ShippingProfileInput
  editContext: CvsEditContext
  returnTo: string
  timestamp: number
}

export interface CvsResult {
  storeId: string
  storeName: string
  address: string
  phone: string
  subType: string
}

export interface CvsConsumed {
  formDraft: ShippingProfileInput
  editContext: CvsEditContext
  /** 成功才有；錯誤情境 cvs 為 null + error 有值 */
  cvs: CvsResult | null
  error: string | null
}

/**
 * 把當前 form draft 暫存到 sessionStorage，以便 redirect 回來時還原。
 * sessionStorage 不可用（隱私模式 / iOS 嚴格模式）會 swallow exception。
 */
export function saveCvsRedirect(payload: Omit<CvsPendingPayload, 'timestamp'>): void {
  try {
    const data: CvsPendingPayload = { ...payload, timestamp: Date.now() }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch {
    // sessionStorage 不可用 — fallback：return 後 form 為空，user 重填即可
  }
}

/**
 * 讀回 sessionStorage 並解析 URL 的 cvs_* / cvs_error params。
 * 必須兩者都存在才視為「ECpay 流程回來」；否則回 null（user 直連網址或 stale）。
 * 讀完一律清掉 sessionStorage + URL 的 cvs_* params。
 *
 * @param currentSearch window.location.search（含 leading ?）
 * @returns 還原所需的全部資料；非 cvs return 場景回 null
 */
export function consumeCvsRedirect(currentSearch: string): CvsConsumed | null {
  const params = new URLSearchParams(currentSearch)
  const hasCvsParam =
    params.has('cvs_store_id') || params.has('cvs_error')
  if (!hasCvsParam) {
    return null
  }

  // 清 URL 的 cvs_* params（保留其他 query params，無痕 history.replaceState）
  const cleanedParams = new URLSearchParams(currentSearch)
  for (const key of Array.from(cleanedParams.keys())) {
    if (key.startsWith('cvs_')) cleanedParams.delete(key)
  }
  const cleanedSearch = cleanedParams.toString()
  const newUrl =
    window.location.pathname +
    (cleanedSearch ? `?${cleanedSearch}` : '') +
    window.location.hash
  try {
    window.history.replaceState({}, '', newUrl)
  } catch {
    // history API 不可用就算了，保留 URL 也不至於壞功能
  }

  // 從 sessionStorage 拿 form draft + edit context
  let pending: CvsPendingPayload | null = null
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as CvsPendingPayload
      if (parsed.timestamp && Date.now() - parsed.timestamp <= TTL_MS) {
        pending = parsed
      }
    }
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    pending = null
  }

  // 沒 pending（sessionStorage 不可用、TTL 過期）→ 用一份空白 draft
  // 但同時保留 cvs 結果，讓 picker 至少能顯示已選好的門市
  const formDraft: ShippingProfileInput = pending?.formDraft ?? emptyFormDraft()
  const editContext: CvsEditContext = pending?.editContext ?? { page: 'shipping-profiles', editingId: 'new' }

  // 錯誤情境（cvs_error）
  const errorCode = params.get('cvs_error')
  if (errorCode) {
    const errorMessages: Record<string, string> = {
      invalid: '選店失敗或簽章驗證未通過，請再試一次',
      missing_store: '沒有取得門市資訊，請再試一次',
    }
    return {
      formDraft,
      editContext,
      cvs: null,
      error: errorMessages[errorCode] ?? '選店失敗，請再試一次',
    }
  }

  return {
    formDraft,
    editContext,
    cvs: {
      storeId: params.get('cvs_store_id') ?? '',
      storeName: params.get('cvs_store_name') ?? '',
      address: params.get('cvs_address') ?? '',
      phone: params.get('cvs_phone') ?? '',
      subType: params.get('cvs_sub_type') ?? '',
    },
    error: null,
  }
}

/**
 * 組去 backend cvs-map endpoint 的 URL，已包含 return 路徑。
 *
 * @param shippingType seven_eleven / family_mart（home 不會走這裡）
 * @param returnPath 結束後要回到的相對路徑（必須命中後端白名單，否則後端會 400）
 */
export function buildCvsMapUrl(
  shippingType: ShippingType,
  returnPath: string,
): string | null {
  const subType = SUB_TYPE_MAP[shippingType]
  if (!subType) return null
  return `/api/v1/logistics/cvs-map?type=${encodeURIComponent(subType)}&return=${encodeURIComponent(returnPath)}`
}

function emptyFormDraft(): ShippingProfileInput {
  return {
    shipping_type: 'seven_eleven',
    recipient_name: '',
    phone: '',
    email: null,
    city: '',
    district: '',
    address_detail: '',
    store_id: null,
    store_name: null,
    is_default: false,
  }
}
