<script setup lang="ts">
import { computed } from "vue"
import type { IBoardStockRow, PutThroughTradeDTO } from "~/types/iboard"

interface Props {
  stocks: IBoardStockRow[]
  isLoading?: boolean
  selectedSymbol?: string | null
  isPutThrough?: boolean
  putThroughTrades?: PutThroughTradeDTO[]
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
  selectedSymbol: null,
  isPutThrough: false,
  putThroughTrades: () => [],
})

const emit = defineEmits<{
  "select-stock": [symbol: string]
  "open-order": [symbol: string]
}>()

const getPriceColorClass = (
  price: number,
  refPrice: number,
  ceiling: number,
  floor: number,
) => {
  if (ceiling > 0 && price >= ceiling) return "text-market-ceiling"
  if (floor > 0 && price <= floor) return "text-market-floor"
  if (price > refPrice) return "text-market-advance"
  if (price < refPrice) return "text-market-decline"
  return "text-market-unchanged"
}

const formatNumber = (num: number): string => {
  if (num === null || num === undefined || Number.isNaN(num)) return "-"
  return new Intl.NumberFormat("vi-VN").format(num)
}

const formatPrice = (p: number): string => {
  if (!p || Number.isNaN(p)) return "-"
  return p.toFixed(2)
}

const getSparklineSvg = (points: number[], _isPositive?: boolean) => {
  if (!points || points.length < 2) return { path: "", area: "" }
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  const width = 80
  const height = 24
  const padding = 2

  const coords = points.map((val, idx) => {
    const x = padding + (idx / (points.length - 1)) * (width - 2 * padding)
    const y = height - padding - ((val - min) / range) * (height - 2 * padding)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  const path = `M ${coords.join(" L ")}`
  const firstX = padding
  const lastX = width - padding
  const area = `${path} L ${lastX},${height} L ${firstX},${height} Z`

  return { path, area }
}

const getTickerInitials = (sym: string): string => {
  return sym.slice(0, 3).toUpperCase()
}
</script>

<template>
  <div class="flex-1 flex flex-col min-w-0 bg-tv-canvas select-none overflow-x-auto">
    <!-- CHẾ ĐỘ 1: BẢNG GIAO DỊCH THỎA THUẬN (Put-Through) - Ảnh 3, 4, 5 Cột Trái -->
    <template v-if="isPutThrough">
      <div class="w-full h-full flex flex-col font-mono text-xs">
        <div class="grid grid-cols-4 px-3 py-2 bg-tv-surface border-b border-tv-border text-[11px] text-tv-secondary font-sans font-semibold sticky top-0 z-10">
          <span class="text-left">Thời gian</span>
          <span class="text-left">Mã CK</span>
          <span class="text-right">Giá khớp</span>
          <span class="text-right">KL Khớp</span>
        </div>

        <div class="flex-1 overflow-y-auto divide-y divide-tv-border/50">
          <div
            v-for="(trade, idx) in putThroughTrades"
            :key="idx"
            class="grid grid-cols-4 px-3 py-2.5 items-center hover:bg-white/[0.04] transition-colors cursor-pointer"
            :class="selectedSymbol === trade.symbol ? 'bg-white/[0.08]' : ''"
            @click="emit('select-stock', trade.symbol)"
          >
            <span class="text-tv-secondary text-left">{{ trade.time }}</span>
            <span class="font-bold text-white text-left tracking-wide">{{ trade.symbol }}</span>
            <span class="text-right font-semibold text-market-advance">
              {{ formatPrice(trade.price) }}
            </span>
            <span class="text-right text-tv-primary">
              {{ formatNumber(trade.volume) }}
            </span>
          </div>
        </div>
      </div>
    </template>

    <!-- CHẾ ĐỘ 2: BẢNG GIÁ NIÊM YẾT / NGÀNH / PHÁI SINH / CHỨNG QUYỀN / ETF - Ảnh 1, 2 -->
    <template v-else>
      <div class="w-full flex-1 flex flex-col font-mono text-xs">
        <!-- Header Hàng Cột Bảng Giá -->
        <div class="grid grid-cols-12 px-3 py-2.5 bg-tv-surface border-b border-tv-border text-[11px] text-tv-secondary font-sans font-semibold sticky top-0 z-10">
          <div class="col-span-4 sm:col-span-3 text-left">Mã chứng khoán</div>
          <div class="col-span-2 text-right">Giá khớp</div>
          <div class="col-span-2 text-right">1 ngày (% / +/-)</div>
          <div class="col-span-2 text-right">Tổng khối lượng</div>
          <div class="hidden sm:block col-span-1 text-center">Biểu đồ</div>
          <div class="col-span-2 sm:col-span-1 text-center">Mua / Bán</div>
        </div>

        <!-- Skeleton Loading -->
        <div v-if="isLoading" class="p-4 space-y-3">
          <div v-for="i in 8" :key="i" class="h-10 bg-white/[0.03] rounded animate-pulse" />
        </div>

        <!-- Danh Sách Mã Cổ Phiếu -->
        <div v-else class="flex-1 overflow-y-auto divide-y divide-tv-border/40">
          <div
            v-for="stk in stocks"
            :key="stk.symbol"
            class="grid grid-cols-12 px-3 py-2.5 items-center hover:bg-white/[0.04] transition-colors cursor-pointer group"
            :class="selectedSymbol === stk.symbol ? 'bg-white/[0.08]' : ''"
            @click="emit('select-stock', stk.symbol)"
          >
            <!-- Cột 1: Mã CK, Icon/Avatar, Tên Đầy Đủ (Không hiện 9,99% ưu đãi margin) -->
            <div class="col-span-4 sm:col-span-3 flex items-center gap-2.5 pr-2 min-w-0">
              <div class="w-7 h-7 rounded-full bg-white/[0.08] border border-white/10 flex items-center justify-center shrink-0 text-[10px] font-bold text-white tracking-wider">
                {{ getTickerInitials(stk.symbol) }}
              </div>

              <div class="flex flex-col min-w-0">
                <div class="flex items-center gap-1.5">
                  <span class="font-bold text-white tracking-wide text-xs">
                    {{ stk.symbol }}
                  </span>
                </div>
                <span class="text-[10px] text-tv-secondary truncate max-w-[140px] sm:max-w-[200px]" :title="stk.name">
                  {{ stk.name }}
                </span>
              </div>
            </div>

            <!-- Cột 2: Giá khớp -->
            <div class="col-span-2 text-right font-bold text-xs" :class="getPriceColorClass(stk.last_price, stk.ref_price, stk.ceiling_price, stk.floor_price)">
              {{ formatPrice(stk.last_price) }}
            </div>

            <!-- Cột 3: Biến động 1 ngày -->
            <div class="col-span-2 text-right font-semibold text-xs" :class="stk.change >= 0 ? 'text-market-advance' : 'text-market-decline'">
              <span>{{ stk.change >= 0 ? '+' : '' }}{{ stk.change_percent.toFixed(2) }}%</span>
            </div>

            <!-- Cột 4: Tổng khối lượng -->
            <div class="col-span-2 text-right text-tv-primary font-medium text-xs">
              {{ formatNumber(stk.volume) }}
            </div>

            <!-- Cột 5: Biểu đồ Mini Sparkline -->
            <div class="hidden sm:flex col-span-1 justify-center items-center">
              <svg
                v-if="stk.sparkline && stk.sparkline.length > 1"
                class="w-20 h-6 overflow-visible"
                :class="stk.change >= 0 ? 'text-market-advance' : 'text-market-decline'"
                viewBox="0 0 80 24"
              >
                <!-- Vùng tô phẳng mờ dưới đường giá (không dùng gradient) -->
                <polygon
                  :points="getSparklineSvg(stk.sparkline, stk.change >= 0).area.replace('M ', '').replace(' Z', '').replace(/ L /g, ' ')"
                  fill="currentColor"
                  fill-opacity="0.16"
                />
                <!-- Đường giá -->
                <path
                  :d="getSparklineSvg(stk.sparkline, stk.change >= 0).path"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              <span v-else class="text-[10px] text-tv-secondary">-</span>
            </div>

            <!-- Cột 6: Thanh Tỷ Lệ Mua / Bán + Nút Watchlist -->
            <div class="col-span-2 sm:col-span-1 flex items-center justify-end gap-2 pr-1">
              <div class="flex flex-col items-center w-16">
                <div class="flex items-center justify-between w-full text-[9px] font-semibold mb-0.5">
                  <span class="text-market-advance">{{ stk.buy_ratio || 50 }}%</span>
                  <span class="text-market-decline">{{ stk.sell_ratio || 50 }}%</span>
                </div>
                <div class="w-full h-1 bg-surface-midnight rounded-full overflow-hidden flex">
                  <div
                    class="bg-market-advance h-full"
                    :style="{ width: `${stk.buy_ratio || 50}%` }"
                  />
                  <div
                    class="bg-market-decline h-full"
                    :style="{ width: `${stk.sell_ratio || 50}%` }"
                  />
                </div>
              </div>

              <button
                type="button"
                class="opacity-0 group-hover:opacity-100 p-1 text-tv-secondary hover:text-white transition-opacity cursor-pointer shrink-0"
                title="Thêm vào danh mục theo dõi"
                aria-label="Thêm vào danh mục theo dõi"
                @click.stop="emit('open-order', stk.symbol)"
              >
                <UIcon name="i-heroicons-plus" class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
