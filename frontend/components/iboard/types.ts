export interface IndexBreadth {
  advance: number
  ceiling: number
  unchanged: number
  decline: number
  floor: number
}

export interface IndexDisplayItem {
  id: string
  name: string
  price: string
  change: string
  changePercent: string
  isPositive: boolean
  isUnchanged?: boolean
  volume: string
  value: string
  breadth: IndexBreadth | null
  sparkline: number[]
  ceilingPrice?: string | number
  refPrice?: string | number
  floorPrice?: string | number
}

export interface OrderBookLevel {
  price: number
  volume: number
}

export interface StockRowDisplay {
  symbol: string
  name: string
  exchange: string
  lastPrice: number
  refPrice: number
  ceilingPrice: number
  floorPrice: number
  highPrice: number
  lowPrice: number
  avgPrice: number
  change: number
  changePercent: number
  volume: number
  valueBillion: number
  buyRatio: number
  sellRatio: number
  foreignBuy: number
  foreignSell: number
  foreignRoom: number
  status: "up" | "down" | "ref" | "ceiling" | "floor"
  sparkline: number[]
  bidBook: OrderBookLevel[]
  askBook: OrderBookLevel[]
  category: string
  sector?: string | null
  expiryDate?: string | null
}

export interface FluctuationStats {
  ceil: number
  up: number
  unch: number
  down: number
  flr: number
}

export interface SimulatedOrder {
  id: string
  symbol: string
  side: "BUY" | "SELL"
  price: string
  quantity: number
  status: "MATCHED" | "PENDING"
  time: string
}

export interface SparklineGeometry {
  linePath: string
  areaPath: string
  lastPoint: { x: number; y: number }
}

export type MainCategory =
  | "watchlist"
  | "listed"
  | "sectors"
  | "derivatives"
  | "warrants"
  | "etf"
  | "put_through"
  | "ideas"
  | "screener"

export type ListedSubBasket =
  | "VN30"
  | "HSX"
  | "HNX"
  | "UPCOM"
  | "ODD_LOT"
  | "MARGIN_DISCOUNT"

export interface SectorItem {
  id: string
  name: string
  change: string
}
