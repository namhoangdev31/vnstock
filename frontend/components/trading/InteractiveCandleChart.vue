<template><TradingPanel title="Nến VN30F1M"><template #actions><div class="flex gap-1" role="group" aria-label="Khung thời gian"><button v-for="item in timeframes" :key="item" class="min-h-9 rounded-md px-3 text-xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-aave-violet" :class="timeframe === item ? 'bg-aave-violet text-aave-charcoal' : 'text-aave-graphite hover:bg-white/[0.06]'" @click="$emit('update:timeframe', item)">{{ item }}</button></div></template><div ref="chart" class="h-72 w-full" role="img" :aria-label="`Biểu đồ nến ${timeframe}. ${candles.length} nến`" /><p class="sr-only">{{ candles.length }} nến, giá mới nhất {{ candles.at(-1)?.close ?? "chưa có dữ liệu" }}.</p></TradingPanel></template>
<script setup lang="ts">
import {
  CandlestickSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
} from "lightweight-charts"
const props = defineProps<{
  candles: Array<{
    time: string
    open: number
    high: number
    low: number
    close: number
    volume: number
  }>
  timeframe: string
}>()
defineEmits<{ "update:timeframe": [value: string] }>()
const chart = useTemplateRef<HTMLDivElement>("chart")
const instance = shallowRef<IChartApi | null>(null)
let series: ISeriesApi<"Candlestick"> | null = null
const timeframes = ["1m", "5m", "15m"]
const draw = () => {
  if (!series) return
  const data: CandlestickData<Time>[] = props.candles.map((item) => ({
    time: Math.floor(new Date(item.time).getTime() / 1000) as Time,
    open: item.open,
    high: item.high,
    low: item.low,
    close: item.close,
  }))
  series.setData(data)
  instance.value?.timeScale().fitContent()
}
onMounted(() => {
  if (!chart.value) return
  instance.value = createChart(chart.value, {
    autoSize: true,
    layout: { background: { color: "transparent" }, textColor: "#858387" },
    grid: {
      vertLines: { color: "rgba(255,255,255,.04)" },
      horzLines: { color: "rgba(255,255,255,.04)" },
    },
    rightPriceScale: { borderVisible: false },
    timeScale: { borderVisible: false },
  })
  series = instance.value.addSeries(CandlestickSeries, {
    upColor: "#998eff",
    downColor: "#636161",
    borderVisible: false,
    wickUpColor: "#998eff",
    wickDownColor: "#636161",
  })
  draw()
})
watch(() => props.candles, draw, { deep: true })
onUnmounted(() => {
  instance.value?.remove()
  instance.value = null
  series = null
})
</script>
