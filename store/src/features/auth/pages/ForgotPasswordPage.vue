<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { Loader2, Mail } from 'lucide-vue-next'
import * as authApi from '../api'
import { forgotPasswordSchema, type ForgotPasswordValues } from '../schemas'

const apiError = ref<string | null>(null)
const submitting = ref(false)
const sent = ref(false)
const sentEmail = ref('')

const { handleSubmit, errors, defineField } = useForm<ForgotPasswordValues>({
  validationSchema: toTypedSchema(forgotPasswordSchema),
  initialValues: { email: '' },
})

const [email, emailAttrs] = defineField('email')

const onSubmit = handleSubmit(async (values) => {
  apiError.value = null
  submitting.value = true
  try {
    await authApi.forgotPassword(values.email)
    sentEmail.value = values.email
    sent.value = true
  } catch (e) {
    const err = e as authApi.ApiError
    apiError.value = err.detail || '送出失敗，請稍後再試'
  } finally {
    submitting.value = false
  }
})
</script>

<template>
  <div v-if="sent" class="page success">
    <div class="success-icon"><Mail /></div>
    <h1 class="title">重設信已寄出</h1>
    <p class="lede">
      若 <strong>{{ sentEmail }}</strong> 為已註冊帳號，<br />
      重設密碼連結已寄至此 email。
    </p>
    <p class="hint">連結 1 小時內有效。</p>
    <RouterLink to="/login" class="btn-secondary">回到登入</RouterLink>
  </div>

  <div v-else class="page">
    <header class="head">
      <span class="eyebrow">— Forgot Password —</span>
      <h1 class="title">忘記密碼</h1>
      <p class="lede">輸入註冊時的 email，我們會寄一封重設密碼連結給你。</p>
    </header>

    <form class="form" @submit.prevent="onSubmit" novalidate>
      <div class="field">
        <label for="fp-email">Email</label>
        <input
          id="fp-email"
          v-model="email"
          v-bind="emailAttrs"
          type="email"
          autocomplete="email"
          autofocus
          :class="{ invalid: !!errors.email }"
        />
        <p v-if="errors.email" class="err">{{ errors.email }}</p>
      </div>

      <p v-if="apiError" class="api-err">{{ apiError }}</p>

      <button type="submit" class="btn-primary" :disabled="submitting">
        <Loader2 v-if="submitting" class="spin" />
        <span>{{ submitting ? '送出中...' : '寄送重設連結' }}</span>
      </button>
    </form>

    <div class="alt">
      想起來了？
      <RouterLink to="/login" class="alt-link">回到登入 →</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; }
.success { text-align: center; align-items: center; }

.head { text-align: center; margin-bottom: 32px; }
.eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-fresh);
}
.title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 32px;
  letter-spacing: 0.08em;
  color: var(--color-ink-strong);
  margin: 12px 0 8px;
}
.lede {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 14px;
  line-height: 1.95;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
  margin: 0 0 16px;
}
.lede strong { color: var(--color-ink-strong); font-weight: 400; }

.hint {
  font-size: 12px;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
  margin: 0 0 24px;
}

.success-icon {
  width: 64px; height: 64px;
  border-radius: 50%;
  background: var(--color-fresh-tint);
  border: 1px solid var(--color-fresh);
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 24px;
}
.success-icon :deep(svg) {
  width: 28px; height: 28px;
  stroke: var(--color-fresh); stroke-width: 1.75; fill: none;
}

.form { display: flex; flex-direction: column; gap: 20px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-ink-default);
}
.field input {
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--color-ink-strong);
  background: var(--color-paper-canvas);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xs);
  padding: 12px 14px;
  outline: none;
  transition: border-color 150ms, box-shadow 150ms;
}
.field input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-tint);
}
.field input.invalid { border-color: var(--color-state-danger); }

.err {
  font-size: 12px;
  color: var(--color-state-danger);
  margin: 2px 0 0;
  letter-spacing: 0.04em;
}
.api-err {
  margin: 0;
  padding: 10px 14px;
  font-size: 13px;
  color: var(--color-state-danger);
  background: rgba(155, 58, 80, 0.08);
  border: 1px solid var(--color-state-danger);
  border-radius: var(--radius-xs);
  letter-spacing: 0.04em;
}

.btn-primary {
  margin-top: 8px;
  height: 48px;
  font-family: var(--font-body);
  font-size: 12px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-paper-canvas);
  background: var(--color-ink-strong);
  border: 1px solid var(--color-ink-strong);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: background 200ms, border-color 200ms;
}
.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-deep);
  border-color: var(--color-accent-deep);
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-secondary {
  margin-top: 8px;
  height: 48px;
  padding: 0 32px;
  font-family: var(--font-body);
  font-size: 12px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-ink-strong);
  background: transparent;
  border: 1px solid var(--color-line);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  transition: border-color 200ms, color 200ms;
}
.btn-secondary:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.spin {
  width: 14px; height: 14px;
  stroke: currentColor; stroke-width: 1.75; fill: none;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.alt {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid var(--color-line-subtle);
  text-align: center;
  font-size: 13px;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
}
.alt-link {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
  margin-left: 8px;
}
.alt-link:hover { color: var(--color-accent-deep); }
</style>
