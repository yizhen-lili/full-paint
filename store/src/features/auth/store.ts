import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from './api'
import type { MeResponse } from './api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<MeResponse | null>(null)
  const bootstrapped = ref(false)

  const isLoggedIn = computed(() => user.value !== null)
  const isCustomer = computed(() => user.value?.role === 'customer')

  /**
   * Called on app boot. Reads /auth/me; 401 → null (visitor); other errors logged.
   * Always sets bootstrapped = true so guards can proceed.
   */
  async function fetchMe(): Promise<void> {
    try {
      user.value = await authApi.fetchMe()
    } catch (err) {
      // Network failure / unexpected status — treat as visitor, log for debug.
      console.warn('[auth] fetchMe failed, treating as visitor:', err)
      user.value = null
    } finally {
      bootstrapped.value = true
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      user.value = null
    }
  }

  /**
   * Used by 401 global interceptor (S04+) to clear local state without API call.
   */
  function clear(): void {
    user.value = null
    bootstrapped.value = true
  }

  return {
    user,
    bootstrapped,
    isLoggedIn,
    isCustomer,
    fetchMe,
    logout,
    clear,
  }
})
