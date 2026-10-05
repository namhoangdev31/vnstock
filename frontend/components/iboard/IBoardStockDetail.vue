<script setup lang="ts">
import { computed, ref } from "vue"
import type {
  CompanyOverviewDTO,
  CorporateEventDTO,
  IBoardCandleBar,
  MatchedTickDTO,
} from "~/client/stockService"
import type { StockRowDisplay } from "./types"

const props = defineProps<{
  stock: StockRowDisplay
  stockList: StockRowDisplay[]
  candles: IBoardCandleBar[]
  isCandlesLoading?: boolean
  selectedTimeframe: string
  timeframes: string[]
  matchedTicks: MatchedTickDTO[]
  stockOverview: CompanyOverviewDTO | null
  corporateEvents: CorporateEventDTO[]
}>()

const emit = defineEmits<{
  (e: "close"): void
  (e: "select-stock", stock: StockRowDisplay): void
  (e: "update:selectedTimeframe", tf: string): void
  (e: "quick-order", symbol: string, price: number, side: "BUY" | "SELL"): void
}>()

const selectedDetailTab = ref<"depth" | "overview" | "events">("depth")
const selectedDepthSubTab = ref<"depth" | "time">("depth")

const chartCandles = computed(() => {
  const list = props.candles
  if (!list || list.length === 0) {
    return []
  }

  const highs = list.map((c) => c.high)
  const lows = list.map((c) => c.low)
  const vols = list.map((c) => c.volume)

  const minPrice = Math.min(...lows)
  const maxPrice = Math.max(...highs)
  const priceRange = maxPrice - minPrice || 1
  const maxVol = Math.max(...vols) || 1

  const chartHeight = 140
  const topPad = 15
  const count = list.length
  const stepX = 750 / (count + 1)
  const candleW = Math.max(Math.min(stepX * 0.6, 20), 4)

  return list.map((c, i) => {
    const x = 30 + (i + 1) * stepX
    const wickHigh =
      topPad + chartHeight - ((c.high - minPrice) / priceRange) * chartHeight
    const wickLow =
      topPad + chartHeight - ((c.low - minPrice) / priceRange) * chartHeight
    const openY =
      topPad + chartHeight - ((c.open - minPrice) / priceRange) * chartHeight
    const closeY =
      topPad + chartHeight - ((c.close - minPrice) / priceRange) * chartHeight

    const bodyTop = Math.min(openY, closeY)
    const bodyHeight = Math.max(Math.abs(openY - closeY), 2)
    const isBull = c.close >= c.open
    const volHeight = Math.max((c.volume / maxVol) * 45, 4)

    return {
      x,
      wickHigh,
      wickLow,
      bodyTop,
      bodyHeight,
      halfWidth: candleW / 2,
      width: candleW,
      isBull,
      volHeight,
    }
  })
})

const formatBookVolume = (vol: number): string => {
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`
  return vol.toLocaleString("en-US")
}
</script>

<template>
  <div class="flex-1 flex overflow-hidden">
    <!-- Cột bên trái: Danh sách mã chứng khoán để chuyển nhanh -->
    <div class="w-64 border-r border-white/[0.08] bg-aave-inkwell flex flex-col shrink-0">
      <div class="p-2 border-b border-white/[0.08] text-xs font-medium text-aave-graphite flex items-center justify-between">
        <span>Danh sách mã</span>
        <span class="font-mono text-xs">{{ stockList.length }} mã</span>
      </div>
      <div class="flex-1 overflow-y-auto divide-y divide-white/[0.04] scrollbar-thin">
        <div
          v-for="stk in stockList"
          :key="stk.symbol"
          class="p-2.5 flex items-center justify-between cursor-pointer transition-colors"
          :class="stock.symbol === stk.symbol ? 'bg-white/[0.08] border-l-2 border-rose-500' : 'hover:bg-white/[0.04]'"
          @click="emit('select-stock', stk)"
        >
          <div class="flex flex-col">
            <span
              class="font-bold text-xs font-mono"
              :class="stk.change > 0 ? 'text-emerald-400' : stk.change < 0 ? 'text-rose-500' : 'text-amber-400'"
            >
              {{ stk.symbol }}
            </span>
            <span class="text-xs text-aave-graphite font-mono">{{ stk.volume.toLocaleString('en-US') }} CP</span>
          </div>
          <div class="flex flex-col items-end font-mono">
            <span
              class="text-xs font-bold"
              :class="stk.change > 0 ? 'text-emerald-400' : stk.change < 0 ? 'text-rose-500' : 'text-amber-400'"
            >
              {{ stk.lastPrice.toFixed(2) }}
            </span>
            <span
              class="text-xs"
              :class="stk.change > 0 ? 'text-emerald-400' : stk.change < 0 ? 'text-rose-500' : 'text-amber-400'"
            >
              {{ stk.changePercent > 0 ? '+' : '' }}{{ stk.changePercent.toFixed(2) }}%
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Khối trung tâm: Thông tin chi tiết, đồ thị và sổ lệnh -->
    <div class="flex-1 flex flex-col overflow-y-auto">
      <!-- Header chi tiết mã -->
      <div class="p-3 bg-aave-obsidian border-b border-white/[0.08] flex items-center justify-between shrink-0">
        <div class="flex items-center gap-3">
          <button
            type="button"
            class="w-7 h-7 rounded hover:bg-white/[0.08] flex items-center justify-center text-aave-graphite hover:text-white transition-colors"
            @click="emit('close')"
          >
            <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
          </button>

          <div class="flex flex-col">
            <div class="flex items-center gap-2">
              <span class="text-base font-bold font-mono text-white">{{ stock.symbol }}</span>
              <span class="text-xs text-aave-ash">{{ stock.exchange }} - {{ stock.name }}</span>
              <span v-if="stock.sector" class="text-xs px-2 py-0.5 rounded bg-white/[0.06] text-aave-ash">
                {{ stock.sector }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-5">
          <div class="flex items-center gap-2 font-mono">
            <span
              class="text-xl font-bold tabular-nums"
              :class="stock.change > 0 ? 'text-emerald-400' : stock.change < 0 ? 'text-rose-500' : 'text-amber-400'"
            >
              {{ stock.lastPrice.toFixed(2) }}
            </span>
            <div
              class="flex items-center gap-1 text-xs font-medium"
              :class="stock.change > 0 ? 'text-emerald-400' : stock.change < 0 ? 'text-rose-500' : 'text-amber-400'"
            >
              <span>{{ stock.change > 0 ? '+' : '' }}{{ stock.change.toFixed(2) }}</span>
              <span>({{ stock.changePercent > 0 ? '+' : '' }}{{ stock.changePercent.toFixed(2) }}%)</span>
            </div>
          </div>

          <div class="hidden md:flex flex-col text-right font-mono text-xs text-aave-graphite">
            <span>KL: {{ stock.volume.toLocaleString('en-US') }} CP</span>
            <span>GT: {{ stock.valueBillion }} Tỷ</span>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="button"
              class="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors"
              @click="emit('quick-order', stock.symbol, stock.lastPrice, 'BUY')"
            >
              Mua
            </button>
            <button
              type="button"
              class="px-3 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors"
              @click="emit('quick-order', stock.symbol, stock.lastPrice, 'SELL')"
            >
              Bán
            </button>
          </div>
        </div>
      </div>

      <!-- Biểu đồ kỹ thuật nến Candlestick -->
      <div class="p-3 bg-surface-abyss border-b border-white/[0.08] flex flex-col h-72 shrink-0">
        <div class="flex items-center justify-between pb-2 border-b border-white/[0.04]">
          <div class="flex items-center gap-1 text-xs font-mono">
            <button
              v-for="tf in timeframes"
              :key="tf"
              type="button"
              class="px-2 py-0.5 rounded transition-colors"
              :class="selectedTimeframe === tf ? 'bg-white/[0.1] text-white font-bold' : 'text-aave-graphite hover:text-white'"
              @click="emit('update:selectedTimeframe', tf)"
            >
              {{ tf }}
            </button>
          </div>
          <div class="text-xs font-mono text-aave-graphite">
            Khung thời gian phân tích kỹ thuật
          </div>
        </div>

        <div class="flex-1 w-full relative pt-2 flex items-center justify-center">
          <div v-if="isCandlesLoading" class="absolute inset-0 flex items-center justify-center text-xs text-aave-graphite font-mono">
            Đang tải nến kỹ thuật...
          </div>
          <div v-else-if="chartCandles.length === 0" class="absolute inset-0 flex items-center justify-center text-xs text-aave-graphite font-mono">
            Không có dữ liệu nến lịch sử
          </div>
          <svg v-else class="w-full h-full" viewBox="0 0 800 200" preserveAspectRatio="none">
            <line x1="0" y1="50" x2="800" y2="50" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4" />
            <line x1="0" y1="100" x2="800" y2="100" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4" />
            <line x1="0" y1="150" x2="800" y2="150" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4" />

            <g v-for="(c, idx) in chartCandles" :key="idx">
              <line
                :x1="c.x"
                :y1="c.wickHigh"
                :x2="c.x"
                :y2="c.wickLow"
                :stroke="c.isBull ? '#34d399' : '#f43f5e'"
                stroke-width="1.5"
              />

              <rect
                :x="c.x - c.halfWidth"
                :y="c.bodyTop"
                :width="c.width"
                :height="c.bodyHeight"
                :fill="c.isBull ? '#34d399' : '#f43f5e'"
                rx="1"
              />

              <rect
                :x="c.x - c.halfWidth"
                :y="200 - c.volHeight"
                :width="c.width"
                :height="c.volHeight"
                :fill="c.isBull ? 'rgba(52, 211, 153, 0.4)' : 'rgba(244, 63, 94, 0.4)'"
              />
            </g>
          </svg>
        </div>
      </div>

      <!-- Khối các Tabs chi tiết (Bước giá, Thông tin, Sự kiện) -->
      <div class="flex-1 bg-aave-inkwell flex flex-col p-3">
        <div class="flex items-center justify-between border-b border-white/[0.08] pb-2 mb-3">
          <div class="flex items-center gap-3 text-xs font-medium">
            <button
              type="button"
              class="pb-1 transition-colors"
              :class="selectedDetailTab === 'depth' ? 'text-white border-b-2 border-rose-500 font-bold' : 'text-aave-graphite hover:text-white'"
              @click="selectedDetailTab = 'depth'"
            >
              Bước giá
            </button>
            <button
              type="button"
              class="pb-1 transition-colors"
              :class="selectedDetailTab === 'overview' ? 'text-white border-b-2 border-rose-500 font-bold' : 'text-aave-graphite hover:text-white'"
              @click="selectedDetailTab = 'overview'"
            >
              Thông tin
            </button>
            <button
              type="button"
              class="pb-1 transition-colors"
              :class="selectedDetailTab === 'events' ? 'text-white border-b-2 border-rose-500 font-bold' : 'text-aave-graphite hover:text-white'"
              @click="selectedDetailTab = 'events'"
            >
              Sự kiện
            </button>
          </div>

          <div v-if="selectedDetailTab === 'depth'" class="flex items-center gap-2 text-xs font-mono">
            <button
              type="button"
              class="px-2 py-0.5 rounded transition-colors"
              :class="selectedDepthSubTab === 'depth' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
              @click="selectedDepthSubTab = 'depth'"
            >
              Bước giá
            </button>
            <button
              type="button"
              class="px-2 py-0.5 rounded transition-colors"
              :class="selectedDepthSubTab === 'time' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
              @click="selectedDepthSubTab = 'time'"
            >
              Thời gian
            </button>
          </div>
        </div>

        <!-- Tab 1: Bước giá (Sổ lệnh 3 cấp + Thống kê phiên) -->
        <div v-if="selectedDetailTab === 'depth' && selectedDepthSubTab === 'depth'" class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <!-- Dư Mua 3 cấp -->
            <div class="bg-surface-abyss p-3 rounded border border-white/[0.04]">
              <div class="flex items-center justify-between text-xs font-medium text-emerald-400 mb-2 border-b border-white/[0.04] pb-1">
                <span>Dư Mua</span>
                <span class="font-mono text-xs text-aave-graphite">
                  Tổng: {{ stock.bidBook.length > 0 ? formatBookVolume(stock.bidBook.reduce((acc, b) => acc + b.volume, 0)) : '0' }}
                </span>
              </div>
              <div class="space-y-1.5 text-xs font-mono">
                <div
                  v-for="(bid, idx) in stock.bidBook"
                  :key="idx"
                  class="flex items-center justify-between py-1 px-2 rounded hover:bg-white/[0.04] transition-colors"
                >
                  <span class="text-aave-ash">{{ bid.volume.toLocaleString('en-US') }}</span>
                  <span class="font-bold text-emerald-400">{{ bid.price.toFixed(2) }}</span>
                </div>
              </div>
            </div>

            <!-- Dư Bán 3 cấp -->
            <div class="bg-surface-abyss p-3 rounded border border-white/[0.04]">
              <div class="flex items-center justify-between text-xs font-medium text-rose-500 mb-2 border-b border-white/[0.04] pb-1">
                <span>Dư Bán</span>
                <span class="font-mono text-xs text-aave-graphite">
                  Tổng: {{ stock.askBook.length > 0 ? formatBookVolume(stock.askBook.reduce((acc, a) => acc + a.volume, 0)) : '0' }}
                </span>
              </div>
              <div class="space-y-1.5 text-xs font-mono">
                <div
                  v-for="(ask, idx) in stock.askBook"
                  :key="idx"
                  class="flex items-center justify-between py-1 px-2 rounded hover:bg-white/[0.04] transition-colors"
                >
                  <span class="font-bold text-rose-500">{{ ask.price.toFixed(2) }}</span>
                  <span class="text-aave-ash">{{ ask.volume.toLocaleString('en-US') }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Các mức giá biên độ trong phiên -->
          <div class="grid grid-cols-6 gap-2 text-center text-xs font-mono">
            <div class="p-2 rounded bg-surface-abyss border border-cyan-800/40">
              <span class="text-cyan-400 block text-xs">Sàn</span>
              <span class="font-bold text-cyan-400">{{ stock.floorPrice.toFixed(2) }}</span>
            </div>
            <div class="p-2 rounded bg-surface-abyss border border-amber-800/40">
              <span class="text-amber-400 block text-xs">TC</span>
              <span class="font-bold text-amber-400">{{ stock.refPrice.toFixed(2) }}</span>
            </div>
            <div class="p-2 rounded bg-surface-abyss border border-purple-800/40">
              <span class="text-purple-400 block text-xs">Trần</span>
              <span class="font-bold text-purple-400">{{ stock.ceilingPrice.toFixed(2) }}</span>
            </div>
            <div class="p-2 rounded bg-surface-abyss border border-rose-800/40">
              <span class="text-rose-500 block text-xs">Thấp</span>
              <span class="font-bold text-rose-500">{{ stock.lowPrice.toFixed(2) }}</span>
            </div>
            <div class="p-2 rounded bg-surface-abyss border border-white/[0.04]">
              <span class="text-amber-400 block text-xs">TB</span>
              <span class="font-bold text-amber-400">{{ stock.avgPrice.toFixed(2) }}</span>
            </div>
            <div class="p-2 rounded bg-surface-abyss border border-emerald-800/40">
              <span class="text-emerald-400 block text-xs">Cao</span>
              <span class="font-bold text-emerald-400">{{ stock.highPrice.toFixed(2) }}</span>
            </div>
          </div>

          <!-- Thông số dòng tiền khối ngoại -->
          <div class="grid grid-cols-3 gap-3 p-3 rounded bg-surface-abyss border border-white/[0.04] text-xs font-mono">
            <div>
              <span class="text-aave-graphite block">Khối ngoại mua</span>
              <span class="font-bold text-emerald-400">{{ stock.foreignBuy.toLocaleString('en-US') }} CP</span>
            </div>
            <div>
              <span class="text-aave-graphite block">Khối ngoại bán</span>
              <span class="font-bold text-rose-500">{{ stock.foreignSell.toLocaleString('en-US') }} CP</span>
            </div>
            <div>
              <span class="text-aave-graphite block">Room ngoại khả dụng</span>
              <span class="font-bold text-white">{{ stock.foreignRoom.toLocaleString('en-US') }}</span>
            </div>
          </div>
        </div>

        <!-- Tab 2: Sổ khớp lệnh theo thời gian (Time & Sales) -->
        <div v-else-if="selectedDetailTab === 'depth' && selectedDepthSubTab === 'time'" class="flex-1 overflow-y-auto">
          <div v-if="matchedTicks.length === 0" class="p-6 text-center text-xs text-aave-graphite font-mono">
            Không có dữ liệu khớp lệnh trong phiên
          </div>
          <table v-else class="w-full text-xs font-mono">
            <thead class="text-aave-graphite border-b border-white/[0.04]">
              <tr>
                <th class="py-1 px-2 text-left font-normal">Thời gian</th>
                <th class="py-1 px-2 text-center font-normal">M/B</th>
                <th class="py-1 px-2 text-right font-normal">Giá</th>
                <th class="py-1 px-2 text-right font-normal">Khối lượng</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.02]">
              <tr v-for="(tick, idx) in matchedTicks" :key="idx" class="hover:bg-white/[0.04]">
                <td class="py-1.5 px-2 text-aave-ash">{{ tick.time }}</td>
                <td
                  class="py-1.5 px-2 text-center font-bold"
                  :class="tick.side === 'B' ? 'text-emerald-400' : 'text-rose-500'"
                >
                  {{ tick.side }}
                </td>
                <td
                  class="py-1.5 px-2 text-right font-bold"
                  :class="tick.side === 'B' ? 'text-emerald-400' : 'text-rose-500'"
                >
                  {{ tick.price.toFixed(2) }}
                </td>
                <td class="py-1.5 px-2 text-right text-white">{{ tick.volume.toLocaleString('en-US') }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Tab 3: Thông tin tài chính doanh nghiệp -->
        <div v-else-if="selectedDetailTab === 'overview'" class="p-3 text-xs space-y-3">
          <div v-if="!stockOverview" class="p-6 text-center text-xs text-aave-graphite font-mono">
            Chưa có dữ liệu chỉ số tài chính của doanh nghiệp
          </div>
          <div v-else class="grid grid-cols-2 gap-3 font-mono">
            <div class="p-2.5 rounded bg-surface-abyss border border-white/[0.04]">
              <span class="text-aave-graphite block text-xs">Vốn hóa thị trường</span>
              <span class="text-white font-bold text-sm">{{ stockOverview.market_cap_billion.toLocaleString('en-US') }} Tỷ VND</span>
            </div>
            <div class="p-2.5 rounded bg-surface-abyss border border-white/[0.04]">
              <span class="text-aave-graphite block text-xs">P/E Hiện tại</span>
              <span class="text-white font-bold text-sm">{{ stockOverview.pe.toFixed(2) }}</span>
            </div>
            <div class="p-2.5 rounded bg-surface-abyss border border-white/[0.04]">
              <span class="text-aave-graphite block text-xs">P/B Hiện tại</span>
              <span class="text-white font-bold text-sm">{{ stockOverview.pb.toFixed(2) }}</span>
            </div>
            <div class="p-2.5 rounded bg-surface-abyss border border-white/[0.04]">
              <span class="text-aave-graphite block text-xs">ROE 4 quý gần nhất</span>
              <span class="text-white font-bold text-sm">{{ stockOverview.roe.toFixed(2) }}%</span>
            </div>
          </div>
        </div>

        <!-- Tab 4: Sự kiện doanh nghiệp -->
        <div v-else-if="selectedDetailTab === 'events'" class="p-3 text-xs text-aave-ash space-y-2">
          <div v-if="corporateEvents.length === 0" class="p-6 text-center text-xs text-aave-graphite font-mono">
            Không có sự kiện doanh nghiệp được ghi nhận
          </div>
          <div
            v-for="(ev, idx) in corporateEvents"
            v-else
            :key="idx"
            class="p-2 rounded bg-surface-abyss border border-white/[0.04]"
          >
            <span class="text-xs text-aave-graphite font-mono">{{ ev.date }}</span>
            <p class="font-medium text-white mt-0.5">{{ ev.title }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
