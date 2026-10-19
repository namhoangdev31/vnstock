<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import type { IBoardStockDetail } from "~/types/iboard"

interface Props {
  symbol: string
  isDerivatives?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isDerivatives: false,
})

const emit = defineEmits<{
  close: []
  "select-symbol": [symbol: string]
  "open-order": [symbol: string]
}>()

const activeTab = ref<"orderbook" | "info" | "events">("orderbook")
const subTab = ref<"time" | "depth">("time")

const detailData = ref<IBoardStockDetail | null>(null)
const isLoading = ref<boolean>(false)
const errorMessage = ref<string | null>(null)

const fetchStockDetail = async (sym: string) => {
  if (!sym) return
  isLoading.value = true
  errorMessage.value = null
  try {
    const res = await $fetch<IBoardStockDetail>(
      `/api/v1/stock/iboard/stock-detail/${sym}`,
    )
    detailData.value = res
  } catch (err) {
    console.error("Lỗi tải chi tiết mã:", err)
    errorMessage.value = "Không thể nạp dữ liệu chi tiết mã chứng khoán."
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.symbol,
  (newSym) => {
    if (newSym) {
      fetchStockDetail(newSym)
    }
  },
  { immediate: true },
)

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  pollTimer = setInterval(() => {
    if (props.symbol) {
      fetchStockDetail(props.symbol)
    }
  }, 10000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})

const stock = computed(() => detailData.value?.stock)

const priceColorClass = computed(() => {
  if (!stock.value) return "text-white"
  const p = stock.value.last_price
  const refP = stock.value.ref_price
  const ceil = stock.value.ceiling_price
  const flr = stock.value.floor_price

  if (ceil > 0 && p >= ceil) return "text-market-ceiling"
  if (flr > 0 && p <= flr) return "text-market-floor"
  if (p > refP) return "text-market-advance"
  if (p < refP) return "text-market-decline"
  return "text-market-unchanged"
})

const priceBgClass = computed(() => {
  if (!stock.value) return "bg-white/10"
  const p = stock.value.last_price
  const refP = stock.value.ref_price
  const ceil = stock.value.ceiling_price
  const flr = stock.value.floor_price

  if (ceil > 0 && p >= ceil)
    return "bg-market-ceiling/20 border-market-ceiling/40 text-market-ceiling"
  if (flr > 0 && p <= flr)
    return "bg-market-floor/20 border-market-floor/40 text-market-floor"
  if (p > refP)
    return "bg-market-advance/20 border-market-advance/40 text-market-advance"
  if (p < refP)
    return "bg-market-decline/20 border-market-decline/40 text-market-decline"
  return "bg-market-unchanged/20 border-market-unchanged/40 text-market-unchanged"
})

const formatNum = (val: number | null | undefined): string => {
  if (val === null || val === undefined || Number.isNaN(val)) return "0"
  return val.toLocaleString("en-US")
}

const formatPrice = (val: number | null | undefined): string => {
  if (val === null || val === undefined || Number.isNaN(val) || val === 0)
    return "-"
  return val.toFixed(2)
}

const getLevelColor = (price: number): string => {
  if (!stock.value || price === 0) return "text-tv-primary"
  const refP = stock.value.ref_price
  const ceil = stock.value.ceiling_price
  const flr = stock.value.floor_price

  if (ceil > 0 && price >= ceil) return "text-market-ceiling font-bold"
  if (flr > 0 && price <= flr) return "text-market-floor font-bold"
  if (price > refP) return "text-market-advance font-medium"
  if (price < refP) return "text-market-decline font-medium"
  return "text-market-unchanged font-medium"
}

const bidTotal = computed(() => {
  if (detailData.value?.total_bid_qtty) return detailData.value.total_bid_qtty
  if (!stock.value?.bid_book) return 0
  return stock.value.bid_book.reduce((sum, b) => sum + (b.volume || 0), 0)
})

const askTotal = computed(() => {
  if (detailData.value?.total_ask_qtty) return detailData.value.total_ask_qtty
  if (!stock.value?.ask_book) return 0
  return stock.value.ask_book.reduce((sum, a) => sum + (a.volume || 0), 0)
})

const bidRatioPct = computed(() => {
  const tot = bidTotal.value + askTotal.value
  if (tot === 0) return 50
  return Math.round((bidTotal.value / tot) * 100)
})

const askRatioPct = computed(() => 100 - bidRatioPct.value)

const activeBuy = computed(() => detailData.value?.active_buy_vol || 0)
const activeSell = computed(() => detailData.value?.active_sell_vol || 0)
const activeBuyPct = computed(() => {
  const tot = activeBuy.value + activeSell.value
  if (tot === 0) return 50
  return Math.round((activeBuy.value / tot) * 100)
})

const shareholderColors = [
  "#998eff", // aave-violet
  "#089981", // tv-bull
  "#d000ff", // market-ceiling
  "#f5a623", // tv-gold
  "#00e5ff", // market-floor
  "#ff0017", // market-decline
]

const doughnutSlices = computed(() => {
  const list = detailData.value?.shareholders || []
  if (list.length === 0) return []

  const totalRadius = 16
  const circumference = 2 * Math.PI * totalRadius
  let accumulatedPct = 0

  return list.map((sh, idx) => {
    const pct = sh.share_percent
    const strokeDasharray = `${(pct / 100) * circumference} ${circumference}`
    const strokeDashoffset = -((accumulatedPct / 100) * circumference)
    accumulatedPct += pct
    return {
      ...sh,
      color: shareholderColors[idx % shareholderColors.length],
      strokeDasharray,
      strokeDashoffset,
    }
  })
})

const parseEventDate = (
  rawDate: string,
): { day: string; monthYear: string } => {
  if (!rawDate) return { day: "--", monthYear: "--/----" }
  const clean = rawDate.replace("T00:00:00", "").trim()
  const parts = clean.split("-")
  if (parts.length === 3) {
    return { day: parts[2], monthYear: `${parts[1]}/${parts[0]}` }
  }
  return { day: clean.slice(0, 2), monthYear: clean.slice(3) }
}
</script>

<template>
  <div class="flex-1 flex flex-col bg-tv-canvas border border-tv-border rounded-xl overflow-hidden select-none">
    <!-- Header Thông Tin Mã Chi Tiết (Ảnh 3, 4, 5) -->
    <div class="flex flex-wrap items-center justify-between px-4 py-2.5 bg-tv-surface border-b border-tv-border gap-3">
      <!-- Cột Trái: Nút đóng, Mã, Tên, Ngành, Biến động 5D / 1Y -->
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="p-1 rounded text-tv-secondary hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
          title="Đóng chi tiết mã, quay lại bảng giá"
          aria-label="Đóng chi tiết mã"
          @click="emit('close')"
        >
          <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
        </button>

        <div class="flex flex-col">
          <div class="flex items-center gap-2">
            <span class="text-base font-bold font-mono tracking-wide text-white">
              {{ symbol }}
            </span>
            <span class="text-xs text-tv-secondary font-medium truncate max-w-[240px] sm:max-w-[360px]">
              {{ stock?.exchange || "HOSE" }} · {{ stock?.name || symbol }}
            </span>
            <button
              type="button"
              class="text-tv-secondary hover:text-aave-violet transition-colors cursor-pointer"
              title="Ghim mã theo dõi"
              aria-label="Ghim mã theo dõi"
            >
              <UIcon name="i-heroicons-bookmark" class="w-4 h-4" />
            </button>
          </div>

          <div class="flex items-center gap-3 text-xs mt-0.5">
            <span v-if="stock?.sector" class="text-tv-secondary">
              Ngành: <span class="text-aave-violet font-medium">{{ stock.sector }}</span>
            </span>

            <div v-if="detailData?.performance_5d !== null && detailData?.performance_5d !== undefined" class="flex items-center gap-1 font-mono text-[11px]">
              <span class="text-tv-secondary">5 ngày</span>
              <span :class="detailData.performance_5d >= 0 ? 'text-market-advance font-semibold' : 'text-market-decline font-semibold'">
                {{ detailData.performance_5d >= 0 ? '+' : '' }}{{ detailData.performance_5d.toFixed(2) }}%
              </span>
            </div>

            <div v-if="detailData?.performance_1y !== null && detailData?.performance_1y !== undefined" class="flex items-center gap-1 font-mono text-[11px]">
              <span class="text-tv-secondary">1 năm</span>
              <span :class="detailData.performance_1y >= 0 ? 'text-market-advance font-semibold' : 'text-market-decline font-semibold'">
                {{ detailData.performance_1y >= 0 ? '+' : '' }}{{ detailData.performance_1y.toFixed(2) }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Cột Phải: Khối giá khớp, Khối lượng, Giá trị, Nút giao dịch -->
      <div class="flex items-center gap-4">
        <div class="flex flex-col items-end font-mono tabular-nums">
          <div class="flex items-baseline gap-1.5">
            <span class="text-lg font-bold" :class="priceColorClass">
              {{ formatPrice(stock?.last_price) }}
            </span>
            <span
              class="px-1.5 py-0.5 rounded text-[11px] font-semibold border"
              :class="priceBgClass"
            >
              {{ stock && stock.change >= 0 ? '+' : '' }}{{ stock?.change.toFixed(2) || '0.00' }} ({{ stock && stock.change_percent >= 0 ? '+' : '' }}{{ stock?.change_percent.toFixed(2) || '0.00' }}%)
            </span>
          </div>

          <div class="flex items-center gap-2 text-[11px] text-tv-secondary mt-0.5">
            <span>{{ formatNum(stock?.volume) }} CP</span>
            <span>·</span>
            <span>{{ stock?.value_billion.toFixed(2) || '0.00' }} Tỷ</span>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-market-advance hover:bg-market-advance/80 text-black transition-colors cursor-pointer flex items-center gap-1"
            @click="emit('open-order', symbol)"
          >
            <UIcon name="i-heroicons-arrow-trending-up" class="w-3.5 h-3.5" />
            <span>Đặt lệnh</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Khối Nội Dung Thân: Chia làm 2 cột: Cột Giữa (TradingView Chart) & Cột Phải (3 Tab Bước giá / Thông tin / Sự kiện) -->
    <div class="flex-1 flex flex-col lg:flex-row overflow-hidden min-h-[540px]">
      <!-- Biểu đồ kỹ thuật TradingView (Ảnh 3, 4, 5) -->
      <div class="flex-1 flex flex-col min-w-0 border-b lg:border-b-0 lg:border-r border-tv-border bg-tv-canvas relative">
        <TradingViewChart :symbol="symbol" class="w-full h-full min-h-[460px]" />
      </div>

      <!-- Khối Tab Chi Tiết (Rộng ~380px) -->
      <div class="w-full lg:w-[380px] xl:w-[420px] flex flex-col bg-tv-surface shrink-0 overflow-hidden">
        <!-- 3 Tab Tiêu Đề: Bước giá / Thông tin / Sự kiện -->
        <div class="flex items-center border-b border-tv-border bg-tv-card px-2">
          <button
            type="button"
            class="flex-1 py-2.5 text-xs font-semibold transition-colors border-b-2 cursor-pointer text-center"
            :class="
              activeTab === 'orderbook'
                ? 'border-aave-violet text-white'
                : 'border-transparent text-tv-secondary hover:text-white'
            "
            @click="activeTab = 'orderbook'"
          >
            Bước giá
          </button>
          <button
            type="button"
            class="flex-1 py-2.5 text-xs font-semibold transition-colors border-b-2 cursor-pointer text-center"
            :class="
              activeTab === 'info'
                ? 'border-aave-violet text-white'
                : 'border-transparent text-tv-secondary hover:text-white'
            "
            @click="activeTab = 'info'"
          >
            Thông tin
          </button>
          <button
            type="button"
            class="flex-1 py-2.5 text-xs font-semibold transition-colors border-b-2 cursor-pointer text-center"
            :class="
              activeTab === 'events'
                ? 'border-aave-violet text-white'
                : 'border-transparent text-tv-secondary hover:text-white'
            "
            @click="activeTab = 'events'"
          >
            Sự kiện
          </button>
        </div>

        <!-- TAB 1: BƯỚC GIÁ (Ảnh 3) -->
        <div v-if="activeTab === 'orderbook'" class="flex-1 overflow-y-auto flex flex-col p-3 gap-3 font-mono text-xs">
          <!-- Bảng 3 Bước Giá Mua / Bán -->
          <div class="border border-tv-border rounded-lg bg-tv-card/60 overflow-hidden">
            <div class="grid grid-cols-4 px-2.5 py-1.5 bg-tv-card border-b border-tv-border text-[11px] text-tv-secondary">
              <span class="text-left">KL</span>
              <span class="text-right text-market-advance font-semibold">Mua</span>
              <span class="text-left text-market-decline font-semibold pl-3">Bán</span>
              <span class="text-right">KL</span>
            </div>

            <div class="divide-y divide-tv-border/40">
              <div
                v-for="i in 3"
                :key="i"
                class="grid grid-cols-4 px-2.5 py-1.5 text-xs hover:bg-white/[0.03] transition-colors tabular-nums"
              >
                <!-- Bên Mua: KL + Giá -->
                <span class="text-left text-tv-primary">
                  {{ formatNum(stock?.bid_book?.[i - 1]?.volume) }}
                </span>
                <span class="text-right" :class="getLevelColor(stock?.bid_book?.[i - 1]?.price || 0)">
                  {{ formatPrice(stock?.bid_book?.[i - 1]?.price) }}
                </span>

                <!-- Bên Bán: Giá + KL -->
                <span class="text-left pl-3" :class="getLevelColor(stock?.ask_book?.[i - 1]?.price || 0)">
                  {{ formatPrice(stock?.ask_book?.[i - 1]?.price) }}
                </span>
                <span class="text-right text-tv-primary">
                  {{ formatNum(stock?.ask_book?.[i - 1]?.volume) }}
                </span>
              </div>
            </div>
          </div>

          <!-- Thanh Tỷ Lệ Dư Mua vs Dư Bán -->
          <div class="flex flex-col gap-1 text-[11px]">
            <div class="flex items-center justify-between text-tv-secondary">
              <span>Dư mua: <span class="text-white font-semibold">{{ formatNum(bidTotal) }}</span></span>
              <span>Dư bán: <span class="text-white font-semibold">{{ formatNum(askTotal) }}</span></span>
            </div>
            <div class="w-full h-1.5 rounded-full overflow-hidden flex bg-tv-card border border-tv-border">
              <div class="h-full bg-market-advance transition-all duration-300" :style="{ width: `${bidRatioPct}%` }" />
              <div class="h-full bg-market-decline transition-all duration-300" :style="{ width: `${askRatioPct}%` }" />
            </div>
          </div>

          <!-- Dải Giá Giới Hạn Phiên (Sàn, TC, Trần / Thấp, TB, Cao) -->
          <div class="grid grid-cols-3 gap-2 py-2 px-2.5 rounded-lg bg-tv-card/40 border border-tv-border text-[11px] tabular-nums">
            <div class="flex flex-col">
              <span class="text-tv-secondary">Sàn</span>
              <span class="text-market-floor font-bold">{{ formatPrice(stock?.floor_price) }}</span>
            </div>
            <div class="flex flex-col text-center">
              <span class="text-tv-secondary">TC</span>
              <span class="text-market-unchanged font-bold">{{ formatPrice(stock?.ref_price) }}</span>
            </div>
            <div class="flex flex-col text-right">
              <span class="text-tv-secondary">Trần</span>
              <span class="text-market-ceiling font-bold">{{ formatPrice(stock?.ceiling_price) }}</span>
            </div>

            <div class="flex flex-col pt-1 border-t border-tv-border/50">
              <span class="text-tv-secondary">Thấp</span>
              <span class="text-market-decline font-semibold">{{ formatPrice(stock?.low_price) }}</span>
            </div>
            <div class="flex flex-col text-center pt-1 border-t border-tv-border/50">
              <span class="text-tv-secondary">TB</span>
              <span class="text-market-unchanged font-semibold">{{ formatPrice(stock?.avg_price) }}</span>
            </div>
            <div class="flex flex-col text-right pt-1 border-t border-tv-border/50">
              <span class="text-tv-secondary">Cao</span>
              <span class="text-market-advance font-semibold">{{ formatPrice(stock?.high_price) }}</span>
            </div>
          </div>

          <!-- Thống Kê Giao Dịch & Khối Ngoại -->
          <div class="flex flex-col gap-1.5 py-2 px-2.5 rounded-lg bg-tv-card/40 border border-tv-border text-[11px] tabular-nums">
            <div class="flex items-center justify-between">
              <span class="text-tv-secondary">KL Khớp</span>
              <span class="text-white font-medium">{{ formatNum(stock?.volume) }} CP</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-tv-secondary">GT Khớp</span>
              <span class="text-white font-medium">{{ stock?.value_billion.toFixed(2) || '0.00' }} Tỷ</span>
            </div>
            <div class="flex items-center justify-between pt-1 border-t border-tv-border/40">
              <span class="text-tv-secondary">NN Mua / Bán</span>
              <span class="text-white font-medium">
                <span class="text-market-advance">{{ formatNum(stock?.foreign_buy) }}</span> /
                <span class="text-market-decline">{{ formatNum(stock?.foreign_sell) }}</span>
              </span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-tv-secondary">Dư NN</span>
              <span class="text-white font-medium">{{ formatNum(stock?.foreign_room) }}</span>
            </div>
          </div>

          <!-- Khớp Chủ Động & Sổ Lệnh Khớp Thời Gian -->
          <div class="flex flex-col gap-2 pt-1 border-t border-tv-border/70">
            <!-- Thanh tỷ lệ Khớp chủ động M vs B -->
            <div class="flex items-center justify-between text-[11px] font-semibold">
              <span class="text-market-advance">M {{ formatNum(activeBuy) }}</span>
              <span class="text-tv-secondary text-[10px]">Khớp chủ động</span>
              <span class="text-market-decline">{{ formatNum(activeSell) }} B</span>
            </div>
            <div class="w-full h-1.5 rounded-full overflow-hidden flex bg-tv-card border border-tv-border">
              <div class="h-full bg-market-advance" :style="{ width: `${activeBuyPct}%` }" />
              <div class="h-full bg-market-decline" :style="{ width: `${100 - activeBuyPct}%` }" />
            </div>

            <!-- Bảng Sổ Lệnh Khớp (Time & Sales) -->
            <div class="border border-tv-border rounded-lg bg-tv-card/50 overflow-hidden mt-1">
              <div class="grid grid-cols-5 px-2 py-1 bg-tv-card border-b border-tv-border text-[10px] text-tv-secondary">
                <span>Thời gian</span>
                <span class="text-center">M/B</span>
                <span class="text-right">KL khớp</span>
                <span class="text-right">Giá khớp</span>
                <span class="text-right">+/-</span>
              </div>

              <div class="max-h-40 overflow-y-auto divide-y divide-tv-border/30 text-[11px] tabular-nums">
                <div
                  v-for="(t, idx) in detailData?.matched_ticks || []"
                  :key="idx"
                  class="grid grid-cols-5 px-2 py-1 items-center hover:bg-white/[0.03]"
                >
                  <span class="text-tv-secondary text-[10px]">{{ t.time }}</span>
                  <span class="text-center">
                    <span
                      class="px-1 py-0.2 rounded text-[9px] font-bold"
                      :class="t.side === 'B' ? 'bg-market-advance/20 text-market-advance' : 'bg-market-decline/20 text-market-decline'"
                    >
                      {{ t.side }}
                    </span>
                  </span>
                  <span class="text-right text-tv-primary">{{ formatNum(t.volume) }}</span>
                  <span class="text-right" :class="getLevelColor(t.price)">{{ formatPrice(t.price) }}</span>
                  <span
                    class="text-right text-[10px]"
                    :class="stock && t.price > stock.ref_price ? 'text-market-advance' : stock && t.price < stock.ref_price ? 'text-market-decline' : 'text-market-unchanged'"
                  >
                    {{ stock ? (t.price - stock.ref_price > 0 ? '+' : '') + (t.price - stock.ref_price).toFixed(2) : '0.00' }}
                  </span>
                </div>

                <div v-if="!detailData?.matched_ticks?.length" class="p-3 text-center text-tv-secondary text-xs">
                  Chưa có dữ liệu khớp lệnh trong phiên
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 2: THÔNG TIN DOANH NGHIỆP & CƠ CẤU CỔ ĐÔNG (Ảnh 4) -->
        <div v-else-if="activeTab === 'info'" class="flex-1 overflow-y-auto flex flex-col p-4 gap-4 text-xs">
          <!-- Giới Thiệu Doanh Nghiệp -->
          <div class="flex flex-col gap-2">
            <h3 class="text-xs font-bold text-white uppercase tracking-wider">
              Giới thiệu doanh nghiệp
            </h3>
            <p class="text-tv-primary leading-relaxed text-justify bg-tv-card/60 p-3 rounded-lg border border-tv-border">
              {{ detailData?.company_profile || "Doanh nghiệp hoạt động trong lĩnh vực niêm yết trên thị trường chứng khoán Việt Nam. Thông tin chi tiết đang được cập nhật từ hồ sơ công bố thông tin." }}
            </p>
          </div>

          <!-- Cơ Cấu Cổ Đông & Biểu Đồ Tròn Doughnut Chart (Ảnh 4) -->
          <div class="flex flex-col gap-3 pt-2 border-t border-tv-border">
            <h3 class="text-xs font-bold text-white uppercase tracking-wider">
              Cơ cấu cổ đông
            </h3>

            <!-- Biểu Đồ Tròn Doughnut SVG -->
            <div class="flex items-center justify-center py-2">
              <svg viewBox="0 0 42 42" class="w-32 h-32 transform -rotate-90">
                <circle
                  cx="21"
                  cy="21"
                  r="16"
                  fill="transparent"
                  stroke="#2a2e39"
                  stroke-width="5"
                />
                <circle
                  v-for="(slice, sIdx) in doughnutSlices"
                  :key="sIdx"
                  cx="21"
                  cy="21"
                  r="16"
                  fill="transparent"
                  :stroke="slice.color"
                  stroke-width="5"
                  :stroke-dasharray="slice.strokeDasharray"
                  :stroke-dashoffset="slice.strokeDashoffset"
                  class="transition-all duration-500"
                />
              </svg>
            </div>

            <!-- Danh Sách Cổ Đông & Tỷ Lệ % -->
            <div class="flex flex-col gap-2 divide-y divide-tv-border/40 font-mono text-xs">
              <div
                v-for="(sh, idx) in doughnutSlices"
                :key="idx"
                class="flex items-start justify-between pt-1.5 gap-2"
              >
                <div class="flex items-center gap-2 min-w-0">
                  <span class="w-2.5 h-2.5 rounded-full shrink-0" :style="{ backgroundColor: sh.color }" />
                  <span class="text-tv-primary text-[11px] truncate" :title="sh.name">{{ sh.name }}</span>
                </div>
                <span class="text-white font-bold shrink-0 text-[11px]">{{ sh.share_percent.toFixed(2) }}%</span>
              </div>

              <div v-if="!doughnutSlices.length" class="text-center text-tv-secondary py-3">
                Chưa có dữ liệu danh sách cổ đông
              </div>
            </div>
          </div>
        </div>

        <!-- TAB 3: SỰ KIỆN DOANH NGHIỆP (Ảnh 5) -->
        <div v-else-if="activeTab === 'events'" class="flex-1 overflow-y-auto flex flex-col p-3 gap-2.5 text-xs">
          <div
            v-for="(ev, idx) in detailData?.events || []"
            :key="idx"
            class="flex items-start gap-3 p-2.5 rounded-lg bg-tv-card/60 border border-tv-border hover:bg-white/[0.03] transition-colors"
          >
            <!-- Date Badge (Day lớn, Month/Year dưới) -->
            <div class="flex flex-col items-center justify-center w-12 py-1 rounded bg-tv-card border border-tv-border shrink-0">
              <span class="text-base font-bold font-mono text-white leading-none">
                {{ parseEventDate(ev.date).day }}
              </span>
              <span class="text-[9px] font-mono text-tv-secondary mt-0.5">
                {{ parseEventDate(ev.date).monthYear }}
              </span>
            </div>

            <!-- Tiêu Đề & Nội Dung Sự Kiện -->
            <div class="flex flex-col min-w-0 flex-1">
              <span class="text-white font-semibold text-xs leading-snug">
                {{ ev.title }}
              </span>
              <span class="text-[11px] text-tv-secondary mt-1">
                Ngày thực hiện: {{ ev.date || "Đang cập nhật" }}
              </span>
            </div>
          </div>

          <div v-if="!detailData?.events?.length" class="p-6 text-center text-tv-secondary text-xs">
            Chưa có lịch sự kiện doanh nghiệp được công bố
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
