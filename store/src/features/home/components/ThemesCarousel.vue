<script setup lang="ts">
import { computed } from 'vue'
import { useThemesQuery } from '@/features/browse/queries'
import ThemeCard from '@/features/themes/components/ThemeCard.vue'
import SectionMasthead from '@/shared/components/SectionMasthead.vue'

const themesQuery = useThemesQuery()
const themes = computed(() => themesQuery.data.value?.items.slice(0, 4) ?? [])
</script>

<template>
  <section v-if="themes.length > 0" class="section">
    <SectionMasthead
      no="02"
      chapter="Themes"
      title="主題瀏覽"
      caption="curated"
      link-text="所有主題 →"
      link-to="/themes"
    />
    <div class="grid">
      <ThemeCard v-for="t in themes" :key="t.id" :theme="t" />
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
  gap: 24px;
}

@media (max-width: 1023px) {
  .section { padding: 64px 32px; }
  .grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 767px) {
  .section { padding: 48px 24px; }
  .grid { grid-template-columns: 1fr; }
}
</style>
