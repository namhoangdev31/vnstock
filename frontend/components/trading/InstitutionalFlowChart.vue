<template><TradingPanel title="Dòng tiền tổ chức"><div v-if="flows.length" class="space-y-2"><div v-for="(flow, index) in flows.slice(-10)" :key="`${String(flow.trading_date)}-${index}`" class="grid grid-cols-3 gap-2 text-xs"><span class="text-aave-graphite">{{ flow.trading_date }}</span><span class="font-mono text-aave-ash">Ngoại: {{ format(flow.foreign_net_value) }}</span><span class="font-mono text-aave-ash">Tự doanh: {{ format(flow.prop_net_value) }}</span></div></div><p v-else class="text-xs text-aave-graphite">Chưa có dữ liệu dòng tiền tổ chức.</p></TradingPanel></template>
<script setup lang="ts">
defineProps<{ flows: Array<Record<string, unknown>> }>()
const format = (value: unknown) =>
  typeof value === "number" ? value.toLocaleString("vi-VN") : "Chưa có dữ liệu"
</script>
