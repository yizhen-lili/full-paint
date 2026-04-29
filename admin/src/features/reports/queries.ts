import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'

import { getSalesReport } from './api'

export function useSalesReportQuery(
  params: MaybeRefOrGetter<{ date_from?: string; date_to?: string }>,
) {
  return useQuery({
    queryKey: ['admin', 'reports', 'sales', params],
    queryFn: () => getSalesReport(toValue(params)),
    staleTime: 30_000,
  })
}
