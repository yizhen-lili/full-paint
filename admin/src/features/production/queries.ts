import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { computed, toValue } from 'vue'

import {
  approveJob,
  batchPostProcess,
  createJobs,
  deleteJob,
  deleteJobsBatch,
  eliminateBorder,
  getJob,
  listJobs,
  mergeColor,
  startBatch,
  unapproveJob,
  updateSamMask,
  type BatchPostProcessPayload,
  type CreateJobsRequest,
  type EliminateBorderPayload,
  type JobsListParams,
  type MergeColorPayload,
  type SamMaskRequest,
} from './api'

export const PJ_KEYS = {
  all: ['admin', 'production'] as const,
  list: (params: JobsListParams) => ['admin', 'production', 'list', params] as const,
  detail: (id: string) => ['admin', 'production', 'detail', id] as const,
}

export function useJobsQuery(params: MaybeRefOrGetter<JobsListParams>) {
  return useQuery({
    queryKey: ['admin', 'production', 'list', params],
    queryFn: () => listJobs(toValue(params)),
    staleTime: 30_000,
  })
}

export function useJobQuery(id: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: ['admin', 'production', 'detail', id],
    queryFn: () => getJob(toValue(id)!),
    enabled: () => !!toValue(id),
    staleTime: 10_000,
    // pending / processing 狀態時自動輪詢，等 Celery 推進
    refetchInterval: (query) => {
      const data = query.state.data as { status?: string } | undefined
      if (!data) return false
      return data.status === 'pending' || data.status === 'processing' ? 5000 : false
    },
    refetchOnWindowFocus: true,
  })
}

function invalidate(qc: ReturnType<typeof useQueryClient>, id?: string) {
  if (id) qc.invalidateQueries({ queryKey: PJ_KEYS.detail(id) })
  qc.invalidateQueries({ queryKey: PJ_KEYS.all })
}

export function useCreateJobsMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateJobsRequest) => createJobs(payload),
    onSuccess: () => invalidate(qc),
  })
}

export function useApproveJobMutation(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (notes?: string | null) => approveJob(id, notes),
    onSuccess: () => invalidate(qc, id),
  })
}

export function useUnapproveJobMutation(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => unapproveJob(id),
    onSuccess: () => invalidate(qc, id),
  })
}

/** 硬刪除 job — 成功後 invalidate list / detail，前端自行處理 router.push 跳轉。
 *
 * 接受 { id, force? }：force=true 用於強制刪除卡死的 processing job。
 */
export function useDeleteJobMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, force = false }: { id: string; force?: boolean }) =>
      deleteJob(id, { force }),
    onSuccess: (_, vars) => invalidate(qc, vars.id),
  })
}

/** 批次硬刪除 — 不論失敗筆數多少，成功後一律 invalidate 整個 list；
 *  detail 不個別 invalidate（jobs 可能是任意組合），統一 PJ_KEYS.all 就夠。
 */
export function useDeleteJobsBatchMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ jobIds, force = false }: { jobIds: string[]; force?: boolean }) =>
      deleteJobsBatch(jobIds, { force }),
    onSuccess: () => invalidate(qc),
  })
}

// ── F06-B Post-process mutations ──────────────────────────────────────

export function useMergeColorMutation(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: MergeColorPayload) => mergeColor(id, payload),
    onSuccess: () => invalidate(qc, id),
  })
}

export function useEliminateBorderMutation(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: EliminateBorderPayload) => eliminateBorder(id, payload),
    onSuccess: () => invalidate(qc, id),
  })
}

export function useBatchPostProcessMutation(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: BatchPostProcessPayload) => batchPostProcess(id, payload),
    onSuccess: () => invalidate(qc, id),
  })
}

// ── SAM mask + Batch start mutations ──────────────────────────────────

export function useSamMaskMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: SamMaskRequest) => updateSamMask(jobId, payload),
    onSuccess: () => invalidate(qc, jobId),
  })
}

export function useStartBatchMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (batchId: string) => startBatch(batchId),
    onSuccess: () => invalidate(qc),
  })
}

