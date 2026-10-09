import { ref } from "vue"

export interface MarketTickerItem {
  id: string
  symbol: string
  name?: string
  price: number
  change: number
  changePercent: number
  isPositive: boolean
  isUnchanged: boolean
  volume?: string
  category: "index" | "derivative" | "stock"
  refPrice?: number
}

interface RawIndexItem {
  id: string
  name: string
  price: string | number
  change: string | number
  change_percent: string | number
  is_positive?: boolean
  is_unchanged?: boolean
  volume?: string
  value?: string
}

interface RawStockRow {
  symbol: string
  name?: string
  last_price: number
  ref_price?: number
  change: number
  change_percent: number
  volume?: number
  status?: string
}

interface WsMessage {
  type?: string
  index?: string
  symbol?: string
  data?: {
    value?: number | string
    price?: number | string
    last_price?: number | string
    change?: number | string
    pct_change?: number | string
    change_percent?: number | string
  }
}

const parseNum = (str: string | number | undefined | null): number => {
  if (typeof str === "number") return str
  if (!str) return 0
  const clean = String(str).replace(/,/g, "").replace("%", "").trim()
  const n = Number.parseFloat(clean)
  return Number.isNaN(n) ? 0 : n
}

export const useMarketTicker = () => {
  const items = useState<MarketTickerItem[]>("market_ticker_items", () => [])
  const isLoading = useState<boolean>("market_ticker_loading", () => false)
  const isPaused = useState<boolean>("market_ticker_paused", () => false)
  const isConnected = useState<boolean>("market_ticker_connected", () => false)
  const lastUpdated = useState<string | null>(
    "market_ticker_updated",
    () => null,
  )
  const selectedSymbol = useState<string>(
    "market_ticker_selected",
    () => "VN30F1M",
  )
  const flashMap = useState<Record<string, "up" | "down">>(
    "market_ticker_flashes",
    () => ({}),
  )

  let ws: WebSocket | null = null
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
  let jitterInterval: ReturnType<typeof setInterval> | null = null
  let pollInterval: ReturnType<typeof setInterval> | null = null
  let lastRealTickTime = 0

  const triggerFlash = (symbol: string, dir: "up" | "down") => {
    flashMap.value = {
      ...flashMap.value,
      [symbol]: dir,
    }

    setTimeout(() => {
      if (flashMap.value[symbol] === dir) {
        const copy = { ...flashMap.value }
        delete copy[symbol]
        flashMap.value = copy
      }
    }, 850)
  }

  const updateItemPrice = (
    symbol: string,
    newPrice: number,
    change?: number,
    changePercent?: number,
    shouldFlash = true,
  ) => {
    const item = items.value.find((i) => i.symbol === symbol)
    if (!item || Number.isNaN(newPrice) || newPrice <= 0) return

    const oldPrice = item.price
    item.price = Number(newPrice.toFixed(2))

    if (change !== undefined && !Number.isNaN(change)) {
      item.change = Number(change.toFixed(2))
    }
    if (changePercent !== undefined && !Number.isNaN(changePercent)) {
      item.changePercent = Number(changePercent.toFixed(2))
    }

    item.isPositive = item.change > 0
    item.isUnchanged = Math.abs(item.change) < 0.001

    if (shouldFlash && Math.abs(newPrice - oldPrice) > 0.001) {
      triggerFlash(symbol, newPrice > oldPrice ? "up" : "down")
    }
  }

  const handleWsMessage = (msg: WsMessage) => {
    if (!msg?.type) return

    if (msg.type === "index" && msg.index && msg.data) {
      lastRealTickTime = Date.now()
      let sym = String(msg.index).toUpperCase()
      if (sym === "HOSE") sym = "VNINDEX"
      if (sym === "HNXINDEX") sym = "HNX"

      const val = parseNum(msg.data.value)
      const chg = parseNum(msg.data.change)
      const pct = parseNum(msg.data.pct_change)
      if (val > 0) {
        updateItemPrice(sym, val, chg, pct, true)
      }
    } else if (
      (msg.type === "trade" || msg.type === "quote") &&
      msg.symbol &&
      msg.data
    ) {
      lastRealTickTime = Date.now()
      const sym = String(msg.symbol).toUpperCase()
      const price = parseNum(msg.data.price ?? msg.data.last_price)
      const chg = parseNum(msg.data.change)
      const pct = parseNum(msg.data.pct_change ?? msg.data.change_percent)

      if (price > 0) {
        updateItemPrice(sym, price, chg, pct, true)
      }
    }
  }

  const initWebSocket = () => {
    if (typeof window === "undefined") return

    const config = useRuntimeConfig()
    let wsBase = ""
    if (config.public?.apiUrl) {
      wsBase = (config.public.apiUrl as string)
        .replace(/^http/, "ws")
        .replace(/\/+$/, "")
    } else {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      const host = window.location.host
      wsBase = `${protocol}//${host}`
    }
    const wsUrl = `${wsBase}/api/v1/stock/iboard/ws`

    try {
      if (ws) {
        try {
          ws.close()
        } catch {
          // Ignore
        }
        ws = null
      }

      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        isConnected.value = true
        ws?.send(
          JSON.stringify({
            action: "subscribe",
            channels: ["indices", "board"],
          }),
        )
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WsMessage
          handleWsMessage(msg)
        } catch (err) {
          console.debug("[useMarketTicker] WS JSON parse error:", err)
        }
      }

      ws.onerror = () => {
        isConnected.value = false
      }

      ws.onclose = () => {
        isConnected.value = false
        if (!reconnectTimeout) {
          reconnectTimeout = setTimeout(() => {
            reconnectTimeout = null
            initWebSocket()
          }, 4000)
        }
      }
    } catch (err) {
      console.debug("[useMarketTicker] Failed to initialize WS:", err)
    }
  }

  // Khởi động nhịp nhảy giá realtime (Real-time live tick jitter)
  const startRealtimeJitter = () => {
    if (jitterInterval) clearInterval(jitterInterval)

    jitterInterval = setInterval(() => {
      if (isPaused.value || items.value.length === 0) return

      // Nếu vừa nhận tick thật trong 2 giây qua thì để tick thật làm chủ
      if (Date.now() - lastRealTickTime < 2000) return

      // Chọn ngẫu nhiên 1 mã để nhảy giá (ưu tiên phái sinh và top bluechips)
      const priorityPool = [
        "VN30F1M",
        "VN30",
        "VNINDEX",
        "HPG",
        "FPT",
        "VCB",
        "TCB",
        "MWG",
        "GAS",
        "GVR",
        "BSR",
        "ACB",
        "SSI",
      ]
      const availableSymbols = items.value
        .map((i) => i.symbol)
        .filter((sym) => priorityPool.includes(sym))

      if (availableSymbols.length === 0) return

      const targetSym =
        availableSymbols[Math.floor(Math.random() * availableSymbols.length)]
      const item = items.value.find((i) => i.symbol === targetSym)
      if (!item) return

      // Xác định bước giá (tick step) thực tế thị trường
      let step = 0.05
      if (targetSym === "VN30F1M") {
        step = Math.random() > 0.5 ? 0.1 : 0.2
      } else if (targetSym === "VNINDEX" || targetSym === "VN30") {
        step = Number((Math.random() * 0.25 + 0.05).toFixed(2))
      } else if (item.price >= 50) {
        step = 0.1
      } else if (item.price >= 100) {
        step = 0.2
      }

      // Hướng dao động ngẫu nhiên có độ lệch nhẹ theo xu hướng hiện tại
      const goUp = Math.random() > (item.change >= 0 ? 0.45 : 0.55)
      const delta = goUp ? step : -step
      const newPrice = Number((item.price + delta).toFixed(2))
      const newChange = Number((item.change + delta).toFixed(2))

      // Tính lại tỷ lệ thay đổi phần trăm
      const baseRef = item.refPrice || item.price - item.change
      const newPct =
        baseRef > 0
          ? Number(((newChange / baseRef) * 100).toFixed(2))
          : item.changePercent

      updateItemPrice(targetSym, newPrice, newChange, newPct, true)
    }, 1400)
  }

  const fetchTickerData = async () => {
    if (items.value.length === 0) {
      isLoading.value = true
    }

    try {
      const [indicesRes, boardRes] = await Promise.allSettled([
        $fetch<RawIndexItem[]>("/api/v1/stock/iboard/indices"),
        $fetch<RawStockRow[]>("/api/v1/stock/iboard/board", {
          params: { group: "VN30", limit: 30 },
        }),
      ])

      const parsedIndices: MarketTickerItem[] = []
      const parsedStocks: MarketTickerItem[] = []

      if (
        indicesRes.status === "fulfilled" &&
        Array.isArray(indicesRes.value)
      ) {
        for (const raw of indicesRes.value) {
          const price = parseNum(raw.price)
          const change = parseNum(raw.change)
          const changePercent = parseNum(raw.change_percent)
          const isPos = raw.is_positive ?? change > 0
          const isUnch = raw.is_unchanged ?? change === 0

          let sym = raw.name
          if (raw.name === "HNX-INDEX") sym = "HNX"
          if (raw.id === "dji") continue

          parsedIndices.push({
            id: raw.id || sym,
            symbol: sym,
            name: raw.name,
            price,
            change,
            changePercent,
            isPositive: isPos,
            isUnchanged: isUnch,
            volume: raw.volume,
            category: sym === "VN30F1M" ? "derivative" : "index",
            refPrice: price - change,
          })
        }
      }

      if (boardRes.status === "fulfilled" && Array.isArray(boardRes.value)) {
        for (const raw of boardRes.value) {
          if (!raw.symbol) continue
          const price = raw.last_price || 0
          const change = raw.change || 0
          const changePercent = raw.change_percent || 0
          parsedStocks.push({
            id: `stock-${raw.symbol}`,
            symbol: raw.symbol,
            name: raw.name,
            price,
            change,
            changePercent,
            isPositive: change > 0,
            isUnchanged: change === 0,
            volume: raw.volume ? String(raw.volume) : undefined,
            category: "stock",
            refPrice: raw.ref_price || price - change,
          })
        }
      }

      const primaryIndices = parsedIndices.filter((i) =>
        ["VNINDEX", "VN30", "VN30F1M"].includes(i.symbol),
      )
      primaryIndices.sort((a, b) => {
        const order = ["VNINDEX", "VN30", "VN30F1M"]
        return order.indexOf(a.symbol) - order.indexOf(b.symbol)
      })

      const secondaryIndices = parsedIndices.filter(
        (i) => !["VNINDEX", "VN30", "VN30F1M"].includes(i.symbol),
      )

      const prioritySymbols = [
        "HPG",
        "FPT",
        "VCB",
        "TCB",
        "ACB",
        "MBB",
        "MWG",
        "GAS",
        "GVR",
        "BSR",
        "SSI",
        "VHM",
        "VIC",
      ]
      parsedStocks.sort((a, b) => {
        const idxA = prioritySymbols.indexOf(a.symbol)
        const idxB = prioritySymbols.indexOf(b.symbol)
        if (idxA !== -1 && idxB !== -1) return idxA - idxB
        if (idxA !== -1) return -1
        if (idxB !== -1) return 1
        return a.symbol.localeCompare(b.symbol)
      })

      const combined = [...primaryIndices, ...parsedStocks, ...secondaryIndices]

      if (combined.length > 0) {
        items.value = combined
        lastUpdated.value = new Date().toLocaleTimeString("vi-VN")
      }
    } catch (err) {
      console.warn("[useMarketTicker] Lỗi tải dữ liệu ticker:", err)
    } finally {
      isLoading.value = false
    }
  }

  const startTickerService = async () => {
    await fetchTickerData()
    initWebSocket()
    startRealtimeJitter()

    // Đồng bộ lại định kỳ mỗi 15 giây với REST API
    if (pollInterval) clearInterval(pollInterval)
    pollInterval = setInterval(() => {
      fetchTickerData()
    }, 15000)
  }

  const stopTickerService = () => {
    if (ws) {
      try {
        ws.close()
      } catch {
        // Ignore
      }
      ws = null
    }
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }
    if (jitterInterval) {
      clearInterval(jitterInterval)
      jitterInterval = null
    }
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  const togglePause = () => {
    isPaused.value = !isPaused.value
  }

  const selectSymbol = (sym: string) => {
    selectedSymbol.value = sym
  }

  return {
    items,
    isLoading,
    isPaused,
    isConnected,
    lastUpdated,
    selectedSymbol,
    flashMap,
    fetchTickerData,
    startTickerService,
    stopTickerService,
    togglePause,
    selectSymbol,
  }
}
