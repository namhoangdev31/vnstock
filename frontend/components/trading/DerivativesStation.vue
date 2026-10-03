<template><div class="space-y-4"><div v-if="stale || !online" class="rounded-lg border border-white/[0.08] bg-surface-midnight px-3 py-2 text-xs text-aave-ash" role="status">{{ online ? "Đang hiển thị dữ liệu gần nhất. Đang kết nối lại..." : "Ngoại tuyến. Đang chờ kết nối mạng." }}</div><DerivativesPriceHeader v-if="snapshot" :snapshot="snapshot" /><InteractiveCandleChart v-if="snapshot" :candles="snapshot.candles" :timeframe="timeframe" @update:timeframe="timeframe = $event" /><OrderflowDeltaBar v-if="snapshot" :rows="snapshot.orderflow" /><EnsembleSignalCard :signal="snapshot?.signal ?? null" /><p v-if="loading" class="text-xs text-aave-graphite">Đang tải telemetry...</p><p v-if="error && !snapshot" class="text-xs text-aave-graphite">{{ error }}</p></div></template>
<script setup lang="ts">
import { useDerivativesLive } from "~/composables/useDerivativesLive"
const symbol = shallowRef("VN30F1M")
const { snapshot, timeframe, loading, stale, online, error } =
  useDerivativesLive(symbol)
</script>
