import {
  StockService,
  type PortfolioItem,
  type PositionItem,
  type OrderItem,
  type MarginStatusResponse,
  type AlphaBasketsResponse,
} from "~/client/stockService"
import { useCustomToast } from "~/composables/useCustomToast"

export function usePaperTrading() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const portfolios = shallowRef<PortfolioItem[]>([])
  const portfolioId = shallowRef<string | null>(null)
  const portfolio = computed(
    () =>
      portfolios.value.find((item) => item.id === portfolioId.value) ?? null,
  )
  const positions = shallowRef<PositionItem[]>([])
  const orders = shallowRef<OrderItem[]>([])
  const margin = shallowRef<MarginStatusResponse | null>(null)
  const baskets = shallowRef<AlphaBasketsResponse | null>(null)
  const busy = shallowRef(false)

  const refresh = async () => {
    const result = await StockService.listPortfolios()
    portfolios.value = result.data
    portfolioId.value =
      portfolioId.value &&
      result.data.some((item) => item.id === portfolioId.value)
        ? portfolioId.value
        : (result.data[0]?.id ?? null)
    if (!portfolioId.value) return
    const [nextPositions, nextOrders, nextMargin, nextBaskets] =
      await Promise.all([
        StockService.listSimulationPositions({
          path: { portfolio_id: portfolioId.value },
        }),
        StockService.listSimulationOrders({
          query: { portfolio_id: portfolioId.value, limit: 100 },
        }),
        StockService.getMarginStatus({
          path: { portfolio_id: portfolioId.value },
        }),
        StockService.getAlphaBaskets(),
      ])
    positions.value = nextPositions
    orders.value = nextOrders
    margin.value = nextMargin
    baskets.value = nextBaskets
  }

  const placeOrder = async (payload: {
    symbol: string
    side: string
    quantity: number
    price: number
    order_type: string
    stop_price?: number
  }) => {
    if (!portfolioId.value) throw new Error("Chưa có tài khoản mô phỏng")
    busy.value = true
    try {
      await StockService.placePortfolioOrder({
        path: { portfolio_id: portfolioId.value },
        body: payload,
      })
      await refresh()
      showSuccessToast("Lệnh mô phỏng đã được gửi")
    } catch (cause) {
      showErrorToast(
        cause instanceof Error ? cause.message : "Không thể gửi lệnh mô phỏng",
      )
      throw cause
    } finally {
      busy.value = false
    }
  }

  const closePosition = async (position: PositionItem, price: number) => {
    busy.value = true
    try {
      await StockService.closeSimulationPosition({
        path: { position_id: position.id },
        body: { quantity: position.quantity, price },
      })
      await refresh()
      showSuccessToast("Vị thế mô phỏng đã được đóng")
    } finally {
      busy.value = false
    }
  }

  const allocateBasket = async (horizon: string) => {
    if (!portfolioId.value) throw new Error("Chưa có tài khoản mô phỏng")
    busy.value = true
    try {
      await StockService.allocateAlphaBasket({
        path: { portfolio_id: portfolioId.value },
        body: { horizon },
      })
      await refresh()
      showSuccessToast("Rổ alpha đã được phân bổ trong mô phỏng")
    } catch (cause) {
      showErrorToast(
        cause instanceof Error ? cause.message : "Không thể phân bổ rổ alpha",
      )
      throw cause
    } finally {
      busy.value = false
    }
  }

  onMounted(() => {
    void refresh()
  })
  return {
    portfolios,
    portfolioId,
    portfolio,
    positions,
    orders,
    margin,
    baskets,
    busy,
    refresh,
    placeOrder,
    closePosition,
    allocateBasket,
  }
}
