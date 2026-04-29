<script setup lang="ts">
import { ref, watch } from 'vue'
import Dialog from '@/shared/ui/Dialog.vue'
import Button from '@/shared/ui/Button.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'

import type { PhysicalColor } from '../api'
import { rgbToHex } from '../api'

const props = defineProps<{
  open: boolean
  color: PhysicalColor | null
  pending: boolean
}>()

const emit = defineEmits<{
  close: []
  /** create */
  create: [payload: { code: string; name: string; color_family: string | null; brand: string | null; rgb: [number, number, number]; stock_ml: number }]
  /** update（不含 rgb，rgb 走 RgbCalibrationDialog）*/
  update: [payload: { code?: string; name?: string; color_family?: string | null; brand?: string | null; stock_ml?: number }]
}>()

const code = ref('')
const name = ref('')
const family = ref('')
const brand = ref('')
const hex = ref('#000000')
const stockMl = ref('0')
const errors = ref<Record<string, string>>({})

watch(
  [() => props.open, () => props.color],
  () => {
    if (!props.open) return
    const c = props.color
    if (c) {
      code.value = c.code
      name.value = c.name
      family.value = c.color_family ?? ''
      brand.value = c.brand ?? ''
      hex.value = rgbToHex(c.rgb)
      stockMl.value = String(c.stock_ml)
    } else {
      code.value = ''
      name.value = ''
      family.value = ''
      brand.value = ''
      hex.value = '#888888'
      stockMl.value = '0'
    }
    errors.value = {}
  },
  { immediate: true },
)

function validate(): boolean {
  const errs: Record<string, string> = {}
  if (!code.value.trim()) errs.code = '色號必填'
  if (!name.value.trim()) errs.name = '顏色名稱必填'
  if (!props.color && !/^#[0-9a-fA-F]{6}$/.test(hex.value)) errs.hex = 'HEX 格式 #RRGGBB'
  const stock = Number(stockMl.value)
  if (!Number.isFinite(stock) || stock < 0) errs.stock = '庫存必須 ≥ 0'
  errors.value = errs
  return Object.keys(errs).length === 0
}

function submit() {
  if (!validate()) return
  if (props.color) {
    // 編輯（不含 rgb）
    emit('update', {
      code: code.value !== props.color.code ? code.value : undefined,
      name: name.value !== props.color.name ? name.value : undefined,
      color_family: family.value !== (props.color.color_family ?? '') ? family.value || null : undefined,
      brand: brand.value !== (props.color.brand ?? '') ? brand.value || null : undefined,
      stock_ml: Number(stockMl.value) !== props.color.stock_ml ? Number(stockMl.value) : undefined,
    })
  } else {
    // 新增
    const m = hex.value.match(/^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$/)
    if (!m) return
    const rgb: [number, number, number] = [
      parseInt(m[1], 16),
      parseInt(m[2], 16),
      parseInt(m[3], 16),
    ]
    emit('create', {
      code: code.value,
      name: name.value,
      color_family: family.value || null,
      brand: brand.value || null,
      rgb,
      stock_ml: Number(stockMl.value),
    })
  }
}
</script>

<template>
  <Dialog
    :open="open"
    :title="color ? `編輯：${color.code} ${color.name}` : '新增實體色'"
    size="md"
    @close="emit('close')"
  >
    <div class="space-y-4 text-[13px]">
      <div class="grid grid-cols-2 gap-2">
        <div>
          <Label>色號</Label>
          <Input v-model="code" placeholder="201" />
          <p v-if="errors.code" class="mt-1 text-[12px] text-state-danger">{{ errors.code }}</p>
        </div>
        <div>
          <Label>顏色名稱</Label>
          <Input v-model="name" placeholder="SKIN TONE" />
          <p v-if="errors.name" class="mt-1 text-[12px] text-state-danger">{{ errors.name }}</p>
        </div>
        <div>
          <Label>色系（選填）</Label>
          <Input v-model="family" placeholder="膚色系 / 暖棕系 / 中性灰..." />
        </div>
        <div>
          <Label>品牌（選填）</Label>
          <Input v-model="brand" placeholder="例：Liquitex" />
        </div>
      </div>

      <div v-if="!color">
        <Label>RGB（HEX 格式）</Label>
        <div class="flex items-center gap-2">
          <input
            v-model="hex"
            type="color"
            class="w-12 h-9 rounded-[var(--radius-xs)] border border-line-strong cursor-pointer"
          />
          <Input v-model="hex" class="flex-1 font-mono" placeholder="#FF8800" />
        </div>
        <p v-if="errors.hex" class="mt-1 text-[12px] text-state-danger">{{ errors.hex }}</p>
      </div>
      <div v-else>
        <Label>RGB</Label>
        <p class="text-[12px] text-ink-muted">編輯時不可改 RGB — 請走獨立的「校正 RGB」按鈕，會寫入 audit history</p>
      </div>

      <div>
        <Label>庫存（ml）</Label>
        <Input v-model="stockMl" type="number" min="0" />
        <p v-if="errors.stock" class="mt-1 text-[12px] text-state-danger">{{ errors.stock }}</p>
      </div>
    </div>

    <template #footer>
      <Button variant="secondary" :disabled="pending" @click="emit('close')">取消</Button>
      <Button variant="primary" :disabled="pending" @click="submit">{{ color ? '儲存' : '建立' }}</Button>
    </template>
  </Dialog>
</template>
