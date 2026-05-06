<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <section class="split">
    <!-- 左半 dark walnut text panel -->
    <div class="text-panel">
      <div class="text-bg" aria-hidden="true"></div>
      <div class="text-veil" aria-hidden="true"></div>
      <div class="text-inner">
        <div class="eyebrow">
          <span class="eyebrow-no">No. 05</span>
          <span class="eyebrow-rule"></span>
          <span class="eyebrow-tag">Custom</span>
        </div>
        <h2 class="title">
          把<em class="em">最珍惜</em>的<br />
          那張照片，<br />
          變一幅親手畫的畫。
        </h2>
        <p class="desc">
          上傳照片、告訴我們想要的尺寸，我們手工調色、出樣稿給你看。<br />
          確認後再付款開始製作 — 從報價到送到家，平均 14 個工作天。
        </p>
        <RouterLink to="/custom" class="cta">上傳照片開始 →</RouterLink>
      </div>
    </div>

    <!-- 右半 visual block -->
    <div class="visual">
      <div class="visual-tone"></div>
      <span class="visual-cap">— Crafted slowly —</span>
      <span class="visual-letter">易</span>
    </div>
  </section>
</template>

<style scoped>
.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: clamp(440px, 60vh, 600px);
  margin: 96px 0;
}

/* 左半 dark text panel */
.text-panel {
  position: relative;
  overflow: hidden;
}
.text-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.06), transparent 50%),
    linear-gradient(135deg,
      var(--color-accent-deep) 0%,
      #4A3829 70%,
      #3A2D22 130%);
}
.text-veil {
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='g'><feTurbulence type='fractalNoise' baseFrequency='0.7' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1 0 0 0 0 0.95 0 0 0 0 0.85 0 0 0 0.4 0'/></filter><rect width='100%25' height='100%25' filter='url(%23g)'/></svg>");
  opacity: 0.2;
  mix-blend-mode: overlay;
}

.text-inner {
  position: relative;
  z-index: 2;
  height: 100%;
  padding: 72px 64px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  color: var(--color-paper-canvas);
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
}
.eyebrow-no {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--color-fresh-soft);
  font-weight: 500;
}
.eyebrow-rule {
  width: 36px;
  height: 1px;
  background: rgba(236, 227, 210, 0.4);
}
.eyebrow-tag {
  font-family: var(--font-display);
  font-style: italic;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--color-accent-tint);
}

.title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: clamp(36px, 4.5vw, 56px);
  line-height: 1.3;
  letter-spacing: 0.06em;
  margin: 0 0 32px;
  text-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
}
.em {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  color: var(--color-accent-tint);
  margin: 0 0.04em;
}

.desc {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 15px;
  line-height: 2;
  letter-spacing: 0.04em;
  color: rgba(250, 244, 221, 0.85);
  margin: 0 0 40px;
  max-width: 460px;
}

.cta {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  padding: 18px 36px;
  border: 1px solid rgba(250, 244, 221, 0.7);
  color: var(--color-paper-canvas);
  text-decoration: none;
  align-self: flex-start;
  transition: all 200ms;
}
.cta:hover {
  background: var(--color-paper-canvas);
  color: var(--color-ink-strong);
  border-color: var(--color-paper-canvas);
}

/* 右半 visual */
.visual {
  position: relative;
  overflow: hidden;
  background: var(--color-paper-deep);
  display: flex;
  align-items: center;
  justify-content: center;
}
.visual-tone {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 30%, var(--color-paper-surface), transparent 60%),
    linear-gradient(135deg,
      var(--color-paper-deep) 0%,
      var(--color-accent-tint) 50%,
      var(--color-accent-soft) 130%);
}
.visual-cap {
  position: absolute;
  top: 32px;
  right: 32px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-ink-strong);
  opacity: 0.5;
  z-index: 2;
}
.visual-letter {
  position: relative;
  z-index: 1;
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: clamp(160px, 22vw, 280px);
  line-height: 1;
  color: var(--color-ink-strong);
  opacity: 0.08;
  user-select: none;
}

@media (max-width: 1023px) {
  .split {
    grid-template-columns: 1fr;
    margin: 64px 0;
  }
  .text-inner { padding: 56px 32px; }
  .visual { aspect-ratio: 16 / 9; }
}
@media (max-width: 767px) {
  .text-inner { padding: 48px 24px; }
  .title { font-size: 30px; }
  .desc { font-size: 14px; }
}
</style>
