<template><TradingPanel title="Tín hiệu Ensemble"><div v-if="signal" class="grid gap-4 sm:grid-cols-5"><Metric label="Hướng" :value="signal.direction" /><Metric label="Tin cậy" :value="`${(signal.confidence * 100).toFixed(1)}%`" /><Metric label="Vào lệnh" :value="format(signal.entry)" /><Metric label="Dừng lỗ" :value="format(signal.stop_loss)" /><Metric label="Chốt lời" :value="format(signal.take_profit)" /></div><p v-else class="text-sm text-aave-graphite">Chưa có tín hiệu Ensemble được ghi nhận.</p><p class="mt-4 text-[11px] text-aave-graphite">Tín hiệu là dữ liệu nghiên cứu định lượng mô phỏng, không phải lời khuyên đầu tư.</p></TradingPanel></template>
<script setup lang="ts">
import type { DerivativesSnapshot } from "~/client/stockService"
defineProps<{ signal: DerivativesSnapshot["signal"] }>()
const format = (value: number | null | undefined) =>
  value == null
    ? "Chưa có dữ liệu"
    : value.toLocaleString("vi-VN", { maximumFractionDigits: 2 })
</script>
