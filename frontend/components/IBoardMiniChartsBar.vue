<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import type { IBoardIndexItem } from "~/client/types.gen"
import { MarketIndexSymbol } from "~/types/market"
import IBoardIndexSummaryTable from "./IBoardIndexSummaryTable.vue"
import IBoardMarketBreadthModal from "./IBoardMarketBreadthModal.vue"
import IBoardMiniChart from "./IBoardMiniChart.vue"
import TradingViewChart from "./TradingViewChart.vue"

interface Props {
  isDerivatives?: boolean
}

withDefaults(defineProps<Props>(), {
  isDerivatives: false,
})

const defaultSymbols: MarketIndexSymbol[] = [
  MarketIndexSymbol.VNINDEX,
  MarketIndexSymbol.VN30,
  MarketIndexSymbol.HNX30,
  MarketIndexSymbol.HNXINDEX,
]

const availableIndices = [
  { symbol: MarketIndexSymbol.VNINDEX, name: "VN-Index" },
  { symbol: MarketIndexSymbol.VN30, name: "VN30" },
  { symbol: MarketIndexSymbol.HNX30, name: "HNX30" },
  { symbol: MarketIndexSymbol.HNXINDEX, name: "HNX-Index" },
  { symbol: MarketIndexSymbol.VN30F1M, name: "Phái sinh VN30" },
  { symbol: MarketIndexSymbol.UPCOMINDEX, name: "UPCoM" },
]

const activeSymbols = ref<string[]>([...defaultSymbols])
const allIndices = ref<IBoardIndexItem[]>([])
const isLoading = ref(false)

const closeSymbol = (symbol: string) => {
  activeSymbols.value = activeSymbols.value.filter((s) => s !== symbol)
}

const handleChangeSymbol = (oldSym: string, newSym: string) => {
  const idx = activeSymbols.value.indexOf(oldSym)
  if (idx !== -1) {
    activeSymbols.value[idx] = newSym
  }
}

const expandedSymbol = ref<string | null>(null)
const openExpandModal = (symbol: string) => {
  expandedSymbol.value = symbol
}
const closeExpandModal = () => {
  expandedSymbol.value = null
}

const breadthModalOpen = ref(false)
const selectedBreadthIndex = ref("VNINDEX")
const handleOpenBreadth = (symbol: string) => {
  selectedBreadthIndex.value = symbol
  breadthModalOpen.value = true
}

const desiredOrder = ["vnindex", "vn30", "hnx30", "vn30f1m", "hnx", "upcom"]

const tableIndices = computed(() => {
  const filtered = allIndices.value.filter((i) => i.id !== "dji")
  return [...filtered].sort((a, b) => {
    const ia = desiredOrder.indexOf(a.id.toLowerCase())
    const ib = desiredOrder.indexOf(b.id.toLowerCase())
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
  })
})

const fetchIndices = async () => {
  try {
    const data = await $fetch<IBoardIndexItem[]>("/api/v1/stock/iboard/indices")
    if (Array.isArray(data) && data.length > 0) {
      allIndices.value = data
    }
  } catch (err) {
    console.warn("Lỗi nạp danh sách chỉ số thị trường:", err)
  }
}

let intervalTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  isLoading.value = true
  await fetchIndices()
  isLoading.value = false
  intervalTimer = setInterval(fetchIndices, 10000)
})

onBeforeUnmount(() => {
  if (intervalTimer) {
    clearInterval(intervalTimer)
    intervalTimer = null
  }
})
</script>

<template>
  <div class="w-full relative flex flex-col gap-1.5 select-none">

    <div class="w-full flex flex-col xl:flex-row gap-1.5 items-stretch">

      <div
        v-if="activeSymbols.length > 0"
        class="flex-1 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-1.5 min-w-0"
      >
        <div v-for="symbol in activeSymbols" :key="symbol" class="w-full min-w-0">
          <IBoardMiniChart
            :symbol="symbol"
            :available-symbols="availableIndices"
            @close="closeSymbol"
            @expand="openExpandModal"
            @open-breadth="handleOpenBreadth"
            @change-symbol="handleChangeSymbol"
          />
        </div>
      </div>

      <div
        v-else
        class="flex-1 py-8 px-4 rounded border border-dashed border-white/[0.12] bg-[#10121a] flex flex-col items-center justify-center gap-2 text-center"
      >
        <span class="text-zinc-400 text-xs font-mono">
          Chưa có khung biểu đồ nào được kích hoạt.
        </span>
        <button
          type="button"
          class="px-3 py-1 rounded bg-rose-600/20 text-rose-400 border border-rose-500/30 hover:bg-rose-600/30 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
          @click="activeSymbols = [...defaultSymbols]"
        >
          <UIcon name="i-heroicons-arrow-path" class="w-3.5 h-3.5" />
          <span>Khôi phục 4 biểu đồ mặc định</span>
        </button>
      </div>

      <div class="w-full xl:w-[420px] shrink-0">
        <IBoardIndexSummaryTable
          :indices="tableIndices"
          @open-breadth="handleOpenBreadth"
        />
      </div>
    </div>

    <IBoardMarketBreadthModal
      v-model="breadthModalOpen"
      :initial-index="selectedBreadthIndex"
    />

    <UModal
      :model-value="expandedSymbol !== null"
      :ui="{ width: 'sm:max-w-5xl' }"
      @update:model-value="
        (val) => {
          if (!val) closeExpandModal();
        }
      "
    >
      <div
        v-if="expandedSymbol"
        class="bg-[#121316] rounded-xl overflow-hidden border border-white/[0.1] p-4 flex flex-col gap-3"
      >
        <div
          class="flex items-center justify-between border-b border-white/[0.08] pb-2"
        >
          <div class="flex items-center gap-2">
            <h3 class="text-base font-bold text-white font-mono">
              Biểu đồ kỹ thuật {{ expandedSymbol }}
            </h3>
            <span
              class="px-2 py-0.5 rounded text-[10px] bg-rose-600/20 text-rose-400 border border-rose-500/30 font-medium"
            >
              Phân tích kỹ thuật chuyên sâu
            </span>
          </div>

          <button
            type="button"
            class="text-zinc-400 hover:text-white p-1 rounded hover:bg-white/[0.08] cursor-pointer"
            @click="closeExpandModal"
          >
            <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
          </button>
        </div>

        <div class="w-full h-[540px]">
          <TradingViewChart :symbol="expandedSymbol" interval="1" />
        </div>
      </div>
    </UModal>
  </div>
</template>
