<template><TradingPanel title="Mất cân bằng ATC"><div v-if="atc.available" class="text-sm text-aave-ash">{{ atc.reason || "Đã có dữ liệu ATC" }}</div><div v-else class="rounded-lg border border-white/[0.06] p-3 text-xs text-aave-graphite" role="status">Dữ liệu chưa khả dụng: {{ atc.reason }}</div></TradingPanel></template>
<script setup lang="ts">
defineProps<{ atc: { available: boolean; reason: string } }>()
</script>
