<script setup lang="ts">
import { computed, onMounted } from 'vue'
import ListingCard from './components/ListingCard.vue'
import ListingDetail from './components/ListingDetail.vue'
import { useHashRoute } from './composables/useHashRoute'
import { useListings } from './composables/useListings'
import { useStoredSet } from './composables/useStoredSet'
import { relativeTime, SOURCE_LABELS } from './format'
import type { FilterKey, SortKey } from './types'

const favorites = useStoredSet('wohnungssuche.favorites')
const hidden = useStoredSet('wohnungssuche.hidden')
const { data, error, loading, sort, filter, showHidden, visible, counts, load, byId } = useListings(
  favorites.set,
  hidden.set,
)
const route = useHashRoute()

const selected = computed(() => (route.selectedId.value ? byId(route.selectedId.value) : undefined))

const brokenSources = computed(() =>
  Object.entries(data.value?.sources ?? {})
    .filter(([, health]) => health.consecutive_failures >= 3)
    .map(([name]) => SOURCE_LABELS[name as keyof typeof SOURCE_LABELS] ?? name),
)

const filters: { key: FilterKey; label: string }[] = [
  { key: 'all', label: 'Alle' },
  { key: 'new', label: 'Neu' },
  { key: 'favorites', label: '★' },
]
const sorts: { key: SortKey; label: string }[] = [
  { key: 'score', label: 'Beste zuerst' },
  { key: 'price', label: 'Günstigste' },
  { key: 'newest', label: 'Neueste' },
  { key: 'distance', label: 'Zentralste' },
]

function filterCount(key: FilterKey): number {
  if (key === 'new') return counts.value.new
  if (key === 'favorites') return counts.value.favorites
  return counts.value.active
}

onMounted(load)
</script>

<template>
  <header class="header">
    <div class="wrap">
      <div class="title-row">
        <div>
          <h1>Wohnungssuche Regensburg</h1>
          <p v-if="data" class="sub">
            {{ counts.active }} passende Angebote · aktualisiert {{ relativeTime(data.generated_at) }}
          </p>
        </div>
        <button class="refresh" aria-label="Neu laden" :disabled="loading" @click="load">↻</button>
      </div>
      <ul v-if="data" class="criteria">
        <li>≤ {{ data.criteria.max_warm_rent }} € warm</li>
        <li>ab {{ data.criteria.min_area_m2 }} m² (ideal ≥ {{ data.criteria.comfortable_area_m2 }} m²)</li>
        <li>nah an der {{ data.criteria.center_name }}</li>
      </ul>
      <nav class="controls">
        <div class="segmented" role="tablist">
          <button
            v-for="f in filters"
            :key="f.key"
            role="tab"
            :aria-selected="filter === f.key"
            :class="{ active: filter === f.key }"
            @click="filter = f.key"
          >
            {{ f.label }} <span class="count">{{ filterCount(f.key) }}</span>
          </button>
        </div>
        <select v-model="sort" aria-label="Sortierung">
          <option v-for="s in sorts" :key="s.key" :value="s.key">{{ s.label }}</option>
        </select>
      </nav>
    </div>
  </header>

  <main class="wrap">
    <p v-if="brokenSources.length" class="banner warn">
      ⚠️ {{ brokenSources.join(', ') }} liefert gerade keine Daten. Sag Astra Bescheid, damit der Scraper repariert wird.
    </p>
    <p v-if="error" class="banner warn">{{ error }}</p>
    <p v-else-if="loading && !data" class="empty">Lade Wohnungen …</p>
    <p v-else-if="data && !visible.length" class="empty">
      {{ filter === 'favorites' ? 'Noch keine Favoriten – tippe auf ☆ bei einer Wohnung.' : 'Gerade nichts Passendes. Du bekommst einen Push, sobald sich das ändert.' }}
    </p>

    <section class="grid">
      <ListingCard
        v-for="(listing, i) in visible"
        :key="listing.id"
        :listing="listing"
        :rank="i + 1"
        :favorite="favorites.set.value.has(listing.id)"
        @open="route.open(listing.id)"
        @toggle-favorite="favorites.toggle(listing.id)"
      />
    </section>

    <p v-if="counts.hidden" class="hidden-toggle">
      <button class="link" @click="showHidden = !showHidden">
        {{ showHidden ? 'Ausgeblendete verstecken' : `${counts.hidden} ausgeblendete anzeigen` }}
      </button>
    </p>

    <footer v-if="data" class="footer">
      Bewertung: Lage {{ data.criteria.weights.location }} · Platz {{ data.criteria.weights.size }} · Preis
      {{ data.criteria.weights.price }} · Ausstattung {{ data.criteria.weights.extras }} Punkte. Möbel:
      {{ data.criteria.furniture.join(', ') }}.
    </footer>
  </main>

  <ListingDetail
    v-if="selected && data"
    :listing="selected"
    :criteria="data.criteria"
    :favorite="favorites.set.value.has(selected.id)"
    :hidden="hidden.set.value.has(selected.id)"
    @close="route.close()"
    @toggle-favorite="favorites.toggle(selected.id)"
    @toggle-hidden="hidden.toggle(selected.id)"
  />
</template>

<style scoped>
.wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 16px;
}
.header {
  padding-top: env(safe-area-inset-top);
  border-bottom: 1px solid var(--border);
}
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 14px;
}
h1 {
  margin: 0;
  font-size: 22px;
  letter-spacing: -0.01em;
}
.sub {
  margin: 2px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}
.refresh {
  flex: none;
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--text);
  font-size: 20px;
  cursor: pointer;
}
.criteria {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  font-size: 12px;
}
.criteria li {
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--surface-muted);
  color: var(--text-muted);
}
.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 0;
}
.segmented {
  display: inline-flex;
  padding: 3px;
  border-radius: 12px;
  background: var(--surface-muted);
}
.segmented button {
  padding: 7px 11px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--text-muted);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.segmented button.active {
  background: var(--surface);
  color: var(--text);
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.12);
}
.count {
  margin-left: 2px;
  font-weight: 500;
  color: var(--text-muted);
}
select {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text);
  font: inherit;
  font-size: 14px;
}
main {
  padding-top: 16px;
  padding-bottom: calc(32px + env(safe-area-inset-bottom));
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
  gap: 16px;
}
.banner {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
}
.warn {
  background: var(--con-bg);
  color: var(--con-text);
}
.empty {
  padding: 48px 0;
  text-align: center;
  color: var(--text-muted);
}
.hidden-toggle {
  text-align: center;
}
.link {
  border: 0;
  background: none;
  color: var(--accent);
  font: inherit;
  cursor: pointer;
}
.footer {
  margin-top: 32px;
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}
</style>
