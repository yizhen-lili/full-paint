<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  Plus, Pencil, Trash2, Eye, EyeOff, Loader2, Sparkles,
  Upload, X, Wand2, Camera,
} from 'lucide-vue-next'
import { useQuery } from '@tanstack/vue-query'

import Button from '@/shared/ui/Button.vue'
import Dialog from '@/shared/ui/Dialog.vue'
import Input from '@/shared/ui/Input.vue'
import Label from '@/shared/ui/Label.vue'
import Select from '@/shared/ui/Select.vue'
import Textarea from '@/shared/ui/Textarea.vue'
import AppDataTable, { type Column } from '@/shared/components/AppDataTable.vue'

import {
  useCaseCategoriesQuery,
  useCreateCaseMutation,
  useCustomCasesQuery,
  useDeleteCaseMutation,
  useToggleCasePublishMutation,
  useUpdateCaseMutation,
} from '../queries'
import {
  DIFFICULTY_LABEL,
  uploadCaseImage,
  listAvailableJobsForCase,
  type CustomCase,
  type Difficulty,
  type AvailableJob,
} from '../api'

const { data, isLoading } = useCustomCasesQuery()
const { data: categoriesData } = useCaseCategoriesQuery()
const createMut = useCreateCaseMutation()
const updateMut = useUpdateCaseMutation()
const toggleMut = useToggleCasePublishMutation()
const deleteMut = useDeleteCaseMutation()

const items = computed(() => data.value?.items ?? [])

const dialogOpen = ref(false)
const editing = ref<CustomCase | null>(null)
const apiError = ref<string | null>(null)

// form fields
const fImageUrl = ref('')
const fTitle = ref('')
const fDescription = ref('')
const fCategoryId = ref<string>('')
const fCanvasW = ref('')
const fCanvasH = ref('')
const fDifficulty = ref<string>('')
const fIsPublished = ref(false)

// 圖片上傳狀態
const fileInput = ref<HTMLInputElement | null>(null)
const isUploading = ref(false)
const uploadError = ref<string | null>(null)

// 從 production_job 帶入 dialog
const jobPickerOpen = ref(false)
const jobsQuery = useQuery({
  queryKey: ['available-jobs-for-case'] as const,
  queryFn: listAvailableJobsForCase,
  enabled: jobPickerOpen,
  staleTime: 30 * 1000,
})
const jobs = computed<AvailableJob[]>(() =>
  (jobsQuery.data.value?.items ?? []).filter((j) => j.preview_url && j.cover_url),
)
const selectedJobId = ref<string | null>(null)

function triggerFile() {
  fileInput.value?.click()
}

async function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (file.size > 20 * 1024 * 1024) {
    uploadError.value = '檔案超過 20MB'
    return
  }
  if (file.type !== 'image/jpeg' && file.type !== 'image/png') {
    uploadError.value = '只接受 JPEG / PNG'
    return
  }
  uploadError.value = null
  isUploading.value = true
  try {
    fImageUrl.value = await uploadCaseImage(file)
  } catch (err) {
    uploadError.value = (err as { message?: string }).message || '上傳失敗'
  } finally {
    isUploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

function clearImage() {
  fImageUrl.value = ''
  uploadError.value = null
}

function openJobPicker() {
  selectedJobId.value = null
  jobPickerOpen.value = true
}

function pickJob() {
  const job = jobs.value.find((j) => j.id === selectedJobId.value)
  if (!job) return
  // 自動帶入：cover URL + canvas + difficulty
  if (job.cover_url) fImageUrl.value = job.cover_url
  fCanvasW.value = String(job.canvas_w_cm)
  fCanvasH.value = String(job.canvas_h_cm)
  fDifficulty.value = job.difficulty
  jobPickerOpen.value = false
}

watch(
  [() => dialogOpen.value, () => editing.value],
  () => {
    if (dialogOpen.value) {
      const e = editing.value
      fImageUrl.value = e?.image_url ?? ''
      fTitle.value = e?.title ?? ''
      fDescription.value = e?.description ?? ''
      fCategoryId.value = e?.category_id ?? ''
      fCanvasW.value = e?.canvas_w_cm ? String(e.canvas_w_cm) : ''
      fCanvasH.value = e?.canvas_h_cm ? String(e.canvas_h_cm) : ''
      fDifficulty.value = e?.difficulty ?? ''
      fIsPublished.value = e?.is_published ?? false
      apiError.value = null
    }
  },
)

const categoryOptions = computed(() => [
  { value: '', label: '— 未分類 —' },
  ...(categoriesData.value?.items ?? []).map((c) => ({ value: c.id, label: c.name })),
])

const difficultyOptions = [
  { value: '', label: '— 未指定 —' },
  { value: 'beginner', label: DIFFICULTY_LABEL.beginner },
  { value: 'elementary', label: DIFFICULTY_LABEL.elementary },
  { value: 'intermediate', label: DIFFICULTY_LABEL.intermediate },
  { value: 'advanced', label: DIFFICULTY_LABEL.advanced },
]

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(c: CustomCase) {
  editing.value = c
  dialogOpen.value = true
}

async function submit() {
  apiError.value = null
  if (!fImageUrl.value || !fTitle.value) {
    apiError.value = '圖片 URL 與標題為必填'
    return
  }
  const payload = {
    image_url: fImageUrl.value,
    title: fTitle.value,
    description: fDescription.value || null,
    category_id: fCategoryId.value || null,
    canvas_w_cm: fCanvasW.value ? Number(fCanvasW.value) : null,
    canvas_h_cm: fCanvasH.value ? Number(fCanvasH.value) : null,
    difficulty: (fDifficulty.value || null) as Difficulty | null,
    is_published: fIsPublished.value,
  }
  try {
    if (editing.value) {
      await updateMut.mutateAsync({ id: editing.value.id, payload })
    } else {
      await createMut.mutateAsync(payload)
    }
    dialogOpen.value = false
  } catch (e) {
    apiError.value = (e as { message?: string }).message || '儲存失敗'
  }
}

async function togglePublish(c: CustomCase) {
  try {
    await toggleMut.mutateAsync(c.id)
  } catch (e) {
    alert((e as { message?: string }).message || '切換失敗')
  }
}

async function remove(c: CustomCase) {
  if (!confirm(`刪除「${c.title}」？此操作無法復原。`)) return
  try {
    await deleteMut.mutateAsync(c.id)
  } catch (e) {
    alert((e as { message?: string }).message || '刪除失敗')
  }
}

const columns: Column<CustomCase>[] = [
  { key: 'image', label: '預覽', width: '64px' },
  { key: 'title', label: '標題' },
  { key: 'category', label: '分類', width: '110px' },
  { key: 'spec', label: '規格', width: '160px' },
  { key: 'published', label: '上架', width: '80px', align: 'center' },
  { key: 'actions', label: '', width: '120px', align: 'right' },
]

const categoryById = computed(() => {
  const m: Record<string, string> = {}
  for (const c of categoriesData.value?.items ?? []) m[c.id] = c.name
  return m
})
</script>

<template>
  <div class="flex items-center justify-end mb-3">
    <Button variant="primary" @click="openCreate">
      <Plus :size="14" :stroke-width="1.75" />
      新增案例
    </Button>
  </div>

  <AppDataTable
    :columns="columns"
    :rows="items"
    :loading="isLoading"
    :row-key="(r) => r.id"
    empty-text="尚無案例"
    :empty-icon="Sparkles"
  >
    <template #cell-image="{ row }">
      <img
        v-if="row.image_url"
        :src="row.image_url"
        alt=""
        class="w-12 h-12 object-cover rounded-[var(--radius-xs)] border border-line-hairline"
      />
    </template>
    <template #cell-title="{ row }">
      <span class="font-medium text-ink-strong">{{ row.title }}</span>
    </template>
    <template #cell-category="{ row }">
      <span class="text-[12px] text-ink-default">
        {{ row.category_id ? categoryById[row.category_id] || '—' : '未分類' }}
      </span>
    </template>
    <template #cell-spec="{ row }">
      <span class="text-[12px] text-ink-muted">
        <span v-if="row.canvas_w_cm">{{ row.canvas_w_cm }}×{{ row.canvas_h_cm }} cm</span>
        <span v-if="row.difficulty"> · {{ DIFFICULTY_LABEL[row.difficulty as Difficulty] }}</span>
      </span>
    </template>
    <template #cell-published="{ row }">
      <button
        type="button"
        class="inline-flex items-center px-2 h-[20px] text-[11px] rounded-[var(--radius-xs)]"
        :class="
          row.is_published
            ? 'bg-[var(--color-state-success)]/[0.10] text-state-success'
            : 'bg-paper-subtle text-ink-muted'
        "
        @click="togglePublish(row)"
      >
        <Eye v-if="row.is_published" :size="11" :stroke-width="1.5" class="mr-1" />
        <EyeOff v-else :size="11" :stroke-width="1.5" class="mr-1" />
        {{ row.is_published ? '上架中' : '下架' }}
      </button>
    </template>
    <template #cell-actions="{ row }">
      <div class="flex items-center justify-end gap-1">
        <button
          type="button"
          class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:text-ink-strong hover:bg-paper-subtle"
          @click="openEdit(row)"
        >
          <Pencil :size="14" :stroke-width="1.5" />
        </button>
        <button
          type="button"
          class="h-8 w-8 inline-flex items-center justify-center rounded-[var(--radius-xs)] text-ink-muted hover:text-state-danger hover:bg-[var(--color-state-danger)]/[0.10]"
          @click="remove(row)"
        >
          <Trash2 :size="14" :stroke-width="1.5" />
        </button>
      </div>
    </template>
  </AppDataTable>

  <Dialog
    :open="dialogOpen"
    :title="editing ? '編輯案例' : '新增案例'"
    size="lg"
    @close="dialogOpen = false"
  >
    <div class="space-y-4 text-[13px]">
      <p
        v-if="apiError"
        class="px-3 py-2 border border-state-danger/40 bg-[var(--color-state-danger)]/[0.06] text-state-danger text-[12px] rounded-[var(--radius-xs)]"
      >{{ apiError }}</p>

      <div>
        <Label>成品圖</Label>
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png"
          class="hidden"
          @change="onFileChange"
        />
        <!-- empty state -->
        <div
          v-if="!fImageUrl && !isUploading"
          class="w-full aspect-[4/3] flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-[var(--radius-sm)] bg-paper-surface text-ink-muted border-line-strong"
        >
          <Camera :size="28" :stroke-width="1.25" class="text-aux-rice-mid" />
          <p class="text-[13px]">JPEG / PNG，≤ 20MB</p>
          <div class="flex items-center gap-2 flex-wrap justify-center">
            <button
              type="button"
              class="h-9 px-3 inline-flex items-center gap-1.5 rounded-[var(--radius-xs)] border border-line-strong text-[13px] text-ink-default hover:bg-paper-subtle transition-colors"
              @click="triggerFile"
            >
              <Upload :size="14" :stroke-width="1.5" />
              上傳新圖
            </button>
            <button
              type="button"
              class="h-9 px-3 inline-flex items-center gap-1.5 rounded-[var(--radius-xs)] border border-line-strong text-[13px] text-ink-default hover:bg-paper-subtle transition-colors"
              @click="openJobPicker"
            >
              <Wand2 :size="14" :stroke-width="1.5" />
              從製作任務帶入（含規格）
            </button>
          </div>
        </div>
        <!-- uploading -->
        <div
          v-else-if="isUploading"
          class="w-full aspect-[4/3] flex items-center justify-center gap-2 border border-line-hairline rounded-[var(--radius-sm)] bg-paper-subtle"
        >
          <Loader2 :size="18" :stroke-width="1.5" class="animate-spin text-ink-muted" />
          <span class="text-[13px] text-ink-muted">上傳中…</span>
        </div>
        <!-- preview -->
        <div
          v-else
          class="relative w-full aspect-[4/3] rounded-[var(--radius-sm)] overflow-hidden border border-line-hairline"
        >
          <img :src="fImageUrl" alt="案例圖" class="w-full h-full object-cover" />
          <button
            type="button"
            class="absolute top-2 right-2 h-7 w-7 inline-flex items-center justify-center rounded-full bg-white/90 text-ink-strong shadow-sm hover:bg-white"
            @click="clearImage"
          >
            <X :size="14" />
          </button>
          <div class="absolute bottom-2 right-2 flex gap-1.5">
            <button
              type="button"
              class="h-8 px-3 inline-flex items-center gap-1.5 rounded-[var(--radius-xs)] bg-white/95 border border-line text-[12px] text-ink-strong"
              @click="triggerFile"
            >
              <Upload :size="12" :stroke-width="1.5" />
              重新上傳
            </button>
            <button
              type="button"
              class="h-8 px-3 inline-flex items-center gap-1.5 rounded-[var(--radius-xs)] bg-white/95 border border-line text-[12px] text-ink-strong"
              @click="openJobPicker"
            >
              <Wand2 :size="12" :stroke-width="1.5" />
              從 job 帶入
            </button>
          </div>
        </div>
        <p v-if="uploadError" class="text-[12px] text-state-danger mt-1">{{ uploadError }}</p>
      </div>
      <div>
        <Label>標題</Label>
        <Input v-model="fTitle" />
      </div>
      <div>
        <Label>說明（選填）</Label>
        <Textarea v-model="fDescription" :rows="3" />
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div>
          <Label>分類</Label>
          <Select v-model="fCategoryId" :options="categoryOptions" />
        </div>
        <div>
          <Label>難易度</Label>
          <Select v-model="fDifficulty" :options="difficultyOptions" />
        </div>
        <div>
          <Label>畫布寬（cm，選填）</Label>
          <Input v-model="fCanvasW" type="number" min="1" />
        </div>
        <div>
          <Label>畫布高（cm，選填）</Label>
          <Input v-model="fCanvasH" type="number" min="1" />
        </div>
      </div>
      <label class="flex items-center gap-2">
        <input v-model="fIsPublished" type="checkbox" />
        <span class="text-ink-strong">立即上架（前台公開顯示）</span>
      </label>
    </div>
    <template #footer>
      <Button
        variant="secondary"
        :disabled="createMut.isPending.value || updateMut.isPending.value"
        @click="dialogOpen = false"
      >取消</Button>
      <Button
        variant="primary"
        :disabled="createMut.isPending.value || updateMut.isPending.value"
        @click="submit"
      >
        <Loader2
          v-if="createMut.isPending.value || updateMut.isPending.value"
          :size="14" :stroke-width="1.5" class="animate-spin"
        />
        {{ editing ? '儲存' : '建立' }}
      </Button>
    </template>
  </Dialog>

  <!-- 從 production_job 帶入 -->
  <Dialog
    :open="jobPickerOpen"
    title="從製作任務帶入規格 + 封面"
    size="lg"
    @close="jobPickerOpen = false"
  >
    <div class="space-y-3">
      <p class="text-[12px] text-ink-muted">
        選一筆已完成的 production_job，自動帶入畫布尺寸、難度，並用該 job 產出圖當案例封面。
      </p>
      <div v-if="jobsQuery.isPending.value" class="py-12 text-center text-ink-muted text-[13px]">
        <Loader2 :size="16" class="inline-block animate-spin mr-1" /> 載入中…
      </div>
      <div v-else-if="jobs.length === 0" class="py-12 text-center text-ink-muted text-[13px]">
        目前沒有可選的 job（需 approved + 有產出圖）
      </div>
      <ul v-else class="grid grid-cols-3 gap-3 max-h-[480px] overflow-y-auto">
        <li
          v-for="j in jobs"
          :key="j.id"
          class="border rounded-[var(--radius-sm)] overflow-hidden cursor-pointer transition-colors"
          :class="selectedJobId === j.id ? 'border-accent-deep' : 'border-line-hairline hover:border-line'"
          @click="selectedJobId = j.id"
        >
          <div class="aspect-[4/3] bg-paper-subtle">
            <img v-if="j.preview_url" :src="j.preview_url" :alt="`job ${j.id}`" class="w-full h-full object-cover" />
          </div>
          <div class="p-2 text-[11px]">
            <div class="text-ink-strong">{{ j.canvas_w_cm }}×{{ j.canvas_h_cm }} cm</div>
            <div class="text-ink-muted">
              {{ DIFFICULTY_LABEL[j.difficulty as Difficulty] }} · {{ j.num_colors_used }} 色
            </div>
          </div>
        </li>
      </ul>
    </div>
    <template #footer>
      <Button variant="secondary" @click="jobPickerOpen = false">取消</Button>
      <Button variant="primary" :disabled="!selectedJobId" @click="pickJob">
        套用此 job
      </Button>
    </template>
  </Dialog>
</template>
