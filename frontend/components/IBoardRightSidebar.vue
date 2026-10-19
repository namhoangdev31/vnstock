<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import type {
  IBoardMarketPulse,
  PaperOrder,
  TopMoverItem,
} from "~/types/iboard"

interface Props {
  collapsed?: boolean
  selectedSymbol?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  collapsed: false,
  selectedSymbol: "VN30F1M",
})

const emit = defineEmits<{
  "update:collapsed": [value: boolean]
  "select-symbol": [symbol: string]
}>()

const activeTab = ref<"market" | "order" | "book">("market")
const isCollapsed = computed({
  get: () => props.collapsed,
  set: (val: boolean) => emit("update:collapsed", val),
})

const pulseData = ref<IBoardMarketPulse | null>(null)
const isLoadingPulse = ref<boolean>(false)

const fetchMarketPulse = async () => {
  isLoadingPulse.value = true
  try {
    const res = await $fetch<IBoardMarketPulse>(
      "/api/v1/stock/iboard/market-pulse",
    )
    pulseData.value = res
  } catch (err) {
    console.debug("Lỗi tải market pulse:", err)
  } finally {
    isLoadingPulse.value = false
  }
}

onMounted(() => {
  fetchMarketPulse()
})

// Đặt Lệnh Mô Phỏng (Paper Trading - Rule 1 & Rule 2 Compliant)
const orderSide = ref<"BUY" | "SELL">("BUY")
const orderSymbol = ref<string>(props.selectedSymbol || "VN30F1M")
const orderType = ref<"LO" | "MP" | "ATO" | "ATC">("LO")
const orderPrice = ref<number>(100.0)
const orderVolume = ref<number>(100)
const orderSuccessMessage = ref<string | null>(null)

const paperOrders = ref<PaperOrder[]>([
  {
    id: "SIM-001",
    symbol: "MSB",
    side: "BUY",
    order_type: "LO",
    price: 14.65,
    volume: 1000,
    status: "FILLED",
    created_at: "14:45:02",
  },
  {
    id: "SIM-002",
    symbol: "FPT",
    side: "BUY",
    order_type: "LO",
    price: 58.0,
    volume: 500,
    status: "PENDING",
    created_at: "14:46:15",
  },
])

const estimatedValue = computed(() => {
  return orderPrice.value * orderVolume.value * 1000
})

const handlePlacePaperOrder = () => {
  if (!orderSymbol.value || orderVolume.value <= 0) return

  const newOrder: PaperOrder = {
    id: `SIM-${Math.floor(1000 + Math.random() * 9000)}`,
    symbol: orderSymbol.value.toUpperCase().trim(),
    side: orderSide.value,
    order_type: orderType.value,
    price: orderPrice.value,
    volume: orderVolume.value,
    status: "FILLED",
    created_at: new Date().toLocaleTimeString("vi-VN", { hour12: false }),
  }

  paperOrders.value.unshift(newOrder)
  orderSuccessMessage.value = `Đã khớp lệnh mô phỏng ${newOrder.side} ${newOrder.volume} ${newOrder.symbol} giá ${newOrder.price}`
  setTimeout(() => {
    orderSuccessMessage.value = null
  }, 4000)
}

const handleSelectMover = (sym: string) => {
  emit("select-symbol", sym)
}
</script>

<template>
  <!-- Khi Thu Gọn (Ảnh 2): Cột Icon Dọc Hẹp ~40px -->
  <aside
    v-if="isCollapsed"
    class="w-11 bg-tv-surface border-l border-tv-border flex flex-col items-center py-3 gap-4 shrink-0 select-none z-10 transition-all duration-300"
  >
    <button
      type="button"
      class="p-1.5 rounded text-tv-secondary hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
      title="Mở rộng bảng tiện ích"
      aria-label="Mở rộng bảng tiện ích"
      @click="isCollapsed = false"
    >
      <UIcon name="i-heroicons-chevron-double-left" class="w-5 h-5" />
    </button>

    <div class="w-6 h-px bg-tv-border" />

    <button
      type="button"
      class="p-2 rounded transition-colors cursor-pointer flex flex-col items-center gap-1"
      :class="activeTab === 'market' ? 'text-aave-violet bg-white/[0.06]' : 'text-tv-secondary hover:text-white'"
      title="Thị trường & Top biến động"
      aria-label="Thị trường"
      @click="() => { activeTab = 'market'; isCollapsed = false }"
    >
      <UIcon name="i-heroicons-chart-bar" class="w-5 h-5" />
      <span class="text-[9px] font-medium leading-none">Thị trường</span>
    </button>

    <button
      type="button"
      class="p-2 rounded transition-colors cursor-pointer flex flex-col items-center gap-1"
      :class="activeTab === 'order' ? 'text-aave-violet bg-white/[0.06]' : 'text-tv-secondary hover:text-white'"
      title="Đặt lệnh mô phỏng"
      aria-label="Đặt lệnh"
      @click="() => { activeTab = 'order'; isCollapsed = false }"
    >
      <UIcon name="i-heroicons-arrow-trending-up" class="w-5 h-5" />
      <span class="text-[9px] font-medium leading-none">Đặt lệnh</span>
    </button>

    <button
      type="button"
      class="p-2 rounded transition-colors cursor-pointer flex flex-col items-center gap-1"
      :class="activeTab === 'book' ? 'text-aave-violet bg-white/[0.06]' : 'text-tv-secondary hover:text-white'"
      title="Sổ lệnh mô phỏng"
      aria-label="Sổ lệnh"
      @click="() => { activeTab = 'book'; isCollapsed = false }"
    >
      <UIcon name="i-heroicons-queue-list" class="w-5 h-5" />
      <span class="text-[9px] font-medium leading-none">Sổ lệnh</span>
    </button>
  </aside>

  <!-- Khi Mở Rộng (Ảnh 1): Bảng Tiện Ích Rộng ~300px -->
  <aside
    v-else
    class="w-72 xl:w-80 bg-tv-surface border-l border-tv-border flex flex-col shrink-0 select-none overflow-hidden z-10 transition-all duration-300"
  >
    <!-- Thanh Tab Tiêu Đề & Nút Thu Gọn -->
    <div class="flex items-center justify-between px-3 py-2 bg-tv-card border-b border-tv-border">
      <div class="flex items-center gap-1 text-xs font-semibold">
        <button
          type="button"
          class="px-2.5 py-1.5 rounded transition-colors cursor-pointer flex items-center gap-1"
          :class="
            activeTab === 'market'
              ? 'text-white bg-white/[0.1] font-bold'
              : 'text-tv-secondary hover:text-white'
          "
          @click="activeTab = 'market'"
        >
          <UIcon name="i-heroicons-chart-bar" class="w-4 h-4 text-market-advance" />
          <span>Thị trường</span>
        </button>

        <button
          type="button"
          class="px-2.5 py-1.5 rounded transition-colors cursor-pointer flex items-center gap-1"
          :class="
            activeTab === 'order'
              ? 'text-white bg-white/[0.1] font-bold'
              : 'text-tv-secondary hover:text-white'
          "
          @click="activeTab = 'order'"
        >
          <UIcon name="i-heroicons-arrow-trending-up" class="w-4 h-4" />
          <span>Đặt lệnh</span>
        </button>

        <button
          type="button"
          class="px-2.5 py-1.5 rounded transition-colors cursor-pointer flex items-center gap-1"
          :class="
            activeTab === 'book'
              ? 'text-white bg-white/[0.1] font-bold'
              : 'text-tv-secondary hover:text-white'
          "
          @click="activeTab = 'book'"
        >
          <UIcon name="i-heroicons-queue-list" class="w-4 h-4" />
          <span>Sổ lệnh</span>
        </button>
      </div>

      <button
        type="button"
        class="p-1 rounded text-tv-secondary hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer"
        title="Thu gọn bảng tiện ích"
        aria-label="Thu gọn"
        @click="isCollapsed = true"
      >
        <UIcon name="i-heroicons-chevron-double-right" class="w-4 h-4" />
      </button>
    </div>

    <!-- NỘI DUNG TAB THỊ TRƯỜNG (Ảnh 1) -->
    <div v-if="activeTab === 'market'" class="flex-1 overflow-y-auto flex flex-col p-3 gap-4 text-xs font-mono">
      <!-- Thẻ Trợ Lý AI ENSA -->
      <div class="rounded-xl p-3 bg-tv-card/80 border border-tv-border flex flex-col gap-2.5 shadow-sm">
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 rounded-full bg-aave-violet/20 border border-aave-violet/40 flex items-center justify-center shrink-0">
            <UIcon name="i-heroicons-sparkles" class="w-3.5 h-3.5 text-aave-violet" />
          </div>
          <span class="text-xs font-bold font-sans text-white">ENSA Trợ lý AI nói gì?</span>
        </div>

        <p class="text-[11px] text-tv-primary leading-relaxed font-sans">
          {{ pulseData?.ai_insight || "Dòng tiền tích cực luân chuyển vào nhóm Dịch vụ tài chính và Ngân hàng. Độ rộng thị trường duy trì xu hướng cân bằng." }}
        </p>

        <div class="flex items-center justify-between pt-1 border-t border-tv-border/50 text-[11px] font-sans">
          <span class="text-tv-secondary text-[10px]">Hỏi đáp dữ liệu</span>
          <button
            type="button"
            class="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-rose-600 hover:bg-rose-500 text-white transition-colors cursor-pointer"
          >
            Hỏi ngay
          </button>
        </div>
      </div>

      <!-- Top Cổ Phiếu Tăng Giá -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-1.5 text-market-advance font-semibold text-xs">
          <UIcon name="i-heroicons-arrow-trending-up" class="w-4 h-4" />
          <span>Top cổ phiếu tăng giá</span>
        </div>

        <div class="divide-y divide-tv-border/30 rounded-lg bg-tv-card/40 border border-tv-border overflow-hidden">
          <div
            v-for="item in pulseData?.top_gainers || []"
            :key="item.symbol"
            class="flex items-center justify-between px-2.5 py-2 hover:bg-white/[0.04] transition-colors cursor-pointer"
            @click="handleSelectMover(item.symbol)"
          >
            <div class="flex items-center gap-2 min-w-0">
              <span class="w-6 h-6 rounded-full bg-tv-card border border-tv-border flex items-center justify-center text-[10px] font-bold text-white shrink-0">
                {{ item.symbol.slice(0, 2) }}
              </span>
              <div class="flex flex-col min-w-0">
                <span class="text-white font-bold text-xs">{{ item.symbol }}</span>
                <span class="text-[10px] text-tv-secondary truncate max-w-[120px]">{{ item.name }}</span>
              </div>
            </div>

            <div class="flex flex-col items-end tabular-nums">
              <span class="text-market-advance font-bold text-xs">{{ item.price }}</span>
              <span class="text-market-advance text-[10px] font-medium">{{ item.change }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Top Cổ Phiếu Giảm Giá -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-1.5 text-market-decline font-semibold text-xs">
          <UIcon name="i-heroicons-arrow-trending-down" class="w-4 h-4" />
          <span>Top cổ phiếu giảm giá</span>
        </div>

        <div class="divide-y divide-tv-border/30 rounded-lg bg-tv-card/40 border border-tv-border overflow-hidden">
          <div
            v-for="item in pulseData?.top_losers || []"
            :key="item.symbol"
            class="flex items-center justify-between px-2.5 py-2 hover:bg-white/[0.04] transition-colors cursor-pointer"
            @click="handleSelectMover(item.symbol)"
          >
            <div class="flex items-center gap-2 min-w-0">
              <span class="w-6 h-6 rounded-full bg-tv-card border border-tv-border flex items-center justify-center text-[10px] font-bold text-white shrink-0">
                {{ item.symbol.slice(0, 2) }}
              </span>
              <div class="flex flex-col min-w-0">
                <span class="text-white font-bold text-xs">{{ item.symbol }}</span>
                <span class="text-[10px] text-tv-secondary truncate max-w-[120px]">{{ item.name }}</span>
              </div>
            </div>

            <div class="flex flex-col items-end tabular-nums">
              <span class="text-market-decline font-bold text-xs">{{ item.price }}</span>
              <span class="text-market-decline text-[10px] font-medium">{{ item.change }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Top Khối Lượng Giao Dịch -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-1.5 text-tv-gold font-semibold text-xs">
          <UIcon name="i-heroicons-bars-3-bottom-left" class="w-4 h-4" />
          <span>Top khối lượng giao dịch</span>
        </div>

        <div class="divide-y divide-tv-border/30 rounded-lg bg-tv-card/40 border border-tv-border overflow-hidden">
          <div
            v-for="item in pulseData?.top_volume || []"
            :key="item.symbol"
            class="flex items-center justify-between px-2.5 py-2 hover:bg-white/[0.04] transition-colors cursor-pointer"
            @click="handleSelectMover(item.symbol)"
          >
            <div class="flex items-center gap-2 min-w-0">
              <span class="w-6 h-6 rounded-full bg-tv-card border border-tv-border flex items-center justify-center text-[10px] font-bold text-white shrink-0">
                {{ item.symbol.slice(0, 2) }}
              </span>
              <div class="flex flex-col min-w-0">
                <span class="text-white font-bold text-xs">{{ item.symbol }}</span>
                <span class="text-[10px] text-tv-secondary truncate max-w-[120px]">{{ item.name }}</span>
              </div>
            </div>

            <div class="flex flex-col items-end tabular-nums">
              <span class="text-white font-bold text-xs">{{ item.price }}</span>
              <span class="text-[10px] text-tv-secondary">KL: {{ item.volume }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- NỘI DUNG TAB ĐẶT LỆNH MÔ PHỎNG (Paper Trading Strictly) -->
    <div v-else-if="activeTab === 'order'" class="flex-1 overflow-y-auto flex flex-col p-3 gap-3 font-mono text-xs">
      <div class="flex items-center justify-between p-2 rounded-lg bg-tv-card border border-tv-border">
        <span class="text-tv-secondary text-[11px]">Chế độ:</span>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-aave-violet/20 border border-aave-violet/40 text-aave-violet">
          Giả lập mô phỏng
        </span>
      </div>

      <!-- Tab Mua / Bán -->
      <div class="grid grid-cols-2 p-1 rounded-lg bg-tv-card border border-tv-border">
        <button
          type="button"
          class="py-1.5 rounded font-bold transition-colors cursor-pointer text-center"
          :class="orderSide === 'BUY' ? 'bg-market-advance text-black' : 'text-tv-secondary hover:text-white'"
          @click="orderSide = 'BUY'"
        >
          MUA
        </button>
        <button
          type="button"
          class="py-1.5 rounded font-bold transition-colors cursor-pointer text-center"
          :class="orderSide === 'SELL' ? 'bg-market-decline text-white' : 'text-tv-secondary hover:text-white'"
          @click="orderSide = 'SELL'"
        >
          BÁN
        </button>
      </div>

      <!-- Form Nhập -->
      <div class="flex flex-col gap-2.5">
        <div class="flex flex-col gap-1">
          <label class="text-tv-secondary text-[11px]">Mã cổ phiếu</label>
          <input
            v-model="orderSymbol"
            type="text"
            class="px-3 py-1.5 rounded bg-tv-card border border-tv-border text-white uppercase font-bold focus:border-aave-violet outline-none"
          />
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-tv-secondary text-[11px]">Loại lệnh</label>
          <div class="grid grid-cols-4 gap-1">
            <button
              v-for="t in ['LO', 'MP', 'ATO', 'ATC'] as const"
              :key="t"
              type="button"
              class="py-1 rounded text-center font-semibold border transition-colors cursor-pointer"
              :class="orderType === t ? 'border-aave-violet text-white bg-aave-violet/20' : 'border-tv-border text-tv-secondary hover:text-white bg-tv-card'"
              @click="orderType = t"
            >
              {{ t }}
            </button>
          </div>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-tv-secondary text-[11px]">Giá đặt</label>
          <input
            v-model.number="orderPrice"
            type="number"
            step="0.05"
            class="px-3 py-1.5 rounded bg-tv-card border border-tv-border text-white font-bold tabular-nums focus:border-aave-violet outline-none"
          />
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-tv-secondary text-[11px]">Khối lượng</label>
          <input
            v-model.number="orderVolume"
            type="number"
            step="100"
            class="px-3 py-1.5 rounded bg-tv-card border border-tv-border text-white font-bold tabular-nums focus:border-aave-violet outline-none"
          />
        </div>

        <div class="flex items-center justify-between text-xs py-1 text-tv-secondary">
          <span>Giá trị ước tính:</span>
          <span class="text-white font-bold tabular-nums">{{ estimatedValue.toLocaleString('en-US') }} đ</span>
        </div>

        <button
          type="button"
          class="w-full py-2.5 rounded-lg font-bold text-sm transition-all cursor-pointer shadow-md mt-1"
          :class="orderSide === 'BUY' ? 'bg-market-advance hover:bg-market-advance/80 text-black' : 'bg-market-decline hover:bg-market-decline/80 text-white'"
          @click="handlePlacePaperOrder"
        >
          Xác nhận {{ orderSide === 'BUY' ? 'MUA' : 'BÁN' }} (Mô phỏng)
        </button>

        <div
          v-if="orderSuccessMessage"
          class="p-2 rounded bg-market-advance/10 border border-market-advance/30 text-market-advance text-[11px] text-center"
        >
          {{ orderSuccessMessage }}
        </div>

        <div class="p-2.5 rounded bg-white/[0.03] border border-white/[0.06] text-[10px] text-tv-secondary font-sans leading-relaxed">
          Thử nghiệm giả lập mô phỏng phục vụ nghiên cứu thuật toán. Không kết nối tài khoản thực và không sử dụng vốn thực tế theo Quy định Hệ thống.
        </div>
      </div>
    </div>

    <!-- NỘI DUNG TAB SỔ LỆNH MÔ PHỎNG -->
    <div v-else-if="activeTab === 'book'" class="flex-1 overflow-y-auto flex flex-col p-3 gap-2 font-mono text-xs">
      <div class="flex items-center justify-between pb-1 border-b border-tv-border text-tv-secondary text-[11px]">
        <span>Sổ lệnh trong phiên</span>
        <span>{{ paperOrders.length }} lệnh</span>
      </div>

      <div class="flex flex-col gap-2 mt-1">
        <div
          v-for="ord in paperOrders"
          :key="ord.id"
          class="flex flex-col p-2.5 rounded-lg bg-tv-card/60 border border-tv-border gap-1"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1.5">
              <span class="text-white font-bold">{{ ord.symbol }}</span>
              <span
                class="px-1.5 py-0.2 rounded text-[9px] font-bold"
                :class="ord.side === 'BUY' ? 'bg-market-advance/20 text-market-advance' : 'bg-market-decline/20 text-market-decline'"
              >
                {{ ord.side === 'BUY' ? 'MUA' : 'BÁN' }}
              </span>
            </div>
            <span class="text-tv-secondary text-[10px]">{{ ord.created_at }}</span>
          </div>

          <div class="flex items-center justify-between text-[11px] tabular-nums mt-0.5">
            <span class="text-tv-secondary">
              KL: <span class="text-white font-semibold">{{ ord.volume.toLocaleString('en-US') }}</span> @ {{ ord.price.toFixed(2) }}
            </span>
            <span
              class="px-1.5 py-0.2 rounded text-[10px] font-medium"
              :class="ord.status === 'FILLED' ? 'text-market-advance bg-market-advance/10' : 'text-tv-gold bg-tv-gold/10'"
            >
              {{ ord.status === 'FILLED' ? 'Đã khớp' : 'Chờ khớp' }}
            </span>
          </div>
        </div>

        <div v-if="!paperOrders.length" class="p-6 text-center text-tv-secondary text-xs">
          Chưa có lệnh nào được đặt trong phiên
        </div>
      </div>
    </div>
  </aside>
</template>
