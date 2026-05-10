<script setup lang="ts">
// 提示 user 系統信可能被誤判為垃圾信，引導他們去找 + 標記為非垃圾。
// 使用情境：register / forgot-password / change-email / 其他需 user 收信的場景。
defineProps<{
  /** 客製化提示主標題（預設「沒收到信？」） */
  title?: string
}>()
</script>

<template>
  <aside class="spam-tip">
    <strong class="spam-tip-title">📧 {{ title ?? '沒收到信？' }}</strong>
    <p>新註冊網域可能會被誤判為垃圾信，請檢查：</p>
    <ul>
      <li>「<strong>垃圾郵件</strong>」資料夾</li>
      <li>Gmail 的「<strong>促銷內容</strong>」分頁</li>
      <li>所有信件 / 全部郵件</li>
    </ul>
    <p class="spam-tip-hint">
      找到後請按「<strong>回報為非垃圾郵件</strong>」，未來收信會直接進收件夾。
    </p>
  </aside>
</template>

<style scoped>
.spam-tip {
  margin: 0 auto 16px;
  padding: 14px 18px;
  background: var(--color-paper-deep);
  border-left: 2px solid var(--color-accent);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
  text-align: left;
  max-width: 420px;
}
.spam-tip-title {
  display: block;
  font-family: var(--font-cn-serif);
  font-weight: 500;
  font-size: 13px;
  color: var(--color-ink-strong);
  letter-spacing: 0.04em;
  margin-bottom: 6px;
}
.spam-tip p {
  margin: 0 0 6px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--color-ink-default);
  letter-spacing: 0.02em;
}
.spam-tip ul {
  margin: 0 0 8px;
  padding-left: 4px;
  list-style: none;
}
.spam-tip ul li {
  position: relative;
  padding-left: 14px;
  font-size: 12px;
  line-height: 1.85;
  color: var(--color-ink-default);
  letter-spacing: 0.02em;
}
.spam-tip ul li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.85em;
  width: 6px;
  height: 1px;
  background: var(--color-accent);
}
.spam-tip strong {
  color: var(--color-accent);
  font-weight: 500;
}
.spam-tip-hint {
  margin-top: 8px !important;
  padding-top: 8px;
  border-top: 1px dashed var(--color-line-subtle);
  font-size: 11px !important;
  color: var(--color-ink-muted) !important;
}
.spam-tip-hint strong {
  color: var(--color-ink-strong) !important;
}
</style>
