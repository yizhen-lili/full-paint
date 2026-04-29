import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'

import {
  getUser,
  listUsers,
  updateUser,
  type UpdateUserPayload,
  type UsersListParams,
} from './api'

export const AU_KEYS = {
  all: ['admin', 'users'] as const,
  list: (params: UsersListParams) => ['admin', 'users', 'list', params] as const,
  detail: (id: string) => ['admin', 'users', 'detail', id] as const,
}

export function useUsersQuery(params: MaybeRefOrGetter<UsersListParams>) {
  return useQuery({
    queryKey: ['admin', 'users', 'list', params],
    queryFn: () => listUsers(toValue(params)),
    staleTime: 30_000,
  })
}

export function useUserQuery(id: MaybeRefOrGetter<string | undefined>) {
  return useQuery({
    queryKey: ['admin', 'users', 'detail', id],
    queryFn: () => getUser(toValue(id)!),
    enabled: () => !!toValue(id),
    staleTime: 30_000,
  })
}

export function useUpdateUserMutation(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: UpdateUserPayload) => updateUser(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: AU_KEYS.detail(id) })
      qc.invalidateQueries({ queryKey: AU_KEYS.all })
    },
  })
}
