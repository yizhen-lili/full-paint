<script setup lang="ts">
defineProps<{
  /** 章節編號 e.g. "01" / "02" */
  no: string
  /** 英文 chapter 標籤 e.g. "Featured" */
  chapter: string
  /** 中文標題 e.g. "最新上架" */
  title: string
  /** 右側的 link text + path（可選） */
  linkText?: string
  linkTo?: string
  /** 副標 italic 描述（可選） */
  caption?: string
}>()
</script>

<template>
  <header class="masthead">
    <div class="left">
      <div class="rule-row">
        <span class="no">No. {{ no }}</span>
        <span class="dot"></span>
        <span class="chapter">{{ chapter }}</span>
        <span class="line"></span>
      </div>
      <h2 class="title">
        {{ title }}
        <em v-if="caption" class="caption">{{ caption }}</em>
      </h2>
    </div>
    <RouterLink v-if="linkText && linkTo" :to="linkTo" class="more">
      {{ linkText }}
    </RouterLink>
  </header>
</template>

<style scoped>
.masthead {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 36px;
  padding-bottom: 4px;
  flex-wrap: wrap;
}

.left { min-width: 0; flex: 1; }

.rule-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.no {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  color: var(--color-fresh);
  font-weight: 500;
}

.dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-accent);
}

.chapter {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 14px;
  letter-spacing: 0.04em;
  color: var(--color-accent);
}

.line {
  flex: 1;
  height: 1px;
  background: linear-gradient(
    to right,
    var(--color-line),
    transparent 80%
  );
  min-width: 40px;
  margin-left: 4px;
}

.title {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 30px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0;
  line-height: 1.3;
}

.caption {
  font-family: var(--font-display);
  font-style: italic;
  font-weight: 300;
  font-size: 16px;
  letter-spacing: 0.04em;
  color: var(--color-accent);
  margin-left: 12px;
  font-feature-settings: 'liga' 1;
}

.more {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  padding-bottom: 4px;
  transition: color 150ms, border-color 150ms;
  flex-shrink: 0;
}
.more:hover {
  color: var(--color-accent-deep);
  border-bottom-color: var(--color-accent-deep);
}

@media (max-width: 767px) {
  .title { font-size: 24px; }
  .caption { font-size: 14px; margin-left: 8px; }
}
</style>
