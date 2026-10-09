<script setup lang="ts">
import { computed, onMounted, onUnmounted } from "vue"
import {
  type MarketTickerItem,
  useMarketTicker,
} from "~/composables/useMarketTicker"

interface Props {
  speedSeconds?: number
  fluid?: boolean
  theme?: "light" | "dark" | "auto"
}

const props = withDefaults(defineProps<Props>(), {
  speedSeconds: 100,
  fluid: false,
  theme: "auto",
})

const emit = defineEmits<(e: "select", symbol: string) => void>()

const {
  items,
  isLoading,
  flashMap,
  startTickerService,
  stopTickerService,
  selectSymbol,
} = useMarketTicker()

onMounted(async () => {
  await startTickerService()
})

onUnmounted(() => {
  stopTickerService()
})

const onItemClick = (symbol: string) => {
  selectSymbol(symbol)
  emit("select", symbol)
}

// Định dạng giá kiểu Việt Nam: 1.412,68 hoặc 72,15
const formatPrice = (val: number): string => {
  if (typeof val !== "number" || Number.isNaN(val)) return "-"
  const parts = val.toFixed(2).split(".")
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".")
  return parts.join(",")
}

// Định dạng tỷ lệ phần trăm chuẩn tài chính: +0,62%, −0,49%, 0,00%
const formatChangePercent = (item: MarketTickerItem): string => {
  const val = item.changePercent
  if (typeof val !== "number" || Number.isNaN(val) || Math.abs(val) < 0.001) {
    return "0,00%"
  }
  const sign = val > 0 ? "+" : "−"
  const parts = Math.abs(val).toFixed(2).split(".")
  const formattedAbs = `${parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${parts[1]}`
  return `${sign}${formattedAbs}%`
}

const getColorClass = (item: MarketTickerItem): string => {
  if (item.changePercent > 0.001) {
    return "text-tv-bull"
  }
  if (item.changePercent < -0.001) {
    return "text-tv-bear"
  }
  return "text-tv-gold"
}

// Thời lượng chạy marquee mượt mà và chậm rãi
const animationDuration = computed(() => {
  const count = items.value.length
  if (count <= 5) return "50s"
  if (count <= 15) return "65s"
  return `${props.speedSeconds}s`
})

const themeClass = computed(() => {
  return props.theme !== "auto" ? `theme-${props.theme}` : ""
})
</script>

<template>
  <div
    class="w-full relative overflow-hidden backdrop-blur-xl border-b select-none z-20 transition-colors duration-200 bg-ticker-bg/95 border-ticker-border text-ticker-symbol"
    :class="themeClass"
    :data-theme="props.theme !== 'auto' ? props.theme : undefined"
  >
    <div
      class="mx-auto flex h-10 items-center px-4 sm:px-6"
      :class="props.fluid ? 'w-full' : 'max-w-[1200px]'"
    >
      <!-- Running Real-time Ticker Track -->
      <div class="flex-1 overflow-hidden relative h-full flex items-center cursor-default">
        <div
          v-if="items.length > 0"
          class="ticker-track flex w-max items-center whitespace-nowrap will-change-transform"
          :style="{ animationDuration }"
        >
          <!-- Track 1 -->
          <div class="flex items-center gap-8 pr-8 shrink-0">
            <span
              v-for="item in items"
              :key="`track1-${item.symbol}`"
              class="inline-flex items-center gap-2 font-mono text-xs sm:text-sm tabular-nums cursor-pointer transition-colors duration-150 rounded px-1.5 py-0.5 hover:bg-ticker-hover"
              @click="onItemClick(item.symbol)"
            >
              <strong class="tracking-tight transition-colors duration-150 text-ticker-symbol font-semibold">
                {{ item.symbol }}
              </strong>
              <span
                class="tabular-nums transition-colors duration-200"
                :class="[
                  flashMap[item.symbol] === 'up'
                    ? 'text-tv-bull font-bold'
                    : flashMap[item.symbol] === 'down'
                      ? 'text-tv-bear font-bold'
                      : 'text-ticker-price font-medium',
                ]"
              >
                {{ formatPrice(item.price) }}
              </span>
              <span
                class="tabular-nums font-medium"
                :class="getColorClass(item)"
              >
                {{ formatChangePercent(item) }}
              </span>
            </span>
          </div>

          <!-- Track 2 (Duplicate for Seamless Infinite Loop) -->
          <div class="flex items-center gap-8 pr-8 shrink-0" aria-hidden="true">
            <span
              v-for="item in items"
              :key="`track2-${item.symbol}`"
              class="inline-flex items-center gap-2 font-mono text-xs sm:text-sm tabular-nums cursor-pointer transition-colors duration-150 rounded px-1.5 py-0.5 hover:bg-ticker-hover"
              @click="onItemClick(item.symbol)"
            >
              <strong class="tracking-tight transition-colors duration-150 text-ticker-symbol font-semibold">
                {{ item.symbol }}
              </strong>
              <span
                class="tabular-nums transition-colors duration-200"
                :class="[
                  flashMap[item.symbol] === 'up'
                    ? 'text-tv-bull font-bold'
                    : flashMap[item.symbol] === 'down'
                      ? 'text-tv-bear font-bold'
                      : 'text-ticker-price font-medium',
                ]"
              >
                {{ formatPrice(item.price) }}
              </span>
              <span
                class="tabular-nums font-medium"
                :class="getColorClass(item)"
              >
                {{ formatChangePercent(item) }}
              </span>
            </span>
          </div>
        </div>

        <!-- Loading State -->
        <div
          v-else-if="isLoading"
          class="text-xs font-mono flex items-center gap-2 text-ticker-muted"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-aave-violet animate-pulse" />
          <span>Đang nạp luồng bảng giá trực tiếp...</span>
        </div>

        <!-- Empty State -->
        <div
          v-else
          class="text-xs font-mono text-ticker-muted"
        >
          <span>Chưa có dữ liệu thị trường</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes ticker-marquee {
  0% {
    transform: translate3d(0, 0, 0);
  }
  100% {
    transform: translate3d(-50%, 0, 0);
  }
}

.ticker-track {
  display: flex;
  width: max-content;
  animation-name: ticker-marquee;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}

.ticker-track:hover {
  animation-play-state: paused;
}
</style>
