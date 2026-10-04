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
