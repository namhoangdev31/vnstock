<template>
  <div class="space-y-6">

    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs text-slate-400 font-mono mb-1">
          <NuxtLink to="/admin" class="hover:text-emerald-400">Dashboard</NuxtLink>
          <span>/</span>
          <span class="text-emerald-400">TRD Phase 2</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-cpu-chip" class="w-7 h-7 text-teal-400" />
          Phase 2: Tri-Engine Architecture
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Tích hợp 3 Engine: Kỹ thuật Price Action, Dòng tiền khối ngoại & Tự doanh, và Machine Learning xác suất.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <span class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-teal-500/10 text-teal-400 border border-teal-500/20 flex items-center gap-1.5">
          <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
          DoD Tri-Engine: 100%
        </span>
      </div>
    </div>

    <div class="flex border-b border-slate-800 gap-4">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
        :class="activeTab === tab.id ? 'border-teal-400 text-teal-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = tab.id"
      >
        <UIcon :name="tab.icon" class="w-4 h-4" />
        {{ tab.label }}
      </button>
    </div>

    <div v-if="activeTab === 'spec'">
      <MarkdownViewer :content="phase2Markdown" filename="trd-phase-2-tri-engine.md" />
    </div>

    <div v-else-if="activeTab === 'tests'">
      <TestMatrix :tests="testCases" />
    </div>

    <div v-else-if="activeTab === 'simulator'" class="space-y-6">
      <div class="p-6 rounded-2xl bg-surface-abyss border border-white/[0.08] shadow-2xl space-y-6">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-base font-bold text-white flex items-center gap-2">
              <UIcon name="i-heroicons-adjustments-horizontal" class="w-5 h-5 text-teal-400" />
              Mô phỏng phối hợp Ensemble Tri-Engine
            </h3>
            <p class="text-xs text-slate-400">
              Điều chỉnh trọng số (Weights) và điểm số (Scores) của 3 Engine để tính toán tín hiệu vị thế VN30F1M
            </p>
          </div>
          <button
            type="button"
            class="text-xs text-slate-400 hover:text-teal-400 font-mono underline"
            @click="resetEngineDefaults"
          >
            Khôi phục mặc định
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

          <div class="p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-emerald-400">Engine 1: Technical</span>
              <span class="text-xs font-mono font-bold text-slate-300">W: {{ (w1 * 100).toFixed(0) }}%</span>
            </div>
            <div class="space-y-3">
              <div>
                <label class="text-[11px] text-slate-400 flex justify-between">
                  <span>Trọng số</span>
                  <span class="font-mono text-emerald-400">{{ w1 }}</span>
                </label>
                <input
                  v-model.number="w1"
                  type="range"
                  min="0.1"
                  max="0.8"
                  step="0.05"
                  class="w-full accent-emerald-500"
                >
              </div>
              <div>
                <label class="text-[11px] text-slate-400 flex justify-between">
                  <div class="flex items-center gap-1"><span>Điểm tín hiệu</span><UTooltip text="Thang đo -100 đến +100"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div>
                  <span class="font-mono font-bold" :class="s1 >= 0 ? 'text-emerald-400' : 'text-rose-400'">{{ s1 }}</span>
                </label>
                <input
                  v-model.number="s1"
                  type="range"
                  min="-100"
                  max="100"
                  step="5"
                  class="w-full accent-emerald-500"
                >
              </div>
            </div>
            <p class="text-[11px] text-slate-400">
              RSI, MACD, VWAP, Order matching aggression & tick delta.
            </p>
          </div>

          <div class="p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-blue-400">Engine 2: Flow & Liquidity</span>
              <span class="text-xs font-mono font-bold text-slate-300">W: {{ (w2 * 100).toFixed(0) }}%</span>
            </div>
            <div class="space-y-3">
              <div>
                <label class="text-[11px] text-slate-400 flex justify-between">
                  <span>Trọng số</span>
                  <span class="font-mono text-blue-400">{{ w2 }}</span>
                </label>
                <input
                  v-model.number="w2"
                  type="range"
                  min="0.1"
                  max="0.8"
                  step="0.05"
                  class="w-full accent-blue-500"
                >
              </div>
              <div>
                <label class="text-[11px] text-slate-400 flex justify-between">
                  <div class="flex items-center gap-1"><span>Điểm tín hiệu</span><UTooltip text="Thang đo -100 đến +100"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div>
                  <span class="font-mono font-bold" :class="s2 >= 0 ? 'text-blue-400' : 'text-rose-400'">{{ s2 }}</span>
                </label>
                <input
                  v-model.number="s2"
                  type="range"
                  min="-100"
                  max="100"
                  step="5"
                  class="w-full accent-blue-500"
                >
              </div>
            </div>
            <p class="text-[11px] text-slate-400">
              Khối ngoại (Foreign net buy/sell), Tự doanh và áp lực thanh khoản T+2.
            </p>
          </div>

          <div class="p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold uppercase tracking-wider text-purple-400">Engine 3: Quant ML</span>
              <span class="text-xs font-mono font-bold text-slate-300">W: {{ (w3 * 100).toFixed(0) }}%</span>
            </div>
            <div class="space-y-3">
              <div>
                <label class="text-[11px] text-slate-400 flex justify-between">
                  <span>Trọng số</span>
                  <span class="font-mono text-purple-400">{{ w3 }}</span>
                </label>
                <input
                  v-model.number="w3"
                  type="range"
                  min="0.1"
                  max="0.8"
                  step="0.05"
                  class="w-full accent-purple-500"
                >
              </div>
              <div>
                <label class="text-[11px] text-slate-400 flex justify-between">
                  <div class="flex items-center gap-1"><span>Điểm tín hiệu</span><UTooltip text="Thang đo -100 đến +100"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div>
                  <span class="font-mono font-bold" :class="s3 >= 0 ? 'text-purple-400' : 'text-rose-400'">{{ s3 }}</span>
                </label>
                <input
                  v-model.number="s3"
                  type="range"
                  min="-100"
                  max="100"
                  step="5"
                  class="w-full accent-purple-500"
                >
              </div>
            </div>
            <p class="text-[11px] text-slate-400">
              Basis spread arbitrage, độ lệch VN30F1M vs VN30 và xác suất regime.
            </p>
          </div>
        </div>

        <div class="p-6 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4" :class="ensembleBannerClass">
          <div class="space-y-1">
            <span class="text-[11px] uppercase tracking-wider font-mono font-bold text-slate-400">
              Kết quả hợp nhất (Ensemble Decision)
            </span>
            <div class="text-3xl font-extrabold font-mono flex items-center gap-3">
              <span :class="finalSignalClass">{{ finalDecision }}</span>
              <span class="text-sm font-normal text-slate-400">
                (Score: {{ finalScore.toFixed(1) }} / 100)
              </span>
            </div>
            <p class="text-xs text-slate-300">
              Ngưỡng kích hoạt: Score &ge; +25 (Mở vị thế LONG), Score &le; -25 (Mở vị thế SHORT), Còn lại: NEUTRAL / ĐỨNG NGOÀI.
            </p>
          </div>

          <div class="text-right font-mono text-xs text-slate-400 space-y-1">
            <div>Tổng trọng số: <span class="text-white">{{ totalWeight.toFixed(2) }}</span></div>
            <div>Tỉ lệ chuẩn hóa: <span class="text-emerald-400">100% OK</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { phase2Markdown } from "~/data/trd/phase2SpecContent"
useHead({
  title: "TRD Phase 2: Tri-Engine Architecture - Vnstock Quants",
})

const activeTab = ref<"spec" | "tests" | "simulator">("spec")

const tabs: Array<{
  id: "spec" | "tests" | "simulator"
  label: string
  icon: string
}> = [
  {
    id: "spec",
    label: "Tài liệu đặc tả",
    icon: "i-heroicons-document-text",
  },
  {
    id: "tests",
    label: "Ma trận kiểm thử",
    icon: "i-heroicons-check-badge",
  },
  {
    id: "simulator",
    label: "Mô phỏng Tri-Engine",
    icon: "i-heroicons-cpu-chip",
  },
]

const w1 = ref(0.4)
const s1 = ref(45)
const w2 = ref(0.35)
const s2 = ref(30)
const w3 = ref(0.25)
const s3 = ref(-15)

const resetEngineDefaults = () => {
  w1.value = 0.4
  s1.value = 45
  w2.value = 0.35
  s2.value = 30
  w3.value = 0.25
  s3.value = -15
}

const totalWeight = computed(() => w1.value + w2.value + w3.value)

const finalScore = computed(() => {
  const normW1 = w1.value / totalWeight.value
  const normW2 = w2.value / totalWeight.value
  const normW3 = w3.value / totalWeight.value
  return normW1 * s1.value + normW2 * s2.value + normW3 * s3.value
})

const finalDecision = computed(() => {
  if (finalScore.value >= 25) return "TRIGGER: LONG VN30F1M"
  if (finalScore.value <= -25) return "TRIGGER: SHORT VN30F1M"
  return "TÍN HIỆU: NEUTRAL (QUAN SÁT)"
})

const finalSignalClass = computed(() => {
  if (finalScore.value >= 25) return "text-emerald-400"
  if (finalScore.value <= -25) return "text-rose-400"
  return "text-slate-300"
})

const ensembleBannerClass = computed(() => {
  if (finalScore.value >= 25) return "bg-emerald-500/10 border-emerald-500/30"
  if (finalScore.value <= -25) return "bg-rose-500/10 border-rose-500/30"
  return "bg-surface-midnight border-white/[0.08]"
})

const testCases = [
  {
    id: "TEST-E1-01",
    group: "Engine 1 (Technical)",
    scenario: "Xử lý chuỗi nến đa khung thời gian (1m, 5m, 15m, 1D) đồng bộ",
    expectation:
      "Tính toán đúng chỉ số RSI(14), MACD(12,26,9), VWAP nội phiên không bị lag",
    status: "PASS" as const,
  },
  {
    id: "TEST-E1-02",
    group: "Engine 1 (Technical)",
    scenario: "Phân tích luồng khớp lệnh Quote.intraday() dòng tiền chủ động",
    expectation:
      "Bóc tách chính xác Buy Delta vs Sell Delta; phát hiện đột biến khối lượng chủ động",
    status: "PASS" as const,
  },
  {
    id: "TEST-E2-01",
    group: "Engine 2 (Flow & Liquidity)",
    scenario: "Theo dõi dòng tiền Khối ngoại và Tự doanh rổ VN30",
    expectation:
      "Ghi nhận chuẩn xác giá trị mua/bán ròng, tương quan tỷ lệ đỡ giá chỉ số VN30",
    status: "PASS" as const,
  },
  {
    id: "TEST-E2-02",
    group: "Engine 2 (Flow & Liquidity)",
    scenario:
      "Cập nhật bối cảnh vĩ mô giá vàng SJC & tỷ giá USD/VND qua Retail",
    expectation:
      "Cảnh báo áp lực rút ròng ngoại tệ khi USD/VND vượt ngưỡng biến động 1.5%",
    status: "PASS" as const,
  },
  {
    id: "TEST-E3-01",
    group: "Engine 3 (Quant ML)",
    scenario:
      "Theo dõi độ lệch Basis spread (VN30F1M - VN30) theo thời gian thực",
    expectation:
      "Xác định vùng lệch chuẩn quá mức (Over-stretched Basis) để đón bắt đảo chiều hội tụ",
    status: "PASS" as const,
  },
  {
    id: "TEST-ENS-01",
    group: "Ensemble Decision",
    scenario: "Kết hợp 3 Engine tạo kịch bản dự báo phiên ATC (14:15 - 14:30)",
    expectation:
      "Tạo xác suất dự báo bước giá đóng cửa ATC và khuyến nghị vị thế hợp đồng tối ưu",
    status: "PASS" as const,
  },
]
</script>
