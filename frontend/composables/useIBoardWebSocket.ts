import { onMounted, onUnmounted, ref, shallowRef } from "vue"

export interface IBoardWSIndexData {
  index: string
  value: number | null
  change: number | null
  pct_change: number | null
  advance?: number | null
  decline?: number | null
  no_change?: number | null
  ceiling?: number | null
  floor?: number | null
  total_volume?: number | null
  total_value?: number | null
  time?: string | null
}

export interface IBoardWSQuoteData {
  symbol: string
  close_price?: number | null
  reference_price?: number | null
  ceiling_price?: number | null
  floor_price?: number | null
  high_price?: number | null
  low_price?: number | null
  open_price?: number | null
  price_change?: number | null
  percent_change?: number | null
  volume_accumulated?: number | null
  total_value?: number | null
  bid_price_1?: number | null
  bid_vol_1?: number | null
  bid_price_2?: number | null
  bid_vol_2?: number | null
  bid_price_3?: number | null
  bid_vol_3?: number | null
  ask_price_1?: number | null
  ask_vol_1?: number | null
  ask_price_2?: number | null
  ask_vol_2?: number | null
  ask_price_3?: number | null
  ask_vol_3?: number | null
  foreign_buy_volume?: number | null
  foreign_sell_volume?: number | null
  total_bid_qty?: number | null
  total_offer_qty?: number | null
}

export interface IBoardWSTradeData {
  symbol: string
  open?: number | null
  high?: number | null
  low?: number | null
  close?: number | null
  volume?: number | null
  trade_quantity?: number | null
  gross_amount?: number | null
  time?: string | null
}

export interface IBoardWSTick {
  time: string
  price: number
  volume: number
  side: string
}

export interface IBoardWSEventHandlers {
  onIndex?: (data: IBoardWSIndexData) => void
  onIndicesSnapshot?: (indices: IBoardWSIndexData[]) => void
  onQuote?: (symbol: string, data: IBoardWSQuoteData) => void
  onTrade?: (symbol: string, data: IBoardWSTradeData) => void
  onStockSnapshot?: (
    symbol: string,
    quote: IBoardWSQuoteData | null,
    ticks: IBoardWSTick[],
  ) => void
  onForeign?: (symbol: string, data: Record<string, unknown>) => void
}

export function useIBoardWebSocket(handlers: IBoardWSEventHandlers = {}) {
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const currentChannels = shallowRef<Set<string>>(new Set(["indices", "board"]))

  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null
  let reconnectAttempts = 0
  const maxReconnectDelay = 30000

  const resolveWebSocketUrl = (): string => {
    if (typeof window === "undefined") return ""
    const config = useRuntimeConfig()
    const rawApiUrl = (config.public.apiUrl as string) || window.location.origin

    let wsOrigin = ""
    if (rawApiUrl.startsWith("http://")) {
      wsOrigin = rawApiUrl.replace("http://", "ws://")
    } else if (rawApiUrl.startsWith("https://")) {
      wsOrigin = rawApiUrl.replace("https://", "wss://")
    } else {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      wsOrigin = `${protocol}//${window.location.host}`
    }

    // Strip trailing slashes
    wsOrigin = wsOrigin.replace(/\/+$/, "")
    return `${wsOrigin}/api/v1/stock/iboard/ws`
  }

  const connect = () => {
    if (typeof window === "undefined") return
    if (
      socket &&
      (socket.readyState === WebSocket.OPEN ||
        socket.readyState === WebSocket.CONNECTING)
    ) {
      return
    }

    const wsUrl = resolveWebSocketUrl()
    if (!wsUrl) return

    isConnecting.value = true
    try {
      socket = new WebSocket(wsUrl)

      socket.onopen = () => {
        isConnected.value = true
        isConnecting.value = false
        reconnectAttempts = 0

        // Resubscribe to current tracked channels
        if (currentChannels.value.size > 0) {
          sendFrame({
            action: "subscribe",
            channels: Array.from(currentChannels.value),
          })
        }

        // Setup ping heartbeat every 20 seconds
        if (pingTimer) clearInterval(pingTimer)
        pingTimer = setInterval(() => {
          sendFrame({ action: "ping" })
        }, 20000)
      }

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          handleMessage(payload)
        } catch (err) {
          console.debug("[iBoardWS] Malformed JSON message:", err)
        }
      }

      socket.onclose = () => {
        isConnected.value = false
        isConnecting.value = false
        if (pingTimer) clearInterval(pingTimer)
        scheduleReconnect()
      }

      socket.onerror = (err) => {
        console.debug("[iBoardWS] WebSocket connection error:", err)
        if (socket) socket.close()
      }
    } catch (err) {
      console.warn("[iBoardWS] Failed to initiate WebSocket:", err)
      isConnected.value = false
      isConnecting.value = false
      scheduleReconnect()
    }
  }

  const scheduleReconnect = () => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectAttempts++
    const delay = Math.min(
      1000 * 2 ** (reconnectAttempts - 1),
      maxReconnectDelay,
    )
    reconnectTimer = setTimeout(() => {
      connect()
    }, delay)
  }

  const sendFrame = (data: Record<string, unknown>) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      try {
        socket.send(JSON.stringify(data))
      } catch (e) {
        console.debug("[iBoardWS] Failed to send frame:", e)
      }
    }
  }

  const handleMessage = (msg: Record<string, unknown>) => {
    const type = msg.type as string

    if (type === "index" && handlers.onIndex) {
      const idxData = (msg.data as IBoardWSIndexData) || {}
      if (!idxData.index && msg.index) {
        idxData.index = msg.index as string
      }
      handlers.onIndex(idxData)
      return
    }

    if (type === "snapshot_indices" && handlers.onIndicesSnapshot) {
      handlers.onIndicesSnapshot((msg.data as IBoardWSIndexData[]) || [])
      return
    }

    if (type === "quote" && handlers.onQuote) {
      handlers.onQuote(msg.symbol as string, msg.data as IBoardWSQuoteData)
      return
    }

    if (type === "trade" && handlers.onTrade) {
      handlers.onTrade(msg.symbol as string, msg.data as IBoardWSTradeData)
      return
    }

    if (type === "snapshot_stock" && handlers.onStockSnapshot) {
      handlers.onStockSnapshot(
        msg.symbol as string,
        (msg.quote as IBoardWSQuoteData) || null,
        (msg.ticks as IBoardWSTick[]) || [],
      )
      return
    }

    if (type === "foreign" && handlers.onForeign) {
      handlers.onForeign(
        msg.symbol as string,
        msg.data as Record<string, unknown>,
      )
      return
    }
  }

  const subscribe = (channels: string[]) => {
    const nextSet = new Set(currentChannels.value)
    for (const c of channels) {
      nextSet.add(c)
    }
    currentChannels.value = nextSet
    sendFrame({ action: "subscribe", channels })
  }

  const unsubscribe = (channels: string[]) => {
    const nextSet = new Set(currentChannels.value)
    for (const c of channels) {
      nextSet.delete(c)
    }
    currentChannels.value = nextSet
    sendFrame({ action: "unsubscribe", channels })
  }

  const subscribeStock = (symbol: string) => {
    const channel = `stock:${symbol.trim().toUpperCase()}`
    subscribe([channel])
  }

  const unsubscribeStock = (symbol: string) => {
    const channel = `stock:${symbol.trim().toUpperCase()}`
    unsubscribe([channel])
  }

  const disconnect = () => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (pingTimer) clearInterval(pingTimer)
    if (socket) {
      socket.onclose = null
      socket.onerror = null
      socket.close()
      socket = null
    }
    isConnected.value = false
    isConnecting.value = false
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    isConnecting,
    currentChannels,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    subscribeStock,
    unsubscribeStock,
  }
}
