import type { DerivativesSnapshot } from "~/client/stockService"
import { StockService } from "~/client/stockService"
import { useTradingPolling } from "~/composables/useTradingPolling"

export function useDerivativesLive(symbol: Ref<string>) {
  const timeframe = shallowRef("1m")
  const snapshot = shallowRef<DerivativesSnapshot | null>(null)
  let requestVersion = 0
  const polling = useTradingPolling(async () => {
    const version = ++requestVersion
    const result = await StockService.getDerivativesSnapshot({
      query: { symbol: symbol.value, timeframe: timeframe.value, limit: 120 },
    })
    if (version === requestVersion) snapshot.value = result
  })
  watch([symbol, timeframe], () => {
    void polling.refresh()
  })
  return { ...polling, snapshot, timeframe }
}
