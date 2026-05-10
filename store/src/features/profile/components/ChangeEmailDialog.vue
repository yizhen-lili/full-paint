<script setup lang="ts">
import { ref, watch } from 'vue'
import { Loader2, X } from 'lucide-vue-next'
import * as profileApi from '../api'

const props = defineProps<{
  open: boolean
  currentEmail: string
}>()
const emit = defineEmits<{ close: []; success: [newEmail: string] }>()

const newEmail = ref('')
const submitting = ref(false)
const errorText = ref<string | null>(null)

watch(
  () => props.open,
  (v) => {
    if (v) {
      newEmail.value = ''
      submitting.value = false
      errorText.value = null
    }
  },
)

function isEmail(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)
}

async function submit() {
  const e = newEmail.value.trim().toLowerCase()
  if (!isEmail(e)) {
    errorText.value = '請輸入有效的 Email 格式'
    return
  }
  if (e === props.currentEmail.toLowerCase()) {
    errorText.value = '新 Email 不能與目前相同'
    return
  }
  submitting.value = true
  errorText.value = null
  try {
    await profileApi.requestEmailChange(e)
    emit('success', e)
    emit('close')
  } catch (err) {
    const ae = err as profileApi.ApiError
    errorText.value = ae.detail || 'Email 變更失敗'
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
          <h3>變更 Email</h3>
          <button @click="emit('close')" aria-label="關閉"><X :size="16" /></button>
        </header>
        <form class="modal-body" @submit.prevent="submit">
          <p class="modal-desc">
            系統會寄驗證信至新 Email，點連結後正式更換。<br>
            <strong>驗證完成的當下，舊 Email 立即失效。</strong>
          </p>
          <label class="field">
            <span class="field-label">目前 Email</span>
            <span class="readonly-value">{{ currentEmail }}</span>
          </label>
          <label class="field">
            <span class="field-label">新 Email</span>
            <input
              v-model="newEmail"
              type="email"
              autocomplete="email"
              placeholder="new@example.com"
            />
          </label>
          <p v-if="errorText" class="error">{{ errorText }}</p>
        </form>
        <footer class="modal-ft">
          <button class="btn-secondary" type="button" @click="emit('close')">取消</button>
          <button class="btn-primary" type="button" :disabled="submitting" @click="submit">
            <Loader2 v-if="submitting" :size="14" class="spin" />
            寄出驗證信
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
.modal-desc { margin: 0; font-size: 13px; line-height: 1.7; color: var(--color-ink-muted); }
.modal-desc strong { color: var(--color-state-warning); font-weight: 500; }
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
.readonly-value {
  padding: 9px 12px; font-size: 14px; color: var(--color-ink-default);
  background: var(--color-paper-deep); border-radius: var(--radius-xs);
}
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
