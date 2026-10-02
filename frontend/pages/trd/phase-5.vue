<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs text-slate-400 font-mono mb-1">
          <NuxtLink to="/" class="hover:text-emerald-400">Dashboard</NuxtLink>
          <span>/</span>
          <span class="text-emerald-400">TRD Phase 5</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-archive-box" class="w-7 h-7 text-rose-400" />
          Phase 5: Sổ nhật ký dự báo (Forecast Journal)
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Lưu vết 100% dự báo trước phiên, đối soát kết quả thực tế, chấm điểm MAE/Accuracy và hiệu chuẩn mô hình có kiểm soát.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <span class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1.5">
          <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
          DoD Journal: 100%
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
        :class="activeTab === tab.id ? 'border-rose-400 text-rose-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = tab.id"
      >
        <UIcon :name="tab.icon" class="w-4 h-4" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab 1: Spec -->
    <div v-if="activeTab === 'spec'">
      <MarkdownViewer :content="phase5Markdown" filename="trd-phase-5-forecast-journal.md" />
    </div>

    <!-- Tab 2: Test Matrix -->
    <div v-else-if="activeTab === 'tests'">
      <TestMatrix :tests="testCases" />
    </div>

    <!-- Tab 3: Interactive Ledger Simulator -->
    <div v-else-if="activeTab === 'ledger'" class="space-y-6">
      <div class="p-6 rounded-2xl bg-[#090d16] border border-white/[0.08] shadow-2xl space-y-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 class="text-base font-bold text-white flex items-center gap-2">
              <UIcon name="i-heroicons-clipboard-document-list" class="w-5 h-5 text-rose-400" />
              Sổ cái Đối soát & Tự học (Forecast Audit Ledger)
            </h3>
            <p class="text-xs text-slate-400">
              Mỗi dự báo được snapshot trước khi phiên diễn ra; tự động chấm điểm khi có kết quả thực tế.
            </p>
          </div>

          <button
            type="button"
            class="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto transition-colors shadow-lg shadow-rose-600/20"
            @click="resolvePendingForecasts"
          >
            <UIcon name="i-heroicons-arrow-path" class="w-4 h-4" />
            Đối soát kết quả thực tế phiên hôm nay
          </button>
        </div>

        <!-- Ledger Table -->
        <div class="overflow-x-auto rounded-xl border border-white/[0.06] bg-[#070a11]">
          <table class="w-full text-left text-xs font-mono">
            <thead class="bg-[#0b101c] text-slate-400 uppercase text-[10px] tracking-wider border-b border-white/[0.06]">
              <tr>
                <th class="py-3 px-4">Mã / Tài sản</th>
                <th class="py-3 px-4">Khung (Horizon)</th>
                <th class="py-3 px-4">Thời điểm dự báo</th>
                <th class="py-3 px-4">Kỳ vọng / Xu hướng</th>
                <th class="py-3 px-4">Thực tế (Actual)</th>
                <th class="py-3 px-4">Sai số (MAE)</th>
                <th class="py-3 px-4 text-center">Trạng thái</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04]">
              <tr
                v-for="item in journalEntries"
                :key="item.id"
                class="hover:bg-white/[0.02] transition-colors"
              >
                <td class="py-3 px-4 font-bold text-white">{{ item.symbol }}</td>
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded text-[10px] bg-white/[0.04] border border-white/[0.06] text-slate-300">
                    {{ item.horizon }}
                  </span>
                </td>
                <td class="py-3 px-4 text-slate-400">{{ item.predictedAt }}</td>
                <td class="py-3 px-4 text-emerald-400 font-bold">
                  {{ item.prediction }}
                </td>
                <td class="py-3 px-4 text-slate-200">
                  {{ item.actual || 'Đang chờ phiên đối soát' }}
                </td>
                <td class="py-3 px-4 text-slate-300">
                  {{ item.mae !== null ? item.mae.toFixed(1) + ' pts' : 'N/A' }}
                </td>
                <td class="py-3 px-4 text-center">
                  <span
                    class="px-2 py-0.5 rounded text-[10px] font-bold"
                    :class="item.status === 'SCORED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'"
                  >
                    {{ item.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Autonomous Auto-Promote & Circuit Breaker Explanation -->
        <div class="p-5 rounded-xl bg-[#0d1322] border border-white/[0.06] space-y-2 text-xs">
          <h4 class="font-bold text-white flex items-center gap-1.5 font-mono">
            <UIcon name="i-heroicons-arrow-path-rounded-square" class="w-4 h-4 text-rose-400" />
            CƠ CHẾ TỰ HỌC TỰ ĐỘNG (AUTONOMOUS AUTO-PROMOTE & CIRCUIT BREAKER)
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Hệ thống tự động đánh giá Directional Accuracy và Brier Score trên 30 phiên gần nhất. Khi bộ trọng số mới vượt qua Cổng Walk-Forward Gate, phiên bản mới sẽ được tự động kích hoạt (Auto-Promote <span class="font-mono text-emerald-400 font-bold">is_active = true</span>) mà không cần Admin duyệt thủ công. Nếu Drawdown vượt -3%, Circuit Breaker sẽ tự động khóa và phục hồi trọng số phòng thủ an toàn.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { phase5Markdown } from "~/data/trd/phase5SpecContent"
useHead({
  title: "TRD Phase 5: Forecast Journal - Vnstock Quants",
})

const activeTab = ref<"spec" | "tests" | "ledger">("spec")
const { showSuccessToast } = useCustomToast()

const tabs: Array<{
  id: "spec" | "tests" | "ledger"
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
    id: "ledger",
    label: "Mô phỏng Sổ cái Audit",
    icon: "i-heroicons-clipboard-document-list",
  },
]

const journalEntries = ref([
  {
    id: 1,
    symbol: "VN30F1M",
    horizon: "ATC_AUCTION",
    predictedAt: "14:15:00",
    prediction: "LONG (1328.5)",
    actual: "1330.2",
    mae: 1.7,
    status: "SCORED",
  },
  {
    id: 2,
    symbol: "VN30F1M",
    horizon: "NEXT_DAY (T+1)",
    predictedAt: "15:30:00 (Hôm qua)",
    prediction: "BULLISH (+12 pts)",
    actual: "+14.5 pts",
    mae: 2.5,
    status: "SCORED",
  },
  {
    id: 3,
    symbol: "VN30F1M",
    horizon: "ATC_AUCTION",
    predictedAt: "14:15:00 (Hôm nay)",
    prediction: "SHORT (1315.0)",
    actual: null,
    mae: null,
    status: "PENDING",
  },
  {
    id: 4,
    symbol: "FPT",
    horizon: "WEEKLY_ALPHA",
    predictedAt: "Đầu tuần",
    prediction: "OUTPERFORM (+5%)",
    actual: null,
    mae: null,
    status: "PENDING",
  },
])

const resolvePendingForecasts = () => {
  journalEntries.value = journalEntries.value.map((item) => {
    if (item.status === "PENDING") {
      return {
        ...item,
        actual: item.symbol === "VN30F1M" ? "1313.8" : "+6.2%",
        mae: item.symbol === "VN30F1M" ? 1.2 : 1.2,
        status: "SCORED",
      }
    }
    return item
  })
  showSuccessToast(
    "Đã đối soát sổ cái!",
    "Các dự báo PENDING đã được backfill dữ liệu thực tế và chấm điểm độ chính xác.",
  )
}

const testCases = [
  {
    id: "TEST-JRN-01",
    group: "Ledger Persistence",
    scenario:
      "Ghi nhận dự báo tại thời điểm T với engine_weights và model_version",
    expectation:
      "Lưu vào database ngay lập tức với status='pending'; không cho phép sửa đổi predicted_at",
    status: "PASS" as const,
  },
  {
    id: "TEST-JRN-02",
    group: "Realization Backfill",
    scenario: "Cập nhật actual_value khi phiên kết thúc",
    expectation:
      "Status chuyển sang 'resolved'; hệ thống lưu audit trail thời gian đối soát",
    status: "PASS" as const,
  },
  {
    id: "TEST-JRN-03",
    group: "Automated Scoring",
    scenario:
      "Tính toán sai số tuyệt đối trung bình (MAE) và độ chính xác hướng đi (Directional Accuracy)",
    expectation: "Tự động tính đúng MAE; chuyển status sang 'scored'",
    status: "PASS" as const,
  },
  {
    id: "TEST-RCAL-01",
    group: "Autonomous Recalibration",
    scenario: "Hiệu chuẩn trọng số Engine mới trên tập dữ liệu lịch sử",
    expectation:
      "Tự động Auto-Promote khi đạt chuẩn Walk-Forward Gate; duy trì Circuit Breaker và snapshot cho phép rollback",
    status: "PASS" as const,
  },
]
</script>
