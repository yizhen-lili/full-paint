import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'

import {
  createCaseCategory,
  createCustomCase,
  createSurcharge,
  deleteCaseCategory,
  deleteCustomCase,
  deleteSurcharge,
  listCaseCategories,
  listCustomCases,
  listPages,
  listPhotoPrices,
  listSettings,
  listSurcharges,
  toggleCustomCasePublish,
  toggleSurchargeActive,
  updateCaseCategory,
  updateCustomCase,
  updatePhotoPrice,
  updateSurcharge,
  upsertPage,
  upsertSetting,
  type CustomCase,
} from './api'

export const C_KEYS = {
  all: ['admin', 'content'] as const,
  pages: ['admin', 'content', 'pages'] as const,
  settings: ['admin', 'content', 'settings'] as const,
  prices: ['admin', 'content', 'prices'] as const,
  surcharges: ['admin', 'content', 'surcharges'] as const,
  categories: ['admin', 'content', 'categories'] as const,
  cases: ['admin', 'content', 'cases'] as const,
}

export const usePagesQuery = () =>
  useQuery({ queryKey: C_KEYS.pages, queryFn: () => listPages(), staleTime: 60_000 })
export const useSettingsQuery = () =>
  useQuery({ queryKey: C_KEYS.settings, queryFn: () => listSettings(), staleTime: 60_000 })
export const usePhotoPricesQuery = () =>
  useQuery({ queryKey: C_KEYS.prices, queryFn: () => listPhotoPrices(), staleTime: 60_000 })
export const useSurchargesQuery = () =>
  useQuery({ queryKey: C_KEYS.surcharges, queryFn: () => listSurcharges(), staleTime: 60_000 })
export const useCaseCategoriesQuery = () =>
  useQuery({ queryKey: C_KEYS.categories, queryFn: () => listCaseCategories(), staleTime: 60_000 })
export const useCustomCasesQuery = () =>
  useQuery({ queryKey: C_KEYS.cases, queryFn: () => listCustomCases({ page_size: 100 }), staleTime: 60_000 })

function inv(qc: ReturnType<typeof useQueryClient>, key: readonly unknown[]) {
  qc.invalidateQueries({ queryKey: key })
}

export function useUpsertPageMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ slug, payload }: { slug: string; payload: { title: string; content: string } }) =>
      upsertPage(slug, payload),
    onSuccess: () => inv(qc, C_KEYS.pages),
  })
}

export function useUpsertSettingMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: { key: string; value: string }) => upsertSetting(payload),
    onSuccess: () => inv(qc, C_KEYS.settings),
  })
}

export function useUpdatePhotoPriceMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, price }: { id: string; price: number }) => updatePhotoPrice(id, price),
    onSuccess: () => inv(qc, C_KEYS.prices),
  })
}

export function useCreateSurchargeMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createSurcharge,
    onSuccess: () => inv(qc, C_KEYS.surcharges),
  })
}
export function useUpdateSurchargeMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string
      payload: { category: string; label: string; amount: number; is_active: boolean }
    }) => updateSurcharge(id, payload),
    onSuccess: () => inv(qc, C_KEYS.surcharges),
  })
}
export function useToggleSurchargeActiveMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => toggleSurchargeActive(id),
    onSuccess: () => inv(qc, C_KEYS.surcharges),
  })
}
export function useDeleteSurchargeMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteSurcharge(id),
    onSuccess: () => inv(qc, C_KEYS.surcharges),
  })
}

export function useCreateCategoryMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => createCaseCategory(name),
    onSuccess: () => inv(qc, C_KEYS.categories),
  })
}
export function useUpdateCategoryMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => updateCaseCategory(id, name),
    onSuccess: () => inv(qc, C_KEYS.categories),
  })
}
export function useDeleteCategoryMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteCaseCategory(id),
    onSuccess: () => {
      inv(qc, C_KEYS.categories)
      inv(qc, C_KEYS.cases) // 案例 category_id 可能改成 null
    },
  })
}

export function useCreateCaseMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: Omit<CustomCase, 'id' | 'created_at'>) => createCustomCase(payload),
    onSuccess: () => inv(qc, C_KEYS.cases),
  })
}
export function useUpdateCaseMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Omit<CustomCase, 'id' | 'created_at'> }) =>
      updateCustomCase(id, payload),
    onSuccess: () => inv(qc, C_KEYS.cases),
  })
}
export function useToggleCasePublishMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => toggleCustomCasePublish(id),
    onSuccess: () => inv(qc, C_KEYS.cases),
  })
}
export function useDeleteCaseMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteCustomCase(id),
    onSuccess: () => inv(qc, C_KEYS.cases),
  })
}
