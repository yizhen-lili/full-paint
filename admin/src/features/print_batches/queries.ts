import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'

import {
  createBatch,
  finalizeBatch,
  getBatch,
  getCandidates,
  listBatches,
  previewBatch,
  type RequiredItem,
} from './api'

export const PB_KEYS = {
  all: ['admin', 'print-batches'] as const,
  list: (params: { page?: number; page_size?: number }) =>
    ['admin', 'print-batches', 'list', params] as const,
  detail: (id: string) => ['admin', 'print-batches', 'detail', id] as const,
  candidates: ['admin', 'print-batches', 'candidates'] as const,
}

export function useBatchesQuery(params: MaybeRefOrGetter<{ page?: number; page_size?: number }>) {
  return useQuery({
    queryKey: ['admin', 'print-batches', 'list', params],
    queryFn: () => listBatches(toValue(params)),
    staleTime: 30_000,
  })
}

export function useBatchQuery(id: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: ['admin', 'print-batches', 'detail', id],
    queryFn: () => getBatch(toValue(id)!),
    enabled: () => !!toValue(id),
    staleTime: 10_000,
  })
}

export function useCandidatesQuery() {
  return useQuery({
    queryKey: PB_KEYS.candidates,
    queryFn: () => getCandidates(),
    staleTime: 30_000,
  })
}

function inv(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: PB_KEYS.all })
}

export function usePreviewBatchMutation() {
  return useMutation({
    mutationFn: (payload: { required: RequiredItem[]; candidates: RequiredItem[] }) =>
      previewBatch(payload),
  })
}

export function useCreateBatchMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      required: RequiredItem[]
      candidates: RequiredItem[]
      admin_notes?: string | null
    }) => createBatch(payload),
    onSuccess: () => inv(qc),
  })
}

export function useFinalizeBatchMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => finalizeBatch(id),
    onSuccess: () => inv(qc),
  })
}
