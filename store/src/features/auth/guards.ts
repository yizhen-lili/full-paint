import type { NavigationGuard } from 'vue-router'
import { useAuthStore } from './store'

/**
 * Wait for auth bootstrap to complete (fetchMe to settle).
 * Resolves immediately if already bootstrapped.
 */
async function waitForBootstrap(): Promise<void> {
  const auth = useAuthStore()
  if (auth.bootstrapped) return
  return new Promise((resolve) => {
    const start = Date.now()
    const tick = setInterval(() => {
      if (auth.bootstrapped || Date.now() - start > 5000) {
        clearInterval(tick)
        resolve()
      }
    }, 50)
  })
}

/**
 * Global router guard.
 * - meta.requiresAuth: 未登入 → /login?redirect=<原路徑>
 * - meta.guestOnly: 已登入 → /
 */
export const authGuard: NavigationGuard = async (to) => {
  await waitForBootstrap()
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guestOnly && auth.isLoggedIn) {
    return { path: '/' }
  }

  return true
}
