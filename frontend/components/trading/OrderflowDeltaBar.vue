<template><TradingPanel title="Orderflow delta"><div class="space-y-2"><div v-for="row in rows.slice(-12)" :key="row.time" class="flex items-center gap-3 text-[10px] font-mono"><span class="w-16 text-aave-graphite">{{ shortTime(row.time) }}</span><div class="h-2 flex-1 overflow-hidden rounded bg-white/[0.06]"><div class="h-full bg-aave-violet" :style="{ width: `${Math.min(100, Math.abs(row.delta) / maxDelta * 100)}%` }" /></div><span class="w-20 text-right text-aave-ash">{{ row.delta.toLocaleString("vi-VN") }}</span></div><p v-if="!rows.length" class="text-xs text-aave-graphite">Chưa có dữ liệu orderflow.</p></div></TradingPanel></template>
<script setup lang="ts">
const props = defineProps<{ rows: Array<{ time: string; delta: number }> }>()
const maxDelta = computed(() =>
  Math.max(1, ...props.rows.map((row) => Math.abs(row.delta))),
)
const shortTime = (value: string) =>
  new Date(value).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  })
</script>
