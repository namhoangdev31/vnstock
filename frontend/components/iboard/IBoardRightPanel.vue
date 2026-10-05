<script setup lang="ts">
import type { TopMoverItem } from "~/client/stockService"
import type { SimulatedOrder } from "./types"

const props = defineProps<{
  isOpen: boolean
  activeTab: "market" | "order" | "orders_book"
  aiInsightText: string
  topGainers: TopMoverItem[]
  topLosers: TopMoverItem[]
  orderSide: "BUY" | "SELL"
  orderSymbol: string
  orderPrice: string
  orderQuantity: number
  orderType: "LO" | "ATO" | "ATC" | "MP"
  simulatedBalance: number
  simulatedOrders: SimulatedOrder[]
}>()

const emit = defineEmits<{
  (e: "update:isOpen", val: boolean): void
  (e: "update:activeTab", val: "market" | "order" | "orders_book"): void
  (e: "update:orderSide", val: "BUY" | "SELL"): void
  (e: "update:orderSymbol", val: string): void
  (e: "update:orderPrice", val: string): void
  (e: "update:orderQuantity", val: number): void
  (e: "update:orderType", val: "LO" | "ATO" | "ATC" | "MP"): void
  (e: "refresh-pulse"): void
  (e: "submit-order"): void
}>()

const selectMover = (symbol: string, price: string) => {
  emit("update:orderSymbol", symbol)
  emit("update:orderPrice", price)
  emit("update:activeTab", "order")
}
</script>

<template>
  <div
    class="bg-aave-inkwell border-l border-white/[0.08] flex flex-col shrink-0 transition-all duration-200"
    :class="isOpen ? 'w-80' : 'w-10'"
  >
    <!-- Thanh điều hướng Tab của Panel bên phải -->
    <div class="h-10 bg-aave-obsidian border-b border-white/[0.08] flex items-center justify-between px-2 shrink-0">
      <div v-if="isOpen" class="flex items-center gap-1 text-xs font-medium">
        <button
          type="button"
          class="px-2.5 py-1 rounded transition-colors whitespace-nowrap"
          :class="activeTab === 'market' ? 'bg-white/[0.1] text-white font-bold' : 'text-aave-graphite hover:text-white'"
          @click="emit('update:activeTab', 'market')"
        >
          Thị trường
        </button>
        <button
          type="button"
          class="px-2.5 py-1 rounded transition-colors whitespace-nowrap"
          :class="activeTab === 'order' ? 'bg-white/[0.1] text-white font-bold' : 'text-aave-graphite hover:text-white'"
          @click="emit('update:activeTab', 'order')"
        >
          Đặt lệnh
        </button>
        <button
          type="button"
          class="px-2.5 py-1 rounded transition-colors whitespace-nowrap"
          :class="activeTab === 'orders_book' ? 'bg-white/[0.1] text-white font-bold' : 'text-aave-graphite hover:text-white'"
          @click="emit('update:activeTab', 'orders_book')"
        >
          Sổ lệnh
        </button>
      </div>

      <button
        type="button"
        class="p-1 rounded hover:bg-white/[0.08] text-aave-graphite hover:text-white transition-colors"
        :title="isOpen ? 'Thu gọn thanh bên' : 'Mở rộng thanh bên'"
        @click="emit('update:isOpen', !isOpen)"
      >
        <UIcon :name="isOpen ? 'i-heroicons-chevron-double-right' : 'i-heroicons-chevron-double-left'" class="w-4 h-4" />
      </button>
    </div>

    <!-- Nội dung Tab -->
    <div v-if="isOpen" class="flex-1 overflow-y-auto p-3 space-y-3.5 scrollbar-thin">
      <!-- Tab 1: Xung lực thị trường & AI Insights -->
      <template v-if="activeTab === 'market'">
        <div class="p-3 rounded-xl bg-surface-abyss border border-white/[0.06] space-y-2.5">
          <div class="flex items-center gap-2">
            <div class="w-5 h-5 rounded-full bg-rose-600 flex items-center justify-center font-bold text-white text-3xs">
              AI
            </div>
            <span class="text-xs font-bold text-white">Trợ lý định lượng thị trường</span>
          </div>

          <p class="text-xs text-aave-ash leading-relaxed">
            {{ aiInsightText || 'Đang cập nhật phân tích định lượng thị trường...' }}
          </p>

          <button
            type="button"
            class="w-full py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors flex items-center justify-center gap-1.5"
            @click="emit('refresh-pulse')"
          >
            <span>Cập nhật nhận định AI</span>
            <UIcon name="i-heroicons-arrow-path" class="w-3.5 h-3.5" />
          </button>
        </div>

        <!-- Top tăng giá -->
        <div class="space-y-2">
          <div class="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
            <UIcon name="i-heroicons-arrow-trending-up" class="w-4 h-4" />
            <span>Top cổ phiếu tăng giá</span>
          </div>
          <div v-if="topGainers.length === 0" class="p-3 text-center text-xs text-aave-graphite font-mono">
            Đang tính toán top cổ phiếu tăng giá...
          </div>
          <div v-else class="space-y-1.5 max-h-48 overflow-y-auto scrollbar-thin pr-1">
            <div
              v-for="g in topGainers"
              :key="g.symbol"
              class="p-2 rounded bg-surface-abyss border border-white/[0.04] flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors"
              @click="selectMover(g.symbol, g.price)"
            >
              <div class="flex flex-col">
                <span class="font-bold text-xs text-white font-mono">{{ g.symbol }}</span>
                <span class="text-xs text-aave-graphite truncate max-w-[140px]">{{ g.name }}</span>
              </div>
              <div class="flex flex-col items-end font-mono">
                <span class="font-bold text-xs text-emerald-400">{{ g.price }}</span>
                <span class="text-xs text-emerald-400">{{ g.change }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Top giảm giá -->
        <div class="space-y-2">
          <div class="flex items-center gap-1.5 text-xs font-bold text-rose-500">
            <UIcon name="i-heroicons-arrow-trending-down" class="w-4 h-4" />
            <span>Top cổ phiếu giảm giá</span>
          </div>
          <div v-if="topLosers.length === 0" class="p-3 text-center text-xs text-aave-graphite font-mono">
            Đang tính toán top cổ phiếu giảm giá...
          </div>
          <div v-else class="space-y-1.5 max-h-48 overflow-y-auto scrollbar-thin pr-1">
            <div
              v-for="l in topLosers"
              :key="l.symbol"
              class="p-2 rounded bg-surface-abyss border border-white/[0.04] flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors"
              @click="selectMover(l.symbol, l.price)"
            >
              <div class="flex flex-col">
                <span class="font-bold text-xs text-white font-mono">{{ l.symbol }}</span>
                <span class="text-xs text-aave-graphite truncate max-w-[140px]">{{ l.name }}</span>
              </div>
              <div class="flex flex-col items-end font-mono">
                <span class="font-bold text-xs text-rose-500">{{ l.price }}</span>
                <span class="text-xs text-rose-500">{{ l.change }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Tab 2: Phiếu đặt lệnh mô phỏng Sandbox -->
      <template v-else-if="activeTab === 'order'">
        <div class="p-3.5 rounded-xl bg-surface-abyss border border-white/[0.06] space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-white uppercase tracking-wider">Phiếu Lệnh Mô Phỏng</span>
            <span class="text-xs px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-400 border border-emerald-800/40 font-mono">
              Sandbox 100%
            </span>
          </div>

          <div class="grid grid-cols-2 gap-1 p-0.5 bg-aave-obsidian rounded-lg border border-white/[0.08]">
            <button
              type="button"
              class="py-1.5 rounded-md text-xs font-bold transition-colors"
              :class="orderSide === 'BUY' ? 'bg-emerald-600 text-white' : 'text-aave-graphite hover:text-white'"
              @click="emit('update:orderSide', 'BUY')"
            >
              MUA
            </button>
            <button
              type="button"
              class="py-1.5 rounded-md text-xs font-bold transition-colors"
              :class="orderSide === 'SELL' ? 'bg-rose-600 text-white' : 'text-aave-graphite hover:text-white'"
              @click="emit('update:orderSide', 'SELL')"
            >
              BÁN
            </button>
          </div>

          <div>
            <label class="block text-xs font-medium text-aave-graphite mb-1">Mã chứng khoán</label>
            <input
              :value="orderSymbol"
              type="text"
              placeholder="Nhập mã CK..."
              class="w-full bg-aave-obsidian border border-white/[0.1] rounded px-3 py-1.5 text-xs text-white uppercase font-mono font-bold focus:outline-none focus:border-rose-500"
              @input="emit('update:orderSymbol', ($event.target as HTMLInputElement).value.toUpperCase())"
            >
          </div>

          <div>
            <label class="block text-xs font-medium text-aave-graphite mb-1">Loại lệnh</label>
            <div class="grid grid-cols-4 gap-1">
              <button
                v-for="ot in (['LO', 'ATO', 'ATC', 'MP'] as const)"
                :key="ot"
                type="button"
                class="py-1 rounded text-xs font-mono font-medium transition-colors"
                :class="orderType === ot ? 'bg-white/[0.15] text-white font-bold' : 'bg-aave-obsidian text-aave-graphite hover:text-white'"
                @click="emit('update:orderType', ot)"
              >
                {{ ot }}
              </button>
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-aave-graphite mb-1">Giá đặt</label>
            <input
              :value="orderPrice"
              type="text"
              placeholder="0.00"
              class="w-full bg-aave-obsidian border border-white/[0.1] rounded px-3 py-1.5 text-xs text-white font-mono font-bold focus:outline-none focus:border-rose-500"
              @input="emit('update:orderPrice', ($event.target as HTMLInputElement).value)"
            >
          </div>

          <div>
            <label class="block text-xs font-medium text-aave-graphite mb-1">Khối lượng</label>
            <input
              :value="orderQuantity"
              type="number"
              step="100"
              class="w-full bg-aave-obsidian border border-white/[0.1] rounded px-3 py-1.5 text-xs text-white font-mono font-bold focus:outline-none focus:border-rose-500"
              @input="emit('update:orderQuantity', Number(($event.target as HTMLInputElement).value))"
            >
          </div>

          <div class="p-2.5 rounded bg-aave-obsidian border border-white/[0.04] text-xs font-mono">
            <div class="flex items-center justify-between text-aave-graphite">
              <span>Sức mua mô phỏng:</span>
              <span class="text-white font-bold">{{ simulatedBalance.toLocaleString('en-US') }} VND</span>
            </div>
          </div>

          <button
            type="button"
            class="w-full py-2.5 rounded-lg text-white font-bold text-xs transition-colors flex items-center justify-center gap-1.5"
            :class="orderSide === 'BUY' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-rose-600 hover:bg-rose-500'"
            @click="emit('submit-order')"
          >
            <span>Xác nhận lệnh {{ orderSide === 'BUY' ? 'Mua' : 'Bán' }} mô phỏng</span>
          </button>
        </div>
      </template>

      <!-- Tab 3: Sổ lệnh mô phỏng -->
      <template v-else-if="activeTab === 'orders_book'">
        <div class="space-y-2">
          <div class="flex items-center justify-between text-xs font-medium text-aave-graphite pb-1 border-b border-white/[0.04]">
            <span>Sổ lệnh mô phỏng</span>
            <span class="font-mono">{{ simulatedOrders.length }} lệnh</span>
          </div>

          <div v-if="simulatedOrders.length === 0" class="p-6 text-center text-xs text-aave-graphite font-mono">
            Chưa có lệnh mô phỏng nào trong phiên
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="ord in simulatedOrders"
              :key="ord.id"
              class="p-2.5 rounded-lg bg-surface-abyss border border-white/[0.04] text-xs font-mono space-y-1.5"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-1.5">
                  <span class="font-bold text-white">{{ ord.symbol }}</span>
                  <span
                    class="px-1.5 py-0.2 rounded text-xs font-bold"
                    :class="ord.side === 'BUY' ? 'bg-emerald-950/60 text-emerald-400' : 'bg-rose-950/60 text-rose-500'"
                  >
                    {{ ord.side }}
                  </span>
                </div>
                <span class="text-emerald-400 text-xs font-medium">Đã khớp</span>
              </div>

              <div class="flex items-center justify-between text-aave-ash">
                <span>Giá: {{ ord.price }}</span>
                <span>KL: {{ ord.quantity }}</span>
              </div>

              <div class="flex items-center justify-between text-aave-graphite text-xs pt-1 border-t border-white/[0.04]">
                <span>{{ ord.id }}</span>
                <span>{{ ord.time }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
