<template><TradingPanel title="Vị thế đang mở"><div class="overflow-x-auto"><table v-if="positions.length" class="w-full min-w-[620px] text-left text-xs"><thead class="text-aave-graphite"><tr><th class="p-2">Mã</th><th class="p-2">Chiều</th><th class="p-2">Khối lượng</th><th class="p-2">Giá hiện tại</th><th class="p-2">PnL</th><th class="p-2">Thao tác</th></tr></thead><tbody><tr v-for="item in positions" :key="item.id" class="border-t border-white/[0.06] text-aave-ash"><td class="p-2">{{ item.symbol }}</td><td class="p-2">{{ item.side }}</td><td class="p-2 font-mono">{{ item.quantity }}</td><td class="p-2 font-mono">{{ item.current_price }}</td><td class="p-2 font-mono">{{ item.unrealized_pnl }}</td><td class="p-2"><button class="min-h-9 rounded-md border border-white/[0.12] px-3 text-xs text-aave-ash hover:bg-white/[0.06]" @click="$emit('close', item)">Đóng nhanh</button></td></tr></tbody></table><p v-else class="text-xs text-aave-graphite">Chưa có vị thế mở.</p></div></TradingPanel></template>
<script setup lang="ts">
import type { PositionItem } from "~/client/stockService"
defineProps<{ positions: PositionItem[] }>()
defineEmits<{ close: [position: PositionItem] }>()
</script>
