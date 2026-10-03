<template><div class="space-y-4"><div v-if="stale || !online" class="rounded-lg border border-white/[0.08] bg-surface-midnight px-3 py-2 text-xs text-aave-ash" role="status">{{ online ? "Đang hiển thị dữ liệu gần nhất. Đang kết nối lại..." : "Ngoại tuyến. Đang chờ kết nối mạng." }}</div><div v-if="snapshot" class="grid gap-4 xl:grid-cols-2"><AtcImbalanceMonitor :atc="snapshot.atc" /><MonteCarloDistributionChart :data="snapshot.monte_carlo" /></div><ForecastLedgerTable v-if="snapshot" :rows="snapshot.ledger" /><p v-else-if="loading" class="text-xs text-aave-graphite">Đang tải kịch bản dự báo...</p><p v-else-if="error" class="text-xs text-aave-graphite">{{ error }}</p></div></template>
<script setup lang="ts">
import { useAtcPrediction } from "~/composables/useAtcPrediction"
const symbol = shallowRef("VN30F1M")
const { snapshot, loading, stale, online, error } = useAtcPrediction(symbol)
</script>
