<script setup lang="ts">
import { onMounted, ref, useTemplateRef } from 'vue'
import * as authApi from '../api'

const props = defineProps<{
  /** 「continue_with」會顯示「繼續使用 Google」；「signin_with」會是「使用 Google 登入」 */
  text?: 'continue_with' | 'signin_with' | 'signup_with'
}>()

const emit = defineEmits<{
  success: []
  error: [message: string]
}>()

// Vite env：必須在 store/.env 設 VITE_GOOGLE_CLIENT_ID（dev / production 各自）
const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

const containerRef = useTemplateRef<HTMLDivElement>('container')
const error = ref<string | null>(null)
const ready = ref(false)

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential: string }) => void
            ux_mode?: 'popup' | 'redirect'
          }) => void
          renderButton: (parent: HTMLElement, opts: Record<string, unknown>) => void
        }
      }
    }
  }
}

async function handleCredential(response: { credential: string }) {
  error.value = null
  try {
    await authApi.googleSignin(response.credential)
    emit('success')
  } catch (e) {
    const err = e as authApi.ApiError
    const msg = err?.detail || 'Google 登入失敗，請稍後再試'
    error.value = msg
    emit('error', msg)
  }
}

/** GIS script 是 async/defer 載的，可能還沒就緒 — 用 setInterval 簡單 poll */
function waitForGoogle(timeoutMs = 5000): Promise<void> {
  return new Promise((resolve, reject) => {
    const start = Date.now()
    const timer = setInterval(() => {
      if (window.google?.accounts?.id) {
        clearInterval(timer)
        resolve()
      } else if (Date.now() - start > timeoutMs) {
        clearInterval(timer)
        reject(new Error('Google Identity Services 載入逾時'))
      }
    }, 100)
  })
}

onMounted(async () => {
  if (!clientId) {
    error.value = 'VITE_GOOGLE_CLIENT_ID 未設定，Google 登入暫不可用'
    return
  }
  try {
    await waitForGoogle()
    window.google!.accounts.id.initialize({
      client_id: clientId,
      callback: handleCredential,
      ux_mode: 'popup',
    })
    if (containerRef.value) {
      window.google!.accounts.id.renderButton(containerRef.value, {
        theme: 'outline',
        size: 'large',
        text: props.text ?? 'continue_with',
        logo_alignment: 'center',
        shape: 'pill',
        locale: 'zh_TW',
      })
    }
    ready.value = true
  } catch (e) {
    error.value = (e as Error).message
  }
})
</script>

<template>
  <div class="google-wrap">
    <div ref="container" class="google-btn" :class="{ loading: !ready && !error }" />
    <p v-if="error" class="google-err">{{ error }}</p>
  </div>
</template>

<style scoped>
.google-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
.google-btn {
  min-height: 44px;
  width: 100%;
  display: flex;
  justify-content: center;
}
.google-btn.loading::before {
  content: '正在載入 Google 登入…';
  font-size: 12px;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
}
.google-err {
  margin: 0;
  font-size: 12px;
  color: var(--color-state-danger);
  letter-spacing: 0.04em;
  text-align: center;
}
</style>
