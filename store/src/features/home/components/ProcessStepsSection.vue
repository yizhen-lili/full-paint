<script setup lang="ts">
import { RouterLink } from 'vue-router'

const STEPS = [
  {
    no: '01',
    title: '挑一幅',
    body: '從 4 個主題、N 個系列中選一幅你看了會微笑的畫面。',
    aux: 'choose',
    to: '/products',
    cta: '看看商品',
  },
  {
    no: '02',
    title: '選規格',
    body: '畫布尺寸、難易度、礦物顏料色數 — 三步搞定你的版本。',
    aux: 'customize',
    to: '/size-guide',
    cta: '尺寸指南',
  },
  {
    no: '03',
    title: '開畫',
    body: '畫筆 / 顏料 / 畫布 / 顏色對應表全寄到家。一筆一筆，慢慢來。',
    aux: 'paint',
    to: '/custom-process',
    cta: '訂製流程',
  },
]
</script>

<template>
  <section class="process">
    <div class="inner">
      <header class="head">
        <div class="head-rule">
          <span class="head-no">No. 04</span>
          <span class="head-dot"></span>
          <span class="head-cap">Process</span>
          <span class="head-line"></span>
        </div>
        <h2 class="title">
          開始畫的<em class="em">三步</em>
        </h2>
        <p class="lede">
          沒有訂閱、沒有 app、沒有會員等級。<br />
          一份畫、一個下午、一個自己的時光。
        </p>
      </header>

      <div class="steps">
        <div
          v-for="step in STEPS"
          :key="step.no"
          class="step"
        >
          <span class="step-aux" aria-hidden="true">{{ step.aux }}</span>
          <span class="step-no">{{ step.no }}</span>
          <h3 class="step-title">{{ step.title }}</h3>
          <p class="step-body">{{ step.body }}</p>
          <RouterLink :to="step.to" class="step-link">
            {{ step.cta }} →
          </RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.process {
  padding: 96px 56px 112px;
}

.inner {
  max-width: 1200px;
  margin: 0 auto;
}

.head {
  text-align: center;
  margin-bottom: 80px;
}
.head-rule {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}
.head-no {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--color-fresh);
  font-weight: 500;
}
.head-dot {
  width: 4px; height: 4px;
  border-radius: 50%;
  background: var(--color-accent);
}
.head-cap {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--color-accent);
}
.head-line {
  width: 60px;
  height: 1px;
  background: var(--color-line);
}

.title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 48px;
  line-height: 1.2;
  letter-spacing: 0.08em;
  color: var(--color-ink-strong);
  margin: 0 0 20px;
}
.em {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 0.92em;
  color: var(--color-accent);
  margin: 0 0.04em;
}

.lede {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 15px;
  line-height: 2;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
  margin: 0;
}

.steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 64px;
  position: relative;
}

/* hairline 連接 3 步驟 */
.steps::before {
  content: '';
  position: absolute;
  top: 60px;
  left: 12.5%;
  right: 12.5%;
  height: 1px;
  background: linear-gradient(
    to right,
    transparent,
    var(--color-line) 12%,
    var(--color-line) 88%,
    transparent
  );
  pointer-events: none;
  z-index: 0;
}

.step {
  position: relative;
  text-align: center;
  padding: 0 16px;
  z-index: 1;
}

.step-aux {
  display: block;
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 16px;
  color: var(--color-accent);
  letter-spacing: 0.04em;
  margin-bottom: 4px;
  opacity: 0.7;
}

.step-no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: var(--color-paper-canvas);
  border: 1px solid var(--color-line);
  font-family: var(--font-display);
  font-weight: 300;
  font-size: 48px;
  color: var(--color-ink-strong);
  margin-bottom: 24px;
  letter-spacing: 0;
  position: relative;
}

.step-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 24px;
  letter-spacing: 0.08em;
  color: var(--color-ink-strong);
  margin: 0 0 12px;
  line-height: 1.3;
}

.step-body {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 14px;
  line-height: 1.95;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
  margin: 0 0 18px;
  max-width: 280px;
  margin-left: auto;
  margin-right: auto;
}

.step-link {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
  border-bottom: 1px solid var(--color-accent);
  padding-bottom: 3px;
  transition: color 150ms, border-color 150ms;
}
.step-link:hover {
  color: var(--color-accent-deep);
  border-color: var(--color-accent-deep);
}

@media (max-width: 1023px) {
  .process { padding: 72px 32px 88px; }
  .title { font-size: 36px; }
  .steps { grid-template-columns: 1fr; gap: 48px; }
  .steps::before { display: none; }
}
@media (max-width: 767px) {
  .process { padding: 56px 24px 64px; }
  .title { font-size: 30px; }
  .step-no { width: 80px; height: 80px; font-size: 36px; }
}
</style>
