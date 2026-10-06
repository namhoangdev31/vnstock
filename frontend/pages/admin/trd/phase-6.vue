<template>
  <div class="space-y-6">
    <header><div class="flex items-center gap-2 text-xs text-aave-graphite"><NuxtLink to="/admin" class="hover:text-aave-violet">Dashboard</NuxtLink><span>/</span><span class="text-aave-violet">TRD Phase 6</span></div><h1 class="mt-2 flex items-center gap-2 text-2xl font-semibold text-aave-paper"><UIcon name="i-heroicons-chart-pie" class="h-7 w-7 text-aave-violet" />Phase 6: Frontend Dashboards và Quantitative Analytics Cockpit</h1><p class="mt-1 text-sm text-aave-graphite">Tài liệu đặc tả kiến trúc và ma trận kiểm thử hệ thống Dashboard.</p></header>
    <div class="flex gap-1 border-b border-white/[0.08]" role="tablist" aria-label="Tài liệu Phase 6"><button v-for="tab in tabs" :key="tab.id" class="min-h-11 px-3 text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-aave-violet" :class="activeTab === tab.id ? 'border-b-2 border-aave-violet text-aave-violet' : 'text-aave-graphite hover:text-aave-ash'" @click="activeTab = tab.id">{{ tab.label }}</button></div>
    <MarkdownViewer v-if="activeTab === 'spec'" :content="phase6Markdown" filename="trd-phase-6-cockpit.md" />
    <TestMatrix v-else :tests="testCases" />
  </div>
</template>
<script setup lang="ts">
import { phase6Markdown } from "~/data/trd/phase6SpecContent"
useHead({ title: "TRD Phase 6 - Vnstock Quants" })
const activeTab = shallowRef<"spec" | "tests">("spec")
const tabs = [
  { id: "spec", label: "Tài liệu đặc tả" },
  { id: "tests", label: "Ma trận kiểm thử" },
] as const
const testCases = [
  {
    id: "TEST-FE-01",
    group: "Realtime chart",
    scenario: "Cập nhật telemetry liên tục",
    expectation: "Chỉ series và card thay đổi, không remount toàn trang",
    status: "PENDING" as const,
  },
  {
    id: "TEST-FE-02",
    group: "Timeframe",
    scenario: "Chuyển 1m, 5m, 15m",
    expectation: "Tải đúng chuỗi nến và hủy request cũ",
    status: "PENDING" as const,
  },
  {
    id: "TEST-FE-03",
    group: "Margin",
    scenario: "Đặt 1 hợp đồng VN30F1M",
    expectation: "Giá × 100.000 × 17%",
    status: "PENDING" as const,
  },
  {
    id: "TEST-FE-04",
    group: "Validation",
    scenario: "Thiếu số dư",
    expectation: "Nút gửi bị khóa kèm tooltip",
    status: "PENDING" as const,
  },
  {
    id: "TEST-FE-05",
    group: "Simulation",
    scenario: "Gửi và đóng lệnh",
    expectation: "Vị thế và lịch sử cập nhật",
    status: "PENDING" as const,
  },
  {
    id: "TEST-FE-06",
    group: "Prediction",
    scenario: "Phân phối xác suất",
    expectation: "P10, P50, P90 trong biên ±7%",
    status: "PENDING" as const,
  },
  {
    id: "TEST-FE-07",
    group: "Responsive",
    scenario: "Viewport dưới 768px",
    expectation: "Stack dọc, không tràn ngang",
    status: "PENDING" as const,
  },
  {
    id: "TEST-FE-08",
    group: "Resilience",
    scenario: "Mất kết nối",
    expectation: "Hiển thị Offline / Reconnecting",
    status: "PENDING" as const,
  },
]
</script>
