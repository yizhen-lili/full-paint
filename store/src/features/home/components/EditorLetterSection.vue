<script setup lang="ts">
// 安靜的編輯誌引言段 — Hero 之後的呼吸區
</script>

<template>
  <section class="letter">
    <div class="inner">
      <div class="rule-row">
        <span class="rule"></span>
        <span class="cap">— Editor's Letter —</span>
        <span class="rule"></span>
      </div>

      <h2 class="words">
        慢慢畫，<br />
        是<em class="em">另一種</em>速度。
      </h2>

      <p class="body">
        在能滑動三千個短影片的夜晚，
        我們選擇坐在桌前，把一張白布慢慢染成自己的風景。
        每一筆都是一個小決定，
        每一格顏色都是一段獨處時光。
      </p>

      <div class="signature">
        <span class="sig-line">— Yiimui Atelier</span>
        <span class="sig-date">2026 / Spring</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.letter {
  padding: 96px 56px 112px;
}

.inner {
  max-width: 640px;
  margin: 0 auto;
  text-align: center;
}

.rule-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-bottom: 36px;
}
.rule {
  flex: 0 1 80px;
  height: 1px;
  background: var(--color-line);
}
.cap {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-fresh);
  white-space: nowrap;
}

.words {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 44px;
  line-height: 1.4;
  letter-spacing: 0.08em;
  color: var(--color-ink-strong);
  margin: 0 0 36px;
}
.em {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 0.88em;
  color: var(--color-accent);
  margin: 0 0.06em;
}

.body {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 16px;
  line-height: 2.1;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
  margin: 0 0 40px;
}

.signature {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-family: var(--font-display);
}
.sig-line {
  font-style: italic;
  font-weight: 300;
  font-size: 18px;
  color: var(--color-accent-deep);
  letter-spacing: 0.04em;
}
.sig-date {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  font-style: normal;
}

@media (max-width: 767px) {
  .letter { padding: 64px 24px 80px; }
  .words { font-size: 30px; }
  .body { font-size: 15px; }
}
</style>
