<script setup lang="ts">
import HomeHero from '../components/HomeHero.vue'
import EditorLetterSection from '../components/EditorLetterSection.vue'
import LatestProductsSection from '../components/LatestProductsSection.vue'
import ThemesShowcaseSection from '../components/ThemesShowcaseSection.vue'
import FeaturedSeriesSection from '../components/FeaturedSeriesSection.vue'
import ProcessStepsSection from '../components/ProcessStepsSection.vue'
import CustomBanner from '../components/CustomBanner.vue'
import SignatureFooter from '../components/SignatureFooter.vue'
</script>

<template>
  <!-- A. Cinematic Hero — 已是雜誌封面式 -->
  <HomeHero />

  <!-- B. Editor's Letter — 安靜窄欄引言（呼吸區） -->
  <EditorLetterSection />

  <!-- D. Latest Products — 最新上架 4 卡 -->
  <LatestProductsSection />

  <!-- E. Themes — 全寬深色 themes band（重壓底） -->
  <ThemesShowcaseSection />

  <!-- 精選系列 — 4 mood gradient（中等密度） -->
  <FeaturedSeriesSection />

  <!-- F. Process — 3 步驟大序體數字（呼吸 + 流程說明） -->
  <ProcessStepsSection />

  <!-- G. Custom Call — 半深 panel + 半圖 split（CTA） -->
  <CustomBanner />

  <!-- H. Signature — 純 typography 簽名 -->
  <SignatureFooter />
</template>
