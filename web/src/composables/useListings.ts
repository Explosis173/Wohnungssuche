import { computed, ref, type Ref } from 'vue'
import type { AppData, FilterKey, Listing, SortKey } from '../types'
import { isNew } from '../format'

const SORTERS: Record<SortKey, (a: Listing, b: Listing) => number> = {
  score: (a, b) => b.score - a.score,
  price: (a, b) => (a.rent_warm ?? Infinity) - (b.rent_warm ?? Infinity),
  newest: (a, b) => b.first_seen.localeCompare(a.first_seen),
  distance: (a, b) => (a.distance_km ?? Infinity) - (b.distance_km ?? Infinity),
}

export function useListings(favorites: Ref<Set<string>>, hidden: Ref<Set<string>>) {
  const data = ref<AppData | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(true)
  const sort = ref<SortKey>('score')
  const filter = ref<FilterKey>('all')
  const showHidden = ref(false)

  async function load(): Promise<void> {
    loading.value = true
    try {
      const response = await fetch(`data.json?t=${Date.now()}`, { cache: 'no-store' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      data.value = (await response.json()) as AppData
      error.value = null
    } catch (e) {
      error.value = `Daten konnten nicht geladen werden (${e instanceof Error ? e.message : String(e)}).`
    } finally {
      loading.value = false
    }
  }

  const visible = computed<Listing[]>(() => {
    const all = data.value?.listings ?? []
    const filtered = all.filter((l) => {
      if (filter.value === 'favorites') return favorites.value.has(l.id)
      if (!showHidden.value && hidden.value.has(l.id)) return false
      if (filter.value === 'new') return l.active && isNew(l)
      return true
    })
    // Offline listings always go to the end.
    return filtered.sort((a, b) => Number(b.active) - Number(a.active) || SORTERS[sort.value](a, b))
  })

  const counts = computed(() => {
    const all = data.value?.listings ?? []
    return {
      active: all.filter((l) => l.active).length,
      new: all.filter((l) => l.active && isNew(l)).length,
      favorites: all.filter((l) => favorites.value.has(l.id)).length,
      hidden: all.filter((l) => hidden.value.has(l.id)).length,
    }
  })

  const byId = (id: string): Listing | undefined => data.value?.listings.find((l) => l.id === id)

  return { data, error, loading, sort, filter, showHidden, visible, counts, load, byId }
}
