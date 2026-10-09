<template>
  <div class="space-y-6">

    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs text-slate-400 font-mono mb-1">
          <NuxtLink to="/admin" class="hover:text-emerald-400">Dashboard</NuxtLink>
          <span>/</span>
          <span class="text-emerald-400">TRD Phase 3</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-clock" class="w-7 h-7 text-indigo-400" />
          Phase 3: 24/7 Autonomous Daemon
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Vòng lặp tính toán liên tục qua các phiên ATO (08:45), Khớp lệnh liên tục, ATC (14:30), và Post-Market T+1.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <span class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center gap-1.5">
          <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
          DoD Daemon 24/7: 100%
        </span>
      </div>
    </div>

    <div class="flex border-b border-slate-800 gap-4">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
        :class="activeTab === tab.id ? 'border-indigo-400 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = tab.id"
      >
        <UIcon :name="tab.icon" class="w-4 h-4" />
        {{ tab.label }}
      </button>
    </div>

    <div v-if="activeTab === 'spec'">
      <MarkdownViewer :content="phase3Markdown" filename="trd-phase-3-daemon.md" />
    </div>

    <div v-else-if="activeTab === 'tests'">
      <TestMatrix :tests="testCases" />
    </div>

    <div v-else-if="activeTab === 'timeline'" class="space-y-6">
      <div class="p-6 rounded-2xl bg-surface-abyss border border-white/[0.08] shadow-2xl space-y-6">
        <div>
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <UIcon name="i-heroicons-play-circle" class="w-5 h-5 text-aave-violet" />
            <span>Lộ trình Vòng lặp Phiên giao dịch</span>
            <UTooltip text="Session Schedule Protocol">
              <UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" />
            </UTooltip>
          </h3>
          <p class="text-xs text-slate-400">
            Hệ thống vận hành không ngắt quãng 24/7 qua 7 phân đoạn phiên nghiêm ngặt của Sở Giao dịch Chứng khoán:
          </p>
        </div>

        <div class="space-y-3">
          <div
            v-for="(session, idx) in sessionPhases"
            :key="session.name"
            class="p-4 rounded-xl border transition-all cursor-pointer"
            :class="selectedPhaseIdx === idx ? 'bg-indigo-500/10 border-indigo-500/40 text-slate-100' : 'bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700'"
            @click="selectedPhaseIdx = idx"
          >
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div class="flex items-center gap-3">
                <span class="w-6 h-6 rounded-full bg-slate-800 text-slate-300 font-mono text-xs font-bold flex items-center justify-center">
                  {{ idx + 1 }}
                </span>
                <div>
                  <span class="font-bold text-sm text-white">{{ session.name }}</span>
                  <span class="ml-2 font-mono text-xs text-indigo-400 font-semibold">{{ session.time }}</span>
                </div>
              </div>
              <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 self-start sm:self-auto">
                {{ session.status }}
              </span>
            </div>

            <p class="text-xs text-slate-300 mt-2 pl-9 leading-relaxed">
              {{ session.action }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { phase3Markdown } from "~/data/trd/phase3SpecContent"
useHead({
  title: "TRD Phase 3: 24/7 Autonomous Daemon - Vistock Quants",
})

const activeTab = ref<"spec" | "tests" | "timeline">("spec")
const selectedPhaseIdx = ref(0)

const tabs: Array<{
  id: "spec" | "tests" | "timeline"
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
  { id: "timeline", label: "Lộ trình phiên 24/7", icon: "i-heroicons-clock" },
]

const sessionPhases = [
  {
    name: "Pre-ATO / Chuẩn bị đầu ngày",
    time: "08:30 - 08:45",
    status: "SYNC_PIVOTS",
    action:
      "Đồng bộ giá thanh toán ngày hôm trước, tính toán độ lệch Basis qua đêm, cập nhật các ngưỡng Pivot kháng cự/hỗ trợ.",
  },
  {
    name: "ATO Call Auction",
    time: "08:45 - 09:00",
    status: "GAP_DETECTION",
    action:
      "Giám sát khớp lệnh định kỳ mở cửa ATO của VN30F1M, phát hiện biên độ Gap tăng/giảm sớm so với chỉ số cơ sở VN30.",
  },
  {
    name: "Khớp lệnh liên tục buổi sáng",
    time: "09:00 - 11:30",
    status: "HIGH_FREQ_TICK",
    action:
      "Xử lý luồng nến 1m và dữ liệu tick Quote.intraday(), bám sát chỉ báo VWAP, phát hiện breakout và chạy paper trading.",
  },
  {
    name: "Nghỉ trưa liên phiên",
    time: "11:30 - 13:00",
    status: "MIDDAY_RECOMPUTE",
    action:
      "Tái tính toán ngầm mức độ trượt Basis so với rổ 30 cổ phiếu, cập nhật kịch bản phiên chiều.",
  },
  {
    name: "Khớp lệnh liên tục buổi chiều & Chuẩn bị ATC",
    time: "13:00 - 14:30",
    status: "T2_SETTLEMENT_PREP",
    action:
      "Đo lường lượng hàng về T+2 của phiên chiều, quét thanh khoản lớn và kích hoạt bộ dự báo đóng cửa ATC lúc 14:15.",
  },
  {
    name: "Phiên khớp lệnh định kỳ đóng cửa ATC",
    time: "14:30 - 14:45",
    status: "ATC_CONVERGENCE",
    action:
      "Theo dõi cân bằng cung cầu ATC, dự báo giá thanh toán chốt ngày và chốt PnL danh mục mô phỏng.",
  },
  {
    name: "Post-Market / Tối & Đêm 24/7",
    time: "14:45 - 08:30",
    status: "OVERNIGHT_MONTE_CARLO",
    action:
      "Chạy mô phỏng kịch bản Monte Carlo, tính toán rổ cổ phiếu khuyến nghị theo tuần/tháng/quý và sinh dự báo T+1.",
  },
]

const testCases = [
  {
    id: "TEST-DMN-01",
    group: "24/7 Scheduling",
    scenario:
      "Xác định đúng trạng thái phiên theo thời gian thực (Giờ Hà Nội VN_TZ)",
    expectation:
      "Hệ thống tự động chuyển đổi logic không phụ thuộc vào timezone của máy chủ host",
    status: "PASS" as const,
  },
  {
    id: "TEST-DMN-02",
    group: "24/7 Scheduling",
    scenario: "Xử lý ngắt quãng mạng hoặc timeout khi đang trong phiên ATO",
    expectation:
      "Tự động retry với exponential backoff, duy trì trạng thái dữ liệu trước đó, không crash daemon",
    status: "PASS" as const,
  },
  {
    id: "TEST-ATC-01",
    group: "ATC Call Auction",
    scenario: "Kích hoạt mô hình dự báo ATC tại mốc 14:15",
    expectation:
      "Dự báo giá đóng cửa dự kiến của VN30F1M và ước tính khối lượng khớp lệnh ATC",
    status: "PASS" as const,
  },
  {
    id: "TEST-NIT-01",
    group: "Post-Market & Night",
    scenario:
      "Chạy quy trình quét rổ cổ phiếu Alpha (Weekly/Monthly/Quarterly) lúc 15:30",
    expectation:
      "Lọc top cổ phiếu đạt tiêu chí cơ bản, dòng tiền và ghi nhận vào sổ nhật ký dự báo",
    status: "PASS" as const,
  },
]
</script>
