<template><TradingPanel title="Alpha baskets"><div v-if="baskets && Object.keys(baskets.baskets).length" class="grid gap-3 sm:grid-cols-3"><div v-for="(items, horizon) in baskets.baskets" :key="horizon" class="rounded-lg border border-white/[0.06] p-3"><h3 class="text-xs font-semibold text-aave-ash">{{ horizon }}</h3><ul class="mt-2 space-y-1 text-xs text-aave-graphite"><li v-for="item in items" :key="item.symbol" class="flex justify-between"><span>{{ item.symbol }}</span><span class="font-mono text-aave-ash">{{ item.alpha_score.toFixed(2) }}</span></li></ul><button class="mt-3 min-h-9 w-full rounded-md border border-aave-violet/40 px-3 text-xs text-aave-violet disabled:opacity-40" :disabled="busy" @click="$emit('allocate', horizon)">Virtual Allocate</button></div></div><p v-else class="text-xs text-aave-graphite">Chưa có rổ alpha từ backend.</p></TradingPanel></template>
<script setup lang="ts">
import type { AlphaBasketsResponse } from "~/client/stockService"
defineProps<{ baskets: AlphaBasketsResponse | null; busy: boolean }>()
defineEmits<{ allocate: [horizon: string] }>()
</script>
