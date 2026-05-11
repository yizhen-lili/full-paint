<script setup lang="ts">
// /terms — 服務條款
// 對應 docs/yii_mui_static_pages_spec.md 第九頁（用模板）
import { RouterLink } from 'vue-router'
import { useTitle } from '@vueuse/core'
import SectionMasthead from '@/shared/components/SectionMasthead.vue'

useTitle('服務條款｜易木 YIIMUI')

const SECTIONS = [
  {
    no: '01',
    title: '雙方關係與條款適用',
    body: [
      '本服務條款（以下簡稱「本條款」）為您與易木 YIIMUI（以下簡稱「本平台」）之間的契約。',
      '當您註冊帳號、瀏覽商品、下單購買時，即表示您已閱讀並同意本條款全部內容。如不同意，請停止使用本服務。',
    ],
  },
  {
    no: '02',
    title: '商品價格、付款與出貨',
    list: [
      '商品價格以下單當下網站標示為準，本平台保留隨時調整價格之權利',
      '目前提供銀行轉帳付款，下單後 24 小時內完成轉帳並回填末五碼',
      '逾期未付款訂單將自動取消，需重新下單',
      '出貨方式、運費、製作天數等細節依「配送與付款」頁面規定',
    ],
  },
  {
    no: '03',
    title: '退換貨條件',
    body: [
      '退換貨規則依《退換貨政策》辦理。簡要說明：',
    ],
    list: [
      '現成款：未拆封 7 天內可退；瑕疵品 7 天內反映可換',
      '客製款：按下「確認製作」前可全額退款，按下後不可退換',
      '「畫起來不像」不適用退換貨',
    ],
    link: { to: '/refund-policy', label: '完整退換貨政策 →' },
  },
  {
    no: '04',
    title: '客製照片智慧財產權',
    important: true,
    body: [
      '當您於本平台上傳照片進行客製化服務，您授權本平台於以下範圍內使用：',
    ],
    rules: [
      { ok: true, text: '製作客製化數字油畫（必要授權）' },
      { ok: true, text: '案例展示（如您於下單時勾選同意）' },
      { ok: false, text: '商業轉售給第三方（不授權）' },
      { ok: false, text: '修改照片用於非客戶相關用途（不授權）' },
    ],
    closing: [
      '您須擔保所上傳的照片不侵害他人著作權、肖像權或其他智慧財產權。如因您的照片導致第三方爭議，您應自行承擔法律責任。',
      '您可隨時要求刪除照片，刪除後本服務無法繼續，已支付款項依據製作進度個案處理。',
    ],
  },
  {
    no: '05',
    title: '免責條款',
    list: [
      '不可抗力（天災、戰爭、罷工、疫情、網路斷線等）導致的延遲或無法履行，本平台不負違約責任',
      '物流公司運送過程中的延誤、毀損、遺失，本平台協助處理但不承擔賠償責任',
      '因您提供的收件資訊錯誤導致的退件、轉寄費用，由您自行負擔',
      '本網站可能因系統維護暫時無法存取，本平台不對此期間造成的不便負責',
    ],
  },
  {
    no: '06',
    title: '爭議處理與管轄',
    body: [
      '本條款之解釋與適用，以及與本服務有關的爭議，均依中華民國法律處理。',
      '如因本條款所生爭議，雙方同意以台灣台北地方法院為第一審管轄法院。',
    ],
    closing: '本條款最後更新日期：2026 年 5 月 10 日。本平台保留隨時修訂本條款之權利，重大修訂將於網站公告並寄信通知註冊會員。',
  },
]
</script>

<template>
  <main class="page">
    <SectionMasthead
      no="00"
      chapter="Terms"
      title="服務條款"
      caption="Terms of Service"
    />

    <p class="lede">
      使用易木 YIIMUI 服務即表示您同意以下條款。請仔細閱讀，特別是 04「客製照片智慧財產權」條款。
    </p>

    <section v-for="s in SECTIONS" :key="s.no" :class="['article', { 'article-important': s.important }]">
      <header class="article-head">
        <span class="article-no">{{ s.no }}</span>
        <h2 class="article-title">{{ s.title }}</h2>
        <span v-if="s.important" class="important-badge">重要</span>
      </header>

      <div class="article-body">
        <p v-for="(line, idx) in s.body || []" :key="`b-${idx}`">{{ line }}</p>

        <ul v-if="s.list && s.list.length > 0" class="article-list">
          <li v-for="(item, idx) in s.list" :key="`l-${idx}`">{{ item }}</li>
        </ul>

        <ul v-if="s.rules && s.rules.length > 0" class="rules-list">
          <li v-for="(r, idx) in s.rules" :key="`r-${idx}`" :class="['rule', r.ok ? 'rule-ok' : 'rule-no']">
            <span :class="['rule-mark', r.ok ? 'mark-ok' : 'mark-no']">
              {{ r.ok ? '✓' : '✗' }}
            </span>
            <span>{{ r.text }}</span>
          </li>
        </ul>

        <p v-for="(line, idx) in s.closing || []" :key="`c-${idx}`" class="article-closing">
          {{ line }}
        </p>

        <RouterLink v-if="s.link" :to="s.link.to" class="article-link">
          {{ s.link.label }}
        </RouterLink>
      </div>
    </section>

    <footer class="foot">
      <p class="foot-text">
        如對本條款有疑問，請聯絡 <a href="mailto:contact@yiimui.com">contact@yiimui.com</a><br />
        緊急聯絡：<a href="mailto:yiimui.studio@gmail.com">yiimui.studio@gmail.com</a><br />
        we respect your trust ・ 易木 YIIMUI
      </p>
    </footer>
  </main>
</template>

<style scoped>
.page {
  max-width: 760px;
  margin: 0 auto;
  padding: 64px 56px 96px;
}

.lede {
  font-family: var(--font-cn-serif);
  font-weight: 300;
  font-size: 15px;
  line-height: 2;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
  margin: 8px 0 64px;
}

.article {
  margin-bottom: 56px;
  padding-bottom: 48px;
  border-bottom: 1px solid var(--color-line-subtle);
}
.article:last-of-type { border-bottom: none; }

.article-important {
  padding: 32px;
  background: var(--color-accent-tint);
  border: 1px solid var(--color-accent-soft);
  border-radius: var(--radius-xs);
  border-bottom: 1px solid var(--color-accent-soft);
}
.article-important .article-head { margin-bottom: 14px; }

.article-head {
  display: flex;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 18px;
}
.article-no {
  font-family: var(--font-display);
  font-style: italic;
  font-size: 22px;
  color: var(--color-accent);
  font-weight: 300;
  line-height: 1;
}
.article-title {
  font-family: var(--font-cn-serif);
  font-weight: 400;
  font-size: 19px;
  letter-spacing: 0.06em;
  color: var(--color-ink-strong);
  margin: 0;
  flex: 1;
}
.important-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--color-accent);
  font-weight: 500;
  padding: 3px 10px;
  border: 1px solid var(--color-accent);
  border-radius: 999px;
}

.article-body p {
  font-size: 14px;
  line-height: 1.95;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
  margin: 0 0 12px;
}

.article-list {
  list-style: none;
  padding: 0 0 0 12px;
  margin: 0 0 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.article-list li {
  position: relative;
  padding-left: 18px;
  font-size: 14px;
  line-height: 1.85;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
}
.article-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.85em;
  width: 8px;
  height: 1px;
  background: var(--color-accent);
}

.rules-list {
  list-style: none;
  padding: 0;
  margin: 16px 0 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rule {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-xs);
  font-size: 13px;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
}
.rule-ok { background: rgba(127, 159, 121, 0.06); }
.rule-no { background: var(--color-paper-canvas); border: 1px solid var(--color-line); }
.rule-mark {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}
.mark-ok { background: var(--color-fresh); color: var(--color-paper-canvas); }
.mark-no {
  background: transparent;
  color: var(--color-ink-default);
  border: 1.5px solid var(--color-ink-default);
}

.article-closing {
  margin-top: 14px !important;
  font-size: 13px !important;
  color: var(--color-ink-muted) !important;
}

.article-link {
  display: inline-block;
  margin-top: 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--color-accent);
  text-decoration: none;
  border-bottom: 1px solid var(--color-accent);
  padding-bottom: 2px;
}
.article-link:hover { color: var(--color-accent-deep); border-color: var(--color-accent-deep); }

.foot {
  margin-top: 48px;
  text-align: center;
}
.foot-text {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.16em;
  color: var(--color-ink-muted);
  line-height: 2;
  margin: 0;
}

@media (max-width: 1023px) { .page { padding: 48px 32px 72px; } }
@media (max-width: 767px) {
  .page { padding: 36px 24px 56px; }
  .article-title { font-size: 17px; }
  .article-important { padding: 24px 20px; }
}
</style>
