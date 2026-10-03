<template><TradingPanel title="Đặt lệnh mô phỏng"><form class="grid gap-3 sm:grid-cols-2" @submit.prevent="submit"><label class="text-xs text-aave-ash">Mã tài sản<input v-model="form.symbol" class="mt-1 w-full rounded-lg border border-white/[0.08] bg-surface-abyss p-2 text-sm text-aave-paper" required /></label><label class="text-xs text-aave-ash">Chiều<select v-model="form.side" class="mt-1 w-full rounded-lg border border-white/[0.08] bg-surface-abyss p-2 text-sm text-aave-paper"><option>BUY</option><option>SELL</option></select></label><label class="text-xs text-aave-ash">Khối lượng<input v-model.number="form.quantity" type="number" min="1" class="mt-1 w-full rounded-lg border border-white/[0.08] bg-surface-abyss p-2 text-sm text-aave-paper" required /></label><label class="text-xs text-aave-ash">Giá<input v-model.number="form.price" type="number" min="0.01" step="0.01" class="mt-1 w-full rounded-lg border border-white/[0.08] bg-surface-abyss p-2 text-sm text-aave-paper" required /></label><label class="text-xs text-aave-ash">Loại lệnh<select v-model="form.order_type" class="mt-1 w-full rounded-lg border border-white/[0.08] bg-surface-abyss p-2 text-sm text-aave-paper"><option>LO</option><option>MP</option><option>ATO</option><option>ATC</option><option>STOP_LOSS</option></select></label><label class="text-xs text-aave-ash">Giá dừng lỗ<input v-model.number="form.stop_price" type="number" min="0.01" step="0.01" class="mt-1 w-full rounded-lg border border-white/[0.08] bg-surface-abyss p-2 text-sm text-aave-paper" /></label><div class="sm:col-span-2 rounded-lg border border-white/[0.06] p-3 text-xs text-aave-graphite">Ký quỹ dự kiến: <span class="font-mono text-aave-ash">{{ margin.toLocaleString("vi-VN", { maximumFractionDigits: 0 }) }}</span><span class="ml-2">Công thức giá × 100.000 × 17%</span></div><UTooltip :text="canSubmit ? 'Gửi lệnh vào sổ mô phỏng' : 'Số dư khả dụng không đủ hoặc dữ liệu giá chưa hợp lệ'"><button class="min-h-11 rounded-lg bg-aave-violet px-4 text-sm font-semibold text-aave-charcoal disabled:cursor-not-allowed disabled:opacity-40 sm:col-span-2" :disabled="!canSubmit || busy">{{ busy ? 'Đang gửi...' : 'Gửi lệnh mô phỏng' }}</button></UTooltip><p v-if="error" class="text-xs text-aave-graphite sm:col-span-2" role="alert">{{ error }}</p></form></TradingPanel></template>
<script setup lang="ts">
import type { PortfolioItem } from "~/client/stockService"
const props = defineProps<{ portfolio: PortfolioItem | null; busy: boolean }>()
const emit = defineEmits<{
  submit: [
    payload: {
      symbol: string
      side: string
      quantity: number
      price: number
      order_type: string
      stop_price?: number
    },
  ]
}>()
const form = reactive({
  symbol: "VN30F1M",
  side: "BUY",
  quantity: 1,
  price: 0,
  order_type: "LO",
  stop_price: undefined as number | undefined,
})
const error = shallowRef<string | null>(null)
const margin = computed(() => form.price * form.quantity * 100000 * 0.17)
const canSubmit = computed(() =>
  Boolean(
    props.portfolio &&
      form.price > 0 &&
      form.quantity > 0 &&
      margin.value <= props.portfolio.cash_balance,
  ),
)
const submit = () => {
  error.value = canSubmit.value
    ? null
    : "Số dư khả dụng không đủ hoặc dữ liệu giá chưa hợp lệ"
  if (!error.value) emit("submit", { ...form })
}
</script>
