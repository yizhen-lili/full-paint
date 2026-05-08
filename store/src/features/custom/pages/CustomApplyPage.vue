<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'
import SectionMasthead from '@/shared/components/SectionMasthead.vue'
import CustomApplyForm from '../components/CustomApplyForm.vue'
</script>

<template>
  <main class="page">
    <RouterLink to="/custom" class="back-link">
      <ArrowLeft :size="14" /> 客製化首頁
    </RouterLink>

    <SectionMasthead
      no="04"
      chapter="Apply"
      title="開始申請"
      caption="Bring your photo to canvas"
    />

    <p class="intro">
      上傳一張您喜歡的照片，留下基本偏好，<br />
      我們將在 1–3 個工作天內回覆報價。
    </p>

    <CustomApplyForm />
  </main>
</template>

<style scoped>
.page { max-width: 720px; margin: 0 auto; padding: 32px 24px 96px; }
.back-link {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.18em;
  color: var(--color-ink-muted); text-decoration: none; margin-bottom: 32px;
}
.back-link:hover { color: var(--color-accent-deep); }
.intro {
  font-size: 15px; line-height: 1.85; color: var(--color-ink-default);
  margin: 12px 0 40px;
}
</style>
