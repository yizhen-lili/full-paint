import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'

import {
  completePaletteMappings,
  confirmPendingMerges,
  copyMappingsFromJob,
  listCopyCandidates,
  listPaletteMappings,
  rejectPendingMerges,
  updatePaletteMapping,
} from './api_mapping'

export const PM_KEYS = {
  mappings: (jobId: string) => ['admin', 'palette-mappings', jobId] as const,
}

export function usePaletteMappingsQuery(jobId: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: ['admin', 'palette-mappings', jobId],
    queryFn: () => listPaletteMappings(toValue(jobId)!),
    enabled: () => !!toValue(jobId),
    staleTime: 30_000,
  })
}

export function useUpdateMappingMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ templateId, physicalColorId }: { templateId: number; physicalColorId: string }) =>
      updatePaletteMapping(jobId, templateId, physicalColorId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PM_KEYS.mappings(jobId) })
    },
  })
}

export function useCopyCandidatesQuery(
  jobId: MaybeRefOrGetter<string | undefined>,
  enabled: MaybeRefOrGetter<boolean>,
) {
  return useQuery({
    queryKey: ['admin', 'palette-mappings', jobId, 'copy-candidates'],
    queryFn: () => listCopyCandidates(toValue(jobId)!),
    enabled: () => !!toValue(jobId) && toValue(enabled),
    staleTime: 30_000,
  })
}

export function useCopyMappingsMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceJobId: string) => copyMappingsFromJob(jobId, sourceJobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PM_KEYS.mappings(jobId) })
    },
  })
}

export function useCompleteMappingsMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => completePaletteMappings(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PM_KEYS.mappings(jobId) })
      // finalize_template 改 Celery 背景跑（密集模板數十秒、同步會 502）→ 完成對應回來時
      // template_final_url 還沒產好。先 invalidate 一次拿即時狀態；PaletteMappingPage 的
      // pollFinalize 會輪詢 job 直到 finalized_at 更新，再顯示「查看 SVG」連結。
      qc.invalidateQueries({ queryKey: ['admin', 'production', 'detail', jobId] })
    },
  })
}

export function useConfirmPendingMergesMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => confirmPendingMerges(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: PM_KEYS.mappings(jobId) })
      qc.invalidateQueries({ queryKey: ['admin', 'production', 'detail', jobId] })
    },
  })
}

export function useRejectPendingMergesMutation(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => rejectPendingMerges(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'production', 'detail', jobId] })
    },
  })
}
