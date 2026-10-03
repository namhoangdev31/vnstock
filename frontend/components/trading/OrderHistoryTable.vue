<template><TradingPanel title="Lịch sử lệnh"><div class="overflow-x-auto"><table v-if="orders.length" class="w-full min-w-[620px] text-left text-xs"><thead class="text-aave-graphite"><tr><th class="p-2">Thời điểm</th><th class="p-2">Mã</th><th class="p-2">Chiều</th><th class="p-2">Loại</th><th class="p-2">Trạng thái</th></tr></thead><tbody><tr v-for="item in orders" :key="item.id" class="border-t border-white/[0.06] text-aave-ash"><td class="p-2">{{ item.created_at }}</td><td class="p-2">{{ item.symbol }}</td><td class="p-2">{{ item.side }}</td><td class="p-2">{{ item.order_type }}</td><td class="p-2">{{ item.status }}</td></tr></tbody></table><p v-else class="text-xs text-aave-graphite">Chưa có lịch sử lệnh.</p></div></TradingPanel></template>
<script setup lang="ts">
import type { OrderItem } from "~/client/stockService"
defineProps<{ orders: OrderItem[] }>()
</script>
