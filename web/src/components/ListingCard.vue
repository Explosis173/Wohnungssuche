<script setup lang="ts">
import type { Listing } from '../types'
import { area, euro, isNew, SOURCE_LABELS } from '../format'
import ScoreBadge from './ScoreBadge.vue'

defineProps<{ listing: Listing; rank: number; favorite: boolean }>()
defineEmits<{ open: []; toggleFavorite: [] }>()
</script>

<template>
  <article class="card" :class="{ inactive: !listing.active }" @click="$emit('open')">
    <div class="photo">
      <img v-if="listing.images.length" :src="listing.images[0]" :alt="listing.title" loading="lazy" referrerpolicy="no-referrer" />
      <div v-else class="no-photo">Keine Fotos</div>
      <ScoreBadge class="score" :score="listing.score" :rating="listing.rating" />
      <span class="rank">#{{ rank }}</span>
      <span v-if="!listing.active" class="flag gone">nicht mehr online</span>
      <span v-else-if="isNew(listing)" class="flag new">neu</span>
      <button
        class="fav"
        :aria-pressed="favorite"
        :aria-label="favorite ? 'Aus Favoriten entfernen' : 'Zu Favoriten'"
        @click.stop="$emit('toggleFavorite')"
      >
        {{ favorite ? '★' : '☆' }}
      </button>
    </div>
    <div class="body">
      <div class="price-row">
        <strong class="price">{{ euro(listing.rent_warm) }}<span v-if="listing.rent_estimated" title="geschätzt">*</span></strong>
        <span class="muted">warm</span>
        <span class="dot">·</span>
        <strong>{{ area(listing.area_m2) }}</strong>
        <template v-if="listing.rooms">
          <span class="dot">·</span>
          <span>{{ listing.rooms }} Zi.</span>
        </template>
      </div>
      <h2 class="title">{{ listing.title }}</h2>
      <p class="where">
        📍 {{ listing.district ?? 'Regensburg' }}
        <template v-if="listing.distance_km != null">
          · {{ listing.distance_km.toLocaleString('de-DE') }} km · 🚲 {{ listing.bike_minutes }} min
        </template>
      </p>
      <ul class="chips">
        <li v-for="pro in listing.pros.slice(0, 3)" :key="pro" class="chip pro">{{ pro }}</li>
        <li v-for="con in listing.cons.slice(0, 2)" :key="con" class="chip con">{{ con }}</li>
      </ul>
      <p class="source muted">{{ SOURCE_LABELS[listing.source] }}</p>
    </div>
  </article>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--surface);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}
.inactive {
  opacity: 0.55;
}
.photo {
  position: relative;
  aspect-ratio: 16 / 10;
  background: var(--surface-muted);
}
.photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.no-photo {
  display: grid;
  place-items: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 14px;
}
.score {
  position: absolute;
  top: 10px;
  right: 10px;
}
.rank {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgb(0 0 0 / 0.6);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
}
.flag {
  position: absolute;
  bottom: 10px;
  left: 10px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
}
.flag.new {
  background: var(--accent);
}
.flag.gone {
  background: #666;
}
.fav {
  position: absolute;
  bottom: 8px;
  right: 10px;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: rgb(0 0 0 / 0.55);
  color: #ffd54a;
  font-size: 20px;
  cursor: pointer;
}
.body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px 14px;
}
.price-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px;
}
.price {
  font-size: 20px;
}
.dot {
  color: var(--text-muted);
}
.title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.where {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
}
.chip {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
}
.chip.pro {
  background: var(--pro-bg);
  color: var(--pro-text);
}
.chip.con {
  background: var(--con-bg);
  color: var(--con-text);
}
.source {
  margin: 0;
  font-size: 12px;
}
.muted {
  color: var(--text-muted);
}
</style>
