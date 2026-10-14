<script setup lang="ts">
import { computed, ref } from "vue"
import { MarketIndexSymbol } from "~/types/market"

interface Props {
  isDerivatives?: boolean
}

withDefaults(defineProps<Props>(), {
  isDerivatives: false,
})

const defaultSymbols: MarketIndexSymbol[] = [
  MarketIndexSymbol.VN30,
  MarketIndexSymbol.VNINDEX,
  MarketIndexSymbol.HNX30,
  MarketIndexSymbol.VN30F1M,
]

const availableIndices = [
  { symbol: MarketIndexSymbol.VN30, name: "Chỉ số VN30" },
  { symbol: MarketIndexSymbol.VNINDEX, name: "Chỉ số VN-Index" },
  { symbol: MarketIndexSymbol.HNX30, name: "Chỉ số HNX30" },
  { symbol: MarketIndexSymbol.VN30F1M, name: "Phái sinh VN30F1M" },
  { symbol: MarketIndexSymbol.HNX, name: "Chỉ số HNX-Index" },
  { symbol: MarketIndexSymbol.UPCOM, name: "Chỉ số UPCoM-Index" },
]

const activeSymbols = ref<string[]>([...defaultSymbols])

const closeSymbol = (symbol: string) => {
  activeSymbols.value = activeSymbols.value.filter((s) => s !== symbol)
}

const addSymbol = (symbol: string) => {
  if (!activeSymbols.value.includes(symbol)) {
    activeSymbols.value.push(symbol)
  }
}

const expandedSymbol = ref<string | null>(null)
const openExpandModal = (symbol: string) => {
  expandedSymbol.value = symbol
}
const closeExpandModal = () => {
  expandedSymbol.value = null
}

const unselectedIndices = computed(() => {
  return availableIndices.filter(
    (idx) => !activeSymbols.value.includes(idx.symbol),
  )
})

const isDropdownOpen = ref(false)
const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value
}
const closeDropdown = () => {
  isDropdownOpen.value = false
}

const selectAndClose = (symbol: string) => {
  addSymbol(symbol)
  closeDropdown()
}

const resetAndClose = () => {
  activeSymbols.value = [...defaultSymbols]
  closeDropdown()
}
</script>

<template>
  <div class="w-full relative flex flex-col gap-2">

    <div class="flex items-center justify-between px-1">

      <div class="relative">

        <div
          v-if="isDropdownOpen"
          class="absolute top-8 right-0 z-50 w-56 rounded-lg border border-white/[0.12] bg-surface-midnight shadow-2xl p-1.5 flex flex-col gap-1 text-xs"
        >
          <div
            class="px-2.5 py-1.5 text-[10px] font-semibold text-zinc-400 uppercase tracking-wider border-b border-white/[0.06] flex items-center justify-between"
          >
            <span>Chọn chỉ số hiển thị</span>
            <button
              type="button"
              class="text-zinc-500 hover:text-white"
              @click="closeDropdown"
            >
              <UIcon name="i-heroicons-x-mark" class="w-3.5 h-3.5" />
            </button>
          </div>

          <div
            v-if="unselectedIndices.length === 0"
            class="px-3 py-2 text-zinc-500 text-[11px] text-center"
          >
            Tất cả chỉ số đã được mở
          </div>

          <button
            v-for="item in unselectedIndices"
            :key="item.symbol"
            type="button"
            class="w-full text-left px-2.5 py-1.5 rounded hover:bg-white/[0.08] text-white flex items-center justify-between transition-colors cursor-pointer"
            @click="selectAndClose(item.symbol)"
          >
            <span class="font-medium font-mono">{{ item.symbol }}</span>
            <span class="text-zinc-400 text-[10px]">{{ item.name }}</span>
          </button>

          <button
            type="button"
            class="w-full text-left px-2.5 py-1.5 mt-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-rose-400 text-[11px] font-medium flex items-center gap-1.5 transition-colors border-t border-white/[0.06] cursor-pointer"
            @click="resetAndClose"
          >
            <UIcon name="i-heroicons-arrow-path" class="w-3.5 h-3.5" />
            <span>Khôi phục 4 chỉ số mặc định</span>
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="activeSymbols.length > 0"
      class="w-full grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2.5"
    >
      <div v-for="symbol in activeSymbols" :key="symbol" class="w-full min-w-0">
        <IBoardMiniChart
          :symbol="symbol"
          @close="closeSymbol"
          @expand="openExpandModal"
        />
      </div>
    </div>

    <div
      v-else
      class="w-full py-8 px-4 rounded-lg border border-dashed border-white/[0.12] bg-surface-midnight/60 flex flex-col items-center justify-center gap-2 text-center"
    >
      <span class="text-zinc-400 text-xs">
        Chưa có khung biểu đồ nào được kích hoạt.
      </span>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg bg-rose-600/20 text-rose-400 border border-rose-500/30 hover:bg-rose-600/30 text-xs font-medium flex items-center gap-1.5 transition-colors"
        @click="activeSymbols = [...defaultSymbols]"
      >
        <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" />
        <span>Mở lại 4 khung biểu đồ mặc định</span>
      </button>
    </div>

    <UModal
      :model-value="expandedSymbol !== null"
      :ui="{ width: 'sm:max-w-4xl' }"
      @update:model-value="
        (val) => {
          if (!val) closeExpandModal();
        }
      "
    >
      <div
        v-if="expandedSymbol"
        class="bg-surface-midnight rounded-xl overflow-hidden border border-white/[0.1] p-4 flex flex-col gap-3"
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
              Khung thời gian thực
            </span>
          </div>

          <button
            type="button"
            class="text-zinc-400 hover:text-white p-1 rounded hover:bg-white/[0.08]"
            @click="closeExpandModal"
          >
            <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
          </button>
        </div>

        <div class="w-full">
          <IBoardMiniChart
            :symbol="expandedSymbol"
            initial-resolution="1"
            :is-expanded="true"
            @close="closeExpandModal"
          />
        </div>
      </div>
    </UModal>
  </div>
</template>
