<script setup lang="ts">
import IBoardSparkline from "./IBoardSparkline.vue"
import type { StockRowDisplay } from "./types"

const props = defineProps<{
  data: StockRowDisplay[]
  mainCategory: string
  priceUnitDisplay: "percent" | "diff"
  isLoading?: boolean
}>()

const emit = defineEmits<{
  (e: "select-stock", stock: StockRowDisplay): void
  (e: "quick-order", symbol: string, price: number, side: "BUY" | "SELL"): void
}>()

const getPriceColorClass = (
  price: number | undefined | null,
  stk: StockRowDisplay,
  fallback = "text-aave-paper",
) => {
  if (price === undefined || price === null || price === 0) return fallback
  if (price >= stk.ceilingPrice) return "text-purple-400 font-semibold"
  if (price <= stk.floorPrice) return "text-cyan-400 font-semibold"
  if (price > stk.refPrice) return "text-emerald-400 font-semibold"
  if (price < stk.refPrice) return "text-rose-500 font-semibold"
  return "text-amber-400 font-semibold"
}
</script>

<template>
  <div class="flex-1 overflow-auto">
    <div v-if="isLoading && data.length === 0" class="p-8 text-center text-xs text-aave-graphite font-mono">
      <div class="inline-flex items-center gap-2">
        <span class="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
        <span>Đang nạp dữ liệu bảng giá...</span>
      </div>
    </div>

    <div v-else-if="data.length === 0" class="p-8 text-center text-xs text-aave-graphite font-mono">
      Không tìm thấy mã chứng khoán phù hợp
    </div>

    <table v-else class="w-full text-left border-collapse text-xs">
      <thead class="sticky top-0 bg-aave-inkwell border-b border-white/[0.08] text-aave-graphite font-medium z-10">
        <tr>
          <th class="py-2.5 px-4 font-normal">Mã chứng khoán</th>
          <th class="py-2.5 px-4 text-right font-normal">Giá khớp</th>
          <th class="py-2.5 px-4 text-right font-normal">
            {{ priceUnitDisplay === 'percent' ? '% Thay đổi' : '+/- Giá trị' }}
          </th>
          <th v-if="mainCategory === 'derivatives'" class="py-2.5 px-4 text-center font-normal">Ngày đáo hạn</th>
          <th class="py-2.5 px-4 text-right font-normal">Tổng khối lượng</th>
          <th class="py-2.5 px-4 text-center font-normal">Biểu đồ</th>
          <th class="py-2.5 px-4 text-center font-normal min-w-[140px]">Mua / Bán chủ động</th>
          <th class="py-2.5 px-3 text-center font-normal w-12" />
        </tr>
      </thead>
      <tbody class="divide-y divide-white/[0.04]">
        <tr
          v-for="stk in data"
          :key="stk.symbol"
          class="hover:bg-white/[0.04] transition-colors cursor-pointer group"
          @click="emit('select-stock', stk)"
        >
          <td class="py-2.5 px-4">
            <div class="flex items-center gap-2.5">
              <div class="flex flex-col">
                <div class="flex items-center gap-1.5">
                  <span
                    class="font-bold text-sm font-mono tracking-tight"
                    :class="getPriceColorClass(stk.lastPrice, stk)"
                  >
                    {{ stk.symbol }}
                  </span>
                </div>
                <span class="text-xs text-aave-graphite truncate max-w-[200px]">{{ stk.name }}</span>
              </div>
            </div>
          </td>

          <td
            class="py-2.5 px-4 text-right font-mono font-bold tabular-nums text-sm"
            :class="getPriceColorClass(stk.lastPrice, stk)"
          >
            {{ stk.lastPrice.toFixed(mainCategory === 'derivatives' ? 1 : 2) }}
          </td>

          <td
            class="py-2.5 px-4 text-right font-mono font-medium tabular-nums"
            :class="getPriceColorClass(stk.lastPrice, stk)"
          >
            <span v-if="priceUnitDisplay === 'percent'">
              {{ stk.changePercent > 0 ? '+' : '' }}{{ stk.changePercent.toFixed(2) }}%
            </span>
            <span v-else>
              {{ stk.change > 0 ? '+' : '' }}{{ stk.change.toFixed(2) }}
            </span>
          </td>

          <td v-if="mainCategory === 'derivatives'" class="py-2.5 px-4 text-center font-mono text-aave-ash">
            {{ stk.expiryDate || 'Chưa định dạng' }}
          </td>

          <td class="py-2.5 px-4 text-right font-mono text-aave-ash tabular-nums">
            {{ stk.volume.toLocaleString('en-US') }}
          </td>

          <td class="py-2.5 px-4 text-center">
            <IBoardSparkline :stk="stk" />
          </td>

          <td class="py-2.5 px-4 text-center">
            <div class="flex flex-col gap-1 w-32 mx-auto">
              <div class="flex items-center justify-between text-xs font-mono text-aave-graphite">
                <span class="text-emerald-400">{{ stk.buyRatio }}%</span>
                <span class="text-rose-500">{{ stk.sellRatio }}%</span>
              </div>
              <div class="w-full h-1.5 rounded-full overflow-hidden flex bg-white/[0.06]">
                <div class="bg-emerald-500" :style="{ width: `${stk.buyRatio}%` }" />
                <div class="bg-rose-500" :style="{ width: `${stk.sellRatio}%` }" />
              </div>
            </div>
          </td>

          <td class="py-2.5 px-3 text-center">
            <button
              type="button"
              class="w-6 h-6 rounded-full bg-white/[0.06] hover:bg-rose-600 text-aave-ash hover:text-white flex items-center justify-center transition-colors"
              title="Đặt lệnh nhanh"
              @click.stop="emit('quick-order', stk.symbol, stk.lastPrice, 'BUY')"
            >
              <UIcon name="i-heroicons-plus" class="w-3.5 h-3.5" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
