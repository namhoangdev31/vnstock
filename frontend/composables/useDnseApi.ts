import { DNSEClient, type OhlcResponseData } from "@vnstock/dnse"

let _apiClient: DNSEClient | null = null

export interface OhlcCandle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  datetime: string
  tradingDate: string
}

export interface HistoricalOhlcResult {
  symbol: string
  count: number
  candles: OhlcCandle[]
  allCandles: OhlcCandle[]
  todayCandles: OhlcCandle[]
  previousDayCandles: OhlcCandle[]
  todayDate: string
  previousDate: string
  previousClose: number | null
  raw: OhlcResponseData
}

/**
 * DNSE REST API Composable
 */
export const useDnseApi = (): DNSEClient => {
  if (!_apiClient) {
    let apiKey = ""
    let apiSecret = ""
    let baseUrl = "https://openapi.dnse.com.vn"

    try {
      const config = useRuntimeConfig()
      apiKey = (config.public?.dnseApiKey as string) || ""
      apiSecret = (config.public?.dnseApiSecret as string) || ""
      if (config.public?.dnseApiUrl) {
        baseUrl = config.public.dnseApiUrl as string
      }
    } catch {
      if (typeof process !== "undefined" && process.env) {
        apiKey = process.env.DNSE_API_KEY || ""
        apiSecret = process.env.DNSE_API_SECRET || ""
        baseUrl = process.env.DNSE_API_URL || baseUrl
      }
    }

    _apiClient = new DNSEClient({
      apiKey,
      apiSecret,
      baseUrl,
      dateHeaderName: "X-Aux-Date",
    })
  }
  return _apiClient
}

export const dnseApiClient = new Proxy({} as DNSEClient, {
  get(_target, prop, receiver) {
    const client = useDnseApi()
    const value = Reflect.get(client, prop, receiver)
    if (typeof value === "function") {
      return value.bind(client)
    }
    return value
  },
})

/**
 * Lấy lịch sử nến OHLC:
 * Tải nến 1m của ngày hôm nay (từ thời điểm mở phiên đến hiện tại) kèm toàn bộ nến 1m của 1 ngày giao dịch liền trước (T-1).
 */
const KNOWN_INDICES = new Set([
  "VNINDEX",
  "VN30",
  "HNX",
  "UPCOM",
  "HNX30",
  "VN100",
  "VNALL",
  "VNCOND",
  "VNCONS",
  "VNENE",
  "VNFIN",
  "VNHEAL",
  "VNIND",
  "VNIT",
  "VNMAT",
  "VNMID",
  "VNREAL",
  "VNSI",
  "VNSML",
  "VNUTI",
])

export function detectDnseSymbolType(
  symbol: string,
): "DERIVATIVE" | "INDEX" | "STOCK" {
  const upper = symbol.toUpperCase().trim()
  if (
    upper === "VN30F1M" ||
    upper === "VN30F2M" ||
    upper === "VN30F1Q" ||
    upper === "VN30F2Q" ||
    upper === "V100F1M" ||
    upper === "V100F2M" ||
    upper === "V100F1Q" ||
    upper === "V100F2Q" ||
    /^VN30F\d{4}$/.test(upper)
  ) {
    return "DERIVATIVE"
  }
  if (KNOWN_INDICES.has(upper) || upper.endsWith("INDEX")) {
    return "INDEX"
  }
  return "STOCK"
}

/**
 * Lấy nến lịch sử OHLC và lọc nến theo phiên T-1 và T-0 (mặc định cho VN30F1M)
 */
export const getHistoricalOhlc = async (options?: {
  symbol?: string
  type?: "DERIVATIVE" | "STOCK" | "INDEX" | string
  resolution?: "1" | "3" | "5" | "15" | "30" | "1h" | "1D" | "1W" | string
  from?: number
  to?: number
  all?: boolean
}): Promise<HistoricalOhlcResult | null> => {
  const symbol = (options?.symbol ?? "VN30F1M").toUpperCase()
  const type = options?.type ?? detectDnseSymbolType(symbol)
  const resolution = options?.resolution ?? "1"

  const to = options?.to ?? Math.floor(Date.now() / 1000)
  const from = options?.from ?? to - 5 * 86400

  let raw: OhlcResponseData | null = null

  // 1. Ưu tiên gọi qua Backend Proxy (/api/v1/dnse/price/ohlc) để tránh triệt để lỗi CORS trên trình duyệt
  try {
    const config = useRuntimeConfig()
    const apiBase = import.meta.client
      ? ""
      : (config.public?.apiUrl as string) || ""
    const queryParams = new URLSearchParams({
      symbol,
      resolution,
      from: String(from),
      to: String(to),
      type,
    })
    const url = `${apiBase}/api/v1/dnse/price/ohlc?${queryParams.toString()}`
    const backendRes = await $fetch<OhlcResponseData>(url, {
      method: "GET",
      headers: { Accept: "application/json" },
    })
    if (backendRes && Array.isArray(backendRes.t) && backendRes.t.length > 0) {
      raw = backendRes
    }
  } catch (backendErr) {
    console.warn(
      "[getHistoricalOhlc] Backend proxy call failed, falling back to direct DNSEClient:",
      backendErr,
    )
  }

  // 2. Fallback nếu backend proxy không khả dụng
  if (!raw) {
    try {
      const client = useDnseApi()
      const res = await client.getOhlc<OhlcResponseData>(type, {
        symbol,
        resolution,
        from,
        to,
      })
      if (res?.data && Array.isArray(res.data.t) && res.data.t.length > 0) {
        raw = res.data
      }
    } catch (directErr) {
      console.error(
        "[getHistoricalOhlc] Direct DNSEClient fetch failed:",
        directErr,
      )
    }
  }

  if (!raw || !Array.isArray(raw.t) || raw.t.length === 0) {
    return null
  }

  const allCandles: OhlcCandle[] = []
  const groupedByDate: Record<string, OhlcCandle[]> = {}

  for (let i = 0; i < raw.t.length; i++) {
    const timestamp = raw.t[i]
    const dt = new Date(timestamp * 1000)
    const tradingDate = dt.toLocaleDateString("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    })
    const datetime = dt.toLocaleString("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
      hour: "2-digit",
      minute: "2-digit",
      day: "2-digit",
      month: "2-digit",
    })

    const candle: OhlcCandle = {
      time: timestamp,
      open: raw.o[i],
      high: raw.h[i],
      low: raw.l[i],
      close: raw.c[i],
      volume: raw.v[i],
      datetime,
      tradingDate,
    }

    allCandles.push(candle)
    if (!groupedByDate[tradingDate]) {
      groupedByDate[tradingDate] = []
    }
    groupedByDate[tradingDate].push(candle)
  }

  const tradingDates = Object.keys(groupedByDate)
  let previousDayCandles: OhlcCandle[] = []
  let todayCandles: OhlcCandle[] = []
  let previousDate = ""
  let todayDate = ""
  let previousClose: number | null = null

  if (tradingDates.length === 1) {
    todayDate = tradingDates[0]
    todayCandles = groupedByDate[todayDate]
  } else if (tradingDates.length >= 2) {
    // 2 ngày giao dịch gần nhất: T-1 (ngày trước đó) và T-0 (ngày hôm nay)
    previousDate = tradingDates[tradingDates.length - 2]
    todayDate = tradingDates[tradingDates.length - 1]
    previousDayCandles = groupedByDate[previousDate]
    todayCandles = groupedByDate[todayDate]

    if (previousDayCandles.length > 0) {
      previousClose = previousDayCandles[previousDayCandles.length - 1].close
    }
  }

  // Danh sách nến: Nếu options?.all = true hoặc options?.from được truyền vào thì lấy toàn bộ allCandles,
  // ngược lại mặc định lấy 2 phiên gần nhất (T-1 + T-0).
  const combinedCandles =
    options?.all || (options?.from !== undefined && options?.to !== undefined)
      ? allCandles
      : [...previousDayCandles, ...todayCandles]

  return {
    symbol,
    count: combinedCandles.length,
    candles: combinedCandles,
    allCandles,
    todayCandles,
    previousDayCandles,
    todayDate,
    previousDate,
    previousClose,
    raw,
  }
}
