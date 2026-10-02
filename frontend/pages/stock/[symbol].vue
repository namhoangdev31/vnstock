<template>
  <div class="space-y-6">
    <!-- Header with Back Button -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <NuxtLink
          to="/stock"
          class="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <UIcon name="i-heroicons-arrow-left" class="w-5 h-5" />
        </NuxtLink>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-2xl font-bold font-mono text-white tracking-tight">
              {{ symbol }}
            </h1>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {{ overview?.industry_name || 'Cổ phiếu' }}
            </span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5">
            {{ overview?.company_name || 'Đang tải thông tin doanh nghiệp...' }}
          </p>
        </div>
      </div>

      <!-- Last Price Display -->
      <div v-if="lastPrice" class="sm:text-right">
        <div class="text-2xl sm:text-3xl font-bold font-mono text-emerald-400">
          {{ lastPrice.close.toLocaleString('vi-VN') }} <span class="text-xs font-normal text-slate-400">VND</span>
        </div>
        <p class="text-[11px] text-slate-400 font-mono">
          Phiên ngày: {{ lastPrice.trading_date }}
        </p>
      </div>
    </div>

    <!-- Interactive Price Chart Card -->
    <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <UIcon name="i-heroicons-presentation-chart-line" class="w-5 h-5 text-emerald-400" />
          <h2 class="text-sm font-bold text-white">Biểu đồ giá lịch sử (OHLCV)</h2>
        </div>

        <!-- Date Range Filter Buttons -->
        <div class="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 self-start sm:self-auto">
          <button
            v-for="range in ['1W', '1M', '3M', '6M', '1Y', '3Y']"
            :key="range"
            type="button"
            class="px-2.5 py-1 text-xs font-medium rounded-md transition-colors"
            :class="dateRange === range ? 'bg-emerald-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'"
            @click="dateRange = range; loadPriceData()"
          >
            {{ range }}
          </button>
        </div>
      </div>

      <!-- Canvas Chart Container -->
      <div class="relative w-full h-80 rounded-lg bg-slate-950/80 border border-slate-800/60 overflow-hidden flex items-center justify-center">
        <div v-if="priceLoading" class="flex flex-col items-center gap-2 text-slate-400">
          <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin text-emerald-400" />
          <span class="text-xs">Đang tải dữ liệu biểu đồ...</span>
        </div>
        <div v-else-if="ohlcvData.length === 0" class="text-xs text-slate-400">
          Không có dữ liệu giá trong khoảng thời gian này.
        </div>
        <canvas
          v-show="!priceLoading && ohlcvData.length > 0"
          ref="canvasRef"
          class="w-full h-full block"
        />
      </div>
    </div>

    <!-- Tabs: Overview & Financials -->
    <div class="space-y-4">
      <div class="flex border-b border-slate-800 gap-4">
        <button
          type="button"
          class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
          :class="activeTab === 'overview' ? 'border-emerald-400 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
          @click="activeTab = 'overview'"
        >
          <UIcon name="i-heroicons-information-circle" class="w-4 h-4" />
          Tổng quan doanh nghiệp
        </button>
        <button
          type="button"
          class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
          :class="activeTab === 'financials' ? 'border-emerald-400 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
          @click="activeTab = 'financials'"
        >
          <UIcon name="i-heroicons-document-chart-bar" class="w-4 h-4" />
          Báo cáo tài chính
        </button>
      </div>

      <!-- Tab Content: Overview -->
      <div v-if="activeTab === 'overview'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Company Info Card -->
        <div class="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <UIcon name="i-heroicons-building-office-2" class="w-4 h-4 text-emerald-400" />
            Hồ sơ niêm yết
          </h3>
          <div class="space-y-2 text-xs divide-y divide-slate-800/60">
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Tên đầy đủ:</span>
              <span class="font-medium text-slate-200 text-right">{{ overview?.company_name || '—' }}</span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Tên viết tắt:</span>
              <span class="font-medium text-slate-200">{{ overview?.short_name || '—' }}</span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Phân ngành ICB:</span>
              <span class="font-medium text-slate-200">{{ overview?.industry_name || '—' }}</span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Ngày lên sàn:</span>
              <span class="font-mono text-slate-200">{{ overview?.listed_date || '—' }}</span>
            </div>
            <div v-if="overview?.website" class="flex justify-between py-1.5">
              <span class="text-slate-400">Website chính thức:</span>
              <a
                :href="overview.website"
                target="_blank"
                rel="noreferrer"
                class="text-emerald-400 hover:underline flex items-center gap-1"
              >
                {{ overview.website }}
                <UIcon name="i-heroicons-arrow-top-right-on-square" class="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>

        <!-- Valuation & Share Structure -->
        <div class="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <UIcon name="i-heroicons-calculator" class="w-4 h-4 text-emerald-400" />
            Cấu trúc vốn & Quy mô
          </h3>
          <div class="space-y-2 text-xs divide-y divide-slate-800/60">
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Vốn hóa thị trường:</span>
              <span class="font-mono font-bold text-emerald-400">
                {{ overview?.market_cap ? (overview.market_cap / 1e9).toFixed(1) + ' tỷ VND' : '—' }}
              </span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Vốn điều lệ:</span>
              <span class="font-mono text-slate-200">
                {{ overview?.charter_capital ? (overview.charter_capital / 1e9).toFixed(1) + ' tỷ VND' : '—' }}
              </span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Cổ phiếu lưu hành:</span>
              <span class="font-mono text-slate-200">
                {{ overview?.outstanding_shares ? (overview.outstanding_shares / 1e6).toFixed(1) + ' triệu CP' : '—' }}
              </span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Ngày thành lập:</span>
              <span class="font-mono text-slate-200">{{ overview?.established_date || '—' }}</span>
            </div>
          </div>
        </div>

        <!-- Description -->
        <div v-if="overview?.description" class="md:col-span-2 p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-2">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300">
            Giới thiệu doanh nghiệp
          </h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            {{ overview.description }}
          </p>
        </div>
      </div>

      <!-- Tab Content: Financials -->
      <div v-else-if="activeTab === 'financials'" class="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300">
              Báo cáo kết quả kinh doanh theo quý
            </h3>
            <p class="text-xs text-slate-400">Dữ liệu tài chính hợp nhất trích xuất qua vnstock Finance</p>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-950 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
              <tr>
                <th class="py-2.5 px-4">Loại báo cáo</th>
                <th class="py-2.5 px-4">Năm</th>
                <th class="py-2.5 px-4">Kỳ / Quý</th>
                <th class="py-2.5 px-4">Mã định danh</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800/60">
              <tr v-if="financialReports.length === 0">
                <td colspan="4" class="py-8 text-center text-slate-400">
                  Chưa có dữ liệu báo cáo tài chính cho mã này.
                </td>
              </tr>
              <tr
                v-for="(item, idx) in financialReports"
                :key="idx"
                class="hover:bg-slate-800/40 font-mono"
              >
                <td class="py-2.5 px-4 text-emerald-400">{{ item.report_type }}</td>
                <td class="py-2.5 px-4 text-slate-200">{{ item.year }}</td>
                <td class="py-2.5 px-4 text-slate-200">{{ item.quarter ? 'Quý ' + item.quarter : 'Cả năm' }}</td>
                <td class="py-2.5 px-4 text-slate-400 text-[11px]">{{ item.id }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type {
  CompanyOverview,
  FinancialReportItem,
  OHLCVRecord,
} from "~/client/stockService"
import { StockService } from "~/client/stockService"

const route = useRoute()
const symbol = computed(() =>
  ((route.params.symbol as string) || "").toUpperCase(),
)

useHead({
  title: computed(() => `${symbol.value} - Chi tiết cổ phiếu | Vnstock Quants`),
})

const dateRange = ref("3M")
const activeTab = ref<"overview" | "financials">("overview")
const priceLoading = ref(false)
const ohlcvData = ref<OHLCVRecord[]>([])
const overview = ref<CompanyOverview | null>(null)
const financialReports = ref<FinancialReportItem[]>([])
const canvasRef = ref<HTMLCanvasElement | null>(null)

const lastPrice = computed(() => {
  return ohlcvData.value.length > 0
    ? ohlcvData.value[ohlcvData.value.length - 1]
    : null
})

const getStartDate = (range: string) => {
  const d = new Date()
  switch (range) {
    case "1W":
      d.setDate(d.getDate() - 7)
      break
    case "1M":
      d.setMonth(d.getMonth() - 1)
      break
    case "3M":
      d.setMonth(d.getMonth() - 3)
      break
    case "6M":
      d.setMonth(d.getMonth() - 6)
      break
    case "1Y":
      d.setFullYear(d.getFullYear() - 1)
      break
    case "3Y":
      d.setFullYear(d.getFullYear() - 3)
      break
    default:
      d.setMonth(d.getMonth() - 3)
  }
  return d.toISOString().split("T")[0]
}

const renderChart = () => {
  const canvas = canvasRef.value
  if (!canvas || ohlcvData.value.length === 0) return

  const ctx = canvas.getContext("2d")
  if (!ctx) return

  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) return

  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  ctx.scale(dpr, dpr)

  const w = rect.width
  const h = rect.height
  const padding = { top: 20, right: 65, bottom: 25, left: 10 }
  const chartW = w - padding.left - padding.right
  const chartH = h - padding.top - padding.bottom

  const closes = ohlcvData.value.map((d) => d.close)
  const minPrice = Math.min(...closes) * 0.998
  const maxPrice = Math.max(...closes) * 1.002
  const priceRange = maxPrice - minPrice || 1

  // Background
  ctx.fillStyle = "#020617"
  ctx.fillRect(0, 0, w, h)

  // Grid lines
  ctx.strokeStyle = "#1e293b"
  ctx.lineWidth = 0.5
  const gridLines = 5
  for (let i = 0; i <= gridLines; i++) {
    const y = padding.top + (i / gridLines) * chartH
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(w - padding.right, y)
    ctx.stroke()

    // Price labels on right axis
    const price = maxPrice - (i / gridLines) * priceRange
    ctx.fillStyle = "#94a3b8"
    ctx.font = "11px monospace"
    ctx.textAlign = "left"
    ctx.fillText(price.toFixed(0), w - padding.right + 8, y + 4)
  }

  // Emerald Gradient fill
  const gradient = ctx.createLinearGradient(
    0,
    padding.top,
    0,
    h - padding.bottom,
  )
  gradient.addColorStop(0, "rgba(16, 185, 129, 0.25)")
  gradient.addColorStop(1, "rgba(16, 185, 129, 0.0)")

  // Path for fill
  ctx.beginPath()
  ohlcvData.value.forEach((d, i) => {
    const x = padding.left + (i / (ohlcvData.value.length - 1 || 1)) * chartW
    const y = padding.top + ((maxPrice - d.close) / priceRange) * chartH
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  const lastX = padding.left + chartW
  ctx.lineTo(lastX, h - padding.bottom)
  ctx.lineTo(padding.left, h - padding.bottom)
  ctx.closePath()
  ctx.fillStyle = gradient
  ctx.fill()

  // Stroke line
  ctx.beginPath()
  ohlcvData.value.forEach((d, i) => {
    const x = padding.left + (i / (ohlcvData.value.length - 1 || 1)) * chartW
    const y = padding.top + ((maxPrice - d.close) / priceRange) * chartH
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.strokeStyle = "#10b981"
  ctx.lineWidth = 2
  ctx.stroke()

  // Date labels
  ctx.fillStyle = "#64748b"
  ctx.font = "10px monospace"
  ctx.textAlign = "center"
  const labelCount = Math.min(6, ohlcvData.value.length)
  for (let i = 0; i < labelCount; i++) {
    const idx = Math.floor(
      (i / (labelCount - 1 || 1)) * (ohlcvData.value.length - 1),
    )
    const x = padding.left + (idx / (ohlcvData.value.length - 1 || 1)) * chartW
    const dateStr = ohlcvData.value[idx].trading_date.slice(5) // MM-DD
    ctx.fillText(dateStr, x, h - 8)
  }
}

const loadPriceData = async () => {
  priceLoading.value = true
  try {
    const res = await StockService.getDailyPrice({
      path: { symbol: symbol.value },
      query: {
        start: getStartDate(dateRange.value),
        end: new Date().toISOString().split("T")[0],
      },
    })
    ohlcvData.value = res.data ?? []
    nextTick(() => {
      renderChart()
    })
  } catch (err) {
    console.error(err)
  } finally {
    priceLoading.value = false
  }
}

const loadOverview = async () => {
  try {
    const res = await StockService.getCompanyOverview({
      path: { symbol: symbol.value },
    })
    overview.value = res
  } catch (err) {
    console.error(err)
  }
}

const loadFinancials = async () => {
  try {
    const res = await StockService.getFinancials({
      path: { symbol: symbol.value },
      query: { report_type: "income_statement", period: "quarterly" },
    })
    financialReports.value = res.data ?? []
  } catch (err) {
    console.error(err)
  }
}

watch(dateRange, () => {
  loadPriceData()
})

onMounted(() => {
  loadPriceData()
  loadOverview()
  loadFinancials()
  window.addEventListener("resize", renderChart)
})

onUnmounted(() => {
  window.removeEventListener("resize", renderChart)
})
</script>
