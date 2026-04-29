import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'

import {
  createColor,
  getRgbHistory,
  getShortageDashboard,
  listColors,
  revertRgb,
  toggleColorActive,
  updateColor,
  updateColorRgb,
  updateColorStock,
  type ColorsListParams,
  type CreateColorPayload,
  type UpdateColorPayload,
} from './api'

export const COL_KEYS = {
  all: ['admin', 'colors'] as const,
  list: (params: ColorsListParams) => ['admin', 'colors', 'list', params] as const,
  shortage: ['admin', 'colors', 'shortage'] as const,
  rgbHistory: (id: string) => ['admin', 'colors', 'rgb-history', id] as const,
}

export function useColorsQuery(params: MaybeRefOrGetter<ColorsListParams>) {
  return useQuery({
    queryKey: ['admin', 'colors', 'list', params],
    queryFn: () => listColors(toValue(params)),
    staleTime: 30_000,
  })
}

export function useShortageDashboardQuery() {
  return useQuery({
    queryKey: COL_KEYS.shortage,
    queryFn: () => getShortageDashboard(),
    staleTime: 30_000,
  })
}

export function useRgbHistoryQuery(id: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: ['admin', 'colors', 'rgb-history', id],
    queryFn: () => getRgbHistory(toValue(id)!),
    enabled: () => !!toValue(id),
    staleTime: 30_000,
  })
}

function inv(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: COL_KEYS.all })
}

export function useCreateColorMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (p: CreateColorPayload) => createColor(p),
    onSuccess: () => inv(qc),
  })
}

export function useUpdateColorMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateColorPayload }) =>
      updateColor(id, payload),
    onSuccess: () => inv(qc),
  })
}

export function useToggleActiveMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => toggleColorActive(id),
    onSuccess: () => inv(qc),
  })
}

export function useUpdateRgbMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string
      payload: { hex?: string; rgb?: [number, number, number] }
    }) => updateColorRgb(id, payload),
    onSuccess: (_, { id }) => {
      inv(qc)
      qc.invalidateQueries({ queryKey: COL_KEYS.rgbHistory(id) })
    },
  })
}

export function useRevertRgbMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, history_id }: { id: string; history_id: string }) =>
      revertRgb(id, history_id),
    onSuccess: (_, { id }) => {
      inv(qc)
      qc.invalidateQueries({ queryKey: COL_KEYS.rgbHistory(id) })
    },
  })
}

export function useUpdateStockMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, add_ml }: { id: string; add_ml: number }) =>
      updateColorStock(id, add_ml),
    onSuccess: () => inv(qc),
  })
}
