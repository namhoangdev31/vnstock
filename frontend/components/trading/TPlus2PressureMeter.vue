<template><TradingPanel title="Áp lực thanh khoản T+2"><div class="flex items-end gap-4"><div class="h-3 flex-1 overflow-hidden rounded bg-white/[0.06]"><div class="h-full bg-aave-violet" :style="{ width: `${Math.max(0, Math.min(100, pressure * 100))}%` }" /></div><span class="font-mono text-sm text-aave-ash">{{ (pressure * 100).toFixed(1) }}%</span></div><p class="mt-2 text-[11px] text-aave-graphite">Chỉ số áp lực do Engine 2 cung cấp.</p></TradingPanel></template>
<script setup lang="ts">
defineProps<{ pressure: number }>()
</script>
