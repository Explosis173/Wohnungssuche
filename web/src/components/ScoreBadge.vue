<script setup lang="ts">
import { computed } from 'vue'
import type { Rating } from '../types'

const props = defineProps<{ score: number; rating: Rating; large?: boolean }>()

const tone = computed(() => ({ Top: 'top', Gut: 'good', Okay: 'ok', Mäßig: 'meh' })[props.rating])
</script>

<template>
  <div class="badge" :class="[tone, { large }]" :aria-label="`Bewertung ${score} von 100, ${rating}`">
    <span class="value">{{ score }}</span>
    <span class="label">{{ rating }}</span>
  </div>
</template>

<style scoped>
.badge {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  padding: 6px 8px;
  border-radius: 12px;
  color: #fff;
  line-height: 1;
  box-shadow: 0 2px 8px rgb(0 0 0 / 0.25);
}
.value {
  font-size: 20px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.label {
  margin-top: 3px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.large {
  min-width: 72px;
  padding: 10px 12px;
}
.large .value {
  font-size: 30px;
}
.top {
  background: var(--score-top);
}
.good {
  background: var(--score-good);
}
.ok {
  background: var(--score-ok);
}
.meh {
  background: var(--score-meh);
}
</style>
