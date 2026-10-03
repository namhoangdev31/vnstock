<template><div class="space-y-4"><VirtualAccountOverview :portfolio="portfolio" /><OrderPlacementForm :portfolio="portfolio" :busy="busy" @submit="submitOrder" /><ActivePositionsTable :positions="positions" @close="closePosition" /><OrderHistoryTable :orders="orders" /><AlphaBasketsRebalanceCard :baskets="baskets" :busy="busy" @allocate="allocateBasket" /></div></template>
<script setup lang="ts">
import type { PositionItem } from "~/client/stockService"
import { usePaperTrading } from "~/composables/usePaperTrading"
const trading = usePaperTrading()
const { portfolio, positions, orders, baskets, busy } = trading
const submitOrder = async (
  payload: Parameters<typeof trading.placeOrder>[0],
) => {
  await trading.placeOrder(payload)
}
const closePosition = async (position: PositionItem) => {
  await trading.closePosition(position, position.current_price)
}
const allocateBasket = async (horizon: string) => {
  await trading.allocateBasket(horizon)
}
</script>
