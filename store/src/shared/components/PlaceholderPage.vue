<script setup lang="ts">
defineProps<{
  title: string
  hint?: string
  module?: string
}>()
</script>

<template>
  <section class="ph">
    <div class="ph-inner">
      <div v-if="module" class="ph-module">{{ module }}</div>
      <h1 class="ph-title">{{ title }}</h1>
      <p class="ph-hint">{{ hint ?? '建設中，敬請期待' }}</p>
    </div>
  </section>
</template>

<style scoped>
.ph {
  min-height: 50vh;
  max-width: 1440px;
  margin: 0 auto;
  padding: 96px 56px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ph-inner {
  text-align: center;
}

.ph-module {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-accent);
  margin-bottom: 24px;
}

.ph-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 36px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0 0 16px;
}

.ph-hint {
  font-size: 13px;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
  margin: 0;
}

@media (max-width: 767px) {
  .ph { padding: 64px 24px; }
  .ph-title { font-size: 28px; }
}
</style>
