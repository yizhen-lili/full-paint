<script setup lang="ts">
</script>

<template>
  <main class="placeholder">
    <div class="placeholder-inner">
      <div class="eyebrow">2026 春 · 新作上架</div>
      <h1 class="title">易木 YIIMUI</h1>
      <p class="sub">Paint by Number Atelier</p>
      <p class="hint">首頁建設中（S02 — 商品瀏覽 將完整開發）</p>
    </div>
  </main>
</template>

<style scoped>
.placeholder {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 96px 24px;
}

.placeholder-inner {
  text-align: center;
  max-width: 560px;
}

.eyebrow {
  font-family: var(--font-body);
  font-weight: 400;
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-accent);
  margin-bottom: 36px;
}

.title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 60px;
  line-height: 1.4;
  letter-spacing: 0.12em;
  color: var(--color-ink-strong);
  margin: 0;
}

.sub {
  font-family: var(--font-display);
  font-weight: 400;
  font-size: 14px;
  letter-spacing: 0.4em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  margin: 16px 0 48px;
}

.hint {
  font-size: 13px;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
}

@media (max-width: 767px) {
  .title { font-size: 40px; }
  .sub { font-size: 11px; letter-spacing: 0.32em; }
}
</style>
