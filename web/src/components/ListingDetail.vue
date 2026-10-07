<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import type { Criteria, Listing } from '../types'
import { area, date, euro, mapsUrl, relativeTime, SOURCE_LABELS } from '../format'
import ScoreBadge from './ScoreBadge.vue'

const props = defineProps<{ listing: Listing; criteria: Criteria; favorite: boolean; hidden: boolean }>()
const emit = defineEmits<{ close: []; toggleFavorite: []; toggleHidden: [] }>()

const bars = computed(() => {
  const w = props.criteria.weights
  const b = props.listing.breakdown
  return [
    { label: 'Lage', value: b.location, max: w.location },
    { label: 'Platz für deine Möbel', value: b.size, max: w.size },
    { label: 'Preis', value: b.price, max: w.price },
    { label: 'Ausstattung', value: b.extras, max: w.extras },
  ]
})

const adjustments = computed(() =>
  [
    { label: 'Abzüge', value: props.listing.breakdown.penalty },
    { label: 'KI-Einschätzung', value: props.listing.breakdown.ai ?? 0 },
  ].filter((a) => a.value !== 0),
)

const spaceVerdict = computed(() => {
  const a = props.listing.area_m2
  const needed = props.criteria.comfortable_area_m2
  if (a == null) return 'Größe unbekannt – im Inserat nachfragen.'
  if (a >= needed + 6) return `Passt gut: ${Math.round(a - needed)} m² mehr als deine Möbel brauchen (~${needed} m²).`
  if (a >= needed) return `Passt: knapp über den ~${needed} m², die deine Möbel brauchen.`
  return `Eng: ${Math.round(needed - a)} m² weniger als die ~${needed} m², die deine Möbel bequem brauchen.`
})

function onKey(event: KeyboardEvent): void {
  if (event.key === 'Escape') emit('close')
}
onMounted(() => {
  window.addEventListener('keydown', onKey)
  document.body.style.overflow = 'hidden'
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <section class="sheet" role="dialog" aria-modal="true" :aria-label="listing.title">
      <header class="top">
        <button class="icon-btn" aria-label="Zurück" @click="emit('close')">←</button>
        <span class="muted">{{ SOURCE_LABELS[listing.source] }} · gefunden {{ relativeTime(listing.first_seen) }}</span>
        <button class="icon-btn star" :aria-pressed="favorite" aria-label="Favorit" @click="emit('toggleFavorite')">
          {{ favorite ? '★' : '☆' }}
        </button>
      </header>

      <div v-if="listing.images.length" class="gallery">
        <img
          v-for="(src, i) in listing.images"
          :key="src"
          :src="src"
          :alt="`Foto ${i + 1}`"
          loading="lazy"
          referrerpolicy="no-referrer"
        />
      </div>

      <div class="content">
        <p v-if="!listing.active" class="notice">Diese Anzeige ist nicht mehr online.</p>

        <div class="headline">
          <ScoreBadge :score="listing.score" :rating="listing.rating" large />
          <div>
            <h2>{{ listing.title }}</h2>
            <p class="facts">
              <strong>{{ euro(listing.rent_warm) }}</strong> warm<span v-if="listing.rent_estimated"> (geschätzt)</span>
              · <strong>{{ area(listing.area_m2) }}</strong>
              <template v-if="listing.rooms"> · {{ listing.rooms }} Zimmer</template>
            </p>
          </div>
        </div>

        <div class="actions">
          <a class="btn primary" :href="listing.url" target="_blank" rel="noopener">Anzeige öffnen</a>
          <a class="btn" :href="mapsUrl(listing)" target="_blank" rel="noopener">Karte</a>
          <button class="btn" @click="emit('toggleHidden')">{{ hidden ? 'Wieder einblenden' : 'Ausblenden' }}</button>
        </div>

        <h3>Bewertung</h3>
        <div class="bars">
          <div v-for="bar in bars" :key="bar.label" class="bar">
            <div class="bar-head">
              <span>{{ bar.label }}</span>
              <span class="num">{{ Math.round(bar.value) }}/{{ bar.max }}</span>
            </div>
            <div class="track"><div class="fill" :style="{ width: `${(bar.value / bar.max) * 100}%` }" /></div>
          </div>
          <p v-for="adj in adjustments" :key="adj.label" class="adjust" :class="adj.value < 0 ? 'neg' : 'pos'">
            {{ adj.label }}: {{ adj.value > 0 ? '+' : '' }}{{ adj.value }}
          </p>
        </div>
        <p class="space">🛋️ {{ spaceVerdict }}</p>

        <ul class="chips">
          <li v-for="pro in listing.pros" :key="pro" class="chip pro">👍 {{ pro }}</li>
          <li v-for="con in listing.cons" :key="con" class="chip con">⚠️ {{ con }}</li>
        </ul>

        <div v-if="listing.ai_review" class="ai">
          <h3>🤖 KI-Einschätzung</h3>
          <p v-if="listing.ai_review.summary">{{ listing.ai_review.summary }}</p>
          <p v-if="listing.ai_review.furniture_fit"><strong>Möbel:</strong> {{ listing.ai_review.furniture_fit }}</p>
          <ul v-if="listing.ai_review.red_flags?.length">
            <li v-for="flag in listing.ai_review.red_flags" :key="flag">{{ flag }}</li>
          </ul>
        </div>

        <h3>Eckdaten</h3>
        <dl class="table">
          <dt>Warmmiete</dt><dd>{{ euro(listing.rent_warm) }}<span v-if="listing.rent_estimated"> (geschätzt)</span></dd>
          <dt>Kaltmiete</dt><dd>{{ euro(listing.rent_cold) }}</dd>
          <dt>Nebenkosten</dt><dd>{{ euro(listing.utilities) }}</dd>
          <dt>Kaution</dt><dd>{{ euro(listing.deposit) }}</dd>
          <dt>Adresse</dt><dd>{{ listing.address ?? listing.district ?? '–' }}</dd>
          <dt>Zur {{ criteria.center_name }}</dt>
          <dd>
            <template v-if="listing.distance_km != null">
              {{ listing.distance_km.toLocaleString('de-DE') }} km · ca. {{ listing.bike_minutes }} min mit dem Rad
            </template>
            <template v-else>–</template>
          </dd>
          <dt>Frei ab</dt><dd>{{ date(listing.available_from) }}</dd>
          <dt v-if="listing.available_until">Befristet bis</dt>
          <dd v-if="listing.available_until">{{ date(listing.available_until) }}</dd>
          <dt v-if="listing.features.length">Ausstattung</dt>
          <dd v-if="listing.features.length">{{ listing.features.join(', ') }}</dd>
        </dl>

        <h3>Beschreibung</h3>
        <p class="description">{{ listing.description || 'Keine Beschreibung.' }}</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  justify-content: center;
  background: rgb(0 0 0 / 0.45);
}
.sheet {
  width: 100%;
  max-width: 760px;
  height: 100%;
  overflow-y: auto;
  background: var(--bg);
  overscroll-behavior: contain;
}
.top {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: calc(8px + env(safe-area-inset-top)) 12px 8px;
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.icon-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--text);
  font-size: 20px;
  cursor: pointer;
}
.star {
  color: #e6a700;
}
.gallery {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
}
.gallery img {
  flex: 0 0 auto;
  width: min(100%, 560px);
  aspect-ratio: 4 / 3;
  object-fit: cover;
  scroll-snap-align: start;
  background: var(--surface-muted);
}
.content {
  padding: 16px 16px calc(32px + env(safe-area-inset-bottom));
}
.notice {
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--con-bg);
  color: var(--con-text);
}
.headline {
  display: flex;
  gap: 14px;
  align-items: center;
}
h2 {
  margin: 0 0 4px;
  font-size: 19px;
  line-height: 1.3;
}
h3 {
  margin: 24px 0 10px;
  font-size: 15px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.facts {
  margin: 0;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.btn {
  flex: 1 1 auto;
  padding: 11px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text);
  font: inherit;
  font-weight: 600;
  text-align: center;
  text-decoration: none;
  cursor: pointer;
}
.btn.primary {
  border-color: var(--accent);
  background: var(--accent);
  color: #fff;
}
.bars {
  display: grid;
  gap: 10px;
}
.bar-head {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}
.num {
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}
.track {
  height: 8px;
  margin-top: 4px;
  border-radius: 999px;
  background: var(--surface-muted);
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
}
.adjust {
  margin: 0;
  font-size: 14px;
}
.adjust.neg {
  color: var(--con-text);
}
.adjust.pos {
  color: var(--pro-text);
}
.space {
  margin: 14px 0 0;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
}
.chip {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 13px;
}
.chip.pro {
  background: var(--pro-bg);
  color: var(--pro-text);
}
.chip.con {
  background: var(--con-bg);
  color: var(--con-text);
}
.ai {
  margin-top: 8px;
  padding: 2px 14px 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.table {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 8px 16px;
  margin: 0;
  font-size: 14px;
}
.table dt {
  color: var(--text-muted);
}
.table dd {
  margin: 0;
}
.description {
  white-space: pre-line;
  line-height: 1.55;
}
.muted {
  color: var(--text-muted);
}
@media (min-width: 761px) {
  .sheet {
    margin: 24px 0;
    height: calc(100% - 48px);
    border-radius: 18px;
  }
}
</style>
