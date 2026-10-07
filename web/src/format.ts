import type { Listing, Rating } from './types'

export const SOURCE_LABELS: Record<Listing['source'], string> = {
  'wg-gesucht': 'WG-Gesucht',
  kleinanzeigen: 'Kleinanzeigen',
}

export const RATING_EMOJI: Record<Rating, string> = {
  Top: '🔥',
  Gut: '✅',
  Okay: '🙂',
  Mäßig: '😐',
}

const NEW_FOR_MS = 24 * 60 * 60 * 1000

export function euro(value: number | null): string {
  return value == null ? '–' : `${Math.round(value)} €`
}

export function area(value: number | null): string {
  return value == null ? '? m²' : `${Math.round(value)} m²`
}

export function date(value: string | null): string {
  if (!value) return '–'
  const parsed = /^\d{4}-\d{2}-\d{2}/.test(value) ? new Date(value) : null
  return parsed && !Number.isNaN(parsed.getTime())
    ? parsed.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : value
}

export function relativeTime(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 60) return `vor ${Math.max(1, minutes)} min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `vor ${hours} h`
  const days = Math.round(hours / 24)
  return days === 1 ? 'gestern' : `vor ${days} Tagen`
}

export function isNew(listing: Listing): boolean {
  return Date.now() - new Date(listing.first_seen).getTime() < NEW_FOR_MS
}

export function mapsUrl(listing: Listing): string {
  const query =
    listing.lat != null && listing.lon != null
      ? `${listing.lat},${listing.lon}`
      : `${listing.address ?? listing.district ?? ''} Regensburg`
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`
}
