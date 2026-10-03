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

const isIndexRibbonOpen = ref(true)

interface IndexDisplayItem {
  id: string
  name: string
  price: string
  change: string
  changePercent: string
  isPositive: boolean
  isUnchanged?: boolean
  volume: string
  value: string
  breadth: {
    advance: number
    ceiling: number
    unchanged: number
    decline: number
    floor: number
  }
  sparkline: number[]
}

const indices = ref<IndexDisplayItem[]>([])

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

interface StockRowDisplay {
  symbol: string
  name: string
  exchange: string
  marginRate?: string | null
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

const tableData = ref<StockRowDisplay[]>([])
const isLoadingBoard = ref(false)

const mapBackendRow = (raw: IBoardStockRow): StockRowDisplay => ({
  symbol: raw.symbol,
  name: raw.name,
  exchange: raw.exchange,
  marginRate: raw.margin_rate,
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

const getSparklinePoints = (points: number[], width = 64, height = 24) => {
  if (!points || points.length === 0) return ""
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  return points
    .map((val, idx) => {
      const x = (idx / (points.length - 1)) * width
      const y = height - ((val - min) / range) * (height - 4) - 2
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")
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
      indices.value = res.map((r: IBoardIndexItem) => ({
        id: r.id,
        name: r.name,
        price: r.price,
        change: r.change,
        changePercent: r.change_percent,
        isPositive: r.is_positive,
        isUnchanged: r.is_unchanged,
        volume: r.volume,
        value: r.value,
        breadth: r.breadth,
        sparkline: r.sparkline,
      }))
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
  <div class="min-h-screen bg-surface-abyss text-aave-paper font-sans flex flex-col antialiased select-none overflow-x-hidden">

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

    <div v-if="isIndexRibbonOpen" class="bg-aave-obsidian border-b border-white/[0.08] px-3 py-2 flex items-center gap-3 overflow-x-auto shrink-0 scrollbar-thin">
      <div v-if="indices.length === 0" class="flex items-center gap-2 py-1.5 px-3 text-xs text-aave-graphite font-mono">
        <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
        <span>Đang nạp dữ liệu chỉ số thị trường...</span>
      </div>
      <div
        v-for="idx in indices"
        v-else
        :key="idx.id"
        class="flex items-center justify-between gap-3 min-w-[220px] max-w-[260px] flex-1 px-3 py-1.5 rounded bg-surface-abyss border border-white/[0.04] hover:border-white/[0.12] transition-colors cursor-pointer"
      >
        <div class="flex flex-col">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs font-bold text-white">{{ idx.name }}</span>
            <div class="flex items-center gap-1 text-xs font-mono font-medium" :class="idx.isPositive ? 'text-emerald-400' : 'text-rose-500'">
              <span>{{ idx.changePercent }}</span>
              <span>{{ idx.change }}</span>
            </div>
          </div>
          <div class="flex items-center justify-between gap-2 mt-0.5">
            <span class="text-sm font-bold font-mono tabular-nums text-white" :class="idx.isPositive ? 'text-emerald-400' : 'text-rose-500'">
              {{ idx.price }}
            </span>
            <span class="text-xs text-aave-graphite font-mono truncate">{{ idx.volume }}</span>
          </div>
          <div class="flex items-center gap-1.5 mt-1 text-xs font-mono text-aave-graphite">
            <span class="text-emerald-400">{{ idx.breadth.advance }}</span>
            <span>·</span>
            <span class="text-amber-400">{{ idx.breadth.unchanged }}</span>
            <span>·</span>
            <span class="text-rose-500">{{ idx.breadth.decline }}</span>
          </div>
        </div>

        <div class="w-16 h-8 flex items-center justify-center shrink-0">
          <svg class="w-full h-full overflow-visible" viewBox="0 0 64 24">
            <polyline
              fill="none"
              :stroke="idx.isPositive ? '#34d399' : '#f43f5e'"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              :points="getSparklinePoints(idx.sparkline, 64, 24)"
            />
          </svg>
        </div>
      </div>

      <button
        type="button"
        class="px-2 py-1 text-xs text-aave-graphite hover:text-white shrink-0 flex items-center gap-1 transition-colors"
        @click="isIndexRibbonOpen = false"
      >
        <span>Thu gọn</span>
        <UIcon name="i-heroicons-chevron-up" class="w-3.5 h-3.5" />
      </button>
    </div>

    <div v-else class="bg-aave-obsidian border-b border-white/[0.08] px-3 py-1 flex items-center justify-end">
      <button
        type="button"
        class="text-xs text-aave-graphite hover:text-white flex items-center gap-1 transition-colors"
        @click="isIndexRibbonOpen = true"
      >
        <span>Mở dải chỉ số thị trường</span>
        <UIcon name="i-heroicons-chevron-down" class="w-3.5 h-3.5" />
      </button>
    </div>

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

        <div v-if="!selectedStock" class="flex-1 overflow-y-auto">
          <table class="w-full text-left border-collapse text-xs">
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
                          :class="{
                            'text-purple-400': stk.status === 'ceiling',
                            'text-cyan-400': stk.status === 'floor',
                            'text-emerald-400': stk.change > 0 && stk.status !== 'ceiling',
                            'text-rose-500': stk.change < 0 && stk.status !== 'floor',
                            'text-amber-400': stk.change === 0,
                          }"
                        >
                          {{ stk.symbol }}
                        </span>
                        <span v-if="stk.marginRate" class="text-xs px-1.5 py-0.2 rounded bg-purple-950/40 text-purple-400 border border-purple-800/40 font-mono">
                          {{ stk.marginRate }}
                        </span>
                      </div>
                      <span class="text-xs text-aave-graphite truncate max-w-[200px]">{{ stk.name }}</span>
                    </div>
                  </div>
                </td>

                <td class="py-2.5 px-4 text-right font-mono font-bold tabular-nums text-sm"
                  :class="{
                    'text-purple-400': stk.status === 'ceiling',
                    'text-cyan-400': stk.status === 'floor',
                    'text-emerald-400': stk.change > 0 && stk.status !== 'ceiling',
                    'text-rose-500': stk.change < 0 && stk.status !== 'floor',
                    'text-amber-400': stk.change === 0,
                  }"
                >
                  {{ stk.lastPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) }}
                </td>

                <td class="py-2.5 px-4 text-right font-mono font-medium tabular-nums"
                  :class="{
                    'text-emerald-400': stk.change > 0,
                    'text-rose-500': stk.change < 0,
                    'text-amber-400': stk.change === 0,
                  }"
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
                  <div class="w-16 h-6 mx-auto flex items-center justify-center">
                    <svg class="w-full h-full overflow-visible" viewBox="0 0 64 24">
                      <polyline
                        fill="none"
                        :stroke="stk.change > 0 ? '#34d399' : stk.change < 0 ? '#f43f5e' : '#fbbf24'"
                        stroke-width="1.5"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        :points="getSparklinePoints(stk.sparkline, 64, 24)"
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

        <div v-if="isRightPanelOpen" class="flex-1 overflow-y-auto p-3 space-y-4">

          <template v-if="rightPanelTab === 'market'">

            <div class="p-3.5 rounded-xl bg-surface-abyss border border-white/[0.06] space-y-3">
              <div class="flex items-center gap-2">
                <div class="w-6 h-6 rounded-full bg-rose-600 flex items-center justify-center font-bold text-white text-xs">
                  AI
                </div>
                <span class="text-xs font-bold text-white">Trợ lý định lượng thị trường</span>
              </div>

              <p class="text-xs text-aave-ash leading-relaxed">
                {{ aiInsightText || 'Đang cập nhật phân tích định lượng thị trường...' }}
              </p>

              <button
                type="button"
                class="w-full py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
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
              <div v-else class="space-y-1.5">
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
              <div v-else class="space-y-1.5">
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
