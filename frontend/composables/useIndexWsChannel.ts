import { type Ref, onBeforeUnmount, ref, watch } from "vue"
import type { IBoardCandleBar, IBoardIndexItem } from "~/client/types.gen"
import { MarketIndexSymbol } from "~/types/market"

export interface MiniChartIndexData {
  id: string
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  isPositive: boolean
  isUnchanged: boolean
  volume: string
  value: string
  status: string
  breadth?: {
    advance: number
    ceiling: number
    unchanged: number
    decline: number
    floor: number
  } | null
  derivativesDepth?: {
    buyQuantity: number
    sellQuantity: number
    refPrice: number
    ceilingPrice: number
    floorPrice: number
  } | null
}

const parseNum = (str: string | number | undefined | null): number => {
  if (typeof str === "number") return str
  if (!str) return 0
  const clean = String(str).replace(/,/g, "").replace("%", "").trim()
  const n = Number.parseFloat(clean)
  return Number.isNaN(n) ? 0 : n
}

export function useIndexWsChannel(
  symbolRef: Ref<string> | string,
  timeframeRef: Ref<string> = ref("1m"),
) {
  const getSymbol = () =>
    (typeof symbolRef === "string" ? symbolRef : symbolRef.value).toUpperCase()

  const indexData = ref<MiniChartIndexData>({
    id: getSymbol().toLowerCase(),
    symbol: getSymbol(),
    name: getSymbol(),
    price: 0,
    change: 0,
    changePercent: 0,
    isPositive: false,
    isUnchanged: true,
    volume: "-",
    value: "-",
    status: "Đóng cửa",
    breadth: null,
    derivativesDepth: null,
  })

  const candles = ref<IBoardCandleBar[]>([])
  const isLoadingCandles = ref(false)
  const isWsConnected = ref(false)
  const isFlashing = ref<"up" | "down" | null>(null)
  let refPrice = 0

  const normalizeSym = (s: string) =>
    String(s || "")
      .replace(/[^A-Z0-9]/g, "")
      .toUpperCase()

  const isIndexMatch = (item: IBoardIndexItem, targetSym: string): boolean => {
    const normTarget = normalizeSym(targetSym)
    const normName = normalizeSym(item.name)
    const normId = normalizeSym(item.id)

    if (normName === normTarget || normId === normTarget) return true
    if (
      normTarget === MarketIndexSymbol.HNX &&
      (normName.includes(MarketIndexSymbol.HNX) ||
        normId === MarketIndexSymbol.HNX)
    )
      return true
    if (
      normTarget === MarketIndexSymbol.HNXINDEX &&
      (normName.includes(MarketIndexSymbol.HNX) ||
        normId === MarketIndexSymbol.HNX)
    )
      return true
    if (
      normTarget === MarketIndexSymbol.UPCOM &&
      normName.startsWith(MarketIndexSymbol.UPCOM)
    )
      return true
    if (
      normTarget === MarketIndexSymbol.UPCOMINDEX &&
      normName.startsWith(MarketIndexSymbol.UPCOM)
    )
      return true
    if (normTarget === "DOWJONESFUTURES" && normId === MarketIndexSymbol.DJI)
      return true
    return false
  }

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let isCleanedUp = false

  const triggerPriceFlash = (dir: "up" | "down") => {
    isFlashing.value = dir
    setTimeout(() => {
      if (isFlashing.value === dir) {
        isFlashing.value = null
      }
    }, 650)
  }

  const loadIndexSnapshot = async () => {
    const sym = getSymbol()
    try {
      const list = await $fetch<IBoardIndexItem[]>(
        "/api/v1/stock/iboard/indices",
      )
      const found = list.find((i) => isIndexMatch(i, sym))
      if (found) {
        applyIndexSnapshot(found)
        if (
          candles.value.length === 0 &&
          Array.isArray(found.sparkline) &&
          found.sparkline.length > 0
        ) {
          candles.value = found.sparkline.map((val, idx) => ({
            time: `${14 - Math.floor((50 - idx) / 60)}:${String((idx * 2) % 60).padStart(2, "0")}`,
            open: idx > 0 ? found.sparkline[idx - 1] : val,
            high: Math.max(val, idx > 0 ? found.sparkline[idx - 1] : val),
            low: Math.min(val, idx > 0 ? found.sparkline[idx - 1] : val),
            close: val,
            volume: 1000 + Math.floor(Math.random() * 5000),
          }))
        }
      }
    } catch (err) {
      console.warn(`[${sym}] Lỗi nạp dữ liệu chỉ số từ backend:`, err)
    }
  }

  const loadCandles = async () => {
    const sym = getSymbol()
    const tf =
      typeof timeframeRef === "string" ? timeframeRef : timeframeRef.value
    isLoadingCandles.value = true

    try {
      const data = await $fetch<IBoardCandleBar[]>(
        `/api/v1/stock/iboard/candles/${sym}`,
        {
          params: { timeframe: tf, limit: 60 },
        },
      )
      if (Array.isArray(data) && data.length > 0) {
        candles.value = data
        const lastCandle = data[data.length - 1]
        if (lastCandle) {
          if (indexData.value.price === 0) {
            indexData.value.price = lastCandle.close
          }
          if (refPrice > 0 && indexData.value.change === 0) {
            const chg = Number((indexData.value.price - refPrice).toFixed(2))
            const pct = Number(((chg / refPrice) * 100).toFixed(2))
            indexData.value.change = chg
            indexData.value.changePercent = pct
            indexData.value.isPositive = chg > 0
            indexData.value.isUnchanged = Math.abs(chg) < 0.001
          }
        }
      } else {
        await loadIndexSnapshot()
      }
    } catch {
      await loadIndexSnapshot()
    } finally {
      isLoadingCandles.value = false
    }
  }

  const applyIndexSnapshot = (item: IBoardIndexItem) => {
    const p = parseNum(item.price)
    const chg = parseNum(item.change)
    const pct = parseNum(item.change_percent)

    if (item.ref_price && typeof item.ref_price === "number") {
      refPrice = item.ref_price
    } else if (p > 0 && !Number.isNaN(chg) && chg !== 0) {
      refPrice = Number((p - chg).toFixed(2))
    }

    indexData.value = {
      id: item.id,
      symbol: item.name,
      name: item.name,
      price: p,
      change: chg,
      changePercent: pct,
      isPositive: chg > 0,
      isUnchanged: Math.abs(chg) < 0.001,
      volume: item.volume || "-",
      value: item.value || "-",
      status: "Đóng cửa",
      breadth: item.breadth || null,
      derivativesDepth: null,
    }
  }

  const updateCandleWithTick = (newPrice: number, vol = 0) => {
    if (newPrice <= 0 || candles.value.length === 0) return

    const last = candles.value[candles.value.length - 1]
    const updated: IBoardCandleBar = {
      ...last,
      high: Math.max(last.high, newPrice),
      low: Math.min(last.low, newPrice),
      close: newPrice,
      volume: last.volume + (vol > 0 ? vol : 10),
    }

    candles.value = [...candles.value.slice(0, -1), updated]
  }

  const initWebSocket = () => {
    if (typeof window === "undefined" || isCleanedUp) return

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
    const sym = getSymbol()

    try {
      if (ws) {
        try {
          ws.close()
        } catch {}
        ws = null
      }

      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        if (isCleanedUp) return
        isWsConnected.value = true

        const subChannels = ["indices", `stock:${sym}`]
        ws?.send(
          JSON.stringify({
            action: "subscribe",
            channels: subChannels,
          }),
        )

        if (heartbeatTimer) clearInterval(heartbeatTimer)
        heartbeatTimer = setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "ping" }))
          }
        }, 25000)
      }

      ws.onmessage = (event: MessageEvent) => {
        if (isCleanedUp) return
        try {
          const msg = JSON.parse(event.data)
          if (!msg) return

          if (msg.type === "snapshot_indices" && Array.isArray(msg.data)) {
            const found = msg.data.find((i: IBoardIndexItem) =>
              isIndexMatch(i, sym),
            )
            if (found) {
              applyIndexSnapshot(found)
            }
          }

          if (msg.type === "index" && msg.index) {
            const incomingKey = String(msg.index).toUpperCase()
            const matchIndex =
              incomingKey === sym ||
              (sym === MarketIndexSymbol.VNINDEX &&
                incomingKey === MarketIndexSymbol.HOSE) ||
              (sym === MarketIndexSymbol.HOSE &&
                incomingKey === MarketIndexSymbol.VNINDEX) ||
              (sym === MarketIndexSymbol.HNX &&
                (incomingKey === MarketIndexSymbol.HNXINDEX ||
                  incomingKey === MarketIndexSymbol.HNX)) ||
              (sym === MarketIndexSymbol.HNXINDEX &&
                (incomingKey === MarketIndexSymbol.HNX ||
                  incomingKey === MarketIndexSymbol.HNXINDEX)) ||
              (sym === MarketIndexSymbol.UPCOM &&
                incomingKey.includes(MarketIndexSymbol.UPCOM))
            if (matchIndex) {
              const val = parseNum(msg.data?.value)
              const chg = parseNum(msg.data?.change)
              const pct = parseNum(msg.data?.pct_change)
              if (val > 0) {
                const old = indexData.value.price
                indexData.value.price = val
                if (
                  msg.data?.change !== undefined &&
                  msg.data?.change !== null &&
                  !Number.isNaN(chg)
                ) {
                  indexData.value.change = chg
                } else if (refPrice > 0) {
                  indexData.value.change = Number((val - refPrice).toFixed(2))
                }

                if (
                  msg.data?.pct_change !== undefined &&
                  msg.data?.pct_change !== null &&
                  !Number.isNaN(pct)
                ) {
                  indexData.value.changePercent = pct
                } else if (refPrice > 0) {
                  indexData.value.changePercent = Number(
                    ((indexData.value.change / refPrice) * 100).toFixed(2),
                  )
                }

                indexData.value.isPositive = indexData.value.change > 0
                indexData.value.isUnchanged =
                  Math.abs(indexData.value.change) < 0.001
                if (old > 0 && Math.abs(val - old) > 0.001) {
                  triggerPriceFlash(val > old ? "up" : "down")
                }

                if (msg.data?.total_volume) {
                  const vol = parseNum(msg.data.total_volume)
                  indexData.value.volume = `${(vol / 1e6).toFixed(2)} Triệu CP`
                }
                if (msg.data?.total_value) {
                  const valBillion = parseNum(msg.data.total_value) / 1e9
                  indexData.value.value = `${valBillion.toFixed(2)} Tỷ`
                }
                if (msg.data?.advance !== undefined) {
                  indexData.value.breadth = {
                    advance: msg.data.advance || 0,
                    ceiling: msg.data.ceiling || 0,
                    unchanged: msg.data.no_change || 0,
                    decline: msg.data.decline || 0,
                    floor: msg.data.floor || 0,
                  }
                }

                updateCandleWithTick(val)
              }
            }
          }

          if ((msg.type === "trade" || msg.type === "quote") && msg.symbol) {
            if (String(msg.symbol).toUpperCase() === sym) {
              const price = parseNum(msg.data?.price ?? msg.data?.last_price)
              const chg = parseNum(msg.data?.change)
              const pct = parseNum(msg.data?.pct_change)
              const vol = parseNum(msg.data?.quantity ?? msg.data?.vol)

              if (price > 0) {
                const old = indexData.value.price
                indexData.value.price = price
                if (
                  !Number.isNaN(chg) &&
                  msg.data?.change !== undefined &&
                  msg.data?.change !== null
                ) {
                  indexData.value.change = chg
                } else if (refPrice > 0) {
                  indexData.value.change = Number((price - refPrice).toFixed(2))
                }

                if (
                  !Number.isNaN(pct) &&
                  msg.data?.pct_change !== undefined &&
                  msg.data?.pct_change !== null
                ) {
                  indexData.value.changePercent = pct
                } else if (refPrice > 0) {
                  indexData.value.changePercent = Number(
                    ((indexData.value.change / refPrice) * 100).toFixed(2),
                  )
                }

                indexData.value.isPositive = indexData.value.change > 0
                indexData.value.isUnchanged =
                  Math.abs(indexData.value.change) < 0.001

                if (old > 0 && Math.abs(price - old) > 0.001) {
                  triggerPriceFlash(price > old ? "up" : "down")
                }
                updateCandleWithTick(price, vol)
              }
            }
          }
        } catch {}
      }

      ws.onclose = () => {
        isWsConnected.value = false
        if (!isCleanedUp) {
          if (reconnectTimer) clearTimeout(reconnectTimer)
          reconnectTimer = setTimeout(initWebSocket, 4000)
        }
      }

      ws.onerror = () => {
        isWsConnected.value = false
      }
    } catch {
      isWsConnected.value = false
    }
  }

  const start = async () => {
    await Promise.allSettled([loadIndexSnapshot(), loadCandles()])
    initWebSocket()
  }

  const stop = () => {
    isCleanedUp = true
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (heartbeatTimer) clearInterval(heartbeatTimer)
    if (ws) {
      try {
        ws.close()
      } catch {}
      ws = null
    }
  }

  if (typeof timeframeRef !== "string") {
    watch(timeframeRef, () => {
      loadCandles()
    })
  }

  onBeforeUnmount(() => {
    stop()
  })

  return {
    indexData,
    candles,
    isLoadingCandles,
    isWsConnected,
    isFlashing,
    loadCandles,
    start,
    stop,
  }
}
