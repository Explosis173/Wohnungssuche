export type Rating = 'Top' | 'Gut' | 'Okay' | 'Mäßig'

export interface ScoreBreakdown {
  location: number
  size: number
  price: number
  extras: number
  penalty: number
  ai?: number
}

export interface AiReview {
  summary?: string
  furniture_fit?: string
  red_flags?: string[]
  score_adjustment?: number
}

export interface Listing {
  id: string
  source: 'wg-gesucht' | 'kleinanzeigen'
  url: string
  title: string
  kind: string
  rent_warm: number | null
  rent_cold: number | null
  utilities: number | null
  rent_estimated: boolean
  deposit: number | null
  area_m2: number | null
  rooms: number | null
  address: string | null
  zip_code: string | null
  district: string | null
  lat: number | null
  lon: number | null
  available_from: string | null
  available_until: string | null
  description: string
  features: string[]
  images: string[]
  score: number
  rating: Rating
  breakdown: ScoreBreakdown
  pros: string[]
  cons: string[]
  distance_km: number | null
  bike_minutes: number | null
  ai_review: AiReview | null
  first_seen: string
  last_seen: string
  notified_at: string | null
  active: boolean
}

export interface SourceHealth {
  last_success: string | null
  last_error: string | null
  consecutive_failures: number
  last_count: number
}

export interface Criteria {
  max_warm_rent: number
  min_area_m2: number
  comfortable_area_m2: number
  center_name: string
  center: [number, number]
  furniture: string[]
  weights: { location: number; size: number; price: number; extras: number }
}

export interface AppData {
  generated_at: string
  criteria: Criteria
  sources: Record<string, SourceHealth>
  listings: Listing[]
}

export type SortKey = 'score' | 'price' | 'newest' | 'distance'
export type FilterKey = 'all' | 'new' | 'favorites'
