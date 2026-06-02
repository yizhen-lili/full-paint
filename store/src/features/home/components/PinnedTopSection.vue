<script setup lang="ts">
import { computed } from 'vue'
import { useHomepagePinnedQuery } from '@/features/products/queries'
import ProductCard from '@/features/products/components/ProductCard.vue'
import SectionMasthead from '@/shared/components/SectionMasthead.vue'

const { data } = useHomepagePinnedQuery()
const items = computed(() => data.value?.items ?? [])
</script>

<template>
  <!-- 沒置頂時整段不渲染（user 決議：LatestProductsSection 照舊顯示最新） -->
  <section v-if="items.length > 0" class="section">
    <SectionMasthead
      no="01"
      chapter="Featured"
      title="本季嚴選"
      caption="hand picked"
      link-text="看全部 →"
      link-to="/products"
    />

    <div class="grid">
      <ProductCard
        v-for="(p, idx) in items"
        :key="p.id"
        :product="p"
        :number="String(idx + 1).padStart(2, '0')"
      />
    </div>
  </section>
</template>

<style scoped>
.section {
  max-width: 1440px;
  margin: 0 auto;
  padding: 96px 56px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 32px;
}

@media (max-width: 1279px) {
  .grid { grid-template-columns: repeat(3, 1fr); gap: 28px; }
}
@media (max-width: 1023px) {
  .section { padding: 64px 32px; }
  .grid { grid-template-columns: repeat(2, 1fr); gap: 24px; }
}
@media (max-width: 767px) {
  .section { padding: 48px 24px; }
  .grid { grid-template-columns: 1fr; gap: 20px; }
}
</style>
