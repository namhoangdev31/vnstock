<template><div class="space-y-4"><div v-if="stale || !online" class="rounded-lg border border-white/[0.08] bg-surface-midnight px-3 py-2 text-xs text-aave-ash" role="status">{{ online ? "Đang hiển thị dữ liệu gần nhất. Đang kết nối lại..." : "Ngoại tuyến. Đang chờ kết nối mạng." }}</div><div v-if="snapshot" class="grid gap-4 xl:grid-cols-2"><InstitutionalFlowChart :flows="snapshot.flows" /><MarketBreadthGauge :breadth="snapshot.breadth" /><TPlus2PressureMeter :pressure="Number(snapshot.engine.t2_pressure ?? 0)" /><MacroSummaryTicker :macro="snapshot.macro" /></div><p v-else-if="loading" class="text-xs text-aave-graphite">Đang tải radar dòng tiền...</p><p v-else-if="error" class="text-xs text-aave-graphite">{{ error }}</p></div></template>
<script setup lang="ts">
import { useFlowBreadthRadar } from "~/composables/useFlowBreadthRadar"
const { snapshot, loading, stale, online, error } = useFlowBreadthRadar()
</script>
