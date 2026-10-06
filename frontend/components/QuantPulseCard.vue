<script setup lang="ts">
import { ref, onMounted } from "vue"
import { dnseWsClient } from "~/composables/useDnseWs"
import { getHistoricalOhlc, type OhlcCandle } from "~/composables/useDnseApi"
import type { Ohlc } from "@vnstock/dnse"

const realtimeOhlc = ref<Ohlc | null>(null)
const previousDayCandles = ref<OhlcCandle[]>([])
const todayCandles = ref<OhlcCandle[]>([])
const allCandles = ref<OhlcCandle[]>([])

const previousDate = ref("")
const todayDate = ref("")
const previousClose = ref<number | null>(null)

const loadingHistory = ref(false)
const historyCount = ref(0)
const selectedTab = ref<"all" | "today" | "previous">("today")
const viewMode = ref<"chart" | "candles" | "ta">("chart")

// Cấu hình TradingView Chart
const chartOptions = {
  theme: "dark",
  autosize: true,
  symbol: "HNX:VN30F1M",
  interval: "1",
  timezone: "Asia/Ho_Chi_Minh",
  locale: "vi_VN",
  style: "1",
  toolbar_bg: "#09090b",
  enable_publishing: false,
  allow_symbol_change: true,
  details: false,
  hotlist: false,
  calendar: false,
}

// Cấu hình TradingView Phân Tích Kỹ Thuật
const taOptions = {
  interval: "15m",
  width: "100%",
  isTransparent: true,
  height: 420,
  symbol: "HNX:VN30F1M",
  showIntervalTabs: true,
  locale: "vi_VN",
  colorTheme: "dark",
}

onMounted(async () => {
  loadingHistory.value = true
  try {
    const history = await getHistoricalOhlc({
      symbol: "VN30F1M",
      resolution: "1",
    })
    if (history) {
      allCandles.value = history.candles
      todayCandles.value = history.todayCandles
      previousDayCandles.value = history.previousDayCandles
      previousDate.value = history.previousDate
      todayDate.value = history.todayDate
      previousClose.value = history.previousClose
      historyCount.value = history.count
      console.log(
        `Đã nạp ${history.count} nến 1m lịch sử cho ${history.symbol}. Phiên T-1: ${history.previousDayCandles.length} nến, Phiên hôm nay: ${history.todayCandles.length} nến`
      )
    }
  } catch (err) {
    console.error("Lỗi khi tải lịch sử OHLC:", err)
  } finally {
    loadingHistory.value = false
  }

  try {
    await dnseWsClient.connect()
    await dnseWsClient.subscribeOhlc(["VN30F1M"], "1", (item) => {
      realtimeOhlc.value = item

      const itemTime = item.time
      const lastIndex = todayCandles.value.length - 1

      if (lastIndex >= 0 && todayCandles.value[lastIndex].time === itemTime) {
        const current = todayCandles.value[lastIndex]
        current.high = Math.max(current.high, item.high)
        current.low = Math.min(current.low, item.low)
        current.close = item.close
        current.volume = item.volume
      } else if (lastIndex >= 0 && itemTime > todayCandles.value[lastIndex].time) {
        const dt = new Date(itemTime * 1000)
        const newCandle: OhlcCandle = {
          time: itemTime,
          open: item.open,
          high: item.high,
          low: item.low,
          close: item.close,
          volume: item.volume,
          tradingDate: todayDate.value,
          datetime: dt.toLocaleString("vi-VN", {
            timeZone: "Asia/Ho_Chi_Minh",
            hour: "2-digit",
            minute: "2-digit",
            day: "2-digit",
            month: "2-digit",
          }),
        }
        todayCandles.value.push(newCandle)
        allCandles.value.push(newCandle)
        historyCount.value = allCandles.value.length
      }
    })
  } catch (err) {
    console.error("Lỗi kết nối WebSocket DNSE:", err)
  }
})
</script>

<template>
  <div class="p-4 border border-zinc-800 rounded bg-zinc-950 text-zinc-100 font-mono text-xs space-y-3">
    <!-- Header thông tin mã & các chế độ xem -->
    <div class="flex items-center justify-between border-b border-zinc-800 pb-2">
      <div class="flex items-center gap-3">
        <span class="font-bold text-sm text-zinc-100">VN30F1M &middot; Nến 1 Phút</span>
        <span v-if="previousClose !== null" class="text-[11px] text-zinc-400">
          Đóng cửa T-1: <span class="text-zinc-200 font-semibold">{{ previousClose.toFixed(1) }}</span>
        </span>
      </div>

      <!-- Nút chuyển View Mode -->
      <div class="flex gap-1 bg-zinc-900 p-0.5 border border-zinc-800 rounded text-[11px]">
        <button
          type="button"
          class="px-2 py-0.5 rounded transition-colors"
          :class="viewMode === 'chart' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
          @click="viewMode = 'chart'"
        >
          Biểu đồ TradingView
        </button>
        <button
          type="button"
          class="px-2 py-0.5 rounded transition-colors"
          :class="viewMode === 'candles' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
          @click="viewMode = 'candles'"
        >
          Bảng Nến DNSE
        </button>
        <button
          type="button"
          class="px-2 py-0.5 rounded transition-colors"
          :class="viewMode === 'ta' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
          @click="viewMode = 'ta'"
        >
          Tín Hiệu Kỹ Thuật
        </button>
      </div>
    </div>

    <!-- Tóm tắt 2 phiên: Phiên hôm trước T-1 và Phiên hôm nay -->
    <div class="grid grid-cols-2 gap-2 text-[11px]">
      <div class="p-2 bg-zinc-900 border border-zinc-800 rounded">
        <div class="text-zinc-500 mb-1">Phiên trước đó: {{ previousDate || "T-1" }}</div>
        <div class="text-zinc-200 font-semibold">{{ previousDayCandles.length }} nến 1 phút</div>
      </div>
      <div class="p-2 bg-zinc-900 border border-zinc-800 rounded">
        <div class="text-zinc-500 mb-1">Phiên hôm nay: {{ todayDate || "T-0" }}</div>
        <div class="text-emerald-400 font-semibold">{{ todayCandles.length }} nến từ lúc mở cửa</div>
      </div>
    </div>

    <!-- Khối cập nhật Realtime từ WebSocket DNSE -->
    <div class="p-2.5 bg-zinc-900 border border-zinc-800 rounded">
      <div class="flex items-center justify-between text-zinc-400 text-[11px] mb-1">
        <span>Cập nhật Realtime qua WebSocket DNSE:</span>
        <span v-if="realtimeOhlc" class="text-emerald-400 text-[10px] font-semibold">Đang nhận dữ liệu</span>
      </div>
      <div v-if="realtimeOhlc" class="grid grid-cols-5 gap-2 text-center">
        <div><span class="text-zinc-500">Mở:</span> {{ realtimeOhlc.open.toFixed(1) }}</div>
        <div><span class="text-zinc-500">Cao:</span> {{ realtimeOhlc.high.toFixed(1) }}</div>
        <div><span class="text-zinc-500">Thấp:</span> {{ realtimeOhlc.low.toFixed(1) }}</div>
        <div><span class="text-zinc-500">Đóng:</span> {{ realtimeOhlc.close.toFixed(1) }}</div>
        <div><span class="text-zinc-500">KL:</span> {{ realtimeOhlc.volume.toLocaleString() }}</div>
      </div>
      <div v-else class="text-zinc-500 italic">Đang đợi tín hiệu WebSocket...</div>
    </div>

    <!-- VIEW 1: Biểu đồ TradingView -->
    <div v-if="viewMode === 'chart'" class="h-[520px] w-full border border-zinc-800 rounded overflow-hidden bg-zinc-900">
      <Chart :options="chartOptions" class="w-full h-full" />
    </div>

    <!-- VIEW 2: Phân tích kỹ thuật TradingView Gauge -->
    <div v-else-if="viewMode === 'ta'" class="p-4 border border-zinc-800 rounded bg-zinc-900 flex justify-center">
      <TechnicalAnalysis :options="taOptions" />
    </div>

    <!-- VIEW 3: Bảng danh sách nến DNSE chi tiết -->
    <div v-else class="space-y-2">
      <!-- Bộ lọc tab xem nến -->
      <div class="flex gap-1 border-b border-zinc-800 pb-1 text-[11px]">
        <button
          type="button"
          class="px-2 py-1 rounded"
          :class="selectedTab === 'today' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
          @click="selectedTab = 'today'"
        >
          Hôm nay [{{ todayCandles.length }}]
        </button>
        <button
          type="button"
          class="px-2 py-1 rounded"
          :class="selectedTab === 'previous' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
          @click="selectedTab = 'previous'"
        >
          Phiên trước [{{ previousDayCandles.length }}]
        </button>
        <button
          type="button"
          class="px-2 py-1 rounded"
          :class="selectedTab === 'all' ? 'bg-zinc-800 text-zinc-100 font-semibold' : 'text-zinc-400 hover:text-zinc-200'"
          @click="selectedTab = 'all'"
        >
          Toàn bộ [{{ allCandles.length }}]
        </button>
      </div>

      <!-- Danh sách nến hiển thị -->
      <div class="space-y-1 max-h-[350px] overflow-y-auto pr-1">
        <div
          v-for="candle in (selectedTab === 'today' ? todayCandles : selectedTab === 'previous' ? previousDayCandles : allCandles).slice(-15)"
          :key="candle.time"
          class="grid grid-cols-6 gap-1 p-1 bg-zinc-900/60 rounded text-[11px]"
        >
          <span class="text-zinc-500">{{ candle.datetime }}</span>
          <span>O: {{ candle.open.toFixed(1) }}</span>
          <span class="text-emerald-400">H: {{ candle.high.toFixed(1) }}</span>
          <span class="text-rose-400">L: {{ candle.low.toFixed(1) }}</span>
          <span class="font-bold">C: {{ candle.close.toFixed(1) }}</span>
          <span class="text-right text-zinc-400">V: {{ candle.volume.toLocaleString() }}</span>
        </div>
      </div>
    </div>
  </div>
</template>