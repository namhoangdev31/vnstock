<template><TradingPanel title="Phân phối Monte Carlo"><div v-if="data.available" class="space-y-3"><div class="grid grid-cols-3 gap-3"><Metric label="P10" :value="format(data.p10)" /><Metric label="P50" :value="format(data.p50)" /><Metric label="P90" :value="format(data.p90)" /></div><div class="flex h-32 items-end gap-1" aria-label="Biểu đồ phân phối xác suất"><div v-for="(point, index) in data.histogram" :key="index" class="flex-1 bg-aave-violet/70" :style="{ height: `${Math.max(3, Math.min(100, point.probability * 100))}%` }" :title="format(point.price)" /></div></div><p v-else class="text-xs text-aave-graphite" role="status">{{ data.reason || "Chưa có dữ liệu Monte Carlo" }}</p></TradingPanel></template>
<script setup lang="ts">
defineProps<{
  data: {
    available: boolean
    simulations: number
    p10: number | null
    p50: number | null
    p90: number | null
    histogram: Array<{ price: number; probability: number }>
    reason: string | null
  }
}>()
const format = (value: number | null) =>
  value == null
    ? "Chưa có dữ liệu"
    : value.toLocaleString("vi-VN", { maximumFractionDigits: 2 })
</script>
