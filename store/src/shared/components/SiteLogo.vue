<script setup lang="ts">
import { RouterLink } from 'vue-router'

defineProps<{
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'dark'
}>()
</script>

<template>
  <RouterLink to="/" class="logo" :class="[size ?? 'md', variant ?? 'default']">
    <span class="logo-cn">易木 YIIMUI</span>
    <span class="logo-en">Paint by Number Atelier</span>
  </RouterLink>
</template>

<style scoped>
.logo {
  display: inline-block;
  text-align: center;
  text-decoration: none;
  color: inherit;
  line-height: 1.2;
}

.logo-cn {
  display: block;
  font-family: var(--font-cn-serif);
  font-weight: 300;
  letter-spacing: 0.12em;
  color: var(--color-ink-strong);
}

.logo-en {
  display: block;
  font-family: var(--font-display);
  font-weight: 400;
  letter-spacing: 0.4em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin-top: 4px;
}

.sm .logo-cn { font-size: 18px; }
.sm .logo-en { font-size: 8px; letter-spacing: 0.32em; }
.md .logo-cn { font-size: 22px; }
.md .logo-en { font-size: 9px; }
.lg .logo-cn { font-size: 44px; letter-spacing: 0.16em; }
.lg .logo-en { font-size: 12px; letter-spacing: 0.5em; margin-top: 12px; }

.dark .logo-cn { color: var(--color-paper-canvas); }
.dark .logo-en { color: rgba(245, 241, 232, 0.6); }
</style>
