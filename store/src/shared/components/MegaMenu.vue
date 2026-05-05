<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  label: string
  to?: string
}>()

const open = ref(false)
let closeTimer: ReturnType<typeof setTimeout> | null = null

function show() {
  if (closeTimer) {
    clearTimeout(closeTimer)
    closeTimer = null
  }
  open.value = true
}

function scheduleClose() {
  closeTimer = setTimeout(() => {
    open.value = false
  }, 120)
}
</script>

<template>
  <div class="mega" @mouseenter="show" @mouseleave="scheduleClose">
    <RouterLink :to="to ?? '#'" class="mega-trigger">
      {{ label }}
    </RouterLink>
    <Transition name="mega-fade">
      <div v-if="open" class="mega-panel" @mouseenter="show" @mouseleave="scheduleClose">
        <slot />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.mega {
  position: relative;
  display: inline-block;
}

.mega-trigger {
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-default);
  text-decoration: none;
  padding: 8px 0;
  display: inline-block;
  transition: color 150ms;
}

.mega-trigger:hover {
  color: var(--color-accent);
}

.mega-panel {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 8px;
  background: var(--color-paper-surface);
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-sm);
  padding: 24px;
  min-width: 480px;
  max-width: calc(100vw - 32px);
  box-shadow: 0 8px 32px rgba(46, 40, 35, 0.06);
  z-index: 60;
}

.mega-fade-enter-active,
.mega-fade-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}
.mega-fade-enter-from,
.mega-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
