<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { useIndexWsChannel } from "~/composables/useIndexWsChannel"
import { MarketIndexSymbol } from "~/types/market"
import IBoardIntradayCanvas from "./IBoardIntradayCanvas.vue"

interface Props {
  symbol: string
  availableSymbols?: Array<{ symbol: string; name: string }>
}

const props = withDefaults(defineProps<Props>(), {
  availableSymbols: () => [],
})

const emit = defineEmits<{
  (e: "close", symbol: string): void
  (e: "expand", symbol: string): void
  (e: "change-symbol", oldSym: string, newSym: string): void
}>()

const isDropdownOpen = ref(false)

const { indexData, isWsConnected, isFlashing, start, stop } = useIndexWsChannel(
  props.symbol,
)

const formatPrice = (val: number | string | undefined | null): string => {
  if (val === undefined || val === null || val === "") return "-"
  const n = typeof val === "number" ? val : Number.parseFloat(String(val))
  if (Number.isNaN(n)) return String(val)
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  })
}

const formatSignedChange = (chg: number): string => {
  if (typeof chg !== "number" || Number.isNaN(chg) || Math.abs(chg) < 0.001) {
    return "0.00"
  }
  const sign = chg > 0 ? "+" : ""
  return `${sign}${chg.toFixed(2)}`
}

const formatChangePercent = (val: number): string => {
  if (typeof val !== "number" || Number.isNaN(val) || Math.abs(val) < 0.001) {
    return "0.00%"
  }
  const sign = val > 0 ? "+" : ""
  return `${sign}${val.toFixed(2)}%`
}

const formatVolumeText = computed(() => {
  const isDeriv = props.symbol === MarketIndexSymbol.VN30F1M
  if (indexData.value.raw_volume && indexData.value.raw_volume > 0) {
    const v = Math.round(indexData.value.raw_volume)
    return isDeriv
      ? `${v.toLocaleString("en-US")} HĐ`
      : `${v.toLocaleString("en-US")} CP`
  }
  return indexData.value.volume || "-"
})

const formatValueText = computed(() => {
  if (indexData.value.raw_value && indexData.value.raw_value > 0) {
    return `${indexData.value.raw_value.toLocaleString("en-US", {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    })} Tỷ`
  }
  return indexData.value.value || "-"
})

const getColorClass = (change: number): string => {
  if (change > 0.001) return "text-[#089981]"
  if (change < -0.001) return "text-[#f23645]"
  return "text-[#f59e0b]"
}

const derivPrices = computed(() => {
  if (indexData.value.symbol !== MarketIndexSymbol.VN30F1M) return null
  const ref =
    indexData.value.derivativesDepth?.refPrice ||
    (indexData.value.price > 0 && indexData.value.change !== 0
      ? Number((indexData.value.price - indexData.value.change).toFixed(1))
      : 0)
  if (!ref || ref <= 0) return null
  const ceil =
    indexData.value.derivativesDepth?.ceilingPrice ||
    Number((ref * 1.07).toFixed(1))
  const flr =
    indexData.value.derivativesDepth?.floorPrice ||
    Number((ref * 0.93).toFixed(1))
  return {
    refPrice: ref,
    ceilingPrice: ceil,
    floorPrice: flr,
  }
})

const switchSymbol = (newSym: string) => {
  isDropdownOpen.value = false
  if (newSym !== props.symbol) {
    emit("change-symbol", props.symbol, newSym)
  }
}

watch(
  () => props.symbol,
  () => {
    stop()
    start()
  },
)

onMounted(async () => {
  await start()
})

onBeforeUnmount(() => {
  stop()
})
</script>

<template>
  <div
    class="flex flex-col relative bg-[#10121a] hover:bg-[#131622] p-1.5 rounded border border-white/[0.08] transition-all select-none shadow-sm min-w-0"
    :class="{
      'ring-1 ring-[#089981]/50': isFlashing === 'up',
      'ring-1 ring-[#f23645]/50': isFlashing === 'down',
    }"
  >

    <div class="relative w-full">

      <IBoardIntradayCanvas
        :sparkline="indexData.sparkline || []"
        :ref-price="indexData.ref_price"
        :current-price="indexData.price"
        :is-positive="indexData.isPositive"
        :symbol="props.symbol"
      />

      <div
        class="absolute top-0.5 right-0.5 flex items-center gap-0.5 z-20 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <button
          type="button"
          class="p-0.5 rounded text-zinc-500 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          title="Mở biểu đồ kỹ thuật"
          @click="emit('expand', props.symbol)"
        >
          <UIcon
            name="i-heroicons-arrows-pointing-out"
            class="w-3 h-3"
          />
        </button>
        <button
          type="button"
          class="p-0.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-white/10 transition-colors cursor-pointer"
          title="Đóng chỉ số"
          @click="emit('close', props.symbol)"
        >
          <UIcon name="i-heroicons-x-mark" class="w-3 h-3" />
        </button>
      </div>
    </div>

    <div class="flex flex-col gap-0.5 pt-1.5 px-0.5 text-[10px] font-mono leading-tight">

      <div class="flex items-center justify-between leading-none">

        <div class="relative">
          <button
            type="button"
            class="flex items-center gap-0.5 font-bold font-mono text-[11px] text-white hover:text-rose-400 transition-colors cursor-pointer"
            @click="isDropdownOpen = !isDropdownOpen"
          >
            <span>{{ indexData.name || props.symbol }}</span>
            <UIcon
              name="i-heroicons-chevron-down"
              class="w-2.5 h-2.5 text-zinc-400"
            />
          </button>

          <div
            v-if="isDropdownOpen"
            class="absolute top-5 left-0 z-50 w-36 py-1 rounded bg-[#181a24] border border-white/[0.12] shadow-2xl flex flex-col gap-0.5"
          >
            <button
              v-for="item in availableSymbols"
              :key="item.symbol"
              type="button"
              class="w-full text-left px-2 py-1 text-[10px] hover:bg-white/10 text-white flex items-center justify-between transition-colors cursor-pointer"
              :class="item.symbol === props.symbol ? 'text-rose-400 font-bold' : ''"
              @click="switchSymbol(item.symbol)"
            >
              <span>{{ item.symbol }}</span>
              <span class="text-zinc-500 text-[9px]">{{ item.name }}</span>
            </button>
          </div>
        </div>

        <div
          class="flex items-center gap-0.5 font-bold tabular-nums"
          :class="getColorClass(indexData.change)"
        >
          <span>{{
            indexData.change > 0 ? "↑" : indexData.change < 0 ? "↓" : ""
          }}</span>
          <span class="text-[11px]">{{ formatPrice(indexData.price) }}</span>
          <span class="text-[9px] font-normal">
            ({{ formatSignedChange(indexData.change) }}
            {{ formatChangePercent(indexData.changePercent) }})
          </span>
        </div>
      </div>

      <div class="flex items-center justify-between text-zinc-300 text-[10px] tabular-nums pt-0.5">
        <span>{{ formatVolumeText }}</span>
        <span>{{ formatValueText }}</span>
      </div>

      <div class="flex items-center justify-between tabular-nums pt-0.5 text-[9px]">

        <div
          v-if="props.symbol === MarketIndexSymbol.VN30F1M && derivPrices"
          class="flex items-center gap-1.5 font-semibold"
        >
          <span class="text-[#f59e0b]">{{
            formatPrice(derivPrices.refPrice)
          }}</span>
          <span class="text-[#c084fc]">{{
            formatPrice(derivPrices.ceilingPrice)
          }}</span>
          <span class="text-[#22d3ee]">{{
            formatPrice(derivPrices.floorPrice)
          }}</span>
        </div>

        <div
          v-else-if="indexData.breadth"
          class="flex items-center gap-1.5 leading-none"
        >

          <span class="text-[#089981] flex items-center gap-0.5">
            <span>↑</span>
            <span>{{ indexData.breadth.advance }}</span>
            <span class="text-[#c084fc]"
              >({{ indexData.breadth.ceiling }})</span
            >
          </span>

          <span class="text-[#f59e0b] flex items-center gap-0.5">
            <span>—</span>
            <span>{{ indexData.breadth.unchanged }}</span>
          </span>

          <span class="text-[#f23645] flex items-center gap-0.5">
            <span>↓</span>
            <span>{{ indexData.breadth.decline }}</span>
            <span class="text-[#22d3ee]"
              >({{ indexData.breadth.floor }})</span
            >
          </span>
        </div>

        <span class="text-zinc-500 font-sans text-[9px]">{{
          indexData.status || "Đóng cửa"
        }}</span>
      </div>
    </div>
  </div>
</template>
