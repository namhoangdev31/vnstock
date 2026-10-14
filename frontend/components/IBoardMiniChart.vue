<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { createDnseDatafeed } from "~/composables/useDnseDatafeed"
import { useIndexWsChannel } from "~/composables/useIndexWsChannel"
import { loadTradingViewScript } from "~/composables/useTradingViewScript"
import { MarketIndexSymbol } from "~/types/market"

interface Props {
  symbol: string
  initialResolution?: string
  isExpanded?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  initialResolution: "1",
  isExpanded: false,
})

const emit = defineEmits<{
  (e: "close", symbol: string): void
  (e: "expand", symbol: string): void
}>()

const containerId = `tv_mini_frame_${props.symbol.toLowerCase()}_${Math.random().toString(36).substring(2, 8)}`
const chartContainerRef = ref<HTMLDivElement | null>(null)
const isLoading = ref(true)
const loadError = ref<string | null>(null)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let tvWidget: any = null

const { indexData, isWsConnected, isFlashing, start, stop } = useIndexWsChannel(
  props.symbol,
)

function initChart() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const TradingView = (window as any).TradingView
  if (!TradingView?.widget) {
    loadError.value = "Không tìm thấy thư viện TradingView Charting Library"
    isLoading.value = false
    return
  }

  try {
    const datafeed = createDnseDatafeed()

    tvWidget = new TradingView.widget({
      container: containerId,
      locale: "vi",
      library_path: "/charting_library/",
      symbol: props.symbol,
      interval: props.initialResolution,
      timezone: "Asia/Ho_Chi_Minh",
      theme: "dark",
      autosize: true,
      datafeed,
      fullscreen: false,
      loading_screen: {
        backgroundColor: "#111217",
        foregroundColor: "#10b981",
      },
      disabled_features: [
        "use_localstorage_for_settings",
        "study_templates",
        "header_widget",
        "left_toolbar",
        "timeframes_toolbar",
        "control_bar",
        "context_menus",
        "pane_context_menu",
        "symbol_info",
        "display_market_status",
      ],
      enabled_features: [],
      overrides: {
        "paneProperties.background": "#111217",
        "paneProperties.backgroundType": "solid",
        "paneProperties.vertGridProperties.color": "rgba(255, 255, 255, 0.04)",
        "paneProperties.horzGridProperties.color": "rgba(255, 255, 255, 0.04)",
        "scalesProperties.textColor": "#a1a1aa",
        "mainSeriesProperties.candleStyle.upColor": "#089981",
        "mainSeriesProperties.candleStyle.downColor": "#f23645",
        "mainSeriesProperties.candleStyle.borderUpColor": "#089981",
        "mainSeriesProperties.candleStyle.borderDownColor": "#f23645",
        "mainSeriesProperties.candleStyle.wickUpColor": "#089981",
        "mainSeriesProperties.candleStyle.wickDownColor": "#f23645",
      },
    })

    tvWidget.onChartReady(() => {
      isLoading.value = false
    })
  } catch (err) {
    console.error(`[${props.symbol}] Khởi tạo widget thất bại:`, err)
    loadError.value = err instanceof Error ? err.message : String(err)
    isLoading.value = false
  }
}

const formatPrice = (val: number | string | undefined | null): string => {
  if (val === undefined || val === null || val === "") return "-"
  const n = typeof val === "number" ? val : Number.parseFloat(String(val))
  if (Number.isNaN(n)) return String(val)
  const parts = n.toFixed(2).split(".")
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  return parts.join(",")
}

const formatChangePercent = (val: number): string => {
  if (typeof val !== "number" || Number.isNaN(val) || Math.abs(val) < 0.001) {
    return "0,00%"
  }
  const sign = val > 0 ? "+" : "−"
  const parts = Math.abs(val).toFixed(2).split(".")
  const formattedAbs = `${parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${parts[1]}`
  return `${sign}${formattedAbs}%`
}

const getColorClass = (change: number): string => {
  if (change > 0.001) return "text-tv-bull"
  if (change < -0.001) return "text-tv-bear"
  return "text-tv-gold"
}

const derivativesRatio = computed(() => {
  const d = indexData.value.derivativesDepth
  if (!d) return { buyPct: 50, sellPct: 50 }
  const total = d.buyQuantity + d.sellQuantity || 1
  const buyPct = Math.round((d.buyQuantity / total) * 100)
  return { buyPct, sellPct: 100 - buyPct }
})

watch(
  () => props.symbol,
  (newSym) => {
    if (tvWidget && newSym) {
      try {
        tvWidget.activeChart().setSymbol(newSym)
      } catch (err) {
        console.warn(`[${props.symbol}] Lỗi khi chuyển mã ${newSym}:`, err)
      }
    }
  },
)

onMounted(async () => {
  await start()
  try {
    await loadTradingViewScript()
    initChart()
  } catch (err) {
    console.error(`[${props.symbol}] Lỗi khi nạp script TradingView:`, err)
    loadError.value = "Không thể nạp tệp thư viện TradingView"
    isLoading.value = false
  }
})

onBeforeUnmount(() => {
  if (tvWidget) {
    try {
      tvWidget.remove()
    } catch (e) {
      console.warn(`[${props.symbol}] Lỗi dọn dẹp widget:`, e)
    }
    tvWidget = null
  }
  stop()
})
</script>

<template>
  <div
    class="flex flex-col bg-surface-midnight rounded-lg border border-white/[0.08] overflow-hidden text-xs select-none transition-all shadow-sm"
    :class="{
      'ring-1 ring-tv-bull/40': isFlashing === 'up',
      'ring-1 ring-tv-bear/40': isFlashing === 'down',
    }"
  >

    <div
      class="px-2.5 py-1.5 flex items-center justify-between border-b border-white/[0.06] bg-surface-canvas/80 gap-2"
    >

      <div class="flex items-center gap-1.5 min-w-0">
        <UTooltip
          :text="
            isWsConnected ? 'WebSocket kết nối trực tiếp' : 'Đang kết nối lại'
          "
        >
          <span
            class="w-1.5 h-1.5 rounded-full inline-block shrink-0"
            :class="
              isWsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
            "
          />
        </UTooltip>

        <span class="text-white font-bold tracking-tight text-xs shrink-0">
          {{ indexData.name || props.symbol }}
        </span>

        <span
          class="font-mono tabular-nums text-xs transition-colors duration-200 shrink-0"
          :class="[
            isFlashing === 'up'
              ? 'text-tv-bull font-bold'
              : isFlashing === 'down'
                ? 'text-tv-bear font-bold'
                : getColorClass(indexData.change),
          ]"
        >
          {{ formatPrice(indexData.price) }}
        </span>

        <span
          class="text-[10px] font-mono tabular-nums flex items-center gap-0.5 font-medium shrink-0"
          :class="getColorClass(indexData.change)"
        >
          <span>{{
            indexData.change > 0 ? "▲" : indexData.change < 0 ? "▼" : "■"
          }}</span>
          <span>{{ indexData.change > 0 ? "+" : "" }}{{
            formatPrice(indexData.change)
          }}</span>
          <span>{{ formatChangePercent(indexData.changePercent) }}</span>
        </span>
      </div>

      <div class="flex items-center gap-1 text-zinc-400 shrink-0">
        <UTooltip text="Mở rộng khung biểu đồ">
          <button
            type="button"
            class="p-0.5 hover:text-white rounded hover:bg-white/[0.08] transition-colors cursor-pointer"
            @click="emit('expand', props.symbol)"
          >
            <UIcon
              name="i-heroicons-arrows-pointing-out"
              class="w-3.5 h-3.5"
            />
          </button>
        </UTooltip>

        <UTooltip text="Đóng khung chỉ số">
          <button
            type="button"
            class="p-0.5 hover:text-rose-400 rounded hover:bg-white/[0.08] transition-colors cursor-pointer"
            @click="emit('close', props.symbol)"
          >
            <UIcon name="i-heroicons-x-mark" class="w-3.5 h-3.5" />
          </button>
        </UTooltip>
      </div>
    </div>

    <div
      class="relative w-full bg-[#111217] overflow-hidden"
      :class="props.isExpanded ? 'h-[440px]' : 'h-[230px]'"
    >
      <div :id="containerId" ref="chartContainerRef" class="w-full h-full" />

      <div
        v-if="isLoading"
        class="absolute inset-0 flex flex-col items-center justify-center bg-[#111217]/90 z-10 font-mono text-xs text-zinc-400 gap-2 pointer-events-none"
      >
        <div
          class="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"
        />
        <span>Đang nạp biểu đồ kỹ thuật...</span>
      </div>

      <div
        v-if="loadError"
        class="absolute inset-0 flex flex-col items-center justify-center bg-[#111217] z-20 font-mono text-xs text-rose-400 p-4 text-center gap-1"
      >
        <span class="font-bold">Không thể khởi tạo biểu đồ</span>
        <span class="text-zinc-500 text-[11px]">{{ loadError }}</span>
      </div>
    </div>

    <div
      class="p-2 border-t border-white/[0.06] bg-surface-canvas/90 flex flex-col gap-1 text-[10px]"
    >

      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2 font-mono tabular-nums text-zinc-400">
          <span>KL: <strong class="text-zinc-200">{{ indexData.volume }}</strong></span>
          <span>GT: <strong class="text-zinc-200">{{ indexData.value }}</strong></span>
        </div>
        <span class="text-zinc-400 font-medium">
          {{ indexData.status }}
        </span>
      </div>

      <template
        v-if="
          indexData.symbol === MarketIndexSymbol.VN30F1M &&
          indexData.derivativesDepth
        "
      >
        <div class="flex flex-col gap-0.5 mt-0.5">
          <div
            class="flex items-center justify-between text-zinc-300 font-mono tabular-nums"
          >
            <span>
              Dư mua:
              <strong class="text-white"
                >{{
                  indexData.derivativesDepth.buyQuantity.toLocaleString("vi-VN")
                }}
                HĐ</strong
              >
            </span>
            <span>
              Dư bán:
              <strong class="text-white"
                >{{
                  indexData.derivativesDepth.sellQuantity.toLocaleString(
                    "vi-VN",
                  )
                }}
                HĐ</strong
              >
            </span>
          </div>

          <div class="h-1 w-full bg-zinc-800 rounded-full flex overflow-hidden">
            <div
              class="bg-tv-bull h-full transition-all duration-300"
              :style="{ width: `${derivativesRatio.buyPct}%` }"
            />
            <div
              class="bg-tv-bear h-full transition-all duration-300"
              :style="{ width: `${derivativesRatio.sellPct}%` }"
            />
          </div>
        </div>

        <div class="flex items-center justify-between text-zinc-400 pt-0.5">
          <span class="text-zinc-500 font-sans">Biên độ dao động:</span>
          <div class="flex items-center gap-1.5 font-mono text-[9px] tabular-nums">
            <UTooltip text="Giá tham chiếu">
              <span class="text-amber-400 font-semibold">
                {{ formatPrice(indexData.derivativesDepth.refPrice) }}
              </span>
            </UTooltip>
            <UTooltip text="Giá trần">
              <span class="text-purple-400 font-semibold">
                {{ formatPrice(indexData.derivativesDepth.ceilingPrice) }}
              </span>
            </UTooltip>
            <UTooltip text="Giá sàn">
              <span class="text-cyan-400 font-semibold">
                {{ formatPrice(indexData.derivativesDepth.floorPrice) }}
              </span>
            </UTooltip>
          </div>
        </div>
      </template>

      <template v-else-if="indexData.breadth">
        <div class="flex items-center justify-between pt-0.5 text-zinc-400">
          <span class="text-zinc-500 font-sans">Độ rộng thị trường:</span>
          <div class="flex items-center gap-1.5 font-mono text-[9px] tabular-nums">
            <UTooltip text="Mã tăng giá">
              <span class="text-tv-bull flex items-center gap-0.5">
                <span>▲</span>
                <span>{{ indexData.breadth.advance }}</span>
                <span
                  v-if="indexData.breadth.ceiling > 0"
                  class="text-purple-400"
                >
                  [{{ indexData.breadth.ceiling }}]
                </span>
              </span>
            </UTooltip>

            <UTooltip text="Mã đứng giá">
              <span class="text-tv-gold flex items-center gap-0.5">
                <span>■</span>
                <span>{{ indexData.breadth.unchanged }}</span>
              </span>
            </UTooltip>

            <UTooltip text="Mã giảm giá">
              <span class="text-tv-bear flex items-center gap-0.5">
                <span>▼</span>
                <span>{{ indexData.breadth.decline }}</span>
                <span
                  v-if="indexData.breadth.floor > 0"
                  class="text-cyan-400"
                >
                  [{{ indexData.breadth.floor }}]
                </span>
              </span>
            </UTooltip>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
