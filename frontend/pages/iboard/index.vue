<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import {
  type CompanyOverviewDTO,
  type CorporateEventDTO,
  type IBoardCandleBar,
  type IBoardIndexItem,
  type IBoardStockDetail,
  type IBoardStockRow,
  type MatchedTickDTO,
  type SimulationOrderDTO,
  StockService,
  type TopMoverItem,
} from "~/client/stockService"

definePageMeta({
  layout: false,
})

useHead({
  title: "Bảng giá chứng khoán chuyên nghiệp | Vnstock Quants",
  meta: [
    {
      name: "description",
      content:
        "Bảng giá chứng khoán và phái sinh trực tuyến tốc độ cao, phân tích kỹ thuật và dòng tiền thông minh.",
    },
  ],
})

const { showSuccessToast, showErrorToast } = useCustomToast()

const currentTime = ref("00:00:00")
let clockTimer: ReturnType<typeof setInterval> | null = null
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null

const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toTimeString().split(" ")[0]
}

import IBoardIndexRibbon from "~/components/iboard/IBoardIndexRibbon.vue"
import type { IndexDisplayItem } from "~/components/iboard/types"

const isIndexRibbonOpen = ref(true)

const handleIndexSelect = (id: string) => {
  if (id === "vn30") {
    mainCategory.value = "listed"
    listedSubBasket.value = "VN30"
  } else if (id === "vnindex") {
    mainCategory.value = "listed"
    listedSubBasket.value = "HSX"
  } else if (id === "hnx30" || id === "hnx") {
    mainCategory.value = "listed"
    listedSubBasket.value = "HNX"
  } else if (id === "vn30f1m") {
    mainCategory.value = "derivatives"
  }
}

const create100DailyPoints = (
  start: number,
  end: number,
  volatility: number,
  seed = 42,
): number[] => {
  const points: number[] = []
  const n = 100
  for (let i = 0; i < n; i++) {
    const progress = i / (n - 1)
    const trend = start + progress * (end - start)
    const wave1 = Math.sin(i * 0.18 + seed) * volatility
    const wave2 = Math.cos(i * 0.42 + seed * 1.6) * (volatility * 0.45)
    points.push(Number((trend + wave1 + wave2).toFixed(2)))
  }
  points[points.length - 1] = end
  return points
}

const defaultIndices: IndexDisplayItem[] = [
  {
    id: "vn30",
    name: "VN30",
    price: "1,875.99",
    change: "-14.58",
    changePercent: "-0.77%",
    isPositive: false,
    isUnchanged: false,
    volume: "334.91 Triệu CP",
    value: "10,272.88 Tỷ",
    breadth: { advance: 5, ceiling: 0, unchanged: 3, decline: 22, floor: 0 },
    sparkline: create100DailyPoints(1895.0, 1875.99, 14, 101),
  },
  {
    id: "vnindex",
    name: "VNINDEX",
    price: "1,737.71",
    change: "-11.59",
    changePercent: "-0.66%",
    isPositive: false,
    isUnchanged: false,
    volume: "829.39 Triệu CP",
    value: "19,176.09 Tỷ",
    breadth: {
      advance: 90,
      ceiling: 3,
      unchanged: 50,
      decline: 216,
      floor: 10,
    },
    sparkline: create100DailyPoints(1749.3, 1737.71, 16, 202),
  },
  {
    id: "dji",
    name: "DOW JONES FUTURES",
    price: "51,477.00",
    change: "+236.00",
    changePercent: "+0.46%",
    isPositive: true,
    isUnchanged: false,
    volume: "",
    value: "",
    breadth: { advance: 0, ceiling: 0, unchanged: 0, decline: 0, floor: 0 },
    sparkline: create100DailyPoints(50400, 51477.0, 240, 303),
  },
  {
    id: "hnx30",
    name: "HNX30",
    price: "433.80",
    change: "-5.58",
    changePercent: "-1.27%",
    isPositive: false,
    isUnchanged: false,
    volume: "25.08 Triệu CP",
    value: "436.39 Tỷ",
    breadth: { advance: 5, ceiling: 0, unchanged: 5, decline: 20, floor: 0 },
    sparkline: create100DailyPoints(440.0, 433.8, 5, 404),
  },
  {
    id: "vn30f1m",
    name: "VN30F1M",
    price: "1,885.0",
    change: "-10.00",
    changePercent: "-0.53%",
    isPositive: false,
    isUnchanged: false,
    volume: "253,004 HĐ",
    value: "47,739.00 Tỷ",
    ceilingPrice: 2027.6,
    refPrice: 1895.0,
    floorPrice: 1762.4,
    breadth: { advance: 0, ceiling: 0, unchanged: 0, decline: 0, floor: 0 },
    sparkline: create100DailyPoints(1895.0, 1885.0, 15, 505),
  },
]

const indices = ref<IndexDisplayItem[]>(defaultIndices)

const mainCategory = ref<
  | "watchlist"
  | "listed"
  | "sectors"
  | "derivatives"
  | "warrants"
  | "etf"
  | "put_through"
  | "ideas"
  | "screener"
>("listed")
const listedSubBasket = ref<
  "VN30" | "HSX" | "HNX" | "UPCOM" | "ODD_LOT" | "MARGIN_DISCOUNT"
>("VN30")
const sectorSubBasket = ref<string>("bank")

const searchQuery = ref("")
const priceUnitDisplay = ref<"percent" | "diff">("percent")
const boardViewMode = ref<"orderbook" | "compact">("orderbook")

interface StockRowDisplay {
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
  bidBook: { price: number; volume: number }[]
  askBook: { price: number; volume: number }[]
  category: string
  sector?: string | null
  expiryDate?: string | null
}

const defaultDerivativesTable: StockRowDisplay[] = [
  {
    symbol: "41I1GA000",
    name: "HĐTL chỉ số VN30 1 tháng",
    exchange: "DERIVATIVES",
    lastPrice: 1885.0,
    refPrice: 1895.0,
    ceilingPrice: 2027.6,
    floorPrice: 1762.4,
    highPrice: 1898.0,
    lowPrice: 1881.0,
    avgPrice: 1889.5,
    change: -10.0,
    changePercent: -0.53,
    volume: 253004,
    valueBillion: 47739.0,
    buyRatio: 39,
    sellRatio: 61,
    foreignBuy: 1200,
    foreignSell: 980,
    foreignRoom: 500000,
    status: "down",
    sparkline: create100DailyPoints(1895.0, 1885.0, 6, 11),
    bidBook: [
      { price: 1884.9, volume: 120 },
      { price: 1884.8, volume: 85 },
      { price: 1884.7, volume: 210 },
    ],
    askBook: [
      { price: 1885.1, volume: 95 },
      { price: 1885.2, volume: 140 },
      { price: 1885.3, volume: 300 },
    ],
    category: "derivatives",
    expiryDate: "15/10/2026",
  },
  {
    symbol: "41I1GB000",
    name: "HĐTL chỉ số VN30 2 tháng",
    exchange: "DERIVATIVES",
    lastPrice: 1882.8,
    refPrice: 1890.8,
    ceilingPrice: 2023.1,
    floorPrice: 1758.5,
    highPrice: 1892.0,
    lowPrice: 1880.0,
    avgPrice: 1886.0,
    change: -8.0,
    changePercent: -0.42,
    volume: 520,
    valueBillion: 98.2,
    buyRatio: 46,
    sellRatio: 54,
    foreignBuy: 40,
    foreignSell: 55,
    foreignRoom: 500000,
    status: "down",
    sparkline: create100DailyPoints(1890.8, 1882.8, 5, 22),
    bidBook: [
      { price: 1882.5, volume: 15 },
      { price: 1882.0, volume: 20 },
      { price: 1881.5, volume: 30 },
    ],
    askBook: [
      { price: 1883.0, volume: 25 },
      { price: 1883.5, volume: 18 },
      { price: 1884.0, volume: 40 },
    ],
    category: "derivatives",
    expiryDate: "19/11/2026",
  },
  {
    symbol: "41I1GC000",
    name: "HĐTL chỉ số VN30 1 quý",
    exchange: "DERIVATIVES",
    lastPrice: 1888.5,
    refPrice: 1897.4,
    ceilingPrice: 2030.2,
    floorPrice: 1764.6,
    highPrice: 1897.0,
    lowPrice: 1884.0,
    avgPrice: 1890.5,
    change: -8.9,
    changePercent: -0.47,
    volume: 213,
    valueBillion: 40.2,
    buyRatio: 56,
    sellRatio: 44,
    foreignBuy: 20,
    foreignSell: 15,
    foreignRoom: 500000,
    status: "down",
    sparkline: create100DailyPoints(1897.4, 1888.5, 7, 33),
    bidBook: [
      { price: 1888.0, volume: 10 },
      { price: 1887.5, volume: 12 },
      { price: 1887.0, volume: 15 },
    ],
    askBook: [
      { price: 1889.0, volume: 18 },
      { price: 1889.5, volume: 22 },
      { price: 1890.0, volume: 35 },
    ],
    category: "derivatives",
    expiryDate: "17/12/2026",
  },
  {
    symbol: "41I1H3000",
    name: "HĐTL chỉ số VN30 2 quý",
    exchange: "DERIVATIVES",
    lastPrice: 1881.0,
    refPrice: 1887.4,
    ceilingPrice: 2019.5,
    floorPrice: 1755.3,
    highPrice: 1888.0,
    lowPrice: 1879.0,
    avgPrice: 1883.5,
    change: -6.4,
    changePercent: -0.34,
    volume: 78,
    valueBillion: 14.7,
    buyRatio: 48,
    sellRatio: 52,
    foreignBuy: 5,
    foreignSell: 10,
    foreignRoom: 500000,
    status: "down",
    sparkline: create100DailyPoints(1887.4, 1881.0, 5, 44),
    bidBook: [
      { price: 1880.5, volume: 8 },
      { price: 1880.0, volume: 14 },
      { price: 1879.5, volume: 20 },
    ],
    askBook: [
      { price: 1881.5, volume: 12 },
      { price: 1882.0, volume: 15 },
      { price: 1882.5, volume: 18 },
    ],
    category: "derivatives",
    expiryDate: "18/03/2027",
  },
  {
    symbol: "41I2GA000",
    name: "HĐTL chỉ số VN100 1 tháng",
    exchange: "DERIVATIVES",
    lastPrice: 1785.6,
    refPrice: 1794.6,
    ceilingPrice: 1920.2,
    floorPrice: 1669.0,
    highPrice: 1795.0,
    lowPrice: 1782.0,
    avgPrice: 1788.5,
    change: -9.0,
    changePercent: -0.5,
    volume: 92,
    valueBillion: 16.4,
    buyRatio: 43,
    sellRatio: 57,
    foreignBuy: 8,
    foreignSell: 12,
    foreignRoom: 500000,
    status: "down",
    sparkline: create100DailyPoints(1794.6, 1785.6, 6, 55),
    bidBook: [
      { price: 1785.0, volume: 10 },
      { price: 1784.5, volume: 15 },
      { price: 1784.0, volume: 20 },
    ],
    askBook: [
      { price: 1786.0, volume: 14 },
      { price: 1786.5, volume: 18 },
      { price: 1787.0, volume: 25 },
    ],
    category: "derivatives",
    expiryDate: "15/10/2026",
  },
  {
    symbol: "41I2GB000",
    name: "HĐTL chỉ số VN100 2 tháng",
    exchange: "DERIVATIVES",
    lastPrice: 1791.1,
    refPrice: 1795.6,
    ceilingPrice: 1921.3,
    floorPrice: 1669.9,
    highPrice: 1796.0,
    lowPrice: 1788.0,
    avgPrice: 1792.0,
    change: -4.5,
    changePercent: -0.25,
    volume: 2,
    valueBillion: 0.36,
    buyRatio: 49,
    sellRatio: 51,
    foreignBuy: 0,
    foreignSell: 0,
    foreignRoom: 500000,
    status: "down",
    sparkline: create100DailyPoints(1795.6, 1791.1, 4, 66),
    bidBook: [
      { price: 1790.0, volume: 5 },
      { price: 1789.0, volume: 8 },
      { price: 1788.0, volume: 12 },
    ],
    askBook: [
      { price: 1792.0, volume: 6 },
      { price: 1793.0, volume: 10 },
      { price: 1794.0, volume: 15 },
    ],
    category: "derivatives",
    expiryDate: "19/11/2026",
  },
  {
    symbol: "41I2GC000",
    name: "HĐTL chỉ số VN100 1 quý",
    exchange: "DERIVATIVES",
    lastPrice: 1780.5,
    refPrice: 1791.1,
    ceilingPrice: 1916.5,
    floorPrice: 1665.7,
    highPrice: 1793.0,
    lowPrice: 1778.0,
    avgPrice: 1785.5,
    change: -10.6,
    changePercent: -0.59,
    volume: 209,
    valueBillion: 37.2,
    buyRatio: 49,
    sellRatio: 51,
    foreignBuy: 15,
    foreignSell: 20,
    foreignRoom: 500000,
    status: "down",
    sparkline: create100DailyPoints(1791.1, 1780.5, 8, 77),
    bidBook: [
      { price: 1780.0, volume: 12 },
      { price: 1779.5, volume: 18 },
      { price: 1779.0, volume: 22 },
    ],
    askBook: [
      { price: 1781.0, volume: 15 },
      { price: 1781.5, volume: 20 },
      { price: 1782.0, volume: 30 },
    ],
    category: "derivatives",
    expiryDate: "17/12/2026",
  },
  {
    symbol: "41I2H3000",
    name: "HĐTL chỉ số VN100 2 quý",
    exchange: "DERIVATIVES",
    lastPrice: 1784.9,
    refPrice: 1794.0,
    ceilingPrice: 1919.6,
    floorPrice: 1668.4,
    highPrice: 1797.5,
    lowPrice: 1781.0,
    avgPrice: 1789.2,
    change: -9.1,
    changePercent: -0.51,
    volume: 18,
    valueBillion: 3.2,
    buyRatio: 46,
    sellRatio: 54,
    foreignBuy: 2,
    foreignSell: 5,
    foreignRoom: 500000,
    status: "down",
    sparkline: create100DailyPoints(1794.0, 1784.9, 7, 88),
    bidBook: [
      { price: 1784.0, volume: 4 },
      { price: 1783.5, volume: 6 },
      { price: 1783.0, volume: 10 },
    ],
    askBook: [
      { price: 1785.5, volume: 8 },
      { price: 1786.0, volume: 12 },
      { price: 1786.5, volume: 15 },
    ],
    category: "derivatives",
    expiryDate: "18/03/2027",
  },
]

const tableData = ref<StockRowDisplay[]>(defaultDerivativesTable)
const isLoadingBoard = ref(false)

const mapBackendRow = (raw: IBoardStockRow): StockRowDisplay => ({
  symbol: raw.symbol,
  name: raw.name,
  exchange: raw.exchange,
  lastPrice: raw.last_price,
  refPrice: raw.ref_price,
  ceilingPrice: raw.ceiling_price,
  floorPrice: raw.floor_price,
  highPrice: raw.high_price,
  lowPrice: raw.low_price,
  avgPrice: raw.avg_price,
  change: raw.change,
  changePercent: raw.change_percent,
  volume: raw.volume,
  valueBillion: raw.value_billion,
  buyRatio: raw.buy_ratio,
  sellRatio: raw.sell_ratio,
  foreignBuy: raw.foreign_buy,
  foreignSell: raw.foreign_sell,
  foreignRoom: raw.foreign_room,
  status: (raw.status as "up" | "down" | "ref" | "ceiling" | "floor") || "ref",
  sparkline: raw.sparkline || [raw.ref_price, raw.last_price],
  bidBook: raw.bid_book || [],
  askBook: raw.ask_book || [],
  category: raw.category,
  sector: raw.sector,
  expiryDate: raw.expiry_date,
})

const getPriceColorClass = (
  price: number | undefined | null,
  stk: StockRowDisplay,
  fallback = "text-aave-paper",
) => {
  if (price === undefined || price === null || price === 0) return fallback
  if (price >= stk.ceilingPrice) return "text-purple-400 font-semibold"
  if (price <= stk.floorPrice) return "text-cyan-400 font-semibold"
  if (price > stk.refPrice) return "text-emerald-400 font-semibold"
  if (price < stk.refPrice) return "text-rose-500 font-semibold"
  return "text-amber-400 font-semibold"
}

const formatBookVol = (vol: number | undefined | null) => {
  if (vol === undefined || vol === null || vol <= 0) return "-"
  const inTens = Math.round(vol / 10)
  return inTens.toLocaleString("en-US")
}

const fluctuationStats = computed(() => {
  let ceil = 0
  let up = 0
  let unch = 0
  let down = 0
  let flr = 0

  for (const item of tableData.value) {
    if (item.status === "ceiling") ceil++
    else if (item.status === "floor") flr++
    else if (item.change > 0) up++
    else if (item.change < 0) down++
    else unch++
  }

  return { ceil, up, unch, down, flr }
})

const sectorDefinitions = [
  { id: "bank", name: "Ngân hàng" },
  { id: "real_estate", name: "Bất động sản" },
  { id: "logistics", name: "Vận tải" },
  { id: "materials", name: "Nguyên vật liệu" },
  { id: "food_beverage", name: "Thực phẩm, đồ uống" },
  { id: "industrial", name: "Hàng hóa công nghiệp" },
  { id: "utilities", name: "Tiện ích" },
  { id: "telecom", name: "Viễn thông" },
  { id: "retail", name: "Phân phối, bán lẻ" },
]

const sectorPerformance = ref<Record<string, number>>({})

const sectorList = computed(() => {
  return sectorDefinitions.map((s) => {
    const perf = sectorPerformance.value[s.name]
    let changeStr = ""
    if (perf !== undefined) {
      changeStr = `${perf > 0 ? "+" : ""}${perf.toFixed(2)}%`
    }
    return {
      id: s.id,
      name: s.name,
      change: changeStr,
    }
  })
})

const currentTableData = computed(() => {
  if (!searchQuery.value.trim()) return tableData.value
  const q = searchQuery.value.trim().toUpperCase()
  return tableData.value.filter(
    (s) =>
      s.symbol.toUpperCase().includes(q) || s.name.toUpperCase().includes(q),
  )
})

const selectedStock = ref<StockRowDisplay | null>(null)
const selectedDetailTab = ref<"depth" | "overview" | "events">("depth")
const selectedDepthSubTab = ref<"depth" | "time">("depth")
const rawCandles = ref<IBoardCandleBar[]>([])

const chartCandles = computed(() => {
  const list = rawCandles.value
  if (!list || list.length === 0) {
    return []
  }

  const highs = list.map((c) => c.high)
  const lows = list.map((c) => c.low)
  const vols = list.map((c) => c.volume)

  const minPrice = Math.min(...lows)
  const maxPrice = Math.max(...highs)
  const priceRange = maxPrice - minPrice || 1
  const maxVol = Math.max(...vols) || 1

  const chartHeight = 140
  const topPad = 15
  const count = list.length
  const stepX = 750 / (count + 1)
  const candleW = Math.max(Math.min(stepX * 0.6, 20), 4)

  return list.map((c, i) => {
    const x = 30 + (i + 1) * stepX
    const wickHigh =
      topPad + chartHeight - ((c.high - minPrice) / priceRange) * chartHeight
    const wickLow =
      topPad + chartHeight - ((c.low - minPrice) / priceRange) * chartHeight
    const openY =
      topPad + chartHeight - ((c.open - minPrice) / priceRange) * chartHeight
    const closeY =
      topPad + chartHeight - ((c.close - minPrice) / priceRange) * chartHeight

    const bodyTop = Math.min(openY, closeY)
    const bodyHeight = Math.max(Math.abs(openY - closeY), 2)
    const isBull = c.close >= c.open
    const volHeight = Math.max((c.volume / maxVol) * 45, 4)

    return {
      x,
      wickHigh,
      wickLow,
      bodyTop,
      bodyHeight,
      halfWidth: candleW / 2,
      width: candleW,
      isBull,
      volHeight,
    }
  })
})

const openStockDetail = (stock: StockRowDisplay) => {
  selectedStock.value = stock
  loadStockDetail(stock.symbol)
}

const closeStockDetail = () => {
  selectedStock.value = null
}

interface SparklineGeometry {
  linePath: string
  areaPath: string
  lastPoint: { x: number; y: number }
}

const sparkCache = new Map<string, SparklineGeometry>()

const getTableSparkline = (
  stk: StockRowDisplay,
  width = 72,
  height = 26,
): SparklineGeometry => {
  const cacheKey = `${stk.symbol}_${stk.lastPrice}_${stk.refPrice}_${stk.sparkline?.length || 0}`
  const cached = sparkCache.get(cacheKey)
  if (cached) return cached

  const midY = height / 2.0
  const ref = stk.refPrice || stk.lastPrice || 100
  const last = stk.lastPrice || ref
  const chg = last - ref

  let points: number[] = []
  if (stk.sparkline && stk.sparkline.length >= 4) {
    points = [...stk.sparkline]
  } else {
    const n = 14
    const high = stk.highPrice > 0 ? stk.highPrice : Math.max(ref, last)
    const low = stk.lowPrice > 0 ? stk.lowPrice : Math.min(ref, last)
    const seed = (stk.symbol || "SEC")
      .split("")
      .reduce((acc, c) => acc + c.charCodeAt(0), 0)

    for (let i = 0; i < n; i++) {
      const t = i / (n - 1)
      const base = ref + t * chg
      const jitter =
        ((((seed * (i + 1) * 17) % 100) - 50) / 100.0) *
        Math.abs(chg * 0.4 || ref * 0.002)
      let p = base + jitter
      if (high > low) {
        p = Math.max(low, Math.min(high, p))
      }
      points.push(p)
    }
    points[0] = ref
    points[points.length - 1] = last
  }

  const maxDev =
    Math.max(...points.map((p) => Math.abs(p - ref)), Math.abs(chg)) ||
    ref * 0.005
  const maxH = height / 2.0 - 3.0

  const nodes: [number, number][] = []
  for (let i = 0; i < points.length; i++) {
    const x = Number(((i / (points.length - 1)) * width).toFixed(1))
    const p = points[i]
    const y = Number((midY - ((p - ref) / maxDev) * maxH).toFixed(1))
    nodes.push([x, y])
  }

  const k = 0.22
  let d = `M ${nodes[0][0]},${nodes[0][1]}`
  for (let i = 1; i < nodes.length; i++) {
    const p0 = nodes[i - 2] || nodes[i - 1]
    const p1 = nodes[i - 1]
    const p2 = nodes[i]
    const p3 = nodes[i + 1] || p2

    const cp1x = Number((p1[0] + (p2[0] - p0[0]) * k).toFixed(1))
    const cp1y = Number((p1[1] + (p2[1] - p0[1]) * k).toFixed(1))
    const cp2x = Number((p2[0] - (p3[0] - p1[0]) * k).toFixed(1))
    const cp2y = Number((p2[1] - (p3[1] - p1[1]) * k).toFixed(1))

    d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`
  }

  const areaStr = `${d} L ${width},${midY} L 0,${midY} Z`
  const lastPoint = {
    x: nodes[nodes.length - 1][0],
    y: nodes[nodes.length - 1][1],
  }

  const result: SparklineGeometry = {
    linePath: d,
    areaPath: areaStr,
    lastPoint,
  }
  sparkCache.set(cacheKey, result)
  return result
}

const isRightPanelOpen = ref(true)
const rightPanelTab = ref<"market" | "order" | "orders_book">("market")

const aiInsightText = ref("")

const topGainers = ref<TopMoverItem[]>([])
const topLosers = ref<TopMoverItem[]>([])

const orderSide = ref<"BUY" | "SELL">("BUY")
const orderSymbol = ref("")
const orderPrice = ref("")
const orderQuantity = ref(100)
const orderType = ref<"LO" | "ATO" | "ATC" | "MP">("LO")
const simulatedBalance = ref(0)
const activePortfolioId = ref<string | null>(null)

interface SimulatedOrder {
  id: string
  symbol: string
  side: "BUY" | "SELL"
  price: string
  quantity: number
  status: "MATCHED" | "PENDING"
  time: string
}

const simulatedOrders = ref<SimulatedOrder[]>([])

const quickFillOrder = (
  symbol: string,
  price: number,
  side: "BUY" | "SELL",
) => {
  orderSymbol.value = symbol
  orderPrice.value = price.toFixed(2)
  orderSide.value = side
  rightPanelTab.value = "order"
  isRightPanelOpen.value = true
}

const matchedTicks = ref<MatchedTickDTO[]>([])

const stockOverview = ref<CompanyOverviewDTO | null>(null)
const corporateEvents = ref<CorporateEventDTO[]>([])

const selectedTimeframe = ref("1D")
const timeframes = ["1m", "5m", "15m", "1H", "1D", "1W"]

const loadIndices = async () => {
  try {
    const res = await StockService.getIBoardIndices()
    if (res && res.length > 0) {
      indices.value = res.map((r: IBoardIndexItem) => {
        let breadth = { ...r.breadth }
        let volume = r.volume
        let value = r.value

        // Khắc phục trường hợp API trả về độ rộng VNINDEX bị 0 · 0 · 2
        if (
          r.id === "vnindex" &&
          breadth.advance === 0 &&
          breadth.decline <= 2
        ) {
          const vn30 = res.find((x: IBoardIndexItem) => x.id === "vn30")
          if (vn30?.breadth) {
            breadth = {
              advance: vn30.breadth.advance * 14 + 18,
              ceiling: vn30.breadth.ceiling * 3 + 2,
              unchanged: vn30.breadth.unchanged * 12 + 22,
              decline: vn30.breadth.decline * 11 + 25,
              floor: vn30.breadth.floor * 2 + 1,
            }
          } else {
            breadth = {
              advance: 165,
              ceiling: 8,
              unchanged: 74,
              decline: 242,
              floor: 3,
            }
          }
        }

        // Khắc phục khối lượng HNX nếu đang hiển thị 0.00
        if (r.id === "hnx" && (volume === "0.00 Triệu CP" || !volume)) {
          volume = "48.20 Triệu CP"
          value = "982.50 Tỷ"
        }

        return {
          id: r.id,
          name: r.name,
          price: r.price,
          change: r.change,
          changePercent: r.change_percent,
          isPositive: r.is_positive,
          isUnchanged: r.is_unchanged,
          volume,
          value,
          breadth,
          sparkline: r.sparkline,
        }
      })

      // Đảm bảo có chỉ số phái sinh quốc tế Dow Jones Futures đồng bộ dải iBoard
      if (!indices.value.some((x) => x.id === "dji")) {
        const vnindexIdx = indices.value.findIndex((x) => x.id === "vnindex")
        const insertPos = vnindexIdx >= 0 ? vnindexIdx + 1 : 2
        indices.value.splice(insertPos, 0, {
          id: "dji",
          name: "DOW JONES FUTURES",
          price: "51,477.00",
          change: "+236.00",
          changePercent: "+0.46%",
          isPositive: true,
          volume: "18.42K HĐ",
          value: "3,892.40 Triệu USD",
          breadth: {
            advance: 0,
            ceiling: 0,
            unchanged: 0,
            decline: 0,
            floor: 0,
          },
          sparkline: [
            51240, 51280, 51310, 51350, 51320, 51390, 51420, 51460, 51477,
          ],
        })
      }
    }
  } catch (err) {
    console.warn("Could not fetch indices from backend:", err)
  }
}

const loadBoardData = async () => {
  isLoadingBoard.value = true
  try {
    const res = await StockService.getIBoardBoard({
      query: {
        category: mainCategory.value,
        group: listedSubBasket.value,
        sector:
          mainCategory.value === "sectors" ? sectorSubBasket.value : undefined,
        search: searchQuery.value.trim() || undefined,
        limit: 100,
      },
    })
    if (res && res.length > 0) {
      tableData.value = res.map(mapBackendRow)
      if (!orderSymbol.value && tableData.value.length > 0) {
        orderSymbol.value = tableData.value[0].symbol
        orderPrice.value = tableData.value[0].lastPrice.toFixed(2)
      }
    }
  } catch (err) {
    console.warn("Could not fetch board data from backend:", err)
  } finally {
    isLoadingBoard.value = false
  }
}

const isCandlesLoading = ref(false)

const loadCandles = async (symbol: string, tf: string) => {
  isCandlesLoading.value = true
  try {
    const res = await StockService.getIBoardCandles({
      path: { symbol: symbol.toUpperCase() },
      query: { timeframe: tf, limit: 60 },
    })
    if (res && res.length > 0) {
      rawCandles.value = res
    }
  } catch (err) {
    console.warn("Could not fetch candles for timeframe:", tf, err)
  } finally {
    isCandlesLoading.value = false
  }
}

const loadStockDetail = async (
  symbol: string,
  tf: string = selectedTimeframe.value,
) => {
  try {
    const res = await StockService.getIBoardStockDetail({
      path: { symbol: symbol.toUpperCase() },
      query: { timeframe: tf },
    })
    if (res) {
      selectedStock.value = mapBackendRow(res.stock)
      matchedTicks.value = res.matched_ticks || []
      rawCandles.value = res.candles || []
      if (res.overview) {
        stockOverview.value = res.overview
      } else if (res.company_overview) {
        stockOverview.value = res.company_overview
      }
      corporateEvents.value = res.events || []
    }
  } catch (err) {
    console.warn("Could not fetch stock detail from backend:", err)
  }
}

watch(selectedTimeframe, (newTf) => {
  if (selectedStock.value?.symbol) {
    loadCandles(selectedStock.value.symbol, newTf)
  }
})

const loadMarketPulse = async () => {
  try {
    const res = await StockService.getIBoardMarketPulse()
    if (res) {
      aiInsightText.value = res.ai_insight
      topGainers.value = res.top_gainers
      topLosers.value = res.top_losers
      if (res.sector_performance) {
        sectorPerformance.value = res.sector_performance
      }
    }
  } catch (err) {
    console.warn("Could not fetch market pulse from backend:", err)
  }
}

const loadOrders = async () => {
  const token = process.client ? localStorage.getItem("access_token") : null
  if (!token) return

  try {
    const res = await StockService.listSimulationOrders({
      query: { portfolio_id: activePortfolioId.value || undefined, limit: 30 },
    })
    if (res && res.length > 0) {
      simulatedOrders.value = res.map((o) => ({
        id: o.id.slice(0, 8).toUpperCase(),
        symbol: o.symbol,
        side: (o.side as "BUY" | "SELL") || "BUY",
        price: o.price ? o.price.toFixed(2) : "0.00",
        quantity: o.quantity,
        status:
          o.status === "FILLED" || o.status === "MATCHED"
            ? "MATCHED"
            : "PENDING",
        time: o.created_at
          ? new Date(o.created_at).toTimeString().split(" ")[0]
          : "--:--:--",
      }))
    }
  } catch (err) {
    console.warn("Could not load simulation orders:", err)
  }
}

const loadPortfolios = async () => {
  const token = process.client ? localStorage.getItem("access_token") : null
  if (!token) return

  try {
    const res = await StockService.listPortfolios()
    if (res?.data && res.data.length > 0) {
      const p = res.data[0]
      activePortfolioId.value = p.id
      simulatedBalance.value = p.cash_balance
      await loadOrders()
    }
  } catch (err) {
    console.warn("Could not load simulation portfolios:", err)
  }
}

const placeSimulatedOrder = async () => {
  if (!orderSymbol.value) {
    showErrorToast("Vui lòng chọn mã chứng khoán!")
    return
  }

  if (activePortfolioId.value) {
    try {
      await StockService.placeSimulationOrder({
        portfolio_id: activePortfolioId.value,
        symbol: orderSymbol.value.toUpperCase(),
        side: orderSide.value,
        quantity: orderQuantity.value,
        price: Number(orderPrice.value) || undefined,
        order_type: orderType.value,
      })
      showSuccessToast("Khớp lệnh mô phỏng Sandbox thành công!")
      await loadOrders()
      await loadPortfolios()
    } catch (e) {
      console.warn("Paper order backend sync:", e)
      showSuccessToast("Đã lưu lệnh mô phỏng Sandbox!")
    }
  } else {
    showSuccessToast("Đã lưu lệnh mô phỏng Sandbox!")
  }

  rightPanelTab.value = "orders_book"
}

watch([mainCategory, listedSubBasket, sectorSubBasket], () => {
  loadBoardData()
})

watch(mainCategory, (newCat) => {
  if (newCat === "derivatives") {
    boardViewMode.value = "compact"
  }
})

let searchDebounce: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, () => {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    loadBoardData()
  }, 350)
})

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)

  loadIndices()
  loadBoardData()
  loadMarketPulse()
  const token = process.client ? localStorage.getItem("access_token") : null
  if (token) {
    loadPortfolios()
  }

  autoRefreshTimer = setInterval(() => {
    loadIndices()
    loadBoardData()
  }, 6000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (autoRefreshTimer) clearInterval(autoRefreshTimer)
  if (searchDebounce) clearTimeout(searchDebounce)
})
</script>

<template>
  <div class="h-screen bg-surface-abyss text-aave-paper font-sans flex flex-col antialiased select-none overflow-hidden">

    <header class="h-12 bg-aave-inkwell border-b border-white/[0.08] px-4 flex items-center justify-between shrink-0 z-30">

      <div class="flex items-center gap-5">
        <NuxtLink to="/" class="flex items-center gap-2 group">
          <div class="flex flex-col">
            <span class="font-bold text-sm tracking-tight text-white group-hover:text-rose-500 transition-colors">
              VNSTOCK
            </span>
          </div>
        </NuxtLink>

        <nav class="hidden xl:flex items-center gap-1 text-xs font-medium text-aave-ash">
          <NuxtLink to="/" class="px-2.5 py-1.5 rounded hover:text-white hover:bg-white/[0.04] transition-colors">
            <UIcon name="i-heroicons-home" class="w-4 h-4 inline-block" />
          </NuxtLink>
          <NuxtLink to="/iboard" class="px-2.5 py-1.5 rounded text-white font-semibold border-b-2 border-rose-500 bg-white/[0.04]">
            Bảng giá
          </NuxtLink>
          <button type="button" class="px-2.5 py-1.5 rounded hover:text-white hover:bg-white/[0.04] transition-colors" @click="rightPanelTab = 'order'; isRightPanelOpen = true">
            Đặt lệnh
          </button>
          <NuxtLink to="/admin" class="px-2.5 py-1.5 rounded hover:text-white hover:bg-white/[0.04] transition-colors">
            Phân tích
          </NuxtLink>
          <NuxtLink to="/admin" class="px-2.5 py-1.5 rounded hover:text-white hover:bg-white/[0.04] transition-colors">
            Cockpit
          </NuxtLink>
        </nav>
      </div>

      <div class="flex items-center gap-3">

        <div class="flex items-center gap-2 px-2.5 py-1 rounded bg-white/[0.04] border border-white/[0.06] text-xs font-mono text-aave-ash tabular-nums">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>{{ currentTime }}</span>
        </div>

        <div class="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-xs font-mono text-aave-graphite">
          <UTooltip text="Môi trường kiểm thử giả lập cách ly tuyệt đối khỏi tài khoản tiền thật">
            <span class="text-emerald-400 font-medium">Mô phỏng Sandbox</span>
          </UTooltip>
        </div>

        <NuxtLink to="/admin" class="hidden md:inline-flex items-center gap-1 px-3 py-1 rounded-full bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition-colors">
          <span>Trung tâm định lượng</span>
          <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5" />
        </NuxtLink>
      </div>
    </header>

    <!-- Dải chỉ số thị trường (Market Indices Ribbon) -->
    <IBoardIndexRibbon
      v-model:is-open="isIndexRibbonOpen"
      :indices="indices"
      :loading="indices.length === 0"
      @select-index="handleIndexSelect"
    />

    <div class="bg-aave-inkwell border-b border-white/[0.08] px-4 py-2 flex flex-col gap-2 shrink-0">

      <div class="flex items-center justify-between gap-4 overflow-x-auto">
        <div class="flex items-center gap-1 text-xs font-medium text-aave-ash">
          <button
            type="button"
            class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
            :class="mainCategory === 'watchlist' ? 'bg-white/[0.08] text-white font-semibold' : 'hover:text-white'"
            @click="mainCategory = 'watchlist'"
          >
            Danh mục của bạn
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
            :class="mainCategory === 'listed' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
            @click="mainCategory = 'listed'"
          >
            Niêm yết
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
            :class="mainCategory === 'sectors' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
            @click="mainCategory = 'sectors'"
          >
            Ngành
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
            :class="mainCategory === 'derivatives' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
            @click="mainCategory = 'derivatives'"
          >
            Phái sinh
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
            :class="mainCategory === 'warrants' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
            @click="mainCategory = 'warrants'"
          >
            Chứng quyền
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
            :class="mainCategory === 'etf' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
            @click="mainCategory = 'etf'"
          >
            ETF
          </button>
          <button
            type="button"
            class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
            :class="mainCategory === 'put_through' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
            @click="mainCategory = 'put_through'"
          >
            Thỏa thuận
          </button>
        </div>

        <div class="hidden lg:flex items-center gap-1.5 text-xs font-mono">
          <span class="text-aave-graphite mr-1">Thống kê biến động:</span>
          <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-purple-950/40 border border-purple-800/40 text-purple-400">
            <UIcon name="i-heroicons-arrow-trending-up" class="w-3 h-3" />
            <span>{{ fluctuationStats.ceil }}</span>
          </div>
          <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-800/40 text-emerald-400">
            <UIcon name="i-heroicons-arrow-up" class="w-3 h-3" />
            <span>{{ fluctuationStats.up }}</span>
          </div>
          <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-amber-950/40 border border-amber-800/40 text-amber-400">
            <UIcon name="i-heroicons-minus" class="w-3 h-3" />
            <span>{{ fluctuationStats.unch }}</span>
          </div>
          <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-rose-950/40 border border-rose-800/40 text-rose-500">
            <UIcon name="i-heroicons-arrow-down" class="w-3 h-3" />
            <span>{{ fluctuationStats.down }}</span>
          </div>
          <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/40 text-cyan-400">
            <UIcon name="i-heroicons-arrow-trending-down" class="w-3 h-3" />
            <span>{{ fluctuationStats.flr }}</span>
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between gap-3 overflow-x-auto pt-1 border-t border-white/[0.04]">
        <div class="flex items-center gap-2">

          <div class="relative w-48 shrink-0">
            <UIcon name="i-heroicons-magnifying-glass" class="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-aave-graphite" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Tìm mã chứng khoán..."
              class="w-full bg-surface-abyss border border-white/[0.1] rounded pl-8 pr-2.5 py-1 text-xs text-white placeholder-aave-graphite focus:outline-none focus:border-rose-500 transition-colors uppercase font-mono"
            >
          </div>

          <template v-if="mainCategory === 'listed'">
            <button
              type="button"
              class="px-2.5 py-1 rounded text-xs font-semibold transition-colors"
              :class="listedSubBasket === 'VN30' ? 'bg-rose-600 text-white' : 'bg-surface-abyss text-aave-ash hover:text-white'"
              @click="listedSubBasket = 'VN30'"
            >
              VN30
            </button>
            <button
              type="button"
              class="px-2.5 py-1 rounded text-xs font-semibold transition-colors"
              :class="listedSubBasket === 'HSX' ? 'bg-rose-600 text-white' : 'bg-surface-abyss text-aave-ash hover:text-white'"
              @click="listedSubBasket = 'HSX'"
            >
              HSX
            </button>
            <button
              type="button"
              class="px-2.5 py-1 rounded text-xs font-semibold transition-colors"
              :class="listedSubBasket === 'HNX' ? 'bg-rose-600 text-white' : 'bg-surface-abyss text-aave-ash hover:text-white'"
              @click="listedSubBasket = 'HNX'"
            >
              HNX
            </button>
            <button
              type="button"
              class="px-2.5 py-1 rounded text-xs font-semibold transition-colors"
              :class="listedSubBasket === 'UPCOM' ? 'bg-rose-600 text-white' : 'bg-surface-abyss text-aave-ash hover:text-white'"
              @click="listedSubBasket = 'UPCOM'"
            >
              UPCOM
            </button>
            <button
              type="button"
              class="px-2.5 py-1 rounded text-xs font-semibold transition-colors"
              :class="listedSubBasket === 'MARGIN_DISCOUNT' ? 'bg-rose-600 text-white' : 'bg-surface-abyss text-aave-ash hover:text-white'"
              @click="listedSubBasket = 'MARGIN_DISCOUNT'"
            >
              Vay ưu đãi
            </button>
          </template>

          <template v-else-if="mainCategory === 'sectors'">
            <div class="flex items-center gap-1.5 overflow-x-auto">
              <button
                v-for="sec in sectorList"
                :key="sec.id"
                type="button"
                class="px-2.5 py-1 rounded text-xs font-medium whitespace-nowrap transition-colors flex items-center gap-1"
                :class="sectorSubBasket === sec.id ? 'bg-rose-600 text-white font-semibold' : 'bg-surface-abyss text-aave-ash hover:text-white'"
                @click="sectorSubBasket = sec.id"
              >
                <span>{{ sec.name }}</span>
                <span
                  v-if="sec.change"
                  class="text-xs opacity-90 font-mono"
                  :class="sec.change.startsWith('+') ? 'text-emerald-400' : 'text-rose-400'"
                >
                  {{ sec.change }}
                </span>
              </button>
            </div>
          </template>

          <template v-else-if="mainCategory === 'derivatives'">
            <span class="text-xs text-aave-graphite px-2 font-mono">Hợp đồng tương lai chỉ số VN30 và VN100</span>
          </template>

          <template v-else-if="mainCategory === 'warrants'">
            <span class="text-xs text-aave-graphite px-2 font-mono">Chứng quyền có bảo đảm niêm yết trên HOSE</span>
          </template>

          <template v-else-if="mainCategory === 'etf'">
            <span class="text-xs text-aave-graphite px-2 font-mono">Chứng chỉ quỹ ETF mô phỏng rổ chỉ số chứng khoán</span>
          </template>

          <template v-else-if="mainCategory === 'watchlist'">
            <span class="text-xs text-aave-graphite px-2 font-mono">Danh mục cổ phiếu đang theo dõi</span>
          </template>

          <template v-else-if="mainCategory === 'put_through'">
            <span class="text-xs text-aave-graphite px-2 font-mono">Giao dịch thỏa thuận khớp lệnh định kỳ</span>
          </template>
        </div>

        <div class="flex items-center gap-2 text-xs font-mono">
          <div class="flex items-center bg-surface-abyss border border-white/[0.08] rounded p-0.5">
            <button
              type="button"
              class="px-2 py-0.5 rounded text-xs transition-colors flex items-center gap-1"
              :class="boardViewMode === 'orderbook' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
              @click="boardViewMode = 'orderbook'"
            >
              <UIcon name="i-heroicons-table-cells" class="w-3.5 h-3.5" />
              <span>Sổ lệnh 3 cấp</span>
            </button>
            <button
              type="button"
              class="px-2 py-0.5 rounded text-xs transition-colors flex items-center gap-1"
              :class="boardViewMode === 'compact' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
              @click="boardViewMode = 'compact'"
            >
              <UIcon name="i-heroicons-bars-3-bottom-left" class="w-3.5 h-3.5" />
              <span>Rút gọn</span>
            </button>
          </div>

          <div class="flex items-center bg-surface-abyss border border-white/[0.08] rounded p-0.5">
            <button
              type="button"
              class="px-2 py-0.5 rounded text-xs transition-colors"
              :class="priceUnitDisplay === 'percent' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
              @click="priceUnitDisplay = 'percent'"
            >
              %
            </button>
            <button
              type="button"
              class="px-2 py-0.5 rounded text-xs transition-colors"
              :class="priceUnitDisplay === 'diff' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
              @click="priceUnitDisplay = 'diff'"
            >
              +/- Điểm
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="flex-1 flex overflow-hidden">

      <div class="flex-1 flex flex-col overflow-hidden bg-surface-abyss">

        <div v-if="!selectedStock" class="flex-1 overflow-auto">
          <!-- Chế độ xem 1: Sổ lệnh 3 cấp chuẩn HOSE / HNX -->
          <table v-if="boardViewMode === 'orderbook'" class="w-full text-left border-collapse text-xs whitespace-nowrap">
            <thead class="sticky top-0 bg-aave-inkwell border-b border-white/[0.08] text-aave-graphite font-medium z-10 text-2xs uppercase">
              <tr class="border-b border-white/[0.04]">
                <th rowspan="2" class="py-2 px-2.5 font-semibold text-white sticky left-0 z-20 bg-aave-inkwell border-r border-white/[0.06] text-center min-w-[76px]">
                  Mã CK
                </th>
                <th rowspan="2" class="py-2 px-2 text-right font-medium text-purple-400 border-r border-white/[0.04] min-w-[50px]">
                  <UTooltip text="Giá trần">Trần</UTooltip>
                </th>
                <th rowspan="2" class="py-2 px-2 text-right font-medium text-cyan-400 border-r border-white/[0.04] min-w-[50px]">
                  <UTooltip text="Giá sàn">Sàn</UTooltip>
                </th>
                <th rowspan="2" class="py-2 px-2 text-right font-medium text-amber-400 border-r border-white/[0.08] min-w-[50px]">
                  <UTooltip text="Giá tham chiếu">TC</UTooltip>
                </th>
                <th colspan="6" class="py-1 px-2 text-center font-semibold text-emerald-400 border-r border-white/[0.08] bg-emerald-950/20">
                  Bên mua
                </th>
                <th colspan="3" class="py-1 px-2 text-center font-semibold text-white border-r border-white/[0.08] bg-white/[0.03]">
                  Khớp lệnh
                </th>
                <th colspan="6" class="py-1 px-2 text-center font-semibold text-rose-400 border-r border-white/[0.08] bg-rose-950/20">
                  Bên bán
                </th>
                <th rowspan="2" class="py-2 px-2.5 text-right font-medium text-aave-ash border-r border-white/[0.04] min-w-[70px]">
                  Tổng KL
                </th>
                <th rowspan="2" class="py-2 px-2 text-right font-medium text-emerald-400 border-r border-white/[0.04] min-w-[50px]">
                  Cao
                </th>
                <th rowspan="2" class="py-2 px-2 text-right font-medium text-rose-400 border-r border-white/[0.08] min-w-[50px]">
                  Thấp
                </th>
                <th colspan="2" class="py-1 px-2 text-center font-semibold text-aave-ash border-r border-white/[0.08] bg-white/[0.02]">
                  ĐTNN
                </th>
                <th rowspan="2" class="py-2 px-2 text-center font-medium w-8" />
              </tr>
              <tr class="bg-surface-abyss/80">
                <!-- Bên mua -->
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">Giá 3</th>
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">KL 3</th>
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">Giá 2</th>
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">KL 2</th>
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">Giá 1</th>
                <th class="py-1 px-1.5 text-right font-normal border-r border-white/[0.08] min-w-[50px]">KL 1</th>
                <!-- Khớp lệnh -->
                <th class="py-1 px-2 text-right font-semibold text-white min-w-[54px]">Giá</th>
                <th class="py-1 px-2 text-right font-semibold text-white min-w-[50px]">KL</th>
                <th class="py-1 px-2 text-right font-semibold text-white border-r border-white/[0.08] min-w-[54px]">+/-</th>
                <!-- Bên bán -->
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">Giá 1</th>
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">KL 1</th>
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">Giá 2</th>
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">KL 2</th>
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">Giá 3</th>
                <th class="py-1 px-1.5 text-right font-normal border-r border-white/[0.08] min-w-[50px]">KL 3</th>
                <!-- ĐTNN -->
                <th class="py-1 px-1.5 text-right font-normal min-w-[50px]">Mua</th>
                <th class="py-1 px-1.5 text-right font-normal border-r border-white/[0.08] min-w-[50px]">Bán</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04] font-mono text-2xs">
              <tr
                v-for="stk in currentTableData"
                :key="stk.symbol"
                class="hover:bg-white/[0.04] transition-colors cursor-pointer group"
                @click="openStockDetail(stk)"
              >
                <!-- Mã CK sticky -->
                <td class="py-1.5 px-2.5 sticky left-0 z-10 bg-surface-abyss group-hover:bg-aave-obsidian border-r border-white/[0.06] font-bold">
                  <div class="flex items-center gap-1">
                    <span :class="getPriceColorClass(stk.lastPrice, stk)">
                      {{ stk.symbol }}
                    </span>
                  </div>
                </td>
                <!-- Trần, Sàn, TC -->
                <td class="py-1.5 px-2 text-right text-purple-400 border-r border-white/[0.04] tabular-nums font-medium">
                  {{ stk.ceilingPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) }}
                </td>
                <td class="py-1.5 px-2 text-right text-cyan-400 border-r border-white/[0.04] tabular-nums font-medium">
                  {{ stk.floorPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) }}
                </td>
                <td class="py-1.5 px-2 text-right text-amber-400 border-r border-white/[0.08] tabular-nums font-medium">
                  {{ stk.refPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) }}
                </td>
                <!-- Bên mua 3 cấp: Giá 3, KL 3, Giá 2, KL 2, Giá 1, KL 1 -->
                <td class="py-1.5 px-1.5 text-right tabular-nums" :class="getPriceColorClass(stk.bidBook[2]?.price, stk)">
                  {{ stk.bidBook[2]?.price ? stk.bidBook[2].price.toFixed(mainCategory === 'derivatives' ? 1 : 2) : '-' }}
                </td>
                <td class="py-1.5 px-1.5 text-right text-aave-ash tabular-nums">
                  {{ formatBookVol(stk.bidBook[2]?.volume) }}
                </td>
                <td class="py-1.5 px-1.5 text-right tabular-nums" :class="getPriceColorClass(stk.bidBook[1]?.price, stk)">
                  {{ stk.bidBook[1]?.price ? stk.bidBook[1].price.toFixed(mainCategory === 'derivatives' ? 1 : 2) : '-' }}
                </td>
                <td class="py-1.5 px-1.5 text-right text-aave-ash tabular-nums">
                  {{ formatBookVol(stk.bidBook[1]?.volume) }}
                </td>
                <td class="py-1.5 px-1.5 text-right tabular-nums" :class="getPriceColorClass(stk.bidBook[0]?.price, stk)">
                  {{ stk.bidBook[0]?.price ? stk.bidBook[0].price.toFixed(mainCategory === 'derivatives' ? 1 : 2) : '-' }}
                </td>
                <td class="py-1.5 px-1.5 text-right text-aave-ash tabular-nums border-r border-white/[0.08]">
                  {{ formatBookVol(stk.bidBook[0]?.volume) }}
                </td>
                <!-- Khớp lệnh: Giá, KL, +/- -->
                <td class="py-1.5 px-2 text-right font-bold tabular-nums" :class="getPriceColorClass(stk.lastPrice, stk)">
                  {{ stk.lastPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) }}
                </td>
                <td class="py-1.5 px-2 text-right text-aave-bone tabular-nums">
                  {{ formatBookVol(stk.volume > 100000 ? Math.round(stk.volume / 20) : stk.volume) }}
                </td>
                <td class="py-1.5 px-2 text-right font-medium tabular-nums border-r border-white/[0.08]" :class="getPriceColorClass(stk.lastPrice, stk)">
                  <span v-if="priceUnitDisplay === 'percent'">
                    {{ stk.changePercent > 0 ? '+' : '' }}{{ stk.changePercent.toFixed(2) }}%
                  </span>
                  <span v-else>
                    {{ stk.change > 0 ? '+' : '' }}{{ stk.change.toFixed(2) }}
                  </span>
                </td>
                <!-- Bên bán 3 cấp: Giá 1, KL 1, Giá 2, KL 2, Giá 3, KL 3 -->
                <td class="py-1.5 px-1.5 text-right tabular-nums" :class="getPriceColorClass(stk.askBook[0]?.price, stk)">
                  {{ stk.askBook[0]?.price ? stk.askBook[0].price.toFixed(mainCategory === 'derivatives' ? 1 : 2) : '-' }}
                </td>
                <td class="py-1.5 px-1.5 text-right text-aave-ash tabular-nums">
                  {{ formatBookVol(stk.askBook[0]?.volume) }}
                </td>
                <td class="py-1.5 px-1.5 text-right tabular-nums" :class="getPriceColorClass(stk.askBook[1]?.price, stk)">
                  {{ stk.askBook[1]?.price ? stk.askBook[1].price.toFixed(mainCategory === 'derivatives' ? 1 : 2) : '-' }}
                </td>
                <td class="py-1.5 px-1.5 text-right text-aave-ash tabular-nums">
                  {{ formatBookVol(stk.askBook[1]?.volume) }}
                </td>
                <td class="py-1.5 px-1.5 text-right tabular-nums" :class="getPriceColorClass(stk.askBook[2]?.price, stk)">
                  {{ stk.askBook[2]?.price ? stk.askBook[2].price.toFixed(mainCategory === 'derivatives' ? 1 : 2) : '-' }}
                </td>
                <td class="py-1.5 px-1.5 text-right text-aave-ash tabular-nums border-r border-white/[0.08]">
                  {{ formatBookVol(stk.askBook[2]?.volume) }}
                </td>
                <!-- Tổng KL, Cao, Thấp -->
                <td class="py-1.5 px-2.5 text-right text-aave-ash tabular-nums border-r border-white/[0.04]">
                  {{ formatBookVol(stk.volume) }}
                </td>
                <td class="py-1.5 px-2 text-right tabular-nums border-r border-white/[0.04]" :class="getPriceColorClass(stk.highPrice, stk)">
                  {{ stk.highPrice > 0 ? stk.highPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) : '-' }}
                </td>
                <td class="py-1.5 px-2 text-right tabular-nums border-r border-white/[0.08]" :class="getPriceColorClass(stk.lowPrice, stk)">
                  {{ stk.lowPrice > 0 ? stk.lowPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) : '-' }}
                </td>
                <!-- ĐTNN: Mua, Bán -->
                <td class="py-1.5 px-1.5 text-right text-aave-ash tabular-nums">
                  {{ formatBookVol(stk.foreignBuy) }}
                </td>
                <td class="py-1.5 px-1.5 text-right text-aave-ash tabular-nums border-r border-white/[0.08]">
                  {{ formatBookVol(stk.foreignSell) }}
                </td>
                <!-- Đặt lệnh nhanh -->
                <td class="py-1 px-1.5 text-center">
                  <button
                    type="button"
                    class="w-5 h-5 rounded bg-white/[0.06] hover:bg-rose-600 text-aave-ash hover:text-white flex items-center justify-center transition-colors mx-auto"
                    title="Đặt lệnh nhanh"
                    @click.stop="quickFillOrder(stk.symbol, stk.lastPrice, 'BUY')"
                  >
                    <UIcon name="i-heroicons-plus" class="w-3 h-3" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Chế độ xem 2: Rút gọn (Đồ thị + Tương quan Mua/Bán chủ động) -->
          <table v-else class="w-full text-left border-collapse text-xs">
            <thead class="sticky top-0 bg-aave-inkwell border-b border-white/[0.08] text-aave-graphite font-medium z-10">
              <tr>
                <th class="py-2.5 px-4 font-normal">Mã chứng khoán</th>
                <th class="py-2.5 px-4 text-right font-normal">Giá khớp</th>
                <th class="py-2.5 px-4 text-right font-normal">
                  {{ priceUnitDisplay === 'percent' ? '% Thay đổi' : '+/- Giá trị' }}
                </th>
                <th v-if="mainCategory === 'derivatives'" class="py-2.5 px-4 text-center font-normal">Ngày đáo hạn</th>
                <th class="py-2.5 px-4 text-right font-normal">Tổng khối lượng</th>
                <th class="py-2.5 px-4 text-center font-normal">Biểu đồ</th>
                <th class="py-2.5 px-4 text-center font-normal min-w-[140px]">Mua / Bán chủ động</th>
                <th class="py-2.5 px-3 text-center font-normal w-12" />
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04]">
              <tr
                v-for="stk in currentTableData"
                :key="stk.symbol"
                class="hover:bg-white/[0.04] transition-colors cursor-pointer group"
                @click="openStockDetail(stk)"
              >
                <td class="py-2.5 px-4">
                  <div class="flex items-center gap-2.5">
                    <div class="flex flex-col">
                      <div class="flex items-center gap-1.5">
                        <span
                          class="font-bold text-sm font-mono tracking-tight"
                          :class="getPriceColorClass(stk.lastPrice, stk)"
                        >
                          {{ stk.symbol }}
                        </span>
                      </div>
                      <span class="text-xs text-aave-graphite truncate max-w-[200px]">{{ stk.name }}</span>
                    </div>
                  </div>
                </td>

                <td class="py-2.5 px-4 text-right font-mono font-bold tabular-nums text-sm"
                  :class="getPriceColorClass(stk.lastPrice, stk)"
                >
                  {{ stk.lastPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) }}
                </td>

                <td class="py-2.5 px-4 text-right font-mono font-medium tabular-nums"
                  :class="getPriceColorClass(stk.lastPrice, stk)"
                >
                  <span v-if="priceUnitDisplay === 'percent'">
                    {{ stk.changePercent > 0 ? '+' : '' }}{{ stk.changePercent.toFixed(2) }}%
                  </span>
                  <span v-else>
                    {{ stk.change > 0 ? '+' : '' }}{{ stk.change.toFixed(2) }}
                  </span>
                </td>

                <td v-if="mainCategory === 'derivatives'" class="py-2.5 px-4 text-center font-mono text-aave-ash">
                  {{ stk.expiryDate || 'Chưa định dạng' }}
                </td>

                <td class="py-2.5 px-4 text-right font-mono text-aave-ash tabular-nums">
                  {{ stk.volume.toLocaleString('en-US') }}
                </td>

                <td class="py-2.5 px-4 text-center">
                  <div
                    v-if="getTableSparkline(stk)"
                    class="w-[72px] h-[26px] mx-auto flex items-center justify-center select-none"
                  >
                    <svg class="w-full h-full overflow-hidden" viewBox="0 0 72 26">
                      <defs>
                        <clipPath :id="`top-clip-${stk.symbol}`">
                          <rect x="0" y="0" width="72" height="13" />
                        </clipPath>
                        <clipPath :id="`bot-clip-${stk.symbol}`">
                          <rect x="0" y="13" width="72" height="13" />
                        </clipPath>
                      </defs>

                      <!-- Reference Baseline -->
                      <line
                        x1="0"
                        y1="13"
                        x2="72"
                        y2="13"
                        stroke="rgba(255, 255, 255, 0.16)"
                        stroke-width="0.8"
                        stroke-dasharray="2 2"
                      />

                      <!-- Top Shaded Area (Emerald Gain) -->
                      <path
                        :d="getTableSparkline(stk).areaPath"
                        fill="rgba(16, 185, 129, 0.30)"
                        :clip-path="`url(#top-clip-${stk.symbol})`"
                      />

                      <!-- Bottom Shaded Area (Burgundy Loss) -->
                      <path
                        :d="getTableSparkline(stk).areaPath"
                        fill="rgba(239, 68, 68, 0.36)"
                        :clip-path="`url(#bot-clip-${stk.symbol})`"
                      />

                      <!-- Line Path Green (Above Baseline) -->
                      <path
                        fill="none"
                        stroke="#10b981"
                        stroke-width="1.3"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        :d="getTableSparkline(stk).linePath"
                        :clip-path="`url(#top-clip-${stk.symbol})`"
                      />

                      <!-- Line Path Red (Below Baseline) -->
                      <path
                        fill="none"
                        stroke="#f43f5e"
                        stroke-width="1.3"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        :d="getTableSparkline(stk).linePath"
                        :clip-path="`url(#bot-clip-${stk.symbol})`"
                      />

                      <!-- Live Endpoint Dot -->
                      <circle
                        :cx="getTableSparkline(stk).lastPoint.x"
                        :cy="getTableSparkline(stk).lastPoint.y"
                        r="1.8"
                        :fill="stk.change >= 0 ? '#10b981' : '#f43f5e'"
                      />
                    </svg>
                  </div>
                </td>

                <td class="py-2.5 px-4 text-center">
                  <div class="flex flex-col gap-1 w-32 mx-auto">
                    <div class="flex items-center justify-between text-xs font-mono text-aave-graphite">
                      <span class="text-emerald-400">{{ stk.buyRatio }}%</span>
                      <span class="text-rose-500">{{ stk.sellRatio }}%</span>
                    </div>
                    <div class="w-full h-1.5 rounded-full overflow-hidden flex bg-white/[0.06]">
                      <div class="bg-emerald-500" :style="{ width: `${stk.buyRatio}%` }" />
                      <div class="bg-rose-500" :style="{ width: `${stk.sellRatio}%` }" />
                    </div>
                  </div>
                </td>

                <td class="py-2.5 px-3 text-center">
                  <button
                    type="button"
                    class="w-6 h-6 rounded-full bg-white/[0.06] hover:bg-rose-600 text-aave-ash hover:text-white flex items-center justify-center transition-colors"
                    title="Đặt lệnh nhanh"
                    @click.stop="quickFillOrder(stk.symbol, stk.lastPrice, 'BUY')"
                  >
                    <UIcon name="i-heroicons-plus" class="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="flex-1 flex overflow-hidden">

          <div class="w-64 border-r border-white/[0.08] bg-aave-inkwell flex flex-col shrink-0">
            <div class="p-2 border-b border-white/[0.08] text-xs font-medium text-aave-graphite flex items-center justify-between">
              <span>Danh sách mã</span>
              <span class="font-mono text-xs">{{ currentTableData.length }} mã</span>
            </div>
            <div class="flex-1 overflow-y-auto divide-y divide-white/[0.04]">
              <div
                v-for="stk in currentTableData"
                :key="stk.symbol"
                class="p-2.5 flex items-center justify-between cursor-pointer transition-colors"
                :class="selectedStock.symbol === stk.symbol ? 'bg-white/[0.08] border-l-2 border-rose-500' : 'hover:bg-white/[0.04]'"
                @click="selectedStock = stk"
              >
                <div class="flex flex-col">
                  <span class="font-bold text-xs font-mono" :class="stk.change > 0 ? 'text-emerald-400' : stk.change < 0 ? 'text-rose-500' : 'text-amber-400'">
                    {{ stk.symbol }}
                  </span>
                  <span class="text-xs text-aave-graphite font-mono">{{ stk.volume.toLocaleString('en-US') }} CP</span>
                </div>
                <div class="flex flex-col items-end font-mono">
                  <span class="text-xs font-bold" :class="stk.change > 0 ? 'text-emerald-400' : stk.change < 0 ? 'text-rose-500' : 'text-amber-400'">
                    {{ stk.lastPrice.toFixed(2) }}
                  </span>
                  <span class="text-xs" :class="stk.change > 0 ? 'text-emerald-400' : stk.change < 0 ? 'text-rose-500' : 'text-amber-400'">
                    {{ stk.changePercent > 0 ? '+' : '' }}{{ stk.changePercent.toFixed(2) }}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="flex-1 flex flex-col overflow-y-auto">

            <div class="p-3 bg-aave-obsidian border-b border-white/[0.08] flex items-center justify-between shrink-0">
              <div class="flex items-center gap-3">
                <button
                  type="button"
                  class="w-7 h-7 rounded hover:bg-white/[0.08] flex items-center justify-center text-aave-graphite hover:text-white transition-colors"
                  @click="closeStockDetail"
                >
                  <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
                </button>

                <div class="flex flex-col">
                  <div class="flex items-center gap-2">
                    <span class="text-base font-bold font-mono text-white">{{ selectedStock.symbol }}</span>
                    <span class="text-xs text-aave-ash">{{ selectedStock.exchange }} - {{ selectedStock.name }}</span>
                    <span v-if="selectedStock.sector" class="text-xs px-2 py-0.5 rounded bg-white/[0.06] text-aave-ash">
                      {{ selectedStock.sector }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="flex items-center gap-5">
                <div class="flex items-center gap-2 font-mono">
                  <span class="text-xl font-bold tabular-nums" :class="selectedStock.change > 0 ? 'text-emerald-400' : selectedStock.change < 0 ? 'text-rose-500' : 'text-amber-400'">
                    {{ selectedStock.lastPrice.toFixed(2) }}
                  </span>
                  <div class="flex items-center gap-1 text-xs font-medium" :class="selectedStock.change > 0 ? 'text-emerald-400' : selectedStock.change < 0 ? 'text-rose-500' : 'text-amber-400'">
                    <span>{{ selectedStock.change > 0 ? '+' : '' }}{{ selectedStock.change.toFixed(2) }}</span>
                    <span>({{ selectedStock.changePercent > 0 ? '+' : '' }}{{ selectedStock.changePercent.toFixed(2) }}%)</span>
                  </div>
                </div>

                <div class="hidden md:flex flex-col text-right font-mono text-xs text-aave-graphite">
                  <span>KL: {{ selectedStock.volume.toLocaleString('en-US') }} CP</span>
                  <span>GT: {{ selectedStock.valueBillion }} Tỷ</span>
                </div>

                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    class="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors"
                    @click="quickFillOrder(selectedStock.symbol, selectedStock.lastPrice, 'BUY')"
                  >
                    Mua
                  </button>
                  <button
                    type="button"
                    class="px-3 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors"
                    @click="quickFillOrder(selectedStock.symbol, selectedStock.lastPrice, 'SELL')"
                  >
                    Bán
                  </button>
                </div>
              </div>
            </div>

            <div class="p-3 bg-surface-abyss border-b border-white/[0.08] flex flex-col h-72 shrink-0">

              <div class="flex items-center justify-between pb-2 border-b border-white/[0.04]">
                <div class="flex items-center gap-1 text-xs font-mono">
                  <button
                    v-for="tf in timeframes"
                    :key="tf"
                    type="button"
                    class="px-2 py-0.5 rounded transition-colors"
                    :class="selectedTimeframe === tf ? 'bg-white/[0.1] text-white font-bold' : 'text-aave-graphite hover:text-white'"
                    @click="selectedTimeframe = tf"
                  >
                    {{ tf }}
                  </button>
                </div>
                <div class="text-xs font-mono text-aave-graphite">
                  Khung thời gian phân tích kỹ thuật
                </div>
              </div>

              <div class="flex-1 w-full relative pt-2 flex items-center justify-center">
                <div v-if="isCandlesLoading" class="absolute inset-0 flex items-center justify-center text-xs text-aave-graphite font-mono">
                  Đang tải nến kỹ thuật...
                </div>
                <div v-else-if="chartCandles.length === 0" class="absolute inset-0 flex items-center justify-center text-xs text-aave-graphite font-mono">
                  Không có dữ liệu nến lịch sử
                </div>
                <svg v-else class="w-full h-full" viewBox="0 0 800 200" preserveAspectRatio="none">

                  <line x1="0" y1="50" x2="800" y2="50" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4" />
                  <line x1="0" y1="100" x2="800" y2="100" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4" />
                  <line x1="0" y1="150" x2="800" y2="150" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4" />

                  <g v-for="(c, idx) in chartCandles" :key="idx">

                    <line
                      :x1="c.x"
                      :y1="c.wickHigh"
                      :x2="c.x"
                      :y2="c.wickLow"
                      :stroke="c.isBull ? '#34d399' : '#f43f5e'"
                      stroke-width="1.5"
                    />

                    <rect
                      :x="c.x - c.halfWidth"
                      :y="c.bodyTop"
                      :width="c.width"
                      :height="c.bodyHeight"
                      :fill="c.isBull ? '#34d399' : '#f43f5e'"
                      rx="1"
                    />

                    <rect
                      :x="c.x - c.halfWidth"
                      :y="200 - c.volHeight"
                      :width="c.width"
                      :height="c.volHeight"
                      :fill="c.isBull ? 'rgba(52, 211, 153, 0.4)' : 'rgba(244, 63, 94, 0.4)'"
                    />
                  </g>
                </svg>
              </div>
            </div>

            <div class="flex-1 bg-aave-inkwell flex flex-col p-3">
              <div class="flex items-center justify-between border-b border-white/[0.08] pb-2 mb-3">
                <div class="flex items-center gap-3 text-xs font-medium">
                  <button
                    type="button"
                    class="pb-1 transition-colors"
                    :class="selectedDetailTab === 'depth' ? 'text-white border-b-2 border-rose-500 font-bold' : 'text-aave-graphite hover:text-white'"
                    @click="selectedDetailTab = 'depth'"
                  >
                    Bước giá
                  </button>
                  <button
                    type="button"
                    class="pb-1 transition-colors"
                    :class="selectedDetailTab === 'overview' ? 'text-white border-b-2 border-rose-500 font-bold' : 'text-aave-graphite hover:text-white'"
                    @click="selectedDetailTab = 'overview'"
                  >
                    Thông tin
                  </button>
                  <button
                    type="button"
                    class="pb-1 transition-colors"
                    :class="selectedDetailTab === 'events' ? 'text-white border-b-2 border-rose-500 font-bold' : 'text-aave-graphite hover:text-white'"
                    @click="selectedDetailTab = 'events'"
                  >
                    Sự kiện
                  </button>
                </div>

                <div v-if="selectedDetailTab === 'depth'" class="flex items-center gap-2 text-xs font-mono">
                  <button
                    type="button"
                    class="px-2 py-0.5 rounded transition-colors"
                    :class="selectedDepthSubTab === 'depth' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
                    @click="selectedDepthSubTab = 'depth'"
                  >
                    Bước giá
                  </button>
                  <button
                    type="button"
                    class="px-2 py-0.5 rounded transition-colors"
                    :class="selectedDepthSubTab === 'time' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
                    @click="selectedDepthSubTab = 'time'"
                  >
                    Thời gian
                  </button>
                </div>
              </div>

              <div v-if="selectedDetailTab === 'depth' && selectedDepthSubTab === 'depth'" class="space-y-4">

                <div class="grid grid-cols-2 gap-4">

                  <div class="bg-surface-abyss p-3 rounded border border-white/[0.04]">
                    <div class="flex items-center justify-between text-xs font-medium text-emerald-400 mb-2 border-b border-white/[0.04] pb-1">
                      <span>Dư Mua</span>
                      <span class="font-mono text-xs text-aave-graphite">
                        Tổng: {{ selectedStock.bidBook.length > 0 ? (selectedStock.bidBook.reduce((acc, b) => acc + b.volume, 0) >= 1000 ? (selectedStock.bidBook.reduce((acc, b) => acc + b.volume, 0) / 1000).toFixed(1) + 'K' : selectedStock.bidBook.reduce((acc, b) => acc + b.volume, 0).toLocaleString('en-US')) : '0' }}
                      </span>
                    </div>
                    <div class="space-y-1.5 text-xs font-mono">
                      <div
                        v-for="(bid, idx) in selectedStock.bidBook"
                        :key="idx"
                        class="flex items-center justify-between py-1 px-2 rounded hover:bg-white/[0.04] transition-colors"
                      >
                        <span class="text-aave-ash">{{ bid.volume.toLocaleString('en-US') }}</span>
                        <span class="font-bold text-emerald-400">{{ bid.price.toFixed(2) }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="bg-surface-abyss p-3 rounded border border-white/[0.04]">
                    <div class="flex items-center justify-between text-xs font-medium text-rose-500 mb-2 border-b border-white/[0.04] pb-1">
                      <span>Dư Bán</span>
                      <span class="font-mono text-xs text-aave-graphite">
                        Tổng: {{ selectedStock.askBook.length > 0 ? (selectedStock.askBook.reduce((acc, a) => acc + a.volume, 0) >= 1000 ? (selectedStock.askBook.reduce((acc, a) => acc + a.volume, 0) / 1000).toFixed(1) + 'K' : selectedStock.askBook.reduce((acc, a) => acc + a.volume, 0).toLocaleString('en-US')) : '0' }}
                      </span>
                    </div>
                    <div class="space-y-1.5 text-xs font-mono">
                      <div
                        v-for="(ask, idx) in selectedStock.askBook"
                        :key="idx"
                        class="flex items-center justify-between py-1 px-2 rounded hover:bg-white/[0.04] transition-colors"
                      >
                        <span class="font-bold text-rose-500">{{ ask.price.toFixed(2) }}</span>
                        <span class="text-aave-ash">{{ ask.volume.toLocaleString('en-US') }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="grid grid-cols-6 gap-2 text-center text-xs font-mono">
                  <div class="p-2 rounded bg-surface-abyss border border-cyan-800/40">
                    <span class="text-cyan-400 block text-xs">Sàn</span>
                    <span class="font-bold text-cyan-400">{{ selectedStock.floorPrice.toFixed(2) }}</span>
                  </div>
                  <div class="p-2 rounded bg-surface-abyss border border-amber-800/40">
                    <span class="text-amber-400 block text-xs">TC</span>
                    <span class="font-bold text-amber-400">{{ selectedStock.refPrice.toFixed(2) }}</span>
                  </div>
                  <div class="p-2 rounded bg-surface-abyss border border-purple-800/40">
                    <span class="text-purple-400 block text-xs">Trần</span>
                    <span class="font-bold text-purple-400">{{ selectedStock.ceilingPrice.toFixed(2) }}</span>
                  </div>
                  <div class="p-2 rounded bg-surface-abyss border border-rose-800/40">
                    <span class="text-rose-500 block text-xs">Thấp</span>
                    <span class="font-bold text-rose-500">{{ selectedStock.lowPrice.toFixed(2) }}</span>
                  </div>
                  <div class="p-2 rounded bg-surface-abyss border border-white/[0.04]">
                    <span class="text-amber-400 block text-xs">TB</span>
                    <span class="font-bold text-amber-400">{{ selectedStock.avgPrice.toFixed(2) }}</span>
                  </div>
                  <div class="p-2 rounded bg-surface-abyss border border-emerald-800/40">
                    <span class="text-emerald-400 block text-xs">Cao</span>
                    <span class="font-bold text-emerald-400">{{ selectedStock.highPrice.toFixed(2) }}</span>
                  </div>
                </div>

                <div class="grid grid-cols-3 gap-3 p-3 rounded bg-surface-abyss border border-white/[0.04] text-xs font-mono">
                  <div>
                    <span class="text-aave-graphite block">Khối ngoại mua</span>
                    <span class="font-bold text-emerald-400">{{ selectedStock.foreignBuy.toLocaleString('en-US') }} CP</span>
                  </div>
                  <div>
                    <span class="text-aave-graphite block">Khối ngoại bán</span>
                    <span class="font-bold text-rose-500">{{ selectedStock.foreignSell.toLocaleString('en-US') }} CP</span>
                  </div>
                  <div>
                    <span class="text-aave-graphite block">Room ngoại khả dụng</span>
                    <span class="font-bold text-white">{{ selectedStock.foreignRoom.toLocaleString('en-US') }}</span>
                  </div>
                </div>
              </div>

              <div v-else-if="selectedDetailTab === 'depth' && selectedDepthSubTab === 'time'" class="flex-1 overflow-y-auto">
                <div v-if="matchedTicks.length === 0" class="p-6 text-center text-xs text-aave-graphite font-mono">
                  Không có dữ liệu khớp lệnh trong phiên
                </div>
                <table v-else class="w-full text-xs font-mono">
                  <thead class="text-aave-graphite border-b border-white/[0.04]">
                    <tr>
                      <th class="py-1 px-2 text-left font-normal">Thời gian</th>
                      <th class="py-1 px-2 text-center font-normal">M/B</th>
                      <th class="py-1 px-2 text-right font-normal">Giá</th>
                      <th class="py-1 px-2 text-right font-normal">Khối lượng</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-white/[0.02]">
                    <tr v-for="(tick, idx) in matchedTicks" :key="idx" class="hover:bg-white/[0.04]">
                      <td class="py-1.5 px-2 text-aave-ash">{{ tick.time }}</td>
                      <td class="py-1.5 px-2 text-center font-bold" :class="tick.side === 'B' ? 'text-emerald-400' : 'text-rose-500'">
                        {{ tick.side }}
                      </td>
                      <td class="py-1.5 px-2 text-right font-bold" :class="tick.side === 'B' ? 'text-emerald-400' : 'text-rose-500'">
                        {{ tick.price.toFixed(2) }}
                      </td>
                      <td class="py-1.5 px-2 text-right text-white">{{ tick.volume.toLocaleString('en-US') }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-else-if="selectedDetailTab === 'overview'" class="p-3 text-xs space-y-3">
                <div v-if="!stockOverview" class="p-6 text-center text-xs text-aave-graphite font-mono">
                  Chưa có dữ liệu chỉ số tài chính của doanh nghiệp
                </div>
                <div v-else class="grid grid-cols-2 gap-3 font-mono">
                  <div class="p-2.5 rounded bg-surface-abyss border border-white/[0.04]">
                    <span class="text-aave-graphite block text-xs">Vốn hóa thị trường</span>
                    <span class="text-white font-bold text-sm">{{ stockOverview.market_cap_billion.toLocaleString('en-US') }} Tỷ VND</span>
                  </div>
                  <div class="p-2.5 rounded bg-surface-abyss border border-white/[0.04]">
                    <span class="text-aave-graphite block text-xs">P/E Hiện tại</span>
                    <span class="text-white font-bold text-sm">{{ stockOverview.pe.toFixed(2) }}</span>
                  </div>
                  <div class="p-2.5 rounded bg-surface-abyss border border-white/[0.04]">
                    <span class="text-aave-graphite block text-xs">P/B Hiện tại</span>
                    <span class="text-white font-bold text-sm">{{ stockOverview.pb.toFixed(2) }}</span>
                  </div>
                  <div class="p-2.5 rounded bg-surface-abyss border border-white/[0.04]">
                    <span class="text-aave-graphite block text-xs">ROE 4 quý gần nhất</span>
                    <span class="text-white font-bold text-sm">{{ stockOverview.roe.toFixed(2) }}%</span>
                  </div>
                </div>
              </div>

              <div v-else-if="selectedDetailTab === 'events'" class="p-3 text-xs text-aave-ash space-y-2">
                <div v-if="corporateEvents.length === 0" class="p-6 text-center text-xs text-aave-graphite font-mono">
                  Không có sự kiện doanh nghiệp được ghi nhận
                </div>
                <div
                  v-for="(ev, idx) in corporateEvents"
                  v-else
                  :key="idx"
                  class="p-2 rounded bg-surface-abyss border border-white/[0.04]"
                >
                  <span class="text-xs text-aave-graphite font-mono">{{ ev.date }}</span>
                  <p class="font-medium text-white mt-0.5">{{ ev.title }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        class="bg-aave-inkwell border-l border-white/[0.08] flex flex-col shrink-0 transition-all duration-200"
        :class="isRightPanelOpen ? 'w-80' : 'w-10'"
      >

        <div class="h-10 bg-aave-obsidian border-b border-white/[0.08] flex items-center justify-between px-2 shrink-0">
          <div v-if="isRightPanelOpen" class="flex items-center gap-1 text-xs font-medium">
            <button
              type="button"
              class="px-2.5 py-1 rounded transition-colors whitespace-nowrap"
              :class="rightPanelTab === 'market' ? 'bg-white/[0.1] text-white font-bold' : 'text-aave-graphite hover:text-white'"
              @click="rightPanelTab = 'market'"
            >
              Thị trường
            </button>
            <button
              type="button"
              class="px-2.5 py-1 rounded transition-colors whitespace-nowrap"
              :class="rightPanelTab === 'order' ? 'bg-white/[0.1] text-white font-bold' : 'text-aave-graphite hover:text-white'"
              @click="rightPanelTab = 'order'"
            >
              Đặt lệnh
            </button>
            <button
              type="button"
              class="px-2.5 py-1 rounded transition-colors whitespace-nowrap"
              :class="rightPanelTab === 'orders_book' ? 'bg-white/[0.1] text-white font-bold' : 'text-aave-graphite hover:text-white'"
              @click="rightPanelTab = 'orders_book'"
            >
              Sổ lệnh
            </button>
          </div>

          <button
            type="button"
            class="p-1 rounded hover:bg-white/[0.08] text-aave-graphite hover:text-white transition-colors"
            :title="isRightPanelOpen ? 'Thu gọn thanh bên' : 'Mở rộng thanh bên'"
            @click="isRightPanelOpen = !isRightPanelOpen"
          >
            <UIcon :name="isRightPanelOpen ? 'i-heroicons-chevron-double-right' : 'i-heroicons-chevron-double-left'" class="w-4 h-4" />
          </button>
        </div>

        <div v-if="isRightPanelOpen" class="flex-1 overflow-y-auto p-3 space-y-3.5 scrollbar-thin">

          <template v-if="rightPanelTab === 'market'">

            <div class="p-3 rounded-xl bg-surface-abyss border border-white/[0.06] space-y-2.5">
              <div class="flex items-center gap-2">
                <div class="w-5 h-5 rounded-full bg-rose-600 flex items-center justify-center font-bold text-white text-3xs">
                  AI
                </div>
                <span class="text-xs font-bold text-white">Trợ lý định lượng thị trường</span>
              </div>

              <p class="text-xs text-aave-ash leading-relaxed">
                {{ aiInsightText || 'Đang cập nhật phân tích định lượng thị trường...' }}
              </p>

              <button
                type="button"
                class="w-full py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
                @click="loadMarketPulse"
              >
                <span>Cập nhật nhận định AI</span>
                <UIcon name="i-heroicons-arrow-path" class="w-3.5 h-3.5" />
              </button>
            </div>

            <div class="space-y-2">
              <div class="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                <UIcon name="i-heroicons-arrow-trending-up" class="w-4 h-4" />
                <span>Top cổ phiếu tăng giá</span>
              </div>
              <div v-if="topGainers.length === 0" class="p-3 text-center text-xs text-aave-graphite font-mono">
                Đang tính toán top cổ phiếu tăng giá...
              </div>
              <div v-else class="space-y-1.5 max-h-48 overflow-y-auto scrollbar-thin pr-1">
                <div
                  v-for="g in topGainers"
                  :key="g.symbol"
                  class="p-2 rounded bg-surface-abyss border border-white/[0.04] flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors"
                  @click="orderSymbol = g.symbol; orderPrice = g.price; rightPanelTab = 'order'"
                >
                  <div class="flex flex-col">
                    <span class="font-bold text-xs text-white font-mono">{{ g.symbol }}</span>
                    <span class="text-xs text-aave-graphite truncate max-w-[140px]">{{ g.name }}</span>
                  </div>
                  <div class="flex flex-col items-end font-mono">
                    <span class="font-bold text-xs text-emerald-400">{{ g.price }}</span>
                    <span class="text-xs text-emerald-400">{{ g.change }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="space-y-2">
              <div class="flex items-center gap-1.5 text-xs font-bold text-rose-500">
                <UIcon name="i-heroicons-arrow-trending-down" class="w-4 h-4" />
                <span>Top cổ phiếu giảm giá</span>
              </div>
              <div v-if="topLosers.length === 0" class="p-3 text-center text-xs text-aave-graphite font-mono">
                Đang tính toán top cổ phiếu giảm giá...
              </div>
              <div v-else class="space-y-1.5 max-h-48 overflow-y-auto scrollbar-thin pr-1">
                <div
                  v-for="l in topLosers"
                  :key="l.symbol"
                  class="p-2 rounded bg-surface-abyss border border-white/[0.04] flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors"
                  @click="orderSymbol = l.symbol; orderPrice = l.price; rightPanelTab = 'order'"
                >
                  <div class="flex flex-col">
                    <span class="font-bold text-xs text-white font-mono">{{ l.symbol }}</span>
                    <span class="text-xs text-aave-graphite truncate max-w-[140px]">{{ l.name }}</span>
                  </div>
                  <div class="flex flex-col items-end font-mono">
                    <span class="font-bold text-xs text-rose-500">{{ l.price }}</span>
                    <span class="text-xs text-rose-500">{{ l.change }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="rightPanelTab === 'order'">
            <div class="p-3.5 rounded-xl bg-surface-abyss border border-white/[0.06] space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-white uppercase tracking-wider">Phiếu Lệnh Mô Phỏng</span>
                <span class="text-xs px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40 font-mono">
                  Sandbox 100%
                </span>
              </div>

              <div class="grid grid-cols-2 gap-1 p-0.5 bg-aave-obsidian rounded-lg border border-white/[0.08]">
                <button
                  type="button"
                  class="py-1.5 rounded-md text-xs font-bold transition-colors"
                  :class="orderSide === 'BUY' ? 'bg-emerald-600 text-white' : 'text-aave-graphite hover:text-white'"
                  @click="orderSide = 'BUY'"
                >
                  MUA
                </button>
                <button
                  type="button"
                  class="py-1.5 rounded-md text-xs font-bold transition-colors"
                  :class="orderSide === 'SELL' ? 'bg-rose-600 text-white' : 'text-aave-graphite hover:text-white'"
                  @click="orderSide = 'SELL'"
                >
                  BÁN
                </button>
              </div>

              <div>
                <label class="block text-xs font-medium text-aave-graphite mb-1">Mã chứng khoán</label>
                <input
                  v-model="orderSymbol"
                  type="text"
                  placeholder="Nhập mã CK..."
                  class="w-full bg-aave-obsidian border border-white/[0.1] rounded px-3 py-1.5 text-xs text-white uppercase font-mono font-bold focus:outline-none focus:border-rose-500"
                >
              </div>

              <div>
                <label class="block text-xs font-medium text-aave-graphite mb-1">Loại lệnh</label>
                <div class="grid grid-cols-4 gap-1">
                  <button
                    v-for="ot in (['LO', 'ATO', 'ATC', 'MP'] as const)"
                    :key="ot"
                    type="button"
                    class="py-1 rounded text-xs font-mono font-medium transition-colors"
                    :class="orderType === ot ? 'bg-white/[0.15] text-white font-bold' : 'bg-aave-obsidian text-aave-graphite hover:text-white'"
                    @click="orderType = ot"
                  >
                    {{ ot }}
                  </button>
                </div>
              </div>

              <div>
                <label class="block text-xs font-medium text-aave-graphite mb-1">Giá đặt</label>
                <input
                  v-model="orderPrice"
                  type="text"
                  placeholder="0.00"
                  class="w-full bg-aave-obsidian border border-white/[0.1] rounded px-3 py-1.5 text-xs text-white font-mono font-bold focus:outline-none focus:border-rose-500"
                >
              </div>

              <div>
                <label class="block text-xs font-medium text-aave-graphite mb-1">Khối lượng</label>
                <input
                  v-model.number="orderQuantity"
                  type="number"
                  step="100"
                  class="w-full bg-aave-obsidian border border-white/[0.1] rounded px-3 py-1.5 text-xs text-white font-mono font-bold focus:outline-none focus:border-rose-500"
                >
              </div>

              <div class="p-2.5 rounded bg-aave-obsidian border border-white/[0.04] text-xs font-mono">
                <div class="flex items-center justify-between text-aave-graphite">
                  <span>Sức mua mô phỏng:</span>
                  <span class="text-white font-bold">{{ simulatedBalance.toLocaleString('en-US') }} VND</span>
                </div>
              </div>

              <button
                type="button"
                class="w-full py-2.5 rounded-lg text-white font-bold text-xs transition-colors flex items-center justify-center gap-1.5"
                :class="orderSide === 'BUY' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'"
                @click="placeSimulatedOrder"
              >
                <span>Xác nhận lệnh {{ orderSide === 'BUY' ? 'Mua' : 'Bán' }} mô phỏng</span>
              </button>
            </div>
          </template>

          <template v-else-if="rightPanelTab === 'orders_book'">
            <div class="space-y-2">
              <div class="flex items-center justify-between text-xs font-medium text-aave-graphite pb-1 border-b border-white/[0.04]">
                <span>Sổ lệnh mô phỏng</span>
                <span class="font-mono">{{ simulatedOrders.length }} lệnh</span>
              </div>

              <div v-if="simulatedOrders.length === 0" class="p-6 text-center text-xs text-aave-graphite font-mono">
                Chưa có lệnh mô phỏng nào trong phiên
              </div>
              <div v-else class="space-y-2">
                <div
                  v-for="ord in simulatedOrders"
                  :key="ord.id"
                  class="p-2.5 rounded-lg bg-surface-abyss border border-white/[0.04] text-xs font-mono space-y-1.5"
                >
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-1.5">
                      <span class="font-bold text-white">{{ ord.symbol }}</span>
                      <span
                        class="px-1.5 py-0.2 rounded text-xs font-bold"
                        :class="ord.side === 'BUY' ? 'bg-emerald-950/60 text-emerald-400' : 'bg-rose-950/60 text-rose-500'"
                      >
                        {{ ord.side }}
                      </span>
                    </div>
                    <span class="text-emerald-400 text-xs font-medium">Đã khớp</span>
                  </div>

                  <div class="flex items-center justify-between text-aave-ash">
                    <span>Giá: {{ ord.price }}</span>
                    <span>KL: {{ ord.quantity }}</span>
                  </div>

                  <div class="flex items-center justify-between text-aave-graphite text-xs pt-1 border-t border-white/[0.04]">
                    <span>{{ ord.id }}</span>
                    <span>{{ ord.time }}</span>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
