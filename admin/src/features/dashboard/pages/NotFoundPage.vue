<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <main class="grid min-h-screen place-items-center bg-neutral-50">
    <section class="space-y-2 text-center">
      <p class="text-xs uppercase tracking-[0.3em] text-neutral-500">404</p>
      <h1 class="text-2xl font-semibold text-neutral-900">頁面不存在</h1>
      <RouterLink to="/dashboard" class="text-sm text-neutral-600 underline">
        回首頁
      </RouterLink>
    </section>
  </main>
</template>
