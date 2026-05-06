<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import { Loader2 } from 'lucide-vue-next'
import * as authApi from '../api'
import { loginSchema, type LoginValues } from '../schemas'
import { useAuthStore } from '../store'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const apiError = ref<string | null>(null)
const submitting = ref(false)

const { handleSubmit, errors, defineField } = useForm<LoginValues>({
  validationSchema: toTypedSchema(loginSchema),
  initialValues: { email: '', password: '' },
})

const [email, emailAttrs] = defineField('email')
const [password, passwordAttrs] = defineField('password')

const redirectTo = computed(() => {
  const r = route.query.redirect
  return typeof r === 'string' && r.length > 0 ? r : '/'
})

const onSubmit = handleSubmit(async (values) => {
  apiError.value = null
  submitting.value = true
  try {
    await authApi.login(values.email, values.password)
    await auth.fetchMe()
    router.push(redirectTo.value)
  } catch (e) {
    const err = e as authApi.ApiError
    if (err.status === 401) {
      apiError.value = '帳號或密碼錯誤'
    } else if (err.status === 403) {
      apiError.value = err.detail || 'Email 尚未驗證，請至信箱完成驗證'
    } else {
      apiError.value = err.detail || '登入失敗，請稍後再試'
    }
  } finally {
    submitting.value = false
  }
})
</script>

<template>
  <div class="page">
    <header class="head">
      <span class="eyebrow">— Sign In —</span>
      <h1 class="title">登入</h1>
      <p class="lede">回到你的小作坊，繼續慢慢畫。</p>
    </header>

    <form class="form" @submit.prevent="onSubmit" novalidate>
      <div class="field">
        <label for="login-email">Email</label>
        <input
          id="login-email"
          v-model="email"
          v-bind="emailAttrs"
          type="email"
          autocomplete="email"
          autofocus
          :class="{ invalid: !!errors.email }"
        />
        <p v-if="errors.email" class="err">{{ errors.email }}</p>
      </div>

      <div class="field">
        <div class="label-row">
          <label for="login-pwd">密碼</label>
          <RouterLink to="/forgot-password" class="forgot">忘記密碼？</RouterLink>
        </div>
        <input
          id="login-pwd"
          v-model="password"
          v-bind="passwordAttrs"
          type="password"
          autocomplete="current-password"
          :class="{ invalid: !!errors.password }"
        />
        <p v-if="errors.password" class="err">{{ errors.password }}</p>
      </div>

      <p v-if="apiError" class="api-err">{{ apiError }}</p>

      <button type="submit" class="btn-primary" :disabled="submitting">
        <Loader2 v-if="submitting" class="spin" />
        <span>{{ submitting ? '登入中...' : '登入' }}</span>
      </button>
    </form>

    <div class="alt">
      還沒有帳號？
      <RouterLink to="/register" class="alt-link">建立新帳號 →</RouterLink>
    </div>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; }

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
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
  margin: 0;
}

.form { display: flex; flex-direction: column; gap: 20px; }

.field { display: flex; flex-direction: column; gap: 6px; }

.label-row { display: flex; justify-content: space-between; align-items: baseline; }

.field label {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-ink-default);
}

.forgot {
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--color-accent);
  text-decoration: none;
  letter-spacing: 0.04em;
  transition: color 150ms;
}
.forgot:hover { color: var(--color-accent-deep); }

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
.field input.invalid {
  border-color: var(--color-state-danger);
}

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
