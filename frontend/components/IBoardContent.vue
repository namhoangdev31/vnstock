<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue"
import type {
  IBoardIndexItem,
  IBoardPutThroughSummary,
  IBoardStockRow,
} from "~/types/iboard"

interface Props {
  isDerivatives?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isDerivatives: false,
})

// Tab Cấp 1 (Chính):
type MainCategory =
  | "watchlist"
  | "listed"
  | "sectors"
  | "derivatives"
  | "warrants"
  | "etf"
  | "put_through"
  | "ideas"
  | "screener"

const route = useRoute()

const activeCategory = ref<MainCategory>(
  (route.query.tab as MainCategory) ||
    (props.isDerivatives ? "derivatives" : "listed"),
)

// Sub-pills cho Niêm Yết
const selectedGroup = ref<"VN30" | "HSX" | "HNX" | "UPCOM">("VN30")

// Sub-pills cho Ngành
const selectedSector = ref<string>("bank")

// Sub-pills cho Thỏa thuận
const selectedPutThroughExchange = ref<"HSX" | "HNX" | "UPCOM">("HSX")

// Search input
const searchInput = ref<string>("")

// State chi tiết mã
const selectedSymbol = ref<string | null>(
  (route.query.symbol as string) || null,
)

// Sidebar phải (Mở rộng / Thu gọn)
const isSidebarOpen = ref<boolean>(true)
const sidebarTab = ref<"pulse" | "order" | "orders">("pulse")

// Modal độ rộng thị trường
const isBreadthModalOpen = ref<boolean>(false)

// Dữ liệu Bảng Giá
const stocks = ref<IBoardStockRow[]>([])
const isLoadingStocks = ref<boolean>(false)

// Dữ liệu Thỏa Thuận (Put-Through)
const putThroughData = ref<IBoardPutThroughSummary | null>(null)
const isLoadingPutThrough = ref<boolean>(false)

// Dữ liệu Chỉ số (Breadth)
const indicesData = ref<IBoardIndexItem[]>([])

// Tải danh sách cổ phiếu
const fetchBoardStocks = async () => {
  if (activeCategory.value === "put_through") return

  isLoadingStocks.value = true
  try {
    const params: Record<string, string> = {
      category: activeCategory.value,
      group: selectedGroup.value,
      limit: "50",
    }
    if (activeCategory.value === "sectors") {
      params.sector = selectedSector.value
    }
    if (searchInput.value.trim()) {
      params.search = searchInput.value.trim()
    }

    const res = await $fetch<IBoardStockRow[]>("/api/v1/stock/iboard/board", {
      params,
    })
    stocks.value = res || []
  } catch (err) {
    console.error("Lỗi tải danh sách cổ phiếu:", err)
  } finally {
    isLoadingStocks.value = false
  }
}

// Tải dữ liệu Thỏa Thuận (Put-Through)
const fetchPutThrough = async () => {
  isLoadingPutThrough.value = true
  try {
    const res = await $fetch<IBoardPutThroughSummary>(
      "/api/v1/stock/iboard/put-through",
      {
        params: { exchange: selectedPutThroughExchange.value },
      },
    )
    putThroughData.value = res
    // Nếu chưa chọn mã nào và có danh sách thỏa thuận, chọn mã đầu tiên (mặc định MSB)
    if (!selectedSymbol.value && res?.trades?.length) {
      selectedSymbol.value = res.trades[0].symbol
    }
  } catch (err) {
    console.error("Lỗi tải giao dịch thỏa thuận:", err)
  } finally {
    isLoadingPutThrough.value = false
  }
}

// Tải dữ liệu Chỉ số và Thống kê biến động
const fetchIndices = async () => {
  try {
    const res = await $fetch<IBoardIndexItem[]>("/api/v1/stock/iboard/indices")
    indicesData.value = res || []
  } catch (err) {
    console.error("Lỗi tải thông tin chỉ số:", err)
  }
}

// Thống kê biến động (Trần / Tăng / Tham chiếu / Giảm / Sàn)
const breadthStats = computed(() => {
  const currentIdx = indicesData.value.find(
    (i: IBoardIndexItem) => i.id === "VNINDEX",
  )
  if (currentIdx?.breadth) {
    return {
      ceiling: currentIdx.breadth.ceiling || 0,
      advance: currentIdx.breadth.advance || 0,
      unchanged: currentIdx.breadth.unchanged || 0,
      decline: currentIdx.breadth.decline || 0,
      floor: currentIdx.breadth.floor || 0,
    }
  }
  return { ceiling: 0, advance: 13, unchanged: 1, decline: 16, floor: 0 }
})

// Theo dõi thay đổi tab hoặc filter
watch(
  [activeCategory, selectedGroup, selectedSector, selectedPutThroughExchange],
  () => {
    if (activeCategory.value === "put_through") {
      fetchPutThrough()
      if (!selectedSymbol.value) {
        selectedSymbol.value = "MSB"
      }
    } else {
      fetchBoardStocks()
    }
  },
)

let searchDebounce: ReturnType<typeof setTimeout> | null = null
watch(searchInput, () => {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    fetchBoardStocks()
  }, 350)
})

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  fetchIndices()
  if (activeCategory.value === "put_through") {
    fetchPutThrough()
  } else {
    fetchBoardStocks()
  }

  refreshTimer = setInterval(() => {
    fetchIndices()
    if (activeCategory.value === "put_through") {
      fetchPutThrough()
    } else if (!selectedSymbol.value) {
      fetchBoardStocks()
    }
  }, 10000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  if (searchDebounce) clearTimeout(searchDebounce)
})

const handleSelectStock = (sym: string) => {
  selectedSymbol.value = sym
}

const handleOpenOrder = (sym: string) => {
  selectedSymbol.value = sym
  isSidebarOpen.value = true
  sidebarTab.value = "order"
}
</script>

<template>
  <main class="flex-1 flex flex-col min-h-0 bg-surface-abyss text-aave-paper overflow-hidden select-none">
    <!-- MINI CHARTS BAR PHÍA TRÊN CÙNG (VNINDEX, VN30, HNX, HNX30, UPCOM, VN30F1M) -->
    <IBoardMiniChartsBar :is-derivatives="isDerivatives" />

    <!-- 1. THANH ĐIỀU HƯỚNG TAB CẤP 1 (Ảnh 1, 2, 3) -->
    <div class="flex items-center justify-between px-3 py-2 bg-tv-surface border-b border-tv-border overflow-x-auto gap-2">
      <div class="flex items-center gap-1 sm:gap-2">
        <!-- Danh mục của bạn -->
        <button
          type="button"
          class="px-2.5 py-1 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer"
          :class="activeCategory === 'watchlist' ? 'bg-white/10 text-white' : 'text-tv-secondary hover:text-white'"
          @click="activeCategory = 'watchlist'"
        >
          Danh mục của bạn
        </button>

        <!-- Niêm yết (Ảnh 1, 2) -->
        <button
          type="button"
          class="px-2.5 py-1 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer"
          :class="activeCategory === 'listed' ? 'bg-white/10 text-white font-bold' : 'text-tv-secondary hover:text-white'"
          @click="activeCategory = 'listed'"
        >
          Niêm yết
        </button>

        <!-- Ngành -->
        <button
          type="button"
          class="px-2.5 py-1 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer"
          :class="activeCategory === 'sectors' ? 'bg-white/10 text-white font-bold' : 'text-tv-secondary hover:text-white'"
          @click="activeCategory = 'sectors'"
        >
          Ngành
        </button>

        <!-- Phái sinh -->
        <button
          type="button"
          class="px-2.5 py-1 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer"
          :class="activeCategory === 'derivatives' ? 'bg-white/10 text-white font-bold' : 'text-tv-secondary hover:text-white'"
          @click="activeCategory = 'derivatives'"
        >
          Phái sinh
        </button>

        <!-- Chứng quyền -->
        <button
          type="button"
          class="px-2.5 py-1 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer"
          :class="activeCategory === 'warrants' ? 'bg-white/10 text-white font-bold' : 'text-tv-secondary hover:text-white'"
          @click="activeCategory = 'warrants'"
        >
          Chứng quyền
        </button>

        <!-- ETF -->
        <button
          type="button"
          class="px-2.5 py-1 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer"
          :class="activeCategory === 'etf' ? 'bg-white/10 text-white font-bold' : 'text-tv-secondary hover:text-white'"
          @click="activeCategory = 'etf'"
        >
          ETF
        </button>

        <!-- Thỏa thuận (Ảnh 3, 4, 5) -->
        <button
          type="button"
          class="px-2.5 py-1 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer"
          :class="activeCategory === 'put_through' ? 'bg-white/10 text-white font-bold' : 'text-tv-secondary hover:text-white'"
          @click="activeCategory = 'put_through'"
        >
          Thỏa thuận
        </button>

        <!-- Tính năng riêng của App (Sắp ra mắt) -->
        <div class="flex items-center gap-1.5 pl-1 border-l border-tv-border">
          <UTooltip text="Tính năng nghiên cứu định lượng riêng của Vistock, đang hoàn thiện">
            <button
              type="button"
              class="px-2 py-1 text-xs text-tv-secondary/60 hover:text-tv-secondary transition-colors whitespace-nowrap cursor-pointer flex items-center gap-1"
            >
              <span>Ý tưởng đầu tư</span>
              <span class="text-[9px] px-1 py-0.2 bg-white/[0.06] rounded text-tv-secondary">Sắp ra mắt</span>
            </button>
          </UTooltip>

          <UTooltip text="Bộ lọc cổ phiếu nâng cao đa yếu tố, đang hoàn thiện">
            <button
              type="button"
              class="px-2 py-1 text-xs text-tv-secondary/60 hover:text-tv-secondary transition-colors whitespace-nowrap cursor-pointer flex items-center gap-1"
            >
              <span>Bộ lọc cổ phiếu</span>
              <span class="text-[9px] px-1 py-0.2 bg-white/[0.06] rounded text-tv-secondary">Sắp ra mắt</span>
            </button>
          </UTooltip>
        </div>
      </div>
    </div>

    <!-- 2. THANH SUB-PILLS & THỐNG KÊ BIẾN ĐỘNG (Ảnh 1, 2 & Ảnh 3) -->
    <div class="flex flex-wrap items-center justify-between px-3 py-2 bg-tv-card border-b border-tv-border gap-2">
      <!-- CỤM TRÁI: Search và Sub-Pills -->
      <div class="flex items-center gap-2 flex-wrap">
        <!-- Ô Tìm Kiếm Mã -->
        <div class="relative w-36 sm:w-44">
          <UIcon name="i-heroicons-magnifying-glass" class="w-4 h-4 text-tv-secondary absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            v-model="searchInput"
            type="text"
            placeholder="Tìm mã"
            class="w-full bg-tv-surface border border-tv-border rounded-lg pl-8 pr-2.5 py-1 text-xs text-white placeholder-tv-secondary focus:outline-none focus:border-aave-violet transition-colors font-mono uppercase"
          />
        </div>

        <!-- Cụm Sub-Pills khi chọn tab NIÊM YẾT (Ảnh 1, 2) -->
        <template v-if="activeCategory === 'listed'">
          <button
            type="button"
            class="px-3 py-1 text-xs font-bold rounded-md transition-colors cursor-pointer"
            :class="selectedGroup === 'VN30' ? 'bg-market-decline text-white' : 'bg-tv-surface text-tv-secondary hover:text-white border border-tv-border'"
            @click="selectedGroup = 'VN30'"
          >
            VN30
          </button>
          <button
            type="button"
            class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer"
            :class="selectedGroup === 'HSX' ? 'bg-market-decline text-white' : 'bg-tv-surface text-tv-secondary hover:text-white border border-tv-border'"
            @click="selectedGroup = 'HSX'"
          >
            HSX
          </button>
          <button
            type="button"
            class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer"
            :class="selectedGroup === 'HNX' ? 'bg-market-decline text-white' : 'bg-tv-surface text-tv-secondary hover:text-white border border-tv-border'"
            @click="selectedGroup = 'HNX'"
          >
            HNX
          </button>
          <button
            type="button"
            class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer"
            :class="selectedGroup === 'UPCOM' ? 'bg-market-decline text-white' : 'bg-tv-surface text-tv-secondary hover:text-white border border-tv-border'"
            @click="selectedGroup = 'UPCOM'"
          >
            UPCOM
          </button>
        </template>

        <!-- Cụm Sub-Pills khi chọn tab THỎA THUẬN (Ảnh 3, 4, 5) -->
        <template v-else-if="activeCategory === 'put_through'">
          <button
            type="button"
            class="px-3 py-1 text-xs font-bold rounded-md transition-colors cursor-pointer"
            :class="selectedPutThroughExchange === 'HSX' ? 'bg-market-decline text-white' : 'bg-tv-surface text-tv-secondary hover:text-white border border-tv-border'"
            @click="selectedPutThroughExchange = 'HSX'"
          >
            HSX
          </button>
          <button
            type="button"
            class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer"
            :class="selectedPutThroughExchange === 'HNX' ? 'bg-market-decline text-white' : 'bg-tv-surface text-tv-secondary hover:text-white border border-tv-border'"
            @click="selectedPutThroughExchange = 'HNX'"
          >
            HNX
          </button>
          <button
            type="button"
            class="px-3 py-1 text-xs font-semibold rounded-md transition-colors cursor-pointer"
            :class="selectedPutThroughExchange === 'UPCOM' ? 'bg-market-decline text-white' : 'bg-tv-surface text-tv-secondary hover:text-white border border-tv-border'"
            @click="selectedPutThroughExchange = 'UPCOM'"
          >
            UPCOM
          </button>
        </template>

        <!-- Cụm Sub-Pills khi chọn tab NGÀNH -->
        <template v-else-if="activeCategory === 'sectors'">
          <div class="flex items-center gap-1 overflow-x-auto">
            <button
              v-for="sec in [
                { id: 'bank', name: 'Ngân hàng' },
                { id: 'real_estate', name: 'Bất động sản' },
                { id: 'materials', name: 'Thép & VL' },
                { id: 'telecom', name: 'Công nghệ' },
                { id: 'retail', name: 'Bán lẻ' },
                { id: 'logistics', name: 'Vận tải' },
              ]"
              :key="sec.id"
              type="button"
              class="px-2.5 py-1 text-xs font-semibold rounded-md transition-colors whitespace-nowrap cursor-pointer"
              :class="selectedSector === sec.id ? 'bg-market-decline text-white' : 'bg-tv-surface text-tv-secondary hover:text-white border border-tv-border'"
              @click="selectedSector = sec.id"
            >
              {{ sec.name }}
            </button>
          </div>
        </template>

        <!-- THỐNG KÊ BIẾN ĐỘNG (Ảnh 1, 2) -->
        <div class="flex items-center gap-1.5 ml-2 pl-2 border-l border-tv-border">
          <button
            type="button"
            class="text-xs font-semibold text-tv-secondary hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Mở bảng phân bổ độ rộng thị trường"
            @click="isBreadthModalOpen = true"
          >
            <span>Thống kê biến động</span>
            <div class="flex items-center gap-1 font-mono text-[11px] font-bold">
              <!-- Trần (Tím) -->
              <span class="px-1.5 py-0.5 rounded bg-market-ceiling/20 text-market-ceiling flex items-center gap-0.5">
                <UIcon name="i-heroicons-arrow-up" class="w-3 h-3" />
                {{ breadthStats.ceiling }}
              </span>
              <!-- Tăng (Xanh lá) -->
              <span class="px-1.5 py-0.5 rounded bg-market-advance/20 text-market-advance flex items-center gap-0.5">
                <UIcon name="i-heroicons-arrow-up" class="w-3 h-3" />
                {{ breadthStats.advance }}
              </span>
              <!-- TC (Vàng) -->
              <span class="px-1.5 py-0.5 rounded bg-market-unchanged/20 text-market-unchanged flex items-center gap-0.5">
                <UIcon name="i-heroicons-minus" class="w-3 h-3" />
                {{ breadthStats.unchanged }}
              </span>
              <!-- Giảm (Đỏ) -->
              <span class="px-1.5 py-0.5 rounded bg-market-decline/20 text-market-decline flex items-center gap-0.5">
                <UIcon name="i-heroicons-arrow-down" class="w-3 h-3" />
                {{ breadthStats.decline }}
              </span>
              <!-- Sàn (Xanh lơ) -->
              <span class="px-1.5 py-0.5 rounded bg-market-floor/20 text-market-floor flex items-center gap-0.5">
                <UIcon name="i-heroicons-arrow-down" class="w-3 h-3" />
                {{ breadthStats.floor }}
              </span>
            </div>
          </button>
        </div>
      </div>

      <!-- CỤM PHẢI: Banner Thỏa Thuận hoặc Nút Công Cụ -->
      <div class="flex items-center gap-3">
        <!-- Banner Thỏa Thuận (Ảnh 3, 4, 5) -->
        <template v-if="activeCategory === 'put_through'">
          <div class="flex items-center gap-2 font-mono text-xs">
            <span class="text-tv-secondary">
              Tổng KLGD <span class="text-white font-bold">{{ putThroughData?.total_volume ? new Intl.NumberFormat('vi-VN').format(putThroughData.total_volume) : '49,056,971' }}</span>
            </span>
            <span class="text-tv-secondary">-</span>
            <span class="text-tv-secondary">
              Tổng GTGD <span class="text-white font-bold">{{ putThroughData?.total_value_billion ? putThroughData.total_value_billion.toFixed(2) : '1,025.99' }} Tỷ</span>
            </span>
            <button
              type="button"
              class="ml-2 px-2.5 py-1 text-xs font-semibold text-white bg-aave-violet hover:bg-aave-violet/80 rounded transition-colors cursor-pointer"
              @click="sidebarTab = 'order'; isSidebarOpen = true"
            >
              Đặt lệnh thoả thuận
            </button>
          </div>
        </template>

        <!-- Nút toggle sidebar phải -->
        <button
          type="button"
          class="p-1 rounded text-tv-secondary hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
          :title="isSidebarOpen ? 'Thu gọn thanh bên' : 'Mở rộng thanh bên'"
          aria-label="Toggle thanh bên"
          @click="isSidebarOpen = !isSidebarOpen"
        >
          <UIcon
            :name="isSidebarOpen ? 'i-heroicons-chevron-double-right' : 'i-heroicons-chevron-double-left'"
            class="w-4 h-4"
          />
        </button>
      </div>
    </div>

    <!-- 3. KHỐI THÂN NỘI DUNG CHÍNH (Content Body) -->
    <div class="flex-1 flex overflow-hidden min-h-0">
      <!-- TRƯỜNG HỢP A: TAB THỎA THUẬN (Ảnh 3, 4, 5) -->
      <template v-if="activeCategory === 'put_through'">
        <div class="flex-1 flex overflow-hidden">
          <!-- Cột Trái (~300px): Bảng Danh Sách Giao Dịch Thỏa Thuận -->
          <div class="w-72 lg:w-80 shrink-0 border-r border-tv-border flex flex-col bg-tv-canvas">
            <IBoardTable
              :stocks="[]"
              :is-put-through="true"
              :put-through-trades="putThroughData?.trades || []"
              :selected-symbol="selectedSymbol"
              @select-stock="handleSelectStock"
            />
          </div>

          <!-- Cột Giữa & Phải: Panel Chi Tiết Cổ Phiếu Đang Chọn (Mặc định MSB) -->
          <div class="flex-1 flex flex-col min-w-0 overflow-hidden bg-tv-canvas">
            <IBoardStockDetailPanel
              v-if="selectedSymbol"
              :symbol="selectedSymbol"
              :is-derivatives="isDerivatives"
              @close="selectedSymbol = null"
              @select-symbol="handleSelectStock"
              @open-order="handleOpenOrder"
            />
            <div v-else class="flex-1 flex items-center justify-center text-tv-secondary text-xs">
              Chọn một mã thỏa thuận ở danh sách bên trái để xem biểu đồ và chi tiết.
            </div>
          </div>
        </div>
      </template>

      <!-- TRƯỜNG HỢP B: CÁC TAB CÒN LẠI (Niêm yết, Ngành, Phái sinh, Chứng quyền, ETF) - Ảnh 1, 2 -->
      <template v-else>
        <div class="flex-1 flex overflow-hidden">
          <!-- Nếu ĐÃ CHỌN 1 mã: Hiện giao diện chi tiết mã + TradingView Chart (Ảnh 3, 4, 5) -->
          <div v-if="selectedSymbol" class="flex-1 flex flex-col min-w-0 overflow-hidden">
            <IBoardStockDetailPanel
              :symbol="selectedSymbol"
              :is-derivatives="isDerivatives"
              @close="selectedSymbol = null"
              @select-symbol="handleSelectStock"
              @open-order="handleOpenOrder"
            />
          </div>

          <!-- Nếu CHƯA CHỌN mã: Hiện toàn bộ Bảng Giá Lưới Đầy Đủ (Ảnh 1, 2) -->
          <div v-else class="flex-1 flex flex-col min-w-0 overflow-hidden">
            <IBoardTable
              :stocks="stocks"
              :is-loading="isLoadingStocks"
              :selected-symbol="selectedSymbol"
              @select-stock="handleSelectStock"
              @open-order="handleOpenOrder"
            />
          </div>
        </div>
      </template>

      <!-- SIDEBAR PHÍA PHẢI: Thị trường / Đặt lệnh mô phỏng / Sổ lệnh (Ảnh 1, 2, 3, 4, 5 Cột Phải) -->
      <IBoardRightSidebar
        :is-open="isSidebarOpen"
        :active-tab="sidebarTab"
        :symbol="selectedSymbol || 'MSB'"
        @update:is-open="isSidebarOpen = $event"
        @update:active-tab="sidebarTab = $event"
        @select-symbol="handleSelectStock"
      />
    </div>

    <!-- MODAL ĐỘ RỘNG THỊ TRƯỜNG (Market Breadth Detail) -->
    <IBoardMarketBreadthModal
      v-model="isBreadthModalOpen"
      initial-index="VNINDEX"
      @select-symbol="handleSelectStock"
    />
  </main>
</template>
