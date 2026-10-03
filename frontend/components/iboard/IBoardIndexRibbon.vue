<template>
  <div>
    <!-- Expanded Ribbon -->
    <div
      v-if="isOpen"
      class="bg-aave-obsidian border-b border-white/[0.08] px-3 py-2 flex items-center gap-2.5 overflow-x-auto shrink-0 scrollbar-thin"
    >
      <!-- Loading Skeleton State -->
      <template v-if="loading && (!indices || indices.length === 0)">
        <div
          v-for="i in 5"
          :key="i"
          class="min-w-[240px] max-w-[280px] flex-1 p-2.5 rounded-lg bg-surface-abyss border border-white/[0.04] animate-pulse"
        >
          <div class="flex items-center justify-between">
            <div class="h-3 w-16 bg-white/[0.06] rounded" />
            <div class="h-3 w-12 bg-white/[0.06] rounded" />
          </div>
          <div class="flex items-center justify-between mt-2">
            <div class="h-5 w-20 bg-white/[0.06] rounded" />
            <div class="h-3 w-10 bg-white/[0.06] rounded" />
          </div>
          <div class="flex items-center justify-between mt-2">
            <div class="h-2.5 w-28 bg-white/[0.06] rounded" />
            <div class="h-6 w-14 bg-white/[0.06] rounded" />
          </div>
        </div>
      </template>

      <!-- Empty State -->
      <div
        v-else-if="!indices || indices.length === 0"
        class="flex items-center gap-2 py-2 px-3 text-xs text-aave-graphite font-mono"
      >
        <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
        <span>Đang nạp dữ liệu dải chỉ số thị trường...</span>
      </div>

      <!-- Visible Indices Cards -->
      <template v-else>
        <IBoardIndexCard
          v-for="idx in activeDisplayIndices"
          :key="idx.id"
          :item="idx"
          :active="selectedId === idx.id"
          @select="handleSelect"
        />
      </template>

      <!-- Action Controls Stacked Vertically on the Far Right -->
      <div class="flex flex-col items-center justify-between self-stretch py-1 pl-2 pr-1 shrink-0 select-none">
        <!-- Close / Collapse Button (Top) -->
        <button
          type="button"
          class="flex items-center gap-0.5 text-[11px] font-medium text-aave-ash hover:text-white transition-colors cursor-pointer select-none"
          title="Thu gọn dải chỉ số"
          @click="$emit('update:isOpen', false)"
        >
          <UIcon name="i-heroicons-chevron-up" class="w-3 h-3 text-aave-ash" />
          <span>Đóng</span>
        </button>

        <!-- Add / Customize Button (Bottom) -->
        <button
          type="button"
          class="w-7 h-7 rounded-full border border-white/[0.14] bg-surface-abyss hover:bg-white/[0.08] hover:border-white/[0.24] text-rose-500 hover:text-rose-400 shrink-0 flex items-center justify-center transition-all cursor-pointer shadow-sm"
          title="Thêm biểu đồ chỉ số"
          @click="isCustomizeModalOpen = true"
        >
          <UIcon name="i-heroicons-plus" class="w-4 h-4 text-rose-500" />
        </button>
      </div>
    </div>

    <!-- Collapsed Ribbon Bar -->
    <div
      v-else
      class="bg-aave-obsidian border-b border-white/[0.08] px-3 py-1 flex items-center justify-between"
    >
      <div class="flex items-center gap-4 text-xs font-mono text-aave-ash overflow-hidden">
        <span class="text-aave-graphite hidden sm:inline">Chỉ số:</span>
        <div
          v-for="idx in activeDisplayIndices.slice(0, 3)"
          :key="idx.id"
          class="flex items-center gap-1.5 shrink-0"
        >
          <span class="font-bold text-white">{{ idx.name }}:</span>
          <span :class="idx.isPositive ? 'text-emerald-400' : 'text-rose-500'">
            {{ idx.price }}
          </span>
          <span class="text-[11px]" :class="idx.isPositive ? 'text-emerald-400' : 'text-rose-500'">
            {{ idx.changePercent }}
          </span>
        </div>
      </div>

      <button
        type="button"
        class="text-xs text-aave-graphite hover:text-white flex items-center gap-1 transition-colors px-2 py-0.5 rounded hover:bg-white/[0.04]"
        @click="$emit('update:isOpen', true)"
      >
        <span>Mở dải chỉ số thị trường</span>
        <UIcon name="i-heroicons-chevron-down" class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- Thêm biểu đồ Modal (Matching DNSE iBoard Modal) -->
    <UModal v-model="isCustomizeModalOpen" :ui="{ width: 'sm:max-w-lg' }">
      <div class="p-5 bg-surface-abyss text-white rounded-lg border border-white/[0.08]">
        <!-- Modal Header -->
        <div class="flex items-center justify-between pb-3 border-b border-white/[0.08]">
          <h3 class="text-sm font-bold text-white tracking-wide">
            Thêm biểu đồ
          </h3>
          <button
            type="button"
            class="text-aave-graphite hover:text-white transition-colors"
            @click="isCustomizeModalOpen = false"
          >
            <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
          </button>
        </div>

        <!-- Search Input -->
        <div class="mt-4 relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-aave-graphite">
            <UIcon name="i-heroicons-magnifying-glass" class="w-4 h-4" />
          </div>
          <input
            v-model="modalSearchQuery"
            type="text"
            placeholder="Tìm mã để thêm chart"
            class="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-surface-midnight border border-white/[0.1] text-white placeholder-aave-graphite focus:outline-none focus:border-rose-500 font-sans"
          >
        </div>

        <!-- Currently Active Charts Count and Chips -->
        <div class="mt-3.5">
          <div class="flex items-center justify-between text-xs">
            <span class="text-aave-ash">
              Biểu đồ đang hiển thị
              <span class="text-white font-mono font-medium ml-1">
                {{ activeChartIds.length }}/12
              </span>
            </span>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 mt-2">
            <span
              v-for="id in activeChartIds"
              :key="id"
              class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-surface-midnight border border-white/[0.1] text-xs font-mono text-white"
            >
              <span>{{ getIndexName(id) }}</span>
              <button
                type="button"
                class="text-aave-graphite hover:text-rose-400 transition-colors cursor-pointer"
                @click="removeChartId(id)"
              >
                <UIcon name="i-heroicons-x-mark" class="w-3 h-3" />
              </button>
            </span>
          </div>
        </div>

        <!-- Category Tabs -->
        <div class="flex items-center gap-5 mt-4 border-b border-white/[0.08] text-xs font-medium text-aave-graphite">
          <button
            v-for="tab in catalogTabs"
            :key="tab.id"
            type="button"
            class="pb-2.5 transition-colors relative"
            :class="activeTab === tab.id ? 'text-rose-500 font-semibold' : 'hover:text-white'"
            @click="activeTab = tab.id"
          >
            <span>{{ tab.label }}</span>
            <span
              v-if="activeTab === tab.id"
              class="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-500"
            />
          </button>
        </div>

        <!-- Indices Catalog List -->
        <div class="mt-3 space-y-1.5 max-h-64 overflow-y-auto pr-1 scrollbar-thin">
          <div
            v-for="item in filteredCatalogItems"
            :key="item.id"
            class="flex items-center justify-between p-2.5 rounded-lg bg-surface-midnight/[0.6] hover:bg-surface-midnight border border-white/[0.04] transition-colors"
          >
            <div class="flex flex-col pr-2">
              <span class="text-xs font-bold text-white tracking-wide">{{ item.name }}</span>
              <span class="text-[11px] text-aave-graphite mt-0.5 line-clamp-1">{{ item.description }}</span>
            </div>

            <!-- Action Button: Xóa if active, Thêm if not active -->
            <button
              v-if="activeChartIds.includes(item.id)"
              type="button"
              class="px-3.5 py-1 rounded-full text-xs font-medium border border-rose-500/60 text-rose-500 hover:bg-rose-500/10 transition-colors shrink-0 cursor-pointer"
              @click="removeChartId(item.id)"
            >
              Xóa
            </button>
            <button
              v-else
              type="button"
              class="px-3.5 py-1 rounded-full text-xs font-medium border border-white/[0.14] text-white hover:bg-white/[0.08] transition-colors shrink-0 cursor-pointer"
              @click="addChartId(item.id)"
            >
              Thêm
            </button>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="flex items-center justify-between mt-5 pt-3 border-t border-white/[0.08]">
          <button
            type="button"
            class="px-3 py-1.5 rounded text-xs text-aave-graphite hover:text-white transition-colors cursor-pointer"
            @click="resetDefaults"
          >
            Đặt lại mặc định
          </button>
          <button
            type="button"
            class="px-4 py-1.5 rounded-lg text-xs font-medium text-white bg-rose-600 hover:bg-rose-500 transition-colors cursor-pointer"
            @click="isCustomizeModalOpen = false"
          >
            Đóng
          </button>
        </div>
      </div>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue"
import IBoardIndexCard from "./IBoardIndexCard.vue"
import type { IndexDisplayItem } from "./types"

const props = withDefaults(
  defineProps<{
    indices: IndexDisplayItem[]
    loading?: boolean
    isOpen?: boolean
    selectedId?: string | null
  }>(),
  {
    loading: false,
    isOpen: true,
    selectedId: null,
  },
)

const emit = defineEmits<{
  "update:isOpen": [value: boolean]
  selectIndex: [id: string]
}>()

const isCustomizeModalOpen = ref(false)
const modalSearchQuery = ref("")
const activeTab = ref<"index" | "top_search" | "top_volume" | "world">("index")

const catalogTabs = [
  { id: "index" as const, label: "Chỉ số" },
  { id: "top_search" as const, label: "Top tìm kiếm" },
  { id: "top_volume" as const, label: "Top KLGD" },
  { id: "world" as const, label: "Thế giới" },
]

// Active displayed chart IDs (initial default matching screenshot)
const activeChartIds = ref<string[]>([
  "vn30",
  "vnindex",
  "dji",
  "hnx30",
  "vn30f1m",
])

// Extended catalog of indices matching DNSE modal
const indexCatalog = [
  {
    id: "vn30",
    name: "VN30",
    description: "Chỉ số 30 cổ phiếu vốn hóa lớn nhất sàn HOSE",
    category: "index",
    isTopSearch: true,
    isTopVolume: true,
  },
  {
    id: "vnindex",
    name: "VNINDEX",
    description: "Chỉ số đại diện toàn bộ sàn HOSE",
    category: "index",
    isTopSearch: true,
    isTopVolume: true,
  },
  {
    id: "upcom",
    name: "UPCOM",
    description: "Chỉ số của toàn bộ cổ phiếu đang niêm yết trên UPCOM",
    category: "index",
    isTopSearch: true,
    isTopVolume: false,
  },
  {
    id: "vnxall",
    name: "VNXALLSHARE",
    description: "Chỉ số của một nhóm cổ phiếu trên HSX và HNX",
    category: "index",
    isTopSearch: false,
    isTopVolume: false,
  },
  {
    id: "vn30f1m",
    name: "VN30F1M",
    description: "Hợp đồng tương lai chỉ số VN30 1 tháng",
    category: "index",
    isTopSearch: true,
    isTopVolume: true,
  },
  {
    id: "vn30f2m",
    name: "VN30F2M",
    description: "Hợp đồng tương lai chỉ số VN30 2 tháng",
    category: "index",
    isTopSearch: false,
    isTopVolume: false,
  },
  {
    id: "vn30f1q",
    name: "VN30F1Q",
    description: "Hợp đồng tương lai chỉ số VN30 1 quý",
    category: "index",
    isTopSearch: false,
    isTopVolume: false,
  },
  {
    id: "vn30f2q",
    name: "VN30F2Q",
    description: "Hợp đồng tương lai chỉ số VN30 2 quý",
    category: "index",
    isTopSearch: false,
    isTopVolume: false,
  },
  {
    id: "hnx30",
    name: "HNX30",
    description: "Chỉ số 30 cổ phiếu dẫn đầu sàn HNX",
    category: "index",
    isTopSearch: false,
    isTopVolume: false,
  },
  {
    id: "hnx",
    name: "HNX-INDEX",
    description: "Chỉ số đại diện toàn bộ sàn HNX",
    category: "index",
    isTopSearch: false,
    isTopVolume: false,
  },
  {
    id: "dji",
    name: "DOW JONES FUTURES",
    description: "Hợp đồng tương lai chỉ số Dow Jones Mỹ",
    category: "world",
    isTopSearch: true,
    isTopVolume: false,
  },
  {
    id: "sp500",
    name: "S&P 500",
    description: "Chỉ số 500 công ty đại chúng lớn nhất thị trường Mỹ",
    category: "world",
    isTopSearch: false,
    isTopVolume: false,
  },
  {
    id: "nasdaq",
    name: "NASDAQ 100",
    description: "Chỉ số công nghệ hàng đầu sàn Nasdaq Mỹ",
    category: "world",
    isTopSearch: true,
    isTopVolume: false,
  },
]

// Fallback items if some indices are added from catalog but not returned by backend
const fallbackItemsMap: Record<string, Partial<IndexDisplayItem>> = {
  upcom: {
    name: "UPCOM",
    price: "92.45",
    change: "+0.32",
    changePercent: "+0.35%",
    isPositive: true,
    volume: "42.10 Triệu CP",
    value: "624.18 Tỷ",
    breadth: {
      advance: 142,
      ceiling: 12,
      unchanged: 98,
      decline: 84,
      floor: 4,
    },
    sparkline: [91.8, 92.0, 92.2, 92.15, 92.3, 92.4, 92.45],
  },
  vnxall: {
    name: "VNXALLSHARE",
    price: "2,410.80",
    change: "-15.20",
    changePercent: "-0.63%",
    isPositive: false,
    volume: "890.15 Triệu CP",
    value: "21,450.00 Tỷ",
    breadth: {
      advance: 180,
      ceiling: 8,
      unchanged: 110,
      decline: 280,
      floor: 12,
    },
    sparkline: [2428, 2424, 2419, 2421, 2416, 2414, 2410.8],
  },
  vn30f2m: {
    name: "VN30F2M",
    price: "1,883.2",
    change: "-8.50",
    changePercent: "-0.45%",
    isPositive: false,
    volume: "4,120 HĐ",
    value: "776.10 Tỷ",
    breadth: { advance: 0, ceiling: 0, unchanged: 0, decline: 1, floor: 0 },
    sparkline: [1892, 1890, 1887, 1885, 1883.2],
  },
  vn30f1q: {
    name: "VN30F1Q",
    price: "1,880.0",
    change: "-7.00",
    changePercent: "-0.37%",
    isPositive: false,
    volume: "860 HĐ",
    value: "161.80 Tỷ",
    breadth: { advance: 0, ceiling: 0, unchanged: 0, decline: 1, floor: 0 },
    sparkline: [1887, 1885, 1882, 1880.0],
  },
  vn30f2q: {
    name: "VN30F2Q",
    price: "1,878.5",
    change: "-6.50",
    changePercent: "-0.35%",
    isPositive: false,
    volume: "340 HĐ",
    value: "63.90 Tỷ",
    breadth: { advance: 0, ceiling: 0, unchanged: 0, decline: 1, floor: 0 },
    sparkline: [1885, 1882, 1880, 1878.5],
  },
  sp500: {
    name: "S&P 500",
    price: "5,864.67",
    change: "+24.30",
    changePercent: "+0.42%",
    isPositive: true,
    volume: "2.84B CP",
    value: "142.50B USD",
    breadth: {
      advance: 310,
      ceiling: 0,
      unchanged: 40,
      decline: 150,
      floor: 0,
    },
    sparkline: [5840, 5845, 5850, 5855, 5860, 5864.67],
  },
  nasdaq: {
    name: "NASDAQ 100",
    price: "20,439.80",
    change: "+112.40",
    changePercent: "+0.55%",
    isPositive: true,
    volume: "4.12B CP",
    value: "210.80B USD",
    breadth: { advance: 68, ceiling: 0, unchanged: 8, decline: 24, floor: 0 },
    sparkline: [20320, 20350, 20390, 20410, 20439.8],
  },
}

const activeDisplayIndices = computed<IndexDisplayItem[]>(() => {
  const result: IndexDisplayItem[] = []
  for (const id of activeChartIds.value) {
    const existing = props.indices?.find(
      (item) => item.id.toLowerCase() === id.toLowerCase(),
    )
    if (existing) {
      result.push(existing)
    } else if (fallbackItemsMap[id]) {
      const fb = fallbackItemsMap[id]
      result.push({
        id,
        name: fb.name || id.toUpperCase(),
        price: fb.price || "0.00",
        change: fb.change || "0.00",
        changePercent: fb.changePercent || "0.00%",
        isPositive: fb.isPositive ?? true,
        volume: fb.volume || "",
        value: fb.value || "",
        breadth: fb.breadth || {
          advance: 0,
          ceiling: 0,
          unchanged: 0,
          decline: 0,
          floor: 0,
        },
        sparkline: fb.sparkline || [100, 101, 102],
      })
    }
  }
  return result
})

const filteredCatalogItems = computed(() => {
  const query = modalSearchQuery.value.trim().toLowerCase()
  return indexCatalog.filter((item) => {
    // Search query filter
    if (query) {
      const matchName = item.name.toLowerCase().includes(query)
      const matchDesc = item.description.toLowerCase().includes(query)
      if (!matchName && !matchDesc) return false
    }

    // Tab filter
    if (activeTab.value === "index") {
      return item.category === "index"
    }
    if (activeTab.value === "top_search") {
      return item.isTopSearch
    }
    if (activeTab.value === "top_volume") {
      return item.isTopVolume
    }
    if (activeTab.value === "world") {
      return item.category === "world"
    }
    return true
  })
})

const getIndexName = (id: string) => {
  const found = indexCatalog.find((i) => i.id === id)
  return found ? found.name : id.toUpperCase()
}

const addChartId = (id: string) => {
  if (activeChartIds.value.length >= 12) return
  if (!activeChartIds.value.includes(id)) {
    activeChartIds.value.push(id)
  }
}

const removeChartId = (id: string) => {
  if (activeChartIds.value.length <= 1) return
  activeChartIds.value = activeChartIds.value.filter((i) => i !== id)
}

const resetDefaults = () => {
  activeChartIds.value = ["vn30", "vnindex", "dji", "hnx30", "vn30f1m"]
}

const handleSelect = (id: string) => {
  emit("selectIndex", id)
}
</script>
