import type { PredictionSnapshot } from "~/client/stockService"
import { StockService } from "~/client/stockService"
import { useTradingPolling } from "~/composables/useTradingPolling"

export function useAtcPrediction(symbol: Ref<string>) {
  const snapshot = shallowRef<PredictionSnapshot | null>(null)
  const polling = useTradingPolling(async () => {
    snapshot.value = await StockService.getPredictionSnapshot({
      query: { symbol: symbol.value },
    })
  })
  watch(symbol, () => {
    void polling.refresh()
  })
  return { ...polling, snapshot }
}
