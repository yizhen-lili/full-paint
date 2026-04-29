<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Select from '@/shared/ui/Select.vue'
import { AlertTriangle } from 'lucide-vue-next'

import type { AdminUser, UpdateUserPayload, UserRole } from '../api'

const props = defineProps<{
  open: boolean
  user: AdminUser | null
  /** 是否是當前登入的 admin（如果是 → 不允許停用 / 改 role）*/
  isSelf: boolean
  pending: boolean
}>()

const emit = defineEmits<{
  close: []
  confirm: [payload: UpdateUserPayload]
}>()

const name = ref('')
const role = ref<UserRole>('customer')
const isActive = ref(true)
const password = ref('')
const errors = ref<Record<string, string>>({})

watch(
  () => [props.open, props.user],
  () => {
    if (!props.user) return
    name.value = props.user.name
    role.value = props.user.role
    isActive.value = props.user.is_active
    password.value = ''
    errors.value = {}
  },
  { immediate: true },
)

const roleOptions = [
  { value: 'customer', label: '一般用戶 customer' },
  { value: 'admin', label: '管理員 admin' },
]

function validate(): boolean {
  const errs: Record<string, string> = {}
  if (!name.value.trim()) errs.name = '名稱不可為空'
  if (password.value && password.value.length > 0) {
    if (password.value.length < 10) errs.password = '密碼至少 10 字'
    else if (!/[A-Za-z]/.test(password.value) || !/[0-9]/.test(password.value)) {
      errs.password = '密碼需包含英數字'
    }
  }
  errors.value = errs
  return Object.keys(errs).length === 0
}

function submit() {
  if (!props.user || !validate()) return
  const payload: UpdateUserPayload = {
    name: name.value.trim() !== props.user.name ? name.value.trim() : null,
    role: role.value !== props.user.role ? role.value : null,
    is_active: isActive.value !== props.user.is_active ? isActive.value : null,
    password: password.value ? password.value : null,
  }
  emit('confirm', payload)
}

const isPromotingToAdmin = (() => {
  return false  // 視覺確認用，於 template 中用 computed
})()
</script>

<template>
  <Dialog
    :open="open"
    :title="user ? `編輯：${user.name}` : ''"
    size="md"
    @close="emit('close')"
  >
    <div v-if="user" class="space-y-4 text-[13px]">
      <div>
        <Label>名稱</Label>
        <Input v-model="name" />
        <p v-if="errors.name" class="mt-1 text-[12px] text-state-danger">{{ errors.name }}</p>
      </div>

      <div>
        <Label>Email</Label>
        <Input :value="user.email" disabled />
        <p class="mt-1 text-[11px] text-ink-muted">Email 不可由 admin 直接改 — 客戶須走 email 驗證流程。</p>
      </div>

      <div>
        <Label>角色</Label>
        <Select v-model="role" :options="roleOptions" :disabled="isSelf" />
        <p v-if="role === 'admin' && user.role === 'customer'" class="mt-1 text-[12px] text-state-warning flex items-start gap-1">
          <AlertTriangle :size="12" :stroke-width="1.5" class="mt-0.5 shrink-0" />
          升為 admin 後，此用戶可進入後台執行所有管理操作（含改其他人 role）。確認嗎？
        </p>
        <p v-if="isSelf" class="mt-1 text-[11px] text-ink-muted">不可變更自己的角色（避免誤降權後鎖死）。</p>
      </div>

      <div>
        <label class="flex items-center gap-2">
          <input
            v-model="isActive"
            type="checkbox"
            :disabled="isSelf"
          />
          <span class="text-ink-strong">啟用此帳號</span>
        </label>
        <p v-if="!isActive" class="mt-1 text-[12px] text-state-warning flex items-start gap-1">
          <AlertTriangle :size="12" :stroke-width="1.5" class="mt-0.5 shrink-0" />
          停用後此用戶下次 API 請求會被擋（401），無法登入。
        </p>
        <p v-if="isSelf" class="mt-1 text-[11px] text-ink-muted">不可停用自己。</p>
      </div>

      <div>
        <Label>重設密碼（留空 = 不改）</Label>
        <Input v-model="password" type="password" placeholder="至少 10 字、含英數" />
        <p v-if="errors.password" class="mt-1 text-[12px] text-state-danger">{{ errors.password }}</p>
        <p v-else class="mt-1 text-[11px] text-ink-muted">系統不會自動通知客戶 — 請另外用其他管道告知。</p>
      </div>
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="pending" @click="emit('close')">取消</Button>
      <Button variant="primary" :disabled="pending" @click="submit">儲存</Button>
    </template>
  </Dialog>
</template>
