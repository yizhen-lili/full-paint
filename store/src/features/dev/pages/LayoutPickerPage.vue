<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'

type Scheme = 'A' | 'B' | 'C' | 'D'

interface Plan {
  id: Scheme
  title: string
  desc: string
  header: string         // header background
  main: string           // page canvas
  footer: string         // footer background
  footerInk?: string     // optional override of footer text color
  headerNote?: string
}

const PLANS: Plan[] = [
  {
    id: 'A',
    title: '奶油三層',
    desc: '上 → 中 → 下漸深，同色系，最溫和。',
    header: '#FBF7EC',
    main: '#F4EFE2',
    footer: '#F2E8D5',
  },
  {
    id: 'B',
    title: '倒框打光',
    desc: '頭尾深、中間淺；內容區像被打光浮出來。',
    header: '#EAE0CC',
    main: '#FBF7EC',
    footer: '#EAE0CC',
  },
  {
    id: 'C',
    title: '雜誌深色 footer',
    desc: 'footer 變黑色磚塊，像書末版權頁；品牌氣場最重。',
    header: '#FBF7EC',
    main: '#F4EFE2',
    footer: '#2E2823',
    footerInk: '#FAF4DD',
  },
  {
    id: 'D',
    title: '核桃 footer band',
    desc: 'footer 變焦糖核桃色，像書脊／皮革條，品牌色顯著。',
    header: '#FBF7EC',
    main: '#F4EFE2',
    footer: '#8C6E52',
    footerInk: '#FAF4DD',
  },
]

const selected = ref<Scheme>('A')
const plan = computed(() => PLANS.find((p) => p.id === selected.value) ?? PLANS[0])

const STYLE_ID = 'layout-picker-override'

function applyOverride() {
  let el = document.getElementById(STYLE_ID) as HTMLStyleElement | null
  if (!el) {
    el = document.createElement('style')
    el.id = STYLE_ID
    document.head.appendChild(el)
  }
  const p = plan.value
  // 用最高層級的 selector 強制覆蓋 scoped CSS
  const footerInkBlock = p.footerInk
    ? `
      .site-footer * { color: ${p.footerInk} !important; }
      .site-footer a { color: ${p.footerInk} !important; opacity: 0.85; }
      .site-footer a:hover { color: ${p.footerInk} !important; opacity: 1; }
    `
    : ''
  el.textContent = `
    .site-header { background: ${p.header} !important; }
    body, main, .layout-pick-canvas { background: ${p.main} !important; }
    .site-footer { background: ${p.footer} !important; }
    ${footerInkBlock}
  `
}

watch(selected, applyOverride, { immediate: true })

onUnmounted(() => {
  const el = document.getElementById(STYLE_ID)
  if (el) el.remove()
})
</script>

<template>
  <main class="layout-pick-canvas">
    <!-- 浮動切換面板 -->
    <aside class="picker-panel">
      <div class="panel-head">
        <span class="panel-eyebrow">— Layout Bands Preview —</span>
        <h2 class="panel-title">Header / Footer 配色</h2>
        <p class="panel-hint">點選方案即時套用到上方 header 與下方 footer。離開頁面會自動還原。</p>
      </div>

      <ul class="plan-list">
        <li v-for="p in PLANS" :key="p.id">
          <button
            type="button"
            class="plan-card"
            :class="{ 'plan-active': selected === p.id }"
            @click="selected = p.id"
          >
            <div class="plan-head">
              <span class="plan-id">{{ p.id }}</span>
              <span class="plan-title">{{ p.title }}</span>
              <span v-if="selected === p.id" class="plan-current">套用中</span>
            </div>
            <p class="plan-desc">{{ p.desc }}</p>
            <div class="plan-swatches">
              <span class="sw" :style="{ background: p.header }">
                <em>Header</em>
                <code>{{ p.header.toUpperCase() }}</code>
              </span>
              <span class="sw" :style="{ background: p.main }">
                <em>Main</em>
                <code>{{ p.main.toUpperCase() }}</code>
              </span>
              <span class="sw" :style="{ background: p.footer, color: p.footerInk ?? 'inherit' }">
                <em :style="{ color: p.footerInk ?? 'inherit' }">Footer</em>
                <code :style="{ color: p.footerInk ?? 'inherit' }">{{ p.footer.toUpperCase() }}</code>
              </span>
            </div>
          </button>
        </li>
      </ul>

      <div class="panel-foot">
        <p>選好後告訴我「我要 X」，我直接寫進整站樣式檔。</p>
      </div>
    </aside>

    <!-- 假內容讓你看到 main canvas 與 header／footer 的對比 -->
    <section class="demo-block">
      <span class="demo-eyebrow">— Demo Content —</span>
      <h1 class="demo-title">易木 YIIMUI</h1>
      <p class="demo-lede">
        往上滾看 header 配色，往下滾看 footer 配色。中間區塊就是 main canvas。
      </p>
    </section>

    <section class="demo-block alt">
      <h2>產品卡片區的視覺感</h2>
      <p>多放一段內容，讓你看到三層的紙感層次。</p>
    </section>

    <section class="demo-block">
      <h2>第三段，再多看一些</h2>
      <p>滾到最底，footer 出場時對比就會出現。</p>
    </section>
  </main>
</template>

<style scoped>
.layout-pick-canvas {
  min-height: calc(100vh - 200px);
  padding: 56px 56px 96px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 56px;
  max-width: 1440px;
  margin: 0 auto;
}

.demo-block {
  padding: 80px 0;
  border-bottom: 1px solid var(--color-line-subtle);
}
.demo-block.alt { border-bottom: 1px dashed var(--color-line-subtle); }
.demo-eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--color-fresh);
}
.demo-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 56px;
  letter-spacing: 0.08em;
  margin: 16px 0 12px;
  color: var(--color-ink-strong);
}
.demo-lede {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 16px;
  line-height: 2;
  color: var(--color-ink-default);
  letter-spacing: 0.04em;
  max-width: 640px;
}
.demo-block h2 {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 28px;
  letter-spacing: 0.06em;
  margin: 0 0 12px;
  color: var(--color-ink-strong);
}
.demo-block p {
  font-size: 14px;
  line-height: 1.95;
  color: var(--color-ink-default);
}

.picker-panel {
  position: sticky;
  top: 100px;
  align-self: start;
  background: var(--color-paper-surface);
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-sm);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-head {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-bottom: 1px solid var(--color-line-subtle);
  padding-bottom: 14px;
}
.panel-eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--color-fresh);
}
.panel-title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 18px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0;
}
.panel-hint {
  font-size: 11px;
  line-height: 1.7;
  color: var(--color-ink-muted);
  margin: 0;
  letter-spacing: 0.02em;
}

.plan-list {
  list-style: none;
  padding: 0; margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.plan-card {
  width: 100%;
  background: var(--color-paper-canvas);
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-xs);
  padding: 14px 16px;
  cursor: pointer;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 150ms;
  font-family: var(--font-body);
}
.plan-card:hover { border-color: var(--color-accent-soft); }
.plan-active {
  border-color: var(--color-accent) !important;
  box-shadow: inset 0 0 0 1px var(--color-accent);
}
.plan-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.plan-id {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  color: var(--color-paper-canvas);
  background: var(--color-ink-strong);
  padding: 2px 8px;
  border-radius: var(--radius-xs);
}
.plan-title {
  font-family: var(--font-cn-serif);
  font-size: 15px;
  color: var(--color-ink-strong);
  letter-spacing: 0.04em;
  flex: 1;
}
.plan-current {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--color-fresh);
  border: 1px solid var(--color-fresh);
  padding: 1px 6px;
  border-radius: var(--radius-xs);
}
.plan-desc {
  font-size: 12px;
  line-height: 1.7;
  color: var(--color-ink-muted);
  margin: 0;
  letter-spacing: 0.02em;
}
.plan-swatches {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 6px;
  margin-top: 4px;
}
.sw {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-end;
  gap: 2px;
  border: 1px solid var(--color-line-subtle);
  border-radius: var(--radius-xs);
  padding: 18px 8px 6px;
  min-height: 56px;
}
.sw em {
  font-style: normal;
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}
.sw code {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.04em;
  color: var(--color-ink-strong);
}

.panel-foot {
  border-top: 1px solid var(--color-line-subtle);
  padding-top: 12px;
}
.panel-foot p {
  font-size: 11px;
  line-height: 1.7;
  color: var(--color-ink-muted);
  margin: 0;
  letter-spacing: 0.02em;
}

@media (max-width: 1023px) {
  .layout-pick-canvas {
    grid-template-columns: 1fr;
    padding: 40px 24px 64px;
  }
  .picker-panel { position: static; }
  .demo-title { font-size: 40px; }
}
</style>
