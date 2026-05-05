<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { PackageX } from 'lucide-vue-next'
</script>

<template>
  <section class="nf">
    <div class="nf-inner">
      <PackageX class="nf-icon" />
      <h1 class="nf-title">找不到這頁</h1>
      <p class="nf-hint">這個網址沒有對應內容，可能是連結失效或誤輸。</p>
      <RouterLink to="/" class="nf-cta">回首頁</RouterLink>
    </div>
  </section>
</template>

<style scoped>
.nf {
  min-height: 60vh;
  max-width: 1440px;
  margin: 0 auto;
  padding: 96px 56px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nf-inner {
  text-align: center;
  max-width: 480px;
}

.nf-icon {
  width: 32px;
  height: 32px;
  stroke: var(--color-ink-muted);
  stroke-width: 1.5;
  fill: none;
  margin-bottom: 24px;
}

.nf-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 36px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0 0 16px;
}

.nf-hint {
  font-size: 14px;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
  margin: 0 0 32px;
  line-height: 1.85;
}

.nf-cta {
  display: inline-block;
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  padding: 13px 28px;
  border: 1px solid var(--color-ink-strong);
  color: var(--color-ink-strong);
  text-decoration: none;
  border-radius: var(--radius-sm);
  transition: background 200ms;
}
.nf-cta:hover { background: var(--color-paper-deep); }

@media (max-width: 767px) {
  .nf { padding: 64px 24px; }
  .nf-title { font-size: 28px; }
}
</style>
