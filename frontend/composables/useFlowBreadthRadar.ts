import type { FlowRadarSnapshot } from "~/client/stockService"
import { StockService } from "~/client/stockService"
import { useTradingPolling } from "~/composables/useTradingPolling"

export function useFlowBreadthRadar() {
  const snapshot = shallowRef<FlowRadarSnapshot | null>(null)
  const polling = useTradingPolling(async () => {
    snapshot.value = await StockService.getFlowRadarSnapshot()
  })
  return { ...polling, snapshot }
}
