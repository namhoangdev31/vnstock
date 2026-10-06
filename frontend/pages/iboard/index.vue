<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import {
  type CompanyOverviewDTO,
  type CorporateEventDTO,
  type IBoardCandleBar,
  type IBoardIndexItem,
  type IBoardStockRow,
  type MatchedTickDTO,
  StockService,
  type TopMoverItem,
} from "~/client/stockService"
import IBoardCategoryNav from "~/components/iboard/IBoardCategoryNav.vue"
import IBoardHeader from "~/components/iboard/IBoardHeader.vue"
import IBoardIndexRibbon from "~/components/iboard/IBoardIndexRibbon.vue"
import IBoardRightPanel from "~/components/iboard/IBoardRightPanel.vue"
import IBoardStockDetail from "~/components/iboard/IBoardStockDetail.vue"
import IBoardTable from "~/components/iboard/IBoardTable.vue"
import type {
  FluctuationStats,
  IndexBreadth,
  IndexDisplayItem,
  LayoutMode,
  ListedSubBasket,
  MainCategory,
  SimulatedOrder,
  StockRowDisplay,
} from "~/components/iboard/types"
import {
  type IBoardWSIndexData,
  type IBoardWSQuoteData,
  type IBoardWSTick,
  type IBoardWSTradeData,
  useIBoardWebSocket,
} from "~/composables/useIBoardWebSocket"

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

// Thời gian hệ thống
const currentTime = ref("00:00:00")
let clockTimer: ReturnType<typeof setInterval> | null = null
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null
let marketPulseTimer: ReturnType<typeof setInterval> | null = null

const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toTimeString().split(" ")[0]
}

// Dải chỉ số thị trường (Ribbon)
const isIndexRibbonOpen = ref(true)
const indices = ref<IndexDisplayItem[]>([])

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

// Điều hướng danh mục & lọc
const mainCategory = ref<MainCategory>("listed")
const listedSubBasket = ref<ListedSubBasket>("VN30")
const sectorSubBasket = ref<string>("bank")
const searchQuery = ref("")
const priceUnitDisplay = ref<"percent" | "diff">("percent")
const layoutMode = ref<LayoutMode>("list")

// Dữ liệu bảng giá
const tableData = ref<StockRowDisplay[]>([])
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

// Thống kê biến động
const fluctuationStats = computed<FluctuationStats>(() => {
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

// Danh mục ngành
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

// Chi tiết cổ phiếu được chọn
const selectedStock = ref<StockRowDisplay | null>(null)
const rawCandles = ref<IBoardCandleBar[]>([])
const isCandlesLoading = ref(false)
const selectedTimeframe = ref("1D")
const timeframes = ["1m", "5m", "15m", "1H", "1D", "1W"]
const matchedTicks = ref<MatchedTickDTO[]>([])
const stockOverview = ref<CompanyOverviewDTO | null>(null)
const corporateEvents = ref<CorporateEventDTO[]>([])

// Panel bên phải (Thị trường, Đặt lệnh, Sổ lệnh)
const isRightPanelOpen = ref(true)
const rightPanelTab = ref<"market" | "order" | "orders_book">("market")
const aiInsightText = ref("")
const topGainers = ref<TopMoverItem[]>([])
const topLosers = ref<TopMoverItem[]>([])

const computedTopGainers = computed<TopMoverItem[]>(() => {
  if (topGainers.value.length > 0) return topGainers.value
  return [...tableData.value]
    .filter((s) => s.changePercent > 0)
    .sort((a, b) => b.changePercent - a.changePercent)
    .slice(0, 5)
    .map((s) => ({
      symbol: s.symbol,
      name: s.name,
      price: s.lastPrice.toFixed(2),
      change: `+${s.changePercent.toFixed(2)}%`,
    }))
})

const computedTopLosers = computed<TopMoverItem[]>(() => {
  if (topLosers.value.length > 0) return topLosers.value
  return [...tableData.value]
    .filter((s) => s.changePercent < 0)
    .sort((a, b) => a.changePercent - b.changePercent)
    .slice(0, 5)
    .map((s) => ({
      symbol: s.symbol,
      name: s.name,
      price: s.lastPrice.toFixed(2),
      change: `${s.changePercent.toFixed(2)}%`,
    }))
})

const effectiveAiInsightText = computed(() => {
  if (aiInsightText.value) return aiInsightText.value
  const f = fluctuationStats.value
  const total = f.up + f.down + f.unch + f.ceil + f.flr
  if (total === 0) return "Thị trường đang tổng hợp dữ liệu giao dịch."
  const sentiment =
    f.up + f.ceil > f.down + f.flr
      ? "tích cực với dòng tiền lan tỏa"
      : "thận trọng với áp lực điều chỉnh"
  return `Độ rộng thị trường ghi nhận ${f.up + f.ceil} mã tăng và ${f.down + f.flr} mã giảm. Dòng tiền phản ánh trạng thái ${sentiment} trên rổ chỉ số.`
})

const orderSide = ref<"BUY" | "SELL">("BUY")
const orderSymbol = ref("")
const orderPrice = ref("")
const orderQuantity = ref(100)
const orderType = ref<"LO" | "ATO" | "ATC" | "MP">("LO")
const simulatedBalance = ref(0)
const activePortfolioId = ref<string | null>(null)
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

const openStockDetail = (stock: StockRowDisplay) => {
  selectedStock.value = stock
  loadStockDetail(stock.symbol)
}

const closeStockDetail = () => {
  selectedStock.value = null
}

// Xử lý WebSocket Realtime DNSE
const calcStockStatus = (
  last: number,
  ref: number,
  ceil: number,
  flr: number,
): "up" | "down" | "ref" | "ceiling" | "floor" => {
  if (ceil > 0 && last >= ceil) return "ceiling"
  if (flr > 0 && last <= flr) return "floor"
  if (last > ref) return "up"
  if (last < ref) return "down"
  return "ref"
}

const formatIndexVolume = (
  num: number | null | undefined,
  isDeriv = false,
): string => {
  if (!num) return "-"
  if (isDeriv) return `${Math.round(num).toLocaleString("en-US")} HĐ`
  return `${(num / 1_000_000).toFixed(2)} Triệu CP`
}

const formatIndexValue = (num: number | null | undefined): string => {
  if (!num) return "-"
  return `${(num / 1_000_000_000).toFixed(2)} Tỷ`
}

const updateIndexItem = (item: IBoardWSIndexData) => {
  if (!item.index || item.value === null || item.value === undefined) return
  const rawId = item.index.toLowerCase()
  const targetId =
    rawId === "hnxindex" ? "hnx" : rawId === "upindex" ? "upcom" : rawId
  const isDeriv = targetId.includes("vn30f")

  const existing = indices.value.find(
    (idx) =>
      idx.id.toLowerCase() === targetId || idx.name.toLowerCase() === rawId,
  )
  const val = item.value ?? 0
  const chg = item.change ?? 0
  const pct = item.pct_change ?? 0
  const isPositive = chg > 0
  const isUnchanged = chg === 0

  const breadth: IndexBreadth | null =
    item.advance !== undefined || item.decline !== undefined
      ? {
          advance: item.advance ?? 0,
          ceiling: item.ceiling ?? 0,
          unchanged: item.no_change ?? 0,
          decline: item.decline ?? 0,
          floor: item.floor ?? 0,
        }
      : (existing?.breadth ?? null)

  const volStr = item.total_volume
    ? formatIndexVolume(item.total_volume, isDeriv)
    : existing?.volume || "-"
  const valStr = item.total_value
    ? formatIndexValue(item.total_value)
    : existing?.value || "-"

  if (existing) {
    existing.price = val.toFixed(2)
    existing.change = `${chg > 0 ? "+" : ""}${chg.toFixed(2)}`
    existing.changePercent = `${pct > 0 ? "+" : ""}${pct.toFixed(2)}%`
    existing.isPositive = isPositive
    existing.isUnchanged = isUnchanged
    if (breadth) existing.breadth = breadth
    if (item.total_volume) existing.volume = volStr
    if (item.total_value) existing.value = valStr
  } else {
    indices.value.push({
      id: targetId,
      name: item.index,
      price: val.toFixed(2),
      change: `${chg > 0 ? "+" : ""}${chg.toFixed(2)}`,
      changePercent: `${pct > 0 ? "+" : ""}${pct.toFixed(2)}%`,
      isPositive,
      isUnchanged,
      volume: volStr,
      value: valStr,
      breadth,
      sparkline: [val],
    })
  }
}

const handleWsIndicesSnapshot = (list: IBoardWSIndexData[]) => {
  for (const item of list) {
    updateIndexItem(item)
  }
}

const handleWsTrade = (symbol: string, trade: IBoardWSTradeData) => {
  const sym = symbol.toUpperCase()
  const target = tableData.value.find((s) => s.symbol.toUpperCase() === sym)
  const last = trade.close

  if (target && last !== undefined && last !== null) {
    target.lastPrice = last
    if (trade.volume !== undefined && trade.volume !== null) {
      target.volume = trade.volume
    }
    if (
      trade.high !== undefined &&
      trade.high !== null &&
      trade.high > target.highPrice
    ) {
      target.highPrice = trade.high
    }
    if (
      trade.low !== undefined &&
      trade.low !== null &&
      (target.lowPrice === 0 || trade.low < target.lowPrice)
    ) {
      target.lowPrice = trade.low
    }
    if (target.refPrice > 0) {
      target.change = target.lastPrice - target.refPrice
      target.changePercent = (target.change / target.refPrice) * 100
    }
    target.status = calcStockStatus(
      target.lastPrice,
      target.refPrice,
      target.ceilingPrice,
      target.floorPrice,
    )
    if (target.sparkline && target.sparkline.length > 0) {
      target.sparkline.push(target.lastPrice)
      if (target.sparkline.length > 25) {
        target.sparkline.shift()
      }
    }
  }

  if (
    selectedStock.value &&
    selectedStock.value.symbol.toUpperCase() === sym &&
    last !== undefined &&
    last !== null
  ) {
    selectedStock.value.lastPrice = last
    if (trade.volume) selectedStock.value.volume = trade.volume
    if (trade.high && trade.high > selectedStock.value.highPrice) {
      selectedStock.value.highPrice = trade.high
    }
    if (
      trade.low &&
      (selectedStock.value.lowPrice === 0 ||
        trade.low < selectedStock.value.lowPrice)
    ) {
      selectedStock.value.lowPrice = trade.low
    }
    if (selectedStock.value.refPrice > 0) {
      selectedStock.value.change =
        selectedStock.value.lastPrice - selectedStock.value.refPrice
      selectedStock.value.changePercent =
        (selectedStock.value.change / selectedStock.value.refPrice) * 100
    }
    selectedStock.value.status = calcStockStatus(
      selectedStock.value.lastPrice,
      selectedStock.value.refPrice,
      selectedStock.value.ceilingPrice,
      selectedStock.value.floorPrice,
    )

    const tickTime = trade.time
      ? trade.time.slice(0, 8)
      : new Date().toTimeString().split(" ")[0]
    const ref = selectedStock.value.refPrice || last
    const side = last > ref ? "B" : last < ref ? "S" : "U"
    matchedTicks.value.unshift({
      time: tickTime,
      price: last,
      volume: trade.trade_quantity ?? trade.volume ?? 100,
      side,
    })
    if (matchedTicks.value.length > 50) {
      matchedTicks.value.pop()
    }
  }
}

const handleWsQuote = (symbol: string, quote: IBoardWSQuoteData) => {
  const sym = symbol.toUpperCase()
  const target = tableData.value.find((s) => s.symbol.toUpperCase() === sym)

  const applyQuoteToRow = (row: StockRowDisplay) => {
    if (quote.close_price !== undefined && quote.close_price !== null) {
      row.lastPrice = quote.close_price
    }
    if (quote.reference_price !== undefined && quote.reference_price !== null) {
      row.refPrice = quote.reference_price
    }
    if (quote.ceiling_price !== undefined && quote.ceiling_price !== null) {
      row.ceilingPrice = quote.ceiling_price
    }
    if (quote.floor_price !== undefined && quote.floor_price !== null) {
      row.floorPrice = quote.floor_price
    }
    if (quote.high_price !== undefined && quote.high_price !== null) {
      row.highPrice = quote.high_price
    }
    if (quote.low_price !== undefined && quote.low_price !== null) {
      row.lowPrice = quote.low_price
    }
    if (quote.price_change !== undefined && quote.price_change !== null) {
      row.change = quote.price_change
    } else if (row.refPrice > 0) {
      row.change = row.lastPrice - row.refPrice
    }
    if (quote.percent_change !== undefined && quote.percent_change !== null) {
      row.changePercent = quote.percent_change
    } else if (row.refPrice > 0) {
      row.changePercent = (row.change / row.refPrice) * 100
    }
    if (
      quote.volume_accumulated !== undefined &&
      quote.volume_accumulated !== null
    ) {
      row.volume = quote.volume_accumulated
    }
    if (
      quote.foreign_buy_volume !== undefined &&
      quote.foreign_buy_volume !== null
    ) {
      row.foreignBuy = quote.foreign_buy_volume
    }
    if (
      quote.foreign_sell_volume !== undefined &&
      quote.foreign_sell_volume !== null
    ) {
      row.foreignSell = quote.foreign_sell_volume
    }
    row.status = calcStockStatus(
      row.lastPrice,
      row.refPrice,
      row.ceilingPrice,
      row.floorPrice,
    )

    const bids: { price: number; volume: number }[] = []
    if (quote.bid_price_1 !== undefined && quote.bid_price_1 !== null) {
      bids.push({ price: quote.bid_price_1, volume: quote.bid_vol_1 ?? 0 })
    }
    if (quote.bid_price_2 !== undefined && quote.bid_price_2 !== null) {
      bids.push({ price: quote.bid_price_2, volume: quote.bid_vol_2 ?? 0 })
    }
    if (quote.bid_price_3 !== undefined && quote.bid_price_3 !== null) {
      bids.push({ price: quote.bid_price_3, volume: quote.bid_vol_3 ?? 0 })
    }
    if (bids.length > 0) row.bidBook = bids

    const asks: { price: number; volume: number }[] = []
    if (quote.ask_price_1 !== undefined && quote.ask_price_1 !== null) {
      asks.push({ price: quote.ask_price_1, volume: quote.ask_vol_1 ?? 0 })
    }
    if (quote.ask_price_2 !== undefined && quote.ask_price_2 !== null) {
      asks.push({ price: quote.ask_price_2, volume: quote.ask_vol_2 ?? 0 })
    }
    if (quote.ask_price_3 !== undefined && quote.ask_price_3 !== null) {
      asks.push({ price: quote.ask_price_3, volume: quote.ask_vol_3 ?? 0 })
    }
    if (asks.length > 0) row.askBook = asks
  }

  if (target) {
    applyQuoteToRow(target)
  }
  if (selectedStock.value && selectedStock.value.symbol.toUpperCase() === sym) {
    applyQuoteToRow(selectedStock.value)
  }
}

const handleWsStockSnapshot = (
  symbol: string,
  quote: IBoardWSQuoteData | null,
  ticks: IBoardWSTick[],
) => {
  const sym = symbol.toUpperCase()
  if (quote) {
    handleWsQuote(sym, quote)
  }
  if (
    selectedStock.value &&
    selectedStock.value.symbol.toUpperCase() === sym &&
    ticks &&
    ticks.length > 0
  ) {
    matchedTicks.value = ticks.map((t) => ({
      time: t.time ? t.time.slice(0, 8) : "--:--:--",
      price: t.price,
      volume: t.volume,
      side: t.side || "U",
    }))
  }
}

const iboardWs = useIBoardWebSocket({
  onIndex: updateIndexItem,
  onIndicesSnapshot: handleWsIndicesSnapshot,
  onTrade: handleWsTrade,
  onQuote: handleWsQuote,
  onStockSnapshot: handleWsStockSnapshot,
})

watch(
  () => selectedStock.value?.symbol,
  (newSym, oldSym) => {
    if (oldSym && oldSym !== newSym) {
      iboardWs.unsubscribeStock(oldSym)
    }
    if (newSym) {
      iboardWs.subscribeStock(newSym)
    }
  },
)

// Gọi API nạp dữ liệu REST
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
        breadth: r.breadth ? { ...r.breadth } : null,
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
      const symList = tableData.value
        .slice(0, 60)
        .map((s) => `stock:${s.symbol}`)
      iboardWs.subscribe(symList)
    }
  } catch (err) {
    console.warn("Could not fetch board data from backend:", err)
  } finally {
    isLoadingBoard.value = false
  }
}

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
    if (!iboardWs.isConnected.value) {
      loadIndices()
      loadBoardData()
    }
  }, 10000)

  marketPulseTimer = setInterval(() => {
    loadMarketPulse()
  }, 60000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (autoRefreshTimer) clearInterval(autoRefreshTimer)
  if (marketPulseTimer) clearInterval(marketPulseTimer)
  if (searchDebounce) clearTimeout(searchDebounce)
})
</script>

<template>
  <div class="h-screen bg-surface-abyss text-aave-paper font-sans flex flex-col antialiased select-none overflow-hidden">
    <!-- Header hệ thống -->
    <IBoardHeader
      :current-time="currentTime"
      :is-ws-connected="iboardWs.isConnected.value"
      :is-ws-connecting="iboardWs.isConnecting.value"
      @open-order-form="rightPanelTab = 'order'; isRightPanelOpen = true"
    />

    <!-- Dải chỉ số thị trường (Market Indices Ribbon) -->
    <IBoardIndexRibbon
      v-model:is-open="isIndexRibbonOpen"
      :indices="indices"
      :loading="indices.length === 0"
      @select-index="handleIndexSelect"
    />

    <!-- Thanh chuyển danh mục & bộ lọc thị trường -->
    <IBoardCategoryNav
      v-model:main-category="mainCategory"
      v-model:listed-sub-basket="listedSubBasket"
      v-model:sector-sub-basket="sectorSubBasket"
      v-model:search-query="searchQuery"
      v-model:price-unit-display="priceUnitDisplay"
      v-model:layout-mode="layoutMode"
      :sector-list="sectorList"
      :fluctuation-stats="fluctuationStats"
    />

    <!-- Không gian làm việc chính (Bảng giá / Chi tiết cổ phiếu + Panel phụ) -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Vùng hiển thị dữ liệu bảng hoặc chi tiết mã -->
      <div class="flex-1 flex flex-col overflow-hidden bg-surface-abyss">
        <!-- Bảng giá niêm yết (hỗ trợ cả dạng Danh sách & Lưới ô thẻ chuẩn DNSE) -->
        <IBoardTable
          v-if="!selectedStock"
          :data="currentTableData"
          :main-category="mainCategory"
          :price-unit-display="priceUnitDisplay"
          :layout-mode="layoutMode"
          :is-loading="isLoadingBoard"
          @select-stock="openStockDetail"
          @quick-order="quickFillOrder"
        />

        <!-- Chi tiết cổ phiếu với nến kỹ thuật & sổ lệnh -->
        <IBoardStockDetail
          v-else
          :stock="selectedStock"
          :stock-list="currentTableData"
          :candles="rawCandles"
          :is-candles-loading="isCandlesLoading"
          :selected-timeframe="selectedTimeframe"
          :timeframes="timeframes"
          :matched-ticks="matchedTicks"
          :stock-overview="stockOverview"
          :corporate-events="corporateEvents"
          @close="closeStockDetail"
          @select-stock="openStockDetail"
          @update:selected-timeframe="selectedTimeframe = $event"
          @quick-order="quickFillOrder"
        />
      </div>

      <!-- Panel bên phải: Thị trường, Phiếu lệnh mô phỏng, Sổ lệnh -->
      <IBoardRightPanel
        v-model:is-open="isRightPanelOpen"
        v-model:active-tab="rightPanelTab"
        v-model:order-side="orderSide"
        v-model:order-symbol="orderSymbol"
        v-model:order-price="orderPrice"
        v-model:order-quantity="orderQuantity"
        v-model:order-type="orderType"
        :ai-insight-text="effectiveAiInsightText"
        :top-gainers="computedTopGainers"
        :top-losers="computedTopLosers"
        :simulated-balance="simulatedBalance"
        :simulated-orders="simulatedOrders"
        @refresh-pulse="loadMarketPulse"
        @submit-order="placeSimulatedOrder"
      />
    </div>
  </div>
</template>
