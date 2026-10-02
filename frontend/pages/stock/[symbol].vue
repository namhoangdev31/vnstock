<template>
  <div class="space-y-6">
    <!-- Header Strip with Back Button -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] backdrop-blur-xl">
      <div class="flex items-center gap-3.5">
        <NuxtLink
          to="/stock"
          class="p-2 rounded-lg bg-white/[0.03] border border-white/[0.08] text-slate-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          title="Quay lại danh mục"
        >
          <UIcon name="i-heroicons-arrow-left" class="w-5 h-5" />
        </NuxtLink>
        <div>
          <div class="flex items-center gap-2.5">
            <h1 class="text-2xl font-bold font-mono text-white tracking-tight">
              {{ symbol }}
            </h1>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {{ overview?.industry_name || 'CỔ PHIẾU' }}
            </span>
            <span v-if="overview?.short_name" class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-white/[0.04] text-slate-300 border border-white/[0.08]">
              {{ overview.short_name }}
            </span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5 font-sans">
            {{ overview?.company_name || 'Đang tải thông tin doanh nghiệp...' }}
          </p>
        </div>
      </div>

      <!-- Last Price Display -->
      <div v-if="lastPrice" class="sm:text-right font-mono">
        <div class="text-2xl sm:text-3xl font-bold text-emerald-400">
          {{ lastPrice.close.toLocaleString('vi-VN') }} <span class="text-xs font-normal text-slate-400">VND</span>
        </div>
        <p class="text-[11px] text-slate-400">
          Khớp ngày: {{ lastPrice.trading_date }}
        </p>
      </div>
    </div>

    <!-- Interactive Price Chart Card -->
    <div class="rounded-2xl border border-white/[0.08] bg-[#090d16]/90 p-5 shadow-2xl space-y-4 backdrop-blur-xl">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-3 font-mono">
          <div class="flex items-center gap-1.5 text-xs font-bold text-white uppercase tracking-wider">
            <span class="w-2 h-2 rounded-full bg-emerald-400" />
            Biểu Đồ Lịch Sử Giá & Khối Lượng (OHLCV)
          </div>
          <span v-if="hoveredBar" class="text-[11px] text-slate-300 hidden md:inline">
            O: <span class="text-white">{{ hoveredBar.open.toLocaleString() }}</span> | 
            H: <span class="text-emerald-400">{{ hoveredBar.high.toLocaleString() }}</span> | 
            L: <span class="text-rose-400">{{ hoveredBar.low.toLocaleString() }}</span> | 
            C: <span class="text-emerald-400">{{ hoveredBar.close.toLocaleString() }}</span> | 
            V: <span class="text-slate-200">{{ hoveredBar.volume.toLocaleString() }}</span>
          </span>
        </div>

        <!-- Date Range Filter Buttons -->
        <div class="flex items-center gap-1 bg-white/[0.02] p-1 rounded-lg border border-white/[0.08] self-start sm:self-auto font-mono">
          <button
            v-for="range in ['1W', '1M', '3M', '6M', '1Y', '3Y']"
            :key="range"
            type="button"
            class="px-2.5 py-1 text-xs font-medium rounded-md transition-colors"
            :class="dateRange === range ? 'bg-emerald-600 text-white font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'"
            @click="dateRange = range; loadPriceData()"
          >
            {{ range }}
          </button>
        </div>
      </div>

      <!-- Canvas Chart Container -->
      <div
        class="relative w-full h-84 rounded-xl bg-[#06080d] border border-white/[0.06] overflow-hidden flex items-center justify-center cursor-crosshair"
        @mousemove="onChartMouseMove"
        @mouseleave="onChartMouseLeave"
      >
        <div v-if="priceLoading" class="flex flex-col items-center gap-2 text-slate-400 font-mono">
          <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin text-emerald-400" />
          <span class="text-xs">Đang tải chuỗi dữ liệu nến...</span>
        </div>
        <div v-else-if="ohlcvData.length === 0" class="text-xs text-slate-400 font-mono">
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
      <div class="flex border-b border-white/[0.08] gap-6 font-mono text-xs">
        <button
          type="button"
          class="pb-3 font-bold transition-colors border-b-2 flex items-center gap-2"
          :class="activeTab === 'overview' ? 'border-emerald-400 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
          @click="activeTab = 'overview'"
        >
          <UIcon name="i-heroicons-building-office" class="w-4 h-4" />
          Hồ Sơ Doanh Nghiệp
        </button>
        <button
          type="button"
          class="pb-3 font-bold transition-colors border-b-2 flex items-center gap-2"
          :class="activeTab === 'financials' ? 'border-emerald-400 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
          @click="activeTab = 'financials'"
        >
          <UIcon name="i-heroicons-document-chart-bar" class="w-4 h-4" />
          Báo Cáo Tài Chính Hợp Nhất
        </button>
      </div>

      <!-- Tab Content: Overview -->
      <div v-if="activeTab === 'overview'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Company Info Card -->
        <div class="p-5 rounded-2xl border border-white/[0.08] bg-[#090d16]/80 space-y-3.5 shadow-xl">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
            <UIcon name="i-heroicons-identification" class="w-4 h-4 text-emerald-400" />
            Thông Tin Niêm Yết
          </h3>
          <div class="space-y-2.5 text-xs divide-y divide-white/[0.04]">
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Tên đầy đủ:</span>
              <span class="font-medium text-slate-200 text-right">{{ overview?.company_name || 'N/A' }}</span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Tên viết tắt:</span>
              <span class="font-medium text-slate-200">{{ overview?.short_name || 'N/A' }}</span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Phân ngành ICB:</span>
              <span class="font-medium text-slate-200">{{ overview?.industry_name || 'N/A' }}</span>
            </div>
            <div class="flex justify-between py-1.5 font-mono">
              <span class="text-slate-400 font-sans">Ngày lên sàn:</span>
              <span class="text-slate-200">{{ overview?.listed_date || 'N/A' }}</span>
            </div>
            <div v-if="overview?.website" class="flex justify-between py-1.5 font-mono">
              <span class="text-slate-400 font-sans">Website chính thức:</span>
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
        <div class="p-5 rounded-2xl border border-white/[0.08] bg-[#090d16]/80 space-y-3.5 shadow-xl">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
            <UIcon name="i-heroicons-calculator" class="w-4 h-4 text-emerald-400" />
            Cấu Trúc Vốn & Quy Mô
          </h3>
          <div class="space-y-2.5 text-xs divide-y divide-white/[0.04]">
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Vốn hóa thị trường:</span>
              <span class="font-mono font-bold text-emerald-400">
                {{ overview?.market_cap ? (overview.market_cap / 1e9).toFixed(1) + ' tỷ VND' : 'N/A' }}
              </span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Vốn điều lệ:</span>
              <span class="font-mono text-slate-200">
                {{ overview?.charter_capital ? (overview.charter_capital / 1e9).toFixed(1) + ' tỷ VND' : 'N/A' }}
              </span>
            </div>
            <div class="flex justify-between py-1.5">
              <span class="text-slate-400">Cổ phiếu lưu hành:</span>
              <span class="font-mono text-slate-200">
                {{ overview?.outstanding_shares ? (overview.outstanding_shares / 1e6).toFixed(1) + ' triệu CP' : 'N/A' }}
              </span>
            </div>
            <div class="flex justify-between py-1.5 font-mono">
              <span class="text-slate-400 font-sans">Ngày thành lập:</span>
              <span class="text-slate-200">{{ overview?.established_date || 'N/A' }}</span>
            </div>
          </div>
        </div>

        <!-- Description -->
        <div v-if="overview?.description" class="md:col-span-2 p-5 rounded-2xl border border-white/[0.08] bg-[#090d16]/80 space-y-2 shadow-xl">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
            Giới Thiệu Doanh Nghiệp
          </h3>
          <p class="text-xs text-slate-400 leading-relaxed font-sans">
            {{ overview.description }}
          </p>
        </div>
      </div>

      <!-- Tab Content: Financials -->
      <div v-else-if="activeTab === 'financials'" class="p-5 rounded-2xl border border-white/[0.08] bg-[#090d16]/80 space-y-4 shadow-xl">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div>
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
              Báo Cáo Kết Quả Kinh Doanh Theo Quý
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">Dữ liệu tài chính hợp nhất trích xuất qua vnstock Finance</p>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-mono">
            <thead class="bg-white/[0.02] text-slate-400 uppercase text-[10px] border-b border-white/[0.06] tracking-wider">
              <tr>
                <th class="py-2.5 px-4">Loại báo cáo</th>
                <th class="py-2.5 px-4">Năm</th>
                <th class="py-2.5 px-4">Kỳ / Quý</th>
                <th class="py-2.5 px-4">Mã định danh</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04]">
              <tr v-if="financialReports.length === 0">
                <td colspan="4" class="py-10 text-center text-slate-400 font-sans">
                  Chưa có dữ liệu báo cáo tài chính cho mã này.
                </td>
              </tr>
              <tr
                v-for="(item, idx) in financialReports"
                :key="idx"
                class="hover:bg-white/[0.02]"
              >
                <td class="py-2.5 px-4 text-emerald-400 font-semibold">{{ item.report_type }}</td>
                <td class="py-2.5 px-4 text-slate-200">{{ item.year }}</td>
                <td class="py-2.5 px-4 text-slate-200">{{ item.quarter ? 'Quý ' + item.quarter : 'Cả năm' }}</td>
                <td class="py-2.5 px-4 text-slate-500 text-[11px]">{{ item.id }}</td>
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
const symbol = computed(() => (route.params.symbol as string).toUpperCase())

useHead({
  title: `${symbol.value} - Chi tiết cổ phiếu & Biểu đồ - Vnstock Quants`,
})

const activeTab = ref<"overview" | "financials">("overview")
const dateRange = ref("3M")
const ohlcvData = ref<OHLCVRecord[]>([])
const priceLoading = ref(false)
const overview = ref<CompanyOverview | null>(null)
const financialReports = ref<FinancialReportItem[]>([])
const canvasRef = ref<HTMLCanvasElement | null>(null)
const hoveredBar = ref<OHLCVRecord | null>(null)
const mousePos = ref<{ x: number; y: number } | null>(null)

const lastPrice = computed(() => {
  if (ohlcvData.value.length === 0) return null
  return ohlcvData.value[ohlcvData.value.length - 1]
})

const getStartDate = (range: string): string => {
  const now = new Date()
  if (range === "1W") now.setDate(now.getDate() - 7)
  else if (range === "1M") now.setMonth(now.getMonth() - 1)
  else if (range === "3M") now.setMonth(now.getMonth() - 3)
  else if (range === "6M") now.setMonth(now.getMonth() - 6)
  else if (range === "1Y") now.setFullYear(now.getFullYear() - 1)
  else if (range === "3Y") now.setFullYear(now.getFullYear() - 3)
  return now.toISOString().split("T")[0]
}

const onChartMouseMove = (e: MouseEvent) => {
  if (!canvasRef.value || ohlcvData.value.length === 0) return
  const rect = canvasRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  mousePos.value = { x, y }

  const padding = { top: 25, right: 70, bottom: 30, left: 15 }
  const chartW = rect.width - padding.left - padding.right
  const relX = Math.max(0, Math.min(x - padding.left, chartW))
  const idx = Math.round((relX / (chartW || 1)) * (ohlcvData.value.length - 1))
  hoveredBar.value = ohlcvData.value[idx] || null
  renderChart()
}

const onChartMouseLeave = () => {
  mousePos.value = null
  hoveredBar.value = null
  renderChart()
}

const renderChart = () => {
  const canvas = canvasRef.value
  if (!canvas || ohlcvData.value.length === 0) return

  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr

  const ctx = canvas.getContext("2d")
  if (!ctx) return
  ctx.scale(dpr, dpr)

  const w = rect.width
  const h = rect.height
  const padding = { top: 25, right: 70, bottom: 30, left: 15 }
  const chartW = w - padding.left - padding.right
  const chartH = h - padding.top - padding.bottom

  const closes = ohlcvData.value.map((d: OHLCVRecord) => d.close)
  const minPrice = Math.min(...closes) * 0.995
  const maxPrice = Math.max(...closes) * 1.005
  const priceRange = maxPrice - minPrice || 1

  const volumes = ohlcvData.value.map((d: OHLCVRecord) => d.volume)
  const maxVol = Math.max(...volumes) || 1

  // Deep dark background
  ctx.fillStyle = "#06080d"
  ctx.fillRect(0, 0, w, h)

  // Subtle grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.05)"
  ctx.lineWidth = 1
  const gridLines = 5
  for (let i = 0; i <= gridLines; i++) {
    const y = padding.top + (i / gridLines) * chartH
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(w - padding.right, y)
    ctx.stroke()

    // Price labels on right axis
    const price = maxPrice - (i / gridLines) * priceRange
    ctx.fillStyle = "#64748b"
    ctx.font = "10px JetBrains Mono, monospace"
    ctx.textAlign = "left"
    ctx.fillText(
      price.toLocaleString("vi-VN", { maximumFractionDigits: 0 }),
      w - padding.right + 10,
      y + 3,
    )
  }

  // Volume Bars (bottom 25% height)
  const volHeight = chartH * 0.22
  ohlcvData.value.forEach((d: OHLCVRecord, i: number) => {
    const x = padding.left + (i / (ohlcvData.value.length - 1 || 1)) * chartW
    const barW = Math.max(1.5, (chartW / ohlcvData.value.length) * 0.65)
    const barH = (d.volume / maxVol) * volHeight
    const barY = h - padding.bottom - barH
    ctx.fillStyle =
      d.close >= d.open ? "rgba(16, 185, 129, 0.25)" : "rgba(244, 63, 94, 0.25)"
    ctx.fillRect(x - barW / 2, barY, barW, barH)
  })

  // Area gradient under price line
  const gradient = ctx.createLinearGradient(
    0,
    padding.top,
    0,
    h - padding.bottom,
  )
  gradient.addColorStop(0, "rgba(16, 185, 129, 0.22)")
  gradient.addColorStop(1, "rgba(16, 185, 129, 0.0)")

  ctx.beginPath()
  ohlcvData.value.forEach((d: OHLCVRecord, i: number) => {
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

  // Stroke price line
  ctx.beginPath()
  ohlcvData.value.forEach((d: OHLCVRecord, i: number) => {
    const x = padding.left + (i / (ohlcvData.value.length - 1 || 1)) * chartW
    const y = padding.top + ((maxPrice - d.close) / priceRange) * chartH
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  ctx.strokeStyle = "#10b981"
  ctx.lineWidth = 1.75
  ctx.stroke()

  // Date labels along X axis
  ctx.fillStyle = "#64748b"
  ctx.font = "10px JetBrains Mono, monospace"
  ctx.textAlign = "center"
  const labelCount = Math.min(6, ohlcvData.value.length)
  for (let i = 0; i < labelCount; i++) {
    const idx = Math.floor(
      (i / (labelCount - 1 || 1)) * (ohlcvData.value.length - 1),
    )
    const x = padding.left + (idx / (ohlcvData.value.length - 1 || 1)) * chartW
    const dateStr = ohlcvData.value[idx].trading_date.slice(5) // MM-DD
    ctx.fillText(dateStr, x, h - 10)
  }

  // Crosshair & Tooltip Overlay
  if (mousePos.value && hoveredBar.value) {
    const { x } = mousePos.value
    const clampedX = Math.max(padding.left, Math.min(x, w - padding.right))
    const barY =
      padding.top + ((maxPrice - hoveredBar.value.close) / priceRange) * chartH

    ctx.strokeStyle = "rgba(255, 255, 255, 0.25)"
    ctx.lineWidth = 0.75
    ctx.setLineDash([3, 3])

    // Vertical line
    ctx.beginPath()
    ctx.moveTo(clampedX, padding.top)
    ctx.lineTo(clampedX, h - padding.bottom)
    ctx.stroke()

    // Horizontal line
    ctx.beginPath()
    ctx.moveTo(padding.left, barY)
    ctx.lineTo(w - padding.right, barY)
    ctx.stroke()
    ctx.setLineDash([])

    // Coordinate point dot
    ctx.beginPath()
    ctx.arc(clampedX, barY, 4, 0, Math.PI * 2)
    ctx.fillStyle = "#10b981"
    ctx.fill()
    ctx.strokeStyle = "#ffffff"
    ctx.lineWidth = 1.5
    ctx.stroke()
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
