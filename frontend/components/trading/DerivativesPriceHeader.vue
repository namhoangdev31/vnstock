<template><TradingPanel><div class="grid gap-4 sm:grid-cols-4"><div><p class="text-[10px] uppercase tracking-wider text-aave-graphite">{{ snapshot.symbol }}</p><p class="mt-1 font-mono text-2xl font-semibold text-aave-paper">{{ format(snapshot.quote.price) }}</p></div><Metric label="Thay đổi" :value="`${format(snapshot.quote.change)} ${snapshot.quote.change_percent == null ? '' : `${snapshot.quote.change_percent.toFixed(2)}%`}`" /><Metric label="Basis F1M - VN30" :value="format(snapshot.basis.value)" /><Metric label="Biên độ ngày" :value="`${format(snapshot.quote.floor)} / ${format(snapshot.quote.ceiling)}`" /></div></TradingPanel></template>
<script setup lang="ts">
import type { DerivativesSnapshot } from "~/client/stockService"
defineProps<{ snapshot: DerivativesSnapshot }>()
const format = (value: number | null) =>
  value == null
    ? "Chưa có dữ liệu"
    : value.toLocaleString("vi-VN", { maximumFractionDigits: 2 })
</script>
