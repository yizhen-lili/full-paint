<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import DefaultLayout from '@/shared/layouts/DefaultLayout.vue'
import AuthLayout from '@/shared/layouts/AuthLayout.vue'
import MinimalLayout from '@/shared/layouts/MinimalLayout.vue'

const route = useRoute()

const layoutComponent = computed(() => {
  switch (route.meta.layout) {
    case 'auth':
      return AuthLayout
    case 'minimal':
      return MinimalLayout
    default:
      return DefaultLayout
  }
})
</script>

<template>
  <component :is="layoutComponent" />
</template>
