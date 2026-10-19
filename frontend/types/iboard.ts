/**
 * Type definitions for iBoard (Bảng giá v2).
 * Strictly typed matching backend SQLModel schemas.
 */

export interface OrderBookLevel {
  price: number
  volume: number
}

export interface IBoardIndexBreadth {
  advance: number
  ceiling: number
  unchanged: number
  decline: number
  floor: number
}

export interface IBoardIndexItem {
  id: string
  name: string
  price: string
  change: string
  change_percent: string
  is_positive: boolean
  is_unchanged?: boolean
  volume: string
  value: string
  breadth?: IBoardIndexBreadth | null
  sparkline: (number | null)[]
  ref_price?: number | null
  raw_volume?: number | null
  raw_value?: number | null
}

export interface IBoardStockRow {
  symbol: string
  name: string
  exchange: string
  last_price: number
  ref_price: number
  ceiling_price: number
  floor_price: number
  high_price: number
  low_price: number
  avg_price: number
  change: number
  change_percent: number
  volume: number
  value_billion: number
  buy_ratio: number
  sell_ratio: number
  foreign_buy: number
  foreign_sell: number
  foreign_room: number
  status: string
  sparkline: number[]
  bid_book: OrderBookLevel[]
  ask_book: OrderBookLevel[]
  category: string
  sector?: string | null
  expiry_date?: string | null
}

export interface MatchedTickDTO {
  time: string
  price: number
  volume: number
  side: "B" | "S" | string
}

export interface ShareholderDTO {
  name: string
  share_percent: number
  quantity?: number | null
}

export interface CompanyOverviewDTO {
  market_cap_billion: number
  pe: number
  pb: number
  roe: number
}

export interface CorporateEventDTO {
  date: string
  title: string
}

export interface IBoardCandleBar {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface IBoardStockDetail {
  stock: IBoardStockRow
  matched_ticks: MatchedTickDTO[]
  overview: CompanyOverviewDTO
  events: CorporateEventDTO[]
  candles: IBoardCandleBar[]
  company_profile?: string | null
  shareholders: ShareholderDTO[]
  performance_5d?: number | null
  performance_1y?: number | null
  active_buy_vol: number
  active_sell_vol: number
  total_bid_qtty: number
  total_ask_qtty: number
}

export interface TopMoverItem {
  symbol: string
  name: string
  price: string
  change: string
  change_percent: number
  volume: string
}

export interface IBoardMarketPulse {
  ai_insight: string
  top_gainers: TopMoverItem[]
  top_losers: TopMoverItem[]
  top_volume: TopMoverItem[]
  sector_performance: Record<string, number>
}

export interface PaperOrder {
  id: string
  symbol: string
  side: "BUY" | "SELL"
  order_type: "LO" | "MP" | "ATO" | "ATC"
  price: number
  volume: number
  status: "FILLED" | "PENDING" | "CANCELLED"
  created_at: string
}

export interface PutThroughTradeDTO {
  time: string
  symbol: string
  price: number
  volume: number
}

export interface IBoardPutThroughSummary {
  exchange: string
  total_volume: number
  total_value_billion: number
  trades: PutThroughTradeDTO[]
}
