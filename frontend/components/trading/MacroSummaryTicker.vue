<template><TradingPanel title="Vĩ mô"><div class="grid gap-3 sm:grid-cols-2"><div v-for="row in macro" :key="String(row.indicator_code)" class="rounded-lg border border-white/[0.06] p-3"><p class="text-[10px] uppercase tracking-wider text-aave-graphite">{{ row.indicator_code }}</p><p class="mt-1 font-mono text-sm text-aave-ash">{{ typeof row.value === 'number' ? row.value.toLocaleString('vi-VN') : 'Chưa có dữ liệu' }}</p><p class="mt-1 text-[10px] text-aave-graphite">Nguồn: {{ row.source ?? 'Chưa xác định' }}</p></div></div><p v-if="!macro.length" class="text-xs text-aave-graphite">Chưa có dữ liệu tỷ giá hoặc vàng.</p></TradingPanel></template>
<script setup lang="ts">
defineProps<{ macro: Array<Record<string, unknown>> }>()
</script>
