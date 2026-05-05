<script setup lang="ts">
defineProps<{
  to?: string
}>()
// aria-label 由 caller 透過 attr inheritance 傳入（Vue 自動 pass through 到 root element）
</script>

<template>
  <component
    :is="to ? 'router-link' : 'button'"
    class="icon-btn"
    :to="to"
  >
    <slot />
  </component>
</template>

<style scoped>
.icon-btn {
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-ink-default);
  border-radius: var(--radius-sm);
  transition: background 150ms;
  cursor: pointer;
  position: relative;
  text-decoration: none;
}

.icon-btn:hover {
  background: var(--color-paper-deep);
}

.icon-btn :deep(svg) {
  width: 18px;
  height: 18px;
  stroke-width: 1.5;
  fill: none;
  stroke: currentColor;
}
</style>
