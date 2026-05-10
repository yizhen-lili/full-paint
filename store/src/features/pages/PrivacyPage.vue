<script setup lang="ts">
// /privacy — 隱私權政策
// 對應 docs/yii_mui_static_pages_spec.md 第九頁（用模板）
import { useTitle } from '@vueuse/core'
import SectionMasthead from '@/shared/components/SectionMasthead.vue'

useTitle('隱私權政策｜易木 YIIMUI')

const SECTIONS = [
  {
    no: '01',
    title: '我們蒐集的個人資料',
    body: [
      '當您在易木 YIIMUI 註冊會員、下單、聯絡客服或訂閱電子報時，我們會蒐集以下類型的個人資料：',
    ],
    list: [
      '基本資料：姓名、Email、聯絡電話、生日（選填）',
      '收件資料：收件人姓名、地址、電話、超商門市資訊',
      '付款資訊：銀行轉帳末五碼（不蒐集完整卡號 / 帳號）',
      '客製照片：您主動上傳作為客製化材料的照片',
      '瀏覽紀錄：IP 位址、裝置與瀏覽器資訊、訪問頁面與時間',
    ],
  },
  {
    no: '02',
    title: '我們為什麼蒐集這些資料',
    list: [
      '處理訂單與配送：完成購買、寄送商品、退換貨流程',
      '客戶服務：回覆詢問、提供售後支援、解決爭議',
      '交易紀錄：依法保存發票與消費紀錄',
      '行銷溝通（須您同意）：寄送電子報、優惠通知、新品上架資訊',
      '網站改善：分析使用情形、優化頁面與商品推薦',
    ],
  },
  {
    no: '03',
    title: '資料如何被使用與分享',
    body: [
      '您的個人資料僅用於上述目的。我們僅在以下必要情境會將部分資料提供給第三方：',
    ],
    list: [
      '物流服務商：傳遞收件資訊以完成配送',
      '金流服務商：未來引入信用卡付款時，僅傳遞必要交易資訊',
      '雲端儲存：使用 Firebase Storage 儲存圖片，已通過 ISO 27001、SOC 2 認證',
      '法律要求：依法令、法院命令或主管機關要求時',
    ],
    closing: '我們不會將您的個人資料出售、出租或以行銷目的轉讓予第三方。',
  },
  {
    no: '04',
    title: '資料保存期限',
    list: [
      '帳號資料：自您主動刪除帳號起 30 天後永久刪除',
      '訂單與交易紀錄：依稅法保存 7 年',
      '客製照片：訂單完成 12 個月後自動刪除（您可隨時要求提早刪除）',
      '瀏覽紀錄：90 天後自動移除',
    ],
  },
  {
    no: '05',
    title: '您對自己資料的權利',
    body: [
      '依個人資料保護法，您可隨時行使以下權利：',
    ],
    list: [
      '查詢、請求閱覽您的個人資料',
      '製給複本或更正資料',
      '請求停止蒐集、處理或利用',
      '請求刪除您的個人資料',
      '撤回行銷溝通同意',
    ],
    closing: '請透過 contact@yiimui.com 聯絡我們，我們將在 7 個工作天內回覆。',
  },
  {
    no: '06',
    title: 'Cookie 政策',
    body: [
      '本網站使用 Cookie 與類似技術改善使用體驗：',
    ],
    list: [
      '必要 Cookie：維持登入狀態、購物車、防範 CSRF 攻擊（無法關閉）',
      '功能 Cookie：記住您的偏好設定（語言、主題）',
      '分析 Cookie：匿名統計頁面流量與使用模式',
    ],
    closing: '您可透過瀏覽器設定停用 Cookie，但部分功能（如登入、購物車）將無法正常使用。',
  },
  {
    no: '07',
    title: '聯絡與爭議',
    body: [
      '若對個資處理有任何疑問或要求，請聯絡：',
      'Email：contact@yiimui.com（24 小時內回覆）',
      'Instagram 私訊：@yiimui',
      '',
      '本政策最後更新日期：2026 年 5 月 10 日。如有重大修訂，我們會於網站公告並寄信通知註冊會員。',
    ],
  },
]
</script>

<template>
  <main class="page">
    <SectionMasthead
      no="00"
      chapter="Privacy"
      title="隱私權政策"
      caption="Privacy Policy"
    />

    <p class="lede">
      易木 YIIMUI 重視您的個人資料保護。本政策說明我們蒐集哪些資料、為什麼蒐集、如何使用，以及您擁有的權利。
    </p>

    <section v-for="s in SECTIONS" :key="s.no" class="article">
      <header class="article-head">
        <span class="article-no">{{ s.no }}</span>
        <h2 class="article-title">{{ s.title }}</h2>
      </header>

      <div class="article-body">
        <p v-for="(line, idx) in s.body || []" :key="`b-${idx}`" :class="{ 'body-spacer': line === '' }">
          {{ line }}
        </p>

        <ul v-if="s.list && s.list.length > 0" class="article-list">
          <li v-for="(item, idx) in s.list" :key="`l-${idx}`">{{ item }}</li>
        </ul>

        <p v-if="s.closing" class="article-closing">{{ s.closing }}</p>
      </div>
    </section>

    <footer class="foot">
      <p class="foot-text">
        本政策由易木 YIIMUI 制定並保留所有解釋權。<br />
        如本政策與最新公告有出入，以最新公告為準。
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
}

.article-body p {
  font-size: 14px;
  line-height: 1.95;
  letter-spacing: 0.04em;
  color: var(--color-ink-default);
  margin: 0 0 12px;
}
.body-spacer { height: 4px; }

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

.article-closing {
  margin-top: 12px !important;
  padding: 12px 16px;
  background: var(--color-paper-deep);
  border-left: 2px solid var(--color-accent);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
  font-size: 13px !important;
  color: var(--color-ink-muted) !important;
}

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
}
</style>
