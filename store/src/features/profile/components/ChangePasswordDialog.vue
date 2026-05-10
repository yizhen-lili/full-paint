<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loader2, X, Eye, EyeOff } from 'lucide-vue-next'
import * as profileApi from '../api'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: []; success: [] }>()

const oldPassword = ref('')
const newPassword = ref('')
const newPassword2 = ref('')
const showOld = ref(false)
const showNew = ref(false)
const submitting = ref(false)
const errorText = ref<string | null>(null)

watch(
  () => props.open,
  (v) => {
    if (v) {
      oldPassword.value = ''
      newPassword.value = ''
      newPassword2.value = ''
      showOld.value = false
      showNew.value = false
      submitting.value = false
      errorText.value = null
    }
  },
)

function validate(): boolean {
  if (oldPassword.value.length === 0) {
    errorText.value = '請輸入目前密碼'
    return false
  }
  if (newPassword.value.length < 10) {
    errorText.value = '新密碼至少 10 碼'
    return false
  }
  if (!/[A-Za-z]/.test(newPassword.value) || !/\d/.test(newPassword.value)) {
    errorText.value = '新密碼需同時包含英文字母與數字'
    return false
  }
  if (newPassword.value !== newPassword2.value) {
    errorText.value = '兩次新密碼不一致'
    return false
  }
  errorText.value = null
  return true
}

async function submit() {
  if (!validate()) return
  submitting.value = true
  try {
    await profileApi.changePassword({
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    emit('success')
    emit('close')
  } catch (e) {
    const err = e as profileApi.ApiError
    errorText.value = err.detail || '密碼修改失敗'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="modal-overlay" @click.self="emit('close')">
      <div class="modal">
        <header class="modal-hd">
          <h3>修改密碼</h3>
          <button @click="emit('close')" aria-label="關閉"><X :size="16" /></button>
        </header>
        <form class="modal-body" @submit.prevent="submit">
          <label class="field">
            <span class="field-label">目前密碼</span>
            <span class="pwd-row">
              <input
                v-model="oldPassword"
                :type="showOld ? 'text' : 'password'"
                autocomplete="current-password"
              />
              <button type="button" class="pwd-toggle" @click="showOld = !showOld" tabindex="-1">
                <component :is="showOld ? EyeOff : Eye" :size="14" :stroke-width="1.5" />
              </button>
            </span>
          </label>
          <label class="field">
            <span class="field-label">新密碼（至少 10 碼，英數混合）</span>
            <span class="pwd-row">
              <input
                v-model="newPassword"
                :type="showNew ? 'text' : 'password'"
                autocomplete="new-password"
              />
              <button type="button" class="pwd-toggle" @click="showNew = !showNew" tabindex="-1">
                <component :is="showNew ? EyeOff : Eye" :size="14" :stroke-width="1.5" />
              </button>
            </span>
          </label>
          <label class="field">
            <span class="field-label">再次輸入新密碼</span>
            <input
              v-model="newPassword2"
              :type="showNew ? 'text' : 'password'"
              autocomplete="new-password"
            />
          </label>
          <p v-if="errorText" class="error">{{ errorText }}</p>
        </form>
        <footer class="modal-ft">
          <button class="btn-secondary" type="button" @click="emit('close')">取消</button>
          <button class="btn-primary" type="button" :disabled="submitting" @click="submit">
            <Loader2 v-if="submitting" :size="14" class="spin" />
            確認修改
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(43, 36, 27, 0.45);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.modal {
  width: 100%; max-width: 440px;
  background: var(--color-paper-canvas);
  border-radius: var(--radius-md);
  display: flex; flex-direction: column;
}
.modal-hd {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px; border-bottom: 1px solid var(--color-line);
}
.modal-hd h3 {
  font-family: var(--font-cn-serif); font-weight: 300;
  font-size: 19px; margin: 0; letter-spacing: 0.04em;
}
.modal-hd button {
  background: transparent; border: 0; cursor: pointer;
  width: 32px; height: 32px; border-radius: 50%;
  color: var(--color-ink-muted);
}
.modal-hd button:hover { background: var(--color-paper-surface); color: var(--color-ink-strong); }
.modal-body {
  padding: 20px 24px; display: flex; flex-direction: column; gap: 14px;
}
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label {
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--color-ink-muted);
}
.field input {
  width: 100%; padding: 9px 12px;
  border: 1px solid var(--color-line-subtle);
  background: var(--color-paper-surface);
  border-radius: var(--radius-xs);
  font: inherit; font-size: 14px;
  color: var(--color-ink-default);
}
.field input:focus { outline: none; border-color: var(--color-accent); }
.pwd-row { position: relative; display: block; }
.pwd-toggle {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: transparent; border: 0; cursor: pointer;
  width: 28px; height: 28px;
  display: inline-flex; align-items: center; justify-content: center;
  color: var(--color-ink-muted); border-radius: var(--radius-xs);
}
.pwd-toggle:hover { color: var(--color-ink-strong); background: var(--color-paper-surface); }
.error {
  margin: 0; font-size: 12px; color: var(--color-state-danger);
}
.modal-ft {
  padding: 16px 24px; border-top: 1px solid var(--color-line);
  display: flex; gap: 8px;
}
.btn-secondary, .btn-primary {
  flex: 1; padding: 11px; border: 0; border-radius: var(--radius-xs);
  cursor: pointer;
  font-family: var(--font-cn-serif); font-size: 13px; letter-spacing: 0.06em;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.btn-secondary {
  background: transparent; border: 1px solid var(--color-line);
  color: var(--color-ink-default);
}
.btn-secondary:hover { border-color: var(--color-accent); color: var(--color-accent-deep); }
.btn-primary {
  background: var(--color-ink-strong); color: var(--color-paper-canvas);
}
.btn-primary:hover { background: var(--color-accent-deep); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.spin { animation: spin 900ms linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
