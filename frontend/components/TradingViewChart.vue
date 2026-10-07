<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue"
import { createDnseDatafeed } from "~/composables/useDnseDatafeed"

interface Props {
  symbol?: string
  interval?: string
}

const props = withDefaults(defineProps<Props>(), {
  symbol: "VN30F1M",
  interval: "1",
})

const containerId = `tv_chart_${Math.random().toString(36).substring(2, 9)}`
const chartContainerRef = ref<HTMLDivElement | null>(null)
const isLoading = ref(true)
const loadError = ref<string | null>(null)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let tvWidget: any = null

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window !== "undefined" && (window as any).TradingView?.widget) {
      resolve()
      return
    }

    const existing = document.querySelector(`script[src="${src}"]`)
    if (existing) {
      existing.addEventListener("load", () => resolve())
      existing.addEventListener("error", (e) => reject(e))
      return
    }

    const script = document.createElement("script")
    script.src = src
    script.type = "text/javascript"
    script.async = true
    script.onload = () => resolve()
    script.onerror = () =>
      reject(new Error(`Không thể nạp tệp thư viện: ${src}`))
    document.head.appendChild(script)
  })
}

function initChart() {
  const TradingView = (window as any).TradingView
  if (!TradingView?.widget) {
    loadError.value =
      "Không tìm thấy lớp TradingView widget trong thư viện tĩnh"
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
      interval: props.interval,
      timezone: "Asia/Ho_Chi_Minh",
      theme: "dark",
      autosize: true,
      datafeed,
      fullscreen: false,
      loading_screen: {
        backgroundColor: "#09090b",
        foregroundColor: "#10b981",
      },
      disabled_features: ["use_localstorage_for_settings"],
      enabled_features: ["study_templates"],
      overrides: {
        "paneProperties.background": "#09090b",
        "paneProperties.backgroundType": "solid",
        "paneProperties.vertGridProperties.color": "#18181b",
        "paneProperties.horzGridProperties.color": "#18181b",
        "scalesProperties.textColor": "#a1a1aa",
        "mainSeriesProperties.candleStyle.upColor": "#10b981",
        "mainSeriesProperties.candleStyle.downColor": "#f43f5e",
        "mainSeriesProperties.candleStyle.borderUpColor": "#10b981",
        "mainSeriesProperties.candleStyle.borderDownColor": "#f43f5e",
        "mainSeriesProperties.candleStyle.wickUpColor": "#10b981",
        "mainSeriesProperties.candleStyle.wickDownColor": "#f43f5e",
      },
    })

    tvWidget.onChartReady(() => {
      isLoading.value = false
    })
  } catch (err) {
    console.error("[TradingViewChart] Khởi tạo biểu đồ thất bại:", err)
    loadError.value = err instanceof Error ? err.message : String(err)
    isLoading.value = false
  }
}

onMounted(async () => {
  try {
    await loadScript("/charting_library/charting_library.standalone.js")
    initChart()
  } catch (err) {
    console.error("[TradingViewChart] Không thể tải thư viện TradingView:", err)
    loadError.value = "Không thể tải tệp thư viện TradingView Charting Library"
    isLoading.value = false
  }
})

onBeforeUnmount(() => {
  if (tvWidget) {
    try {
      tvWidget.remove()
    } catch (e) {
      console.warn("[TradingViewChart] Lỗi khi dọn dẹp widget:", e)
    }
    tvWidget = null
  }
})
</script>

<template>
  <div class="relative w-full h-full min-h-[500px] bg-zinc-950 rounded overflow-hidden">
    <!-- Vùng hiển thị biểu đồ -->
    <div :id="containerId" ref="chartContainerRef" class="w-full h-full min-h-[500px]" />

    <!-- Trạng thái đang tải -->
    <div
      v-if="isLoading"
      class="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950/80 z-10 font-mono text-xs text-zinc-400 gap-2"
    >
      <div class="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      <span>Đang khởi tạo biểu đồ TradingView...</span>
    </div>

    <!-- Trạng thái lỗi -->
    <div
      v-if="loadError"
      class="absolute inset-0 flex flex-col items-center justify-center bg-zinc-950 z-20 font-mono text-xs text-rose-400 p-4 text-center gap-2"
    >
      <span class="font-bold">Khởi tạo biểu đồ không thành công</span>
      <span class="text-zinc-500">{{ loadError }}</span>
    </div>
  </div>
</template>
