import { useMutation, useQuery } from '@tanstack/vue-query'

import { getPaintRequirementSources, getPaintRequirements } from './api'

/** 列出三類來源 — picker 用，初次進頁面就抓。 */
export function useSourcesQuery() {
  return useQuery({
    queryKey: ['admin', 'paint-requirements', 'sources'] as const,
    queryFn: () => getPaintRequirementSources(),
    staleTime: 30_000,
  })
}

/** lazy 查詢：按「查詢」按鈕觸發 mutation；不用 useQuery 避免 input 變化頻繁戳後端。 */
export function usePaintRequirementsMutation() {
  return useMutation({
    mutationFn: (params: { productionJobId: string; quantity: number }) =>
      getPaintRequirements(params.productionJobId, params.quantity),
  })
}
