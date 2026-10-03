<template><TradingPanel title="Tài khoản mô phỏng"><SimulationWarningBadge /><div v-if="portfolio" class="mt-4 grid gap-4 sm:grid-cols-4"><Metric label="Vốn ban đầu" :value="money(portfolio.initial_balance)" /><Metric label="Tiền mặt" :value="money(portfolio.cash_balance)" /><Metric label="Giá trị ròng" :value="money(portfolio.equity)" /><Metric label="Ký quỹ sử dụng" :value="money(portfolio.margin_used)" /></div><p v-else class="mt-4 text-xs text-aave-graphite">Chưa có tài khoản mô phỏng.</p></TradingPanel></template>
<script setup lang="ts">
import type { PortfolioItem } from "~/client/stockService"
defineProps<{ portfolio: PortfolioItem | null }>()
const money = (value: number) =>
  value.toLocaleString("vi-VN", { maximumFractionDigits: 0 })
</script>
