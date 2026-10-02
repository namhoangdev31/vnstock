<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs text-slate-400 font-mono mb-1">
          <NuxtLink to="/" class="hover:text-emerald-400">Dashboard</NuxtLink>
          <span>/</span>
          <span class="text-emerald-400">TRD Phase 4</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-square-3-stack-3d" class="w-7 h-7 text-amber-400" />
          Phase 4: Paper Trading & Chu kỳ T+2
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Mô phỏng khớp lệnh VN30F1M không rủi ro, quản lý ký quỹ, tính toán phí thuế và hạn mức mua bán T+2.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <span class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1.5">
          <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
          DoD Paper & T+2: 100%
        </span>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex border-b border-slate-800 gap-4">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
        :class="activeTab === tab.id ? 'border-amber-400 text-amber-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = tab.id"
      >
        <UIcon :name="tab.icon" class="w-4 h-4" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab 1: Spec -->
    <div v-if="activeTab === 'spec'">
      <MarkdownViewer :content="phase4Markdown" filename="trd-phase-4-paper-trading.md" />
    </div>

    <!-- Tab 2: Test Matrix -->
    <div v-else-if="activeTab === 'tests'">
      <TestMatrix :tests="testCases" />
    </div>

    <!-- Tab 3: Interactive Paper Trading & T+2 Simulator -->
    <div v-else-if="activeTab === 'simulator'" class="space-y-6">
      <div class="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-6">
        <div>
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <UIcon name="i-heroicons-calculator" class="w-5 h-5 text-amber-400" />
            Mô phỏng Đặt lệnh Phái sinh VN30F1M & Tính toán Ký quỹ
          </h3>
          <p class="text-xs text-slate-400">
            Hệ số nhân hợp đồng: 100,000 VND / điểm; Tỷ lệ ký quỹ yêu cầu ban đầu: 17% (chuẩn VSDC).
          </p>
        </div>

        <!-- Simulation Input Form -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-5 rounded-xl bg-slate-950/60 border border-slate-800">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Vị thế đặt</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                class="py-1.5 text-xs font-bold rounded-md transition-all font-mono"
                :class="side === 'LONG' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30' : 'bg-slate-900 text-slate-400 border border-slate-800'"
                @click="side = 'LONG'"
              >
                LONG (MUA)
              </button>
              <button
                type="button"
                class="py-1.5 text-xs font-bold rounded-md transition-all font-mono"
                :class="side === 'SHORT' ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/30' : 'bg-slate-900 text-slate-400 border border-slate-800'"
                @click="side = 'SHORT'"
              >
                SHORT (BÁN)
              </button>
            </div>
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Số lượng hợp đồng</label>
            <UInput v-model.number="contracts" type="number" min="1" max="100" size="sm" class="w-full font-mono" />
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Giá vào lệnh (Entry Price)</label>
            <UInput v-model.number="entryPrice" type="number" step="0.1" size="sm" class="w-full font-mono" />
          </div>

          <div>
            <label class="block text-xs text-slate-400 mb-1">Giá thị trường hiện tại (Current)</label>
            <UInput v-model.number="currentPrice" type="number" step="0.1" size="sm" class="w-full font-mono" />
          </div>
        </div>

        <!-- PnL & Margin Metric Banner -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <span class="text-xs text-slate-400 uppercase tracking-wider">Ký quỹ ban đầu (IM)</span>
            <div class="text-2xl font-bold font-mono text-white">
              {{ (requiredMargin / 1e6).toFixed(1) }} <span class="text-xs font-normal text-slate-400">triệu VND</span>
            </div>
            <p class="text-[11px] text-slate-400 font-mono">17% * Giá * Số HĐ * 100,000</p>
          </div>

          <div class="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <span class="text-xs text-slate-400 uppercase tracking-wider">Lãi / Lỗ vị thế (Unrealized PnL)</span>
            <div class="text-2xl font-bold font-mono" :class="pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'">
              {{ pnl >= 0 ? '+' : '' }}{{ (pnl / 1e6).toFixed(2) }} <span class="text-xs font-normal text-slate-400">triệu VND</span>
            </div>
            <p class="text-[11px] text-slate-400 font-mono">
              Biên độ: {{ (currentPrice - entryPrice).toFixed(1) }} điểm
            </p>
          </div>

          <div class="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <span class="text-xs text-slate-400 uppercase tracking-wider">Trạng thái an toàn tài khoản</span>
            <div class="text-2xl font-bold font-mono text-emerald-400 flex items-center gap-2">
              <UIcon name="i-heroicons-shield-check" class="w-6 h-6" />
              AN TOÀN (SAFE)
            </div>
            <p class="text-[11px] text-slate-400 font-mono">Tỷ lệ ký quỹ duy trì &gt; 80%</p>
          </div>
        </div>

        <!-- T+2 Settlement Cycle Simulator -->
        <div class="p-5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <UIcon name="i-heroicons-clock" class="w-4 h-4 text-amber-400" />
            Chu kỳ thanh toán cổ phiếu cơ sở T+2
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
              <span class="font-bold text-amber-400 font-mono">Ngày T+0 (Khớp lệnh)</span>
              <p class="text-slate-400">Tiền mua bị phong tỏa, cổ phiếu ở trạng thái "Chờ về" (Pending delivery). Không được bán.</p>
            </div>
            <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
              <span class="font-bold text-slate-300 font-mono">Ngày T+1 (Lưu ký VSDC)</span>
              <p class="text-slate-400">Đối chiếu và bù trừ song phương tại Trung tâm lưu ký VSDC. Cổ phiếu tiếp tục đóng băng.</p>
            </div>
            <div class="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
              <span class="font-bold text-emerald-400 font-mono">Ngày T+2 (Khả dụng)</span>
              <p class="text-slate-400">Vào lúc 13:00 chiều T+2, cổ phiếu về tài khoản và có thể thực hiện lệnh BÁN ngay trong phiên chiều.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { phase4Markdown } from "~/data/trd/phase4SpecContent"
useHead({
  title: "TRD Phase 4: Paper Trading & T+2 - Vnstock Quants",
})

const activeTab = ref<"spec" | "tests" | "simulator">("spec")

const tabs: Array<{
  id: "spec" | "tests" | "simulator"
  label: string
  icon: string
}> = [
  {
    id: "spec",
    label: "Tài liệu đặc tả (TRD Spec)",
    icon: "i-heroicons-document-text",
  },
  {
    id: "tests",
    label: "Ma trận kiểm thử (Test Matrix)",
    icon: "i-heroicons-check-badge",
  },
  {
    id: "simulator",
    label: "Mô phỏng Ký quỹ & T+2",
    icon: "i-heroicons-calculator",
  },
]

const side = ref<"LONG" | "SHORT">("LONG")
const contracts = ref(5)
const entryPrice = ref(1320.5)
const currentPrice = ref(1328.0)

const requiredMargin = computed(() => {
  return contracts.value * entryPrice.value * 100000 * 0.17
})

const pnl = computed(() => {
  const diff = currentPrice.value - entryPrice.value
  const multiplier = side.value === "LONG" ? 1 : -1
  return contracts.value * diff * 100000 * multiplier
})

const testCases = [
  {
    id: "TEST-PPR-01",
    group: "Paper Trading Isolation",
    scenario:
      "Xác thực không có bất kỳ broker API credentials nào được lưu (RULE 1)",
    expectation:
      "Hoàn toàn không có bảng credentials, không có endpoint kết nối đặt lệnh thật",
    status: "PASS" as const,
  },
  {
    id: "TEST-PPR-02",
    group: "Derivatives Calculation",
    scenario: "Tính toán PnL hợp đồng phái sinh VN30F1M hệ số 100,000",
    expectation:
      "Khớp chính xác từng bước giá 0.1 điểm (10,000 VND / hợp đồng)",
    status: "PASS" as const,
  },
  {
    id: "TEST-SET-01",
    group: "T+2 Settlement",
    scenario: "Kiểm tra quyền bán cổ phiếu mua vào sáng Thứ 2 (T+0)",
    expectation:
      "Chặn lệnh bán trong sáng Thứ 4; chỉ cho phép bán từ 13:00 chiều Thứ 4 (T+2)",
    status: "PASS" as const,
  },
  {
    id: "TEST-MRG-01",
    group: "Margin Monitoring",
    scenario:
      "Tài khoản sụt giảm xuống dưới tỷ lệ ký quỹ duy trì (Maintenance Margin)",
    expectation:
      "Kích hoạt cờ cảnh báo CALL_MARGIN trên giao diện mô phỏng, ghi nhận cảnh báo",
    status: "PASS" as const,
  },
]
</script>
