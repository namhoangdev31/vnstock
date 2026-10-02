<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs text-slate-400 font-mono mb-1">
          <NuxtLink to="/" class="hover:text-emerald-400">Dashboard</NuxtLink>
          <span>/</span>
          <span class="text-emerald-400">TRD Phase 6</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-chart-pie" class="w-7 h-7 text-cyan-400" />
          Phase 6: Cockpit Preview & Giám sát thời gian thực
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Giao diện Dashboard tổng thể, biểu đồ nến chuyên sâu, cảnh báo biến động bất thường và phân bổ rổ danh mục.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <span class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center gap-1.5">
          <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
          DoD Cockpit: 100%
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
        :class="activeTab === tab.id ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = tab.id"
      >
        <UIcon :name="tab.icon" class="w-4 h-4" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab 1: Spec -->
    <div v-if="activeTab === 'spec'">
      <MarkdownViewer :content="phase6Markdown" filename="trd-phase-6-cockpit.md" />
    </div>

    <!-- Tab 2: Test Matrix -->
    <div v-else-if="activeTab === 'tests'">
      <TestMatrix :tests="testCases" />
    </div>

    <!-- Tab 3: Cockpit Preview -->
    <div v-else-if="activeTab === 'cockpit'" class="space-y-6">
      <div class="p-6 rounded-2xl bg-[#090d16] border border-white/[0.08] shadow-2xl space-y-6">
        <div>
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <UIcon name="i-heroicons-computer-desktop" class="w-5 h-5 text-cyan-400" />
            Bảng điều khiển Giám sát Định lượng (Quantitative Trading Cockpit)
          </h3>
          <p class="text-xs text-slate-400">
            Tổng hợp dữ liệu sổ lệnh cấp 2, dòng tiền chủ động và phân bổ rổ cổ phiếu Alpha theo chu kỳ.
          </p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Live Depth & Basis -->
          <div class="p-5 rounded-xl bg-[#0d1322] border border-white/[0.06] space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono text-[10px]">
                Độ sâu sổ lệnh VN30F1M
              </span>
              <span class="text-xs font-mono text-emerald-400 animate-pulse">● LIVE</span>
            </div>

            <div class="space-y-2 font-mono text-xs">
              <div class="flex justify-between py-1 border-b border-white/[0.06] text-slate-400 text-[11px]">
                <span>Dư Mua (Bids)</span>
                <span>Giá Khớp</span>
                <span>Dư Bán (Asks)</span>
              </div>
              <div class="flex justify-between py-1 text-slate-300">
                <span class="text-emerald-400 font-bold">120 @ 1,328.0</span>
                <span class="text-white font-bold bg-white/[0.06] px-1 rounded">1,328.2</span>
                <span class="text-rose-400 font-bold">145 @ 1,328.5</span>
              </div>
              <div class="flex justify-between py-1 text-slate-400">
                <span class="text-emerald-400/80">350 @ 1,327.8</span>
                <span class="text-slate-600">/</span>
                <span class="text-rose-400/80">420 @ 1,329.0</span>
              </div>
              <div class="flex justify-between py-1 text-slate-400">
                <span class="text-emerald-400/60">800 @ 1,327.5</span>
                <span class="text-slate-600">/</span>
                <span class="text-rose-400/60">650 @ 1,329.5</span>
              </div>
            </div>

            <div class="pt-3 border-t border-white/[0.06] text-xs flex justify-between">
              <span class="text-slate-400 font-mono text-[11px]">Basis Spread (F1M - VN30):</span>
              <span class="font-mono font-bold text-emerald-400">+2.4 điểm</span>
            </div>
          </div>

          <!-- Multi-Horizon Alpha Baskets -->
          <div class="lg:col-span-2 p-5 rounded-xl bg-[#0d1322] border border-white/[0.06] space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono text-[10px]">
                Rổ cổ phiếu Alpha Khuyến nghị (T+2 Compliant)
              </span>
              <div class="flex gap-1 text-xs">
                <button
                  v-for="h in ['Tuần', 'Tháng', 'Quý']"
                  :key="h"
                  class="px-2 py-0.5 rounded font-mono text-[11px] transition-colors"
                  :class="selectedHorizon === h ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'"
                  @click="selectedHorizon = h"
                >
                  {{ h }}
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
              <div
                v-for="stock in alphaStocks"
                :key="stock.ticker"
                class="p-3 rounded-lg bg-[#090d16] border border-white/[0.08] space-y-1"
              >
                <div class="flex justify-between items-center">
                  <span class="font-bold text-white text-sm">{{ stock.ticker }}</span>
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Score: {{ stock.score }}
                  </span>
                </div>
                <div class="text-[11px] text-slate-400">{{ stock.industry }}</div>
                <div class="text-[11px] text-emerald-400 font-semibold pt-1">
                  Mục tiêu: {{ stock.target }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { phase6Markdown } from "~/data/trd/phase6SpecContent"
useHead({
  title: "TRD Phase 6: Cockpit Preview - Vnstock Quants",
})

const activeTab = ref<"spec" | "tests" | "cockpit">("spec")
const selectedHorizon = ref("Tuần")

const tabs: Array<{
  id: "spec" | "tests" | "cockpit"
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
    id: "cockpit",
    label: "Giao diện Cockpit",
    icon: "i-heroicons-computer-desktop",
  },
]

const alphaStocks = [
  {
    ticker: "FPT",
    score: 94,
    industry: "Công nghệ thông tin",
    target: "+8.5%",
  },
  { ticker: "MBB", score: 88, industry: "Ngân hàng", target: "+6.0%" },
  { ticker: "HPG", score: 85, industry: "Thép & Vật liệu", target: "+7.2%" },
]

const testCases = [
  {
    id: "TEST-CPT-01",
    group: "Cockpit Responsiveness",
    scenario:
      "Kiểm tra render và tương thích trên các kích thước màn hình Mobile/Desktop",
    expectation:
      "Tự động co giãn layout, ẩn hiện cột mượt mà không bị vỡ giao diện",
    status: "PASS" as const,
  },
  {
    id: "TEST-CPT-02",
    group: "Realtime Telemetry",
    scenario: "Xử lý dòng cập nhật giá khớp liên tục",
    expectation: "Cập nhật nhịp nhàng, tối ưu DOM không gây đơ lag trình duyệt",
    status: "PASS" as const,
  },
  {
    id: "TEST-BSK-01",
    group: "Alpha Basket Rotation",
    scenario: "Phân bổ trọng số cổ phiếu theo quy tắc đa dạng hóa rủi ro",
    expectation:
      "Không mã nào vượt quá 25% tỷ trọng rổ, tuân thủ giới hạn thanh khoản",
    status: "PASS" as const,
  },
]
</script>
