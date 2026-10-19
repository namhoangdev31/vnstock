export interface MarketBreadthPoint {
  time: string
  timestamp: number
  advance: number
  decline: number
  unchanged: number
  ceiling: number
  floor: number
  total: number
  ceiling_pct: number
  advance_pure_pct: number
  unchanged_pct: number
  decline_pure_pct: number
  floor_pct: number
}

export interface MarketBreadthSeriesResponse {
  index_code: string
  data: MarketBreadthPoint[]
  latest?: MarketBreadthPoint | null
}

export interface MarketBreadthDetailResponse {
  index_code: string
  advance: string[]
  decline: string[]
  no_change: string[]
  ceiling: string[]
  floor: string[]
}
