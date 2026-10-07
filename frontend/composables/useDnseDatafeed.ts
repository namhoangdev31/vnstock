import { getHistoricalOhlc } from "./useDnseApi"
import { dnseWsClient } from "./useDnseWs"
import type { Ohlc } from "@vnstock/dnse"

export interface DatafeedBar {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

export interface DatafeedPeriodParams {
  from: number
  to: number
  countBack: number
  firstDataRequest: boolean
}

export interface DatafeedHistoryMetadata {
  noData?: boolean
  nextTime?: number | null
}

export interface DatafeedSymbolInfo {
  name: string
  ticker?: string
  description: string
  type: string
  session: string
  exchange: string
  listed_exchange: string
  timezone: string
  format: string
  pricescale: number
  minmov: number
  has_intraday?: boolean
  supported_resolutions?: string[]
  intraday_multipliers?: string[]
  has_seconds?: boolean
  has_daily?: boolean
  has_weekly_and_monthly?: boolean
  volume_precision?: number
  data_status?: string
}

export interface DatafeedConfiguration {
  supported_resolutions?: string[]
  supports_marks?: boolean
  supports_timescale_marks?: boolean
  supports_time?: boolean
}

function mapResolutionToDnse(res: string): string {
  if (res === "D" || res === "1D") return "1D"
  if (res === "60" || res === "1H" || res === "1h") return "1h"
  if (res === "W" || res === "1W") return "1W"
  return res
}

/**
 * Custom Datafeed cho TradingView Charting Library sử dụng DNSE API và WebSocket
 */
export function createDnseDatafeed() {
  const subscribers = new Map<
    string,
    {
      symbol: string
      resolution: string
      handler: (ohlc: Ohlc) => void
    }
  >()

  const earliestBarCache = new Map<string, number>()

  return {
    onReady: (callback: (config: DatafeedConfiguration) => void) => {
      setTimeout(() => {
        callback({
          supported_resolutions: ["1", "3", "5", "15", "30", "60", "1D"],
          supports_marks: false,
          supports_timescale_marks: false,
          supports_time: true,
        })
      }, 0)
    },

    searchSymbols: (
      userInput: string,
      _exchange: string,
      _symbolType: string,
      onResult: (
        result: Array<{
          symbol: string
          full_name: string
          description: string
          exchange: string
          type: string
        }>,
      ) => void,
    ) => {
      const defaultSymbols = [
        {
          symbol: "VN30F1M",
          full_name: "HNX:VN30F1M",
          description: "Hợp đồng tương lai chỉ số VN30 tháng hiện tại",
          exchange: "HNX",
          type: "futures",
        },
        {
          symbol: "VN30F2M",
          full_name: "HNX:VN30F2M",
          description: "Hợp đồng tương lai chỉ số VN30 tháng kế tiếp",
          exchange: "HNX",
          type: "futures",
        },
        {
          symbol: "VNINDEX",
          full_name: "HOSE:VNINDEX",
          description: "Chỉ số VN-Index",
          exchange: "HOSE",
          type: "index",
        },
        {
          symbol: "VN30",
          full_name: "HOSE:VN30",
          description: "Chỉ số VN30",
          exchange: "HOSE",
          type: "index",
        },
        {
          symbol: "HNX",
          full_name: "HNX:HNX",
          description: "Chỉ số HNX-Index",
          exchange: "HNX",
          type: "index",
        },
        {
          symbol: "UPCOM",
          full_name: "UPCOM:UPCOM",
          description: "Chỉ số UPCoM-Index",
          exchange: "UPCOM",
          type: "index",
        },
        {
          symbol: "FPT",
          full_name: "HOSE:FPT",
          description: "Công ty Cổ phần FPT",
          exchange: "HOSE",
          type: "stock",
        },
        {
          symbol: "HPG",
          full_name: "HOSE:HPG",
          description: "Công ty Cổ phần Tập đoàn Hòa Phát",
          exchange: "HOSE",
          type: "stock",
        },
      ]
      const query = (userInput || "").toUpperCase().trim()
      const matched = query
        ? defaultSymbols.filter(
            (s) =>
              s.symbol.includes(query) ||
              s.description.toUpperCase().includes(query),
          )
        : defaultSymbols
      onResult(matched)
    },

    resolveSymbol: (
      symbolName: string,
      onResolve: (symbolInfo: DatafeedSymbolInfo) => void,
      _onError: (reason: string) => void,
    ) => {
      const clean = symbolName.includes(":")
        ? symbolName.split(":")[1]
        : symbolName
      const upper = clean.toUpperCase().trim()
      const symbolType = detectDnseSymbolType(upper)

      const isDerivative = symbolType === "DERIVATIVE"
      const isIndex = symbolType === "INDEX"

      const symbolInfo: DatafeedSymbolInfo = {
        ticker: upper,
        name: upper,
        description: isDerivative
          ? `Hợp đồng tương lai ${upper}`
          : isIndex
            ? `Chỉ số ${upper}`
            : `Cổ phiếu ${upper}`,
        type: isDerivative ? "futures" : isIndex ? "index" : "stock",
        session: isDerivative ? "0845-1130,1300-1445" : "0900-1130,1300-1500",
        timezone: "Asia/Ho_Chi_Minh",
        exchange:
          isDerivative || upper === "HNX"
            ? "HNX"
            : upper === "UPCOM"
              ? "UPCOM"
              : "HOSE",
        listed_exchange:
          isDerivative || upper === "HNX"
            ? "HNX"
            : upper === "UPCOM"
              ? "UPCOM"
              : "HOSE",
        format: "price",
        minmov: 1,
        // VN30F1M có 1 chữ số thập phân (pricescale 10). Chỉ số và cổ phiếu chia theo chuẩn thị trường
        pricescale: isDerivative ? 10 : isIndex ? 100 : 1000,
        has_intraday: true,
        intraday_multipliers: ["1", "3", "5", "15", "30", "60"],
        supported_resolutions: ["1", "3", "5", "15", "30", "60", "1D"],
        volume_precision: 0,
        data_status: "streaming",
      }

      setTimeout(() => onResolve(symbolInfo), 0)
    },

    getBars: async (
      symbolInfo: DatafeedSymbolInfo,
      resolution: string,
      periodParams: DatafeedPeriodParams,
      onResult: (bars: DatafeedBar[], meta?: DatafeedHistoryMetadata) => void,
      onError: (reason: string) => void,
    ) => {
      try {
        const symbol = symbolInfo.name.toUpperCase()
        const dnseRes = mapResolutionToDnse(resolution)
        const cacheKey = `${symbol}_${dnseRes}`
        const cachedEarliest = earliestBarCache.get(cacheKey)

        let to = periodParams.to
        let from = periodParams.from

        if (!periodParams.firstDataRequest && cachedEarliest) {
          // Lùi mốc to về trước 1 giây so với nến sớm nhất hiện có để tránh tải lại chính nến đó
          to = Math.floor(cachedEarliest / 1000) - 1
          const requestedSpan = periodParams.to - periodParams.from
          const minSpan = dnseRes === "1D" ? 30 * 86400 : 3 * 86400
          const span = Math.max(requestedSpan, minSpan)
          from = to - span
        } else {
          // Lần tải đầu tiên: Đảm bảo tối thiểu 3 ngày dữ liệu
          const minSpan = dnseRes === "1D" ? 60 * 86400 : 3 * 86400
          if (to - from < minSpan) {
            from = to - minSpan
          }
        }

        let bars: DatafeedBar[] = []
        let attempts = 0
        let currentFrom = from
        const step = dnseRes === "1D" ? 60 * 86400 : 5 * 86400

        // Vòng lặp tìm kiếm nến: Nếu gặp khoảng trống (giờ nghỉ trưa, qua đêm, cuối tuần),
        // tự động mở rộng mốc currentFrom về quá khứ cho tới khi tìm thấy nến
        while (bars.length === 0 && attempts < 5) {
          const history = await getHistoricalOhlc({
            symbol,
            resolution: dnseRes,
            from: currentFrom,
            to,
            all: true,
          })

          if (history?.candles && history.candles.length > 0) {
            const mappedBars: DatafeedBar[] = history.candles.map((c) => ({
              time: c.time < 1e11 ? c.time * 1000 : c.time,
              open: c.open,
              high: c.high,
              low: c.low,
              close: c.close,
              volume: c.volume,
            }))
            mappedBars.sort((a, b) => a.time - b.time)

            if (!periodParams.firstDataRequest && cachedEarliest) {
              bars = mappedBars.filter((b) => b.time < cachedEarliest)
            } else {
              bars = mappedBars
            }
          }

          if (bars.length === 0) {
            attempts++
            currentFrom = currentFrom - step
          }
        }

        if (bars.length === 0) {
          onResult([], { noData: true })
          return
        }

        // Cập nhật nến sớm nhất trong bộ nhớ cache
        const newEarliest = bars[0].time
        if (!cachedEarliest || newEarliest < cachedEarliest) {
          earliestBarCache.set(cacheKey, newEarliest)
        }

        onResult(bars, { noData: false })
      } catch (err) {
        console.error("[DnseDatafeed] Lỗi trong getBars:", err)
        onError(err instanceof Error ? err.message : String(err))
      }
    },

    subscribeBars: async (
      symbolInfo: DatafeedSymbolInfo,
      resolution: string,
      onTick: (bar: DatafeedBar) => void,
      listenerGuid: string,
      _onResetCacheNeededCallback: () => void,
    ) => {
      const symbol = symbolInfo.name.toUpperCase()
      const dnseRes = mapResolutionToDnse(resolution)

      const ohlcHandler = (ohlc: Ohlc) => {
        if (ohlc.symbol.toUpperCase() === symbol) {
          const barTime = ohlc.time < 1e11 ? ohlc.time * 1000 : ohlc.time
          const bar: DatafeedBar = {
            time: barTime,
            open: ohlc.open,
            high: ohlc.high,
            low: ohlc.low,
            close: ohlc.close,
            volume: ohlc.volume,
          }
          onTick(bar)
        }
      }

      subscribers.set(listenerGuid, {
        symbol,
        resolution: dnseRes,
        handler: ohlcHandler,
      })

      try {
        await dnseWsClient.connect()
        await dnseWsClient.subscribeOhlc([symbol], dnseRes, ohlcHandler)
      } catch (err) {
        console.error(
          "[DnseDatafeed] Lỗi khi subscribeBars qua WebSocket DNSE:",
          err,
        )
      }
    },

    unsubscribeBars: (listenerGuid: string) => {
      const sub = subscribers.get(listenerGuid)
      if (sub) {
        dnseWsClient.off("ohlc", sub.handler as (...args: unknown[]) => void)
        subscribers.delete(listenerGuid)
      }
    },

    getServerTime: (callback: (serverTime: number) => void) => {
      callback(Math.floor(Date.now() / 1000))
    },
  }
}
