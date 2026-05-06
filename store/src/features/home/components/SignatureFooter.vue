<script setup lang="ts">
// 純 typography 簽名段，HomePage 結尾的呼吸區
</script>

<template>
  <section class="sign">
    <div class="rule"></div>
    <div class="block">
      <div class="brand-en">YIIMUI</div>
      <div class="brand-cn">易木</div>
      <div class="motto">
        <em class="motto-em">crafted slowly</em>
        <span class="motto-dot"></span>
        <span>2026 Spring · Paint by Number Atelier</span>
      </div>
    </div>
    <div class="rule"></div>
  </section>
</template>

<style scoped>
.sign {
  padding: 80px 56px 56px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 36px;
}

.rule {
  width: 80px;
  height: 1px;
  background: var(--color-line);
}

.block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.brand-en {
  font-family: var(--font-display);
  font-weight: 300;
  font-size: 56px;
  letter-spacing: 0.18em;
  color: var(--color-ink-strong);
  line-height: 1;
}
.brand-cn {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 18px;
  letter-spacing: 0.4em;
  color: var(--color-accent);
  margin-top: 8px;
  padding-left: 0.4em;
}

.motto {
  margin-top: 18px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}
.motto-em {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 14px;
  color: var(--color-fresh);
  text-transform: none;
  letter-spacing: 0.04em;
}
.motto-dot {
  width: 3px; height: 3px;
  border-radius: 50%;
  background: var(--color-accent);
}

@media (max-width: 767px) {
  .sign { padding: 56px 24px 32px; gap: 28px; }
  .brand-en { font-size: 40px; }
  .brand-cn { font-size: 14px; }
}
</style>
