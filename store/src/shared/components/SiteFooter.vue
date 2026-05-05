<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <footer class="site-footer">
    <div class="site-footer-inner">
      <div class="footer-brand">
        <span class="footer-logo">易木 YIIMUI</span>
        <p class="footer-tagline">
          把照片變成一幅可以慢慢畫的數字油畫。<br>
          從目錄商品到客製照片，從台灣寄到你家。
        </p>
      </div>

      <div class="footer-col">
        <h4 class="footer-heading">Shop</h4>
        <ul>
          <li><RouterLink to="/products">所有商品</RouterLink></li>
          <li><RouterLink to="/themes">主題瀏覽</RouterLink></li>
          <li><RouterLink to="/custom">客製照片</RouterLink></li>
          <li><RouterLink to="/size-guide">尺寸指南</RouterLink></li>
        </ul>
      </div>

      <div class="footer-col">
        <h4 class="footer-heading">Service</h4>
        <ul>
          <li><RouterLink to="/shipping-info">出貨流程</RouterLink></li>
          <li><RouterLink to="/custom-process">訂製流程</RouterLink></li>
          <li><RouterLink to="/refund-policy">退款政策</RouterLink></li>
          <li><RouterLink to="/pricing">報價參考</RouterLink></li>
        </ul>
      </div>

      <div class="footer-col">
        <h4 class="footer-heading">Account</h4>
        <ul>
          <li><RouterLink to="/login">登入 / 註冊</RouterLink></li>
          <li><RouterLink to="/orders">我的訂單</RouterLink></li>
          <li><RouterLink to="/custom/requests">客製申請</RouterLink></li>
          <li><RouterLink to="/profile/coupons">折扣券</RouterLink></li>
        </ul>
      </div>
    </div>

    <div class="footer-bottom">
      <span>© 2026 易木 YIIMUI</span>
      <a href="mailto:contact@yiimui.com">contact@yiimui.com</a>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  border-top: 1px solid var(--color-line-subtle);
  margin-top: 120px;
  padding: 96px 56px 48px;
}

.site-footer-inner {
  max-width: 1440px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 64px;
}

.footer-logo {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 22px;
  letter-spacing: 0.12em;
  color: var(--color-ink-strong);
  display: inline-block;
  margin-bottom: 24px;
}

.footer-tagline {
  font-size: 13px;
  line-height: 2;
  color: var(--color-ink-muted);
  max-width: 360px;
  letter-spacing: 0.04em;
  margin: 0;
}

.footer-heading {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-accent);
  font-weight: 400;
  margin: 0 0 24px;
}

.footer-col ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.footer-col li { margin-bottom: 14px; }

.footer-col a {
  font-size: 13px;
  color: var(--color-ink-default);
  letter-spacing: 0.04em;
  text-decoration: none;
  transition: color 150ms;
}
.footer-col a:hover { color: var(--color-accent); }

.footer-bottom {
  max-width: 1440px;
  margin: 64px auto 0;
  padding-top: 32px;
  border-top: 1px solid var(--color-line-subtle);
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}

.footer-bottom a {
  color: inherit;
  text-decoration: none;
  transition: color 150ms;
}
.footer-bottom a:hover { color: var(--color-accent); }

@media (max-width: 1023px) {
  .site-footer { padding: 64px 32px 32px; margin-top: 80px; }
  .site-footer-inner {
    grid-template-columns: 1fr 1fr;
    gap: 40px;
  }
  .footer-brand { grid-column: 1 / -1; margin-bottom: 16px; }
  .footer-bottom { padding: 24px 0 0; }
}

@media (max-width: 767px) {
  .site-footer { padding: 48px 20px 24px; }
  .site-footer-inner { grid-template-columns: 1fr; gap: 32px; }
  .footer-bottom {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }
}
</style>
