import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'

import {
  bulkCompleteNotifications,
  listNotifications,
  updateNotificationStatus,
  type NotificationStatus,
  type NotificationsParams,
} from './api'

export const N_KEYS = {
  all: ['admin', 'notifications'] as const,
  list: (params: NotificationsParams) => ['admin', 'notifications', 'list', params] as const,
}

export function useNotificationsQuery(params: MaybeRefOrGetter<NotificationsParams>) {
  return useQuery({
    queryKey: ['admin', 'notifications', 'list', params],
    queryFn: () => listNotifications(toValue(params)),
    staleTime: 15_000,
    refetchInterval: 30_000, // 半分鐘 polling 模擬即時感
    refetchOnWindowFocus: true,
  })
}

function inv(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: N_KEYS.all })
}

export function useUpdateStatusMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: NotificationStatus }) =>
      updateNotificationStatus(id, status),
    onSuccess: () => inv(qc),
  })
}

export function useBulkCompleteMutation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) => bulkCompleteNotifications(ids),
    onSuccess: () => inv(qc),
  })
}
