<script setup lang="ts">
import type {
  FluctuationStats,
  LayoutMode,
  ListedSubBasket,
  MainCategory,
  SectorItem,
} from "./types"

const props = withDefaults(
  defineProps<{
    mainCategory: MainCategory
    listedSubBasket: ListedSubBasket
    sectorSubBasket: string
    sectorList: SectorItem[]
    fluctuationStats: FluctuationStats
    searchQuery: string
    priceUnitDisplay: "percent" | "diff"
    layoutMode?: LayoutMode
  }>(),
  {
    layoutMode: "list",
  },
)

const emit = defineEmits<{
  (e: "update:mainCategory", val: MainCategory): void
  (e: "update:listedSubBasket", val: ListedSubBasket): void
  (e: "update:sectorSubBasket", val: string): void
  (e: "update:searchQuery", val: string): void
  (e: "update:priceUnitDisplay", val: "percent" | "diff"): void
  (e: "update:layoutMode", val: LayoutMode): void
}>()
</script>

<template>
  <div class="bg-aave-inkwell border-b border-white/[0.08] px-4 py-2 flex flex-col gap-2 shrink-0">
    <!-- Hàng trên: Các danh mục chính và Thống kê biến động thị trường -->
    <div class="flex items-center justify-between gap-4 overflow-x-auto">
      <div class="flex items-center gap-1 text-xs font-medium text-aave-ash">
        <button
          type="button"
          class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
          :class="mainCategory === 'watchlist' ? 'bg-white/[0.08] text-white font-semibold' : 'hover:text-white'"
          @click="emit('update:mainCategory', 'watchlist')"
        >
          Danh mục của bạn
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
          :class="mainCategory === 'listed' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
          @click="emit('update:mainCategory', 'listed')"
        >
          Niêm yết
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
          :class="mainCategory === 'sectors' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
          @click="emit('update:mainCategory', 'sectors')"
        >
          Ngành
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
          :class="mainCategory === 'derivatives' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
          @click="emit('update:mainCategory', 'derivatives')"
        >
          Phái sinh
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
          :class="mainCategory === 'warrants' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
          @click="emit('update:mainCategory', 'warrants')"
        >
          Chứng quyền
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
          :class="mainCategory === 'etf' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
          @click="emit('update:mainCategory', 'etf')"
        >
          ETF
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded transition-colors whitespace-nowrap"
          :class="mainCategory === 'put_through' ? 'bg-rose-600 text-white font-semibold' : 'hover:text-white'"
          @click="emit('update:mainCategory', 'put_through')"
        >
          Thỏa thuận
        </button>
      </div>

      <!-- Thống kê biến động số lượng mã -->
      <div class="hidden lg:flex items-center gap-1.5 text-xs font-mono">
        <span class="text-aave-graphite mr-1">Thống kê biến động:</span>
        <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-purple-950/40 border border-purple-800/40 text-purple-400">
          <UIcon name="i-heroicons-arrow-trending-up" class="w-3 h-3" />
          <span>{{ fluctuationStats.ceil }}</span>
        </div>
        <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-800/40 text-emerald-400">
          <UIcon name="i-heroicons-arrow-up" class="w-3 h-3" />
          <span>{{ fluctuationStats.up }}</span>
        </div>
        <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-amber-950/40 border border-amber-800/40 text-amber-400">
          <UIcon name="i-heroicons-minus" class="w-3 h-3" />
          <span>{{ fluctuationStats.unch }}</span>
        </div>
        <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-rose-950/40 border border-rose-800/40 text-rose-500">
          <UIcon name="i-heroicons-arrow-down" class="w-3 h-3" />
          <span>{{ fluctuationStats.down }}</span>
        </div>
        <div class="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/40 text-cyan-400">
          <UIcon name="i-heroicons-arrow-trending-down" class="w-3 h-3" />
          <span>{{ fluctuationStats.flr }}</span>
        </div>
      </div>
    </div>

    <!-- Hàng dưới: Rổ phụ (Sub-baskets), Tìm kiếm và Đơn vị hiển thị -->
    <div class="flex items-center justify-between gap-3 overflow-x-auto pt-1 border-t border-white/[0.04]">
      <div class="flex items-center gap-2">
        <div class="relative w-48 shrink-0">
          <UIcon name="i-heroicons-magnifying-glass" class="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-aave-graphite" />
          <input
            :value="searchQuery"
            type="text"
            placeholder="Tìm mã chứng khoán..."
            class="w-full bg-surface-abyss border border-white/[0.1] rounded pl-8 pr-2.5 py-1 text-xs text-white placeholder-aave-graphite focus:outline-none focus:border-rose-500 transition-colors uppercase font-mono"
            @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
          >
        </div>

        <template v-if="mainCategory === 'listed'">
          <div class="flex items-center gap-1 text-xs font-mono">
            <button
              v-for="b in (['VN30', 'HSX', 'HNX', 'UPCOM', 'ODD_LOT', 'MARGIN_DISCOUNT'] as const)"
              :key="b"
              type="button"
              class="px-2.5 py-1 rounded transition-colors whitespace-nowrap"
              :class="listedSubBasket === b ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
              @click="emit('update:listedSubBasket', b)"
            >
              {{ b === 'ODD_LOT' ? 'Lô lẻ' : b === 'MARGIN_DISCOUNT' ? 'Ký quỹ' : b }}
            </button>
          </div>
        </template>

        <template v-else-if="mainCategory === 'sectors'">
          <div class="flex items-center gap-1 text-xs font-mono overflow-x-auto">
            <button
              v-for="s in sectorList"
              :key="s.id"
              type="button"
              class="px-2.5 py-1 rounded transition-colors whitespace-nowrap flex items-center gap-1.5"
              :class="sectorSubBasket === s.id ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
              @click="emit('update:sectorSubBasket', s.id)"
            >
              <span>{{ s.name }}</span>
              <span
                v-if="s.change"
                class="text-xs"
                :class="s.change.startsWith('+') ? 'text-emerald-400' : 'text-rose-500'"
              >
                {{ s.change }}
              </span>
            </button>
          </div>
        </template>

        <template v-else-if="mainCategory === 'derivatives'">
          <span class="text-xs text-aave-graphite px-2 font-mono">Hợp đồng tương lai chỉ số VN30 và VN100</span>
        </template>

        <template v-else-if="mainCategory === 'warrants'">
          <span class="text-xs text-aave-graphite px-2 font-mono">Chứng quyền có bảo đảm niêm yết trên HOSE</span>
        </template>

        <template v-else-if="mainCategory === 'etf'">
          <span class="text-xs text-aave-graphite px-2 font-mono">Chứng chỉ quỹ ETF mô phỏng rổ chỉ số chứng khoán</span>
        </template>

        <template v-else-if="mainCategory === 'watchlist'">
          <span class="text-xs text-aave-graphite px-2 font-mono">Danh mục cổ phiếu đang theo dõi</span>
        </template>

        <template v-else-if="mainCategory === 'put_through'">
          <span class="text-xs text-aave-graphite px-2 font-mono">Giao dịch thỏa thuận khớp lệnh định kỳ</span>
        </template>
      </div>

      <div class="flex items-center gap-2 text-xs font-mono">
        <div class="flex items-center bg-surface-abyss border border-white/[0.08] rounded p-0.5">
          <button
            type="button"
            class="px-2 py-0.5 rounded text-xs transition-colors"
            :class="priceUnitDisplay === 'percent' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
            @click="emit('update:priceUnitDisplay', 'percent')"
          >
            %
          </button>
          <button
            type="button"
            class="px-2 py-0.5 rounded text-xs transition-colors"
            :class="priceUnitDisplay === 'diff' ? 'bg-white/[0.1] text-white font-semibold' : 'text-aave-graphite hover:text-white'"
            @click="emit('update:priceUnitDisplay', 'diff')"
          >
            +/- Điểm
          </button>
        </div>

        <!-- Chế độ hiển thị: Danh sách / Lưới ô thẻ chuẩn DNSE -->
        <div class="flex items-center bg-surface-abyss border border-white/[0.08] rounded p-0.5">
          <button
            type="button"
            class="p-1 rounded text-xs transition-colors flex items-center justify-center"
            :class="layoutMode === 'list' ? 'bg-white/[0.1] text-white' : 'text-aave-graphite hover:text-white'"
            title="Dạng bảng danh sách"
            @click="emit('update:layoutMode', 'list')"
          >
            <UIcon name="i-heroicons-bars-3" class="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            class="p-1 rounded text-xs transition-colors flex items-center justify-center"
            :class="layoutMode === 'grid' ? 'bg-white/[0.1] text-white' : 'text-aave-graphite hover:text-white'"
            title="Dạng lưới thẻ"
            @click="emit('update:layoutMode', 'grid')"
          >
            <UIcon name="i-heroicons-squares-2x2" class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
