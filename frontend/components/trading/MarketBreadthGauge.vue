<template><TradingPanel title="Độ rộng HOSE"><div v-if="breadth" class="grid grid-cols-5 gap-2 text-center text-xs"><Metric label="Tăng" :value="String(breadth.advancers ?? 0)" /><Metric label="Giảm" :value="String(breadth.decliners ?? 0)" /><Metric label="Đứng giá" :value="String(breadth.unchanged ?? 0)" /><Metric label="Trần" :value="String(breadth.ceiling_count ?? 0)" /><Metric label="Sàn" :value="String(breadth.floor_count ?? 0)" /></div><p v-else class="text-xs text-aave-graphite">Chưa có dữ liệu độ rộng.</p></TradingPanel></template>
<script setup lang="ts">
defineProps<{ breadth: Record<string, number> | null }>()
</script>
