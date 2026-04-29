<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import PageHeader from '@/shared/components/PageHeader.vue'

import ContentTabs from '../components/ContentTabs.vue'
import StaticPagesTab from '../components/StaticPagesTab.vue'
import SystemSettingsTab from '../components/SystemSettingsTab.vue'
import PhotoPricesTab from '../components/PhotoPricesTab.vue'
import PhotoSurchargesTab from '../components/PhotoSurchargesTab.vue'
import CustomCasesTab from '../components/CustomCasesTab.vue'
import CaseCategoriesTab from '../components/CaseCategoriesTab.vue'

const route = useRoute()
const tab = computed(() => {
  const t = route.query.tab
  if (typeof t === 'string') return t
  return 'pages'
})
</script>

<template>
  <PageHeader title="內容管理" subtitle="靜態頁面 / 系統設定 / 客製定價 / 案例維護" />
  <ContentTabs />

  <StaticPagesTab v-if="tab === 'pages'" />
  <SystemSettingsTab v-else-if="tab === 'settings'" />
  <PhotoPricesTab v-else-if="tab === 'prices'" />
  <PhotoSurchargesTab v-else-if="tab === 'surcharges'" />
  <CustomCasesTab v-else-if="tab === 'cases'" />
  <CaseCategoriesTab v-else-if="tab === 'categories'" />
</template>
