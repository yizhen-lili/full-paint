<script setup lang="ts">
import { RouterView } from 'vue-router'
import SiteLogo from '@/shared/components/SiteLogo.vue'
</script>

<template>
  <div class="auth-layout">
    <header class="auth-header">
      <SiteLogo size="sm" />
    </header>

    <main class="auth-main">
      <div class="auth-card">
        <RouterView />
      </div>
    </main>

    <footer class="auth-footer">
      <span>© 2026 易木 YIIMUI</span>
    </footer>
  </div>
</template>

<style scoped>
.auth-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.auth-header {
  padding: 32px 56px 16px;
  text-align: center;
}

.auth-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px 64px;
}

.auth-card {
  width: 100%;
  max-width: 440px;
  background: var(--color-paper-surface);
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-sm);
  padding: 48px 40px;
}

.auth-footer {
  padding: 24px 56px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}

@media (max-width: 767px) {
  .auth-header { padding: 24px 24px 8px; }
  .auth-card { padding: 32px 24px; }
}
</style>
