<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useProductsQuery } from '@/features/products/queries'

const heroProductQuery = useProductsQuery({ sort: 'latest', page: 1, page_size: 1 })
</script>

<template>
  <section class="hero">
    <!-- 左側裝飾條：垂直 ISSUE 戳印（雜誌封面感） -->
    <aside class="hero-stamp" aria-hidden="true">
      <span class="stamp-issue">Issue 01</span>
      <span class="stamp-rule"></span>
      <span class="stamp-date">Spring · 2026</span>
    </aside>

    <div class="hero-grid">
      <div class="hero-text">
        <div class="hero-eyebrow">
          <span class="eyebrow-no">No. 01</span>
          <span class="eyebrow-rule"></span>
          <span class="eyebrow-tag">Editor's Letter</span>
        </div>

        <h1 class="hero-title">
          <span class="title-line">慢慢</span>
          <span class="title-line">
            畫一幅<em class="title-em">,</em>
          </span>
          <span class="title-line title-line-shift">
            屬於自己的<em class="title-italic">時光</em>。
          </span>
        </h1>

        <p class="hero-sub">
          親手畫的療癒，從一個下午開始。<br />
          壓克力顏料・畫筆・畫布全寄到家 — 一筆一筆，沒有快進鍵。
        </p>

        <div class="hero-actions">
          <RouterLink to="/products" class="btn btn-primary">立即選購</RouterLink>
          <RouterLink to="/custom" class="btn btn-link">用照片客製 →</RouterLink>
        </div>
      </div>

      <div class="hero-visual">
        <span class="visual-cap" aria-hidden="true">— Cover Story —</span>
        <div class="visual-frame">
          <img
            v-if="heroProductQuery.data.value?.items[0]?.cover_image_url"
            :src="heroProductQuery.data.value.items[0].cover_image_url"
            :alt="heroProductQuery.data.value.items[0].title"
          />
          <div v-else class="visual-placeholder">
            <span class="placeholder-letter">易</span>
          </div>
        </div>
        <span class="visual-credit" aria-hidden="true">
          Yiimui Atelier <em>·</em> 慢工製作
        </span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  max-width: 1440px;
  margin: 0 auto;
  padding: 88px 56px 112px;
}

/* 左側垂直 stamp — 雜誌封面風 */
.hero-stamp {
  position: absolute;
  left: 24px;
  top: 120px;
  bottom: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.36em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  pointer-events: none;
}
.stamp-issue { color: var(--color-fresh); font-weight: 500; }
.stamp-rule {
  display: block;
  width: 1px;
  flex: 1;
  background: linear-gradient(
    to bottom,
    transparent,
    var(--color-line),
    transparent
  );
}
.stamp-date { color: var(--color-accent); }

.hero-grid {
  display: grid;
  grid-template-columns: 1fr 0.95fr;
  gap: 88px;
  align-items: end;
}

.hero-text {
  display: flex;
  flex-direction: column;
  padding-top: 24px;
}

/* eyebrow：No. + rule + Editor's Letter（雜誌目次風） */
.hero-eyebrow {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 32px;
}
.eyebrow-no {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--color-fresh);
  font-weight: 500;
}
.eyebrow-rule {
  width: 36px;
  height: 1px;
  background: var(--color-line);
}
.eyebrow-tag {
  font-family: var(--font-display);
  font-style: italic;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--color-accent);
}

/* Title：分行 + 斷行錯位 + italic em，雜誌標題版式 */
.hero-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 72px;
  line-height: 1.1;
  letter-spacing: 0.04em;
  color: var(--color-ink-strong);
  margin: 0 0 44px;
}
.title-line {
  display: block;
}
.title-line-shift {
  margin-left: 0.6em;
  margin-top: 0.08em;
}
.title-em {
  display: inline-block;
  margin-left: 0.04em;
  color: var(--color-accent);
  font-style: normal;
}
.title-italic {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 0.88em;
  letter-spacing: 0.02em;
  color: var(--color-accent-deep);
  margin: 0 0.04em;
  display: inline-block;
  transform: translateY(-2px);
}

.hero-sub {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 15px;
  line-height: 2.1;
  color: var(--color-ink-default);
  margin: 0 0 44px;
  max-width: 460px;
  letter-spacing: 0.04em;
  position: relative;
  padding-left: 18px;
}
.hero-sub::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 2px;
  background: var(--color-line-subtle);
}

.hero-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.btn {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  padding: 16px 32px;
  border: 1px solid;
  background: transparent;
  text-decoration: none;
  display: inline-block;
  transition: all 200ms;
}
.btn-primary {
  background: var(--color-ink-strong);
  color: var(--color-paper-canvas);
  border-color: var(--color-ink-strong);
}
.btn-primary:hover {
  background: var(--color-accent-deep);
  border-color: var(--color-accent-deep);
}
.btn-link {
  border: none;
  padding: 16px 4px;
  color: var(--color-accent);
  letter-spacing: 0.24em;
}
.btn-link:hover {
  color: var(--color-accent-deep);
}

/* 右側 visual：上下 caption + 中間 frame，雜誌 cover story 樣式 */
.hero-visual {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.visual-cap {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
  align-self: flex-end;
}
.visual-frame {
  aspect-ratio: 4 / 5;
  overflow: hidden;
  background: var(--color-paper-deep);
  border: 1px solid var(--color-line-subtle);
  position: relative;
}
.visual-frame::after {
  content: '';
  position: absolute;
  inset: 8px;
  border: 1px solid rgba(247, 241, 227, 0.4);
  pointer-events: none;
}
.visual-frame img {
  width: 100%; height: 100%;
  object-fit: cover;
  filter: sepia(0.04) saturate(0.95);
}
.visual-placeholder {
  width: 100%; height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4), transparent 50%),
    linear-gradient(135deg, var(--color-paper-surface) 0%, var(--color-accent-tint) 60%, var(--color-accent-soft) 130%);
}
.placeholder-letter {
  font-family: var(--font-display);
  font-weight: 300;
  font-size: 220px;
  line-height: 1;
  color: var(--color-ink-strong);
  opacity: 0.06;
  letter-spacing: 0;
}
.visual-credit {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--color-ink-muted);
  align-self: flex-start;
}
.visual-credit em {
  font-style: normal;
  color: var(--color-accent);
  margin: 0 4px;
}

@media (max-width: 1279px) {
  .hero-title { font-size: 60px; }
  .hero-stamp { left: 16px; top: 96px; bottom: 96px; }
}
@media (max-width: 1023px) {
  .hero {
    padding: 64px 32px 80px;
  }
  .hero-stamp { display: none; }
  .hero-grid { gap: 48px; }
  .hero-title { font-size: 48px; }
}
@media (max-width: 767px) {
  .hero {
    padding: 48px 24px 64px;
  }
  .hero-grid { grid-template-columns: 1fr; gap: 40px; }
  .hero-title { font-size: 36px; line-height: 1.18; }
  .hero-sub { font-size: 14px; }
  .placeholder-letter { font-size: 140px; }
}
</style>
