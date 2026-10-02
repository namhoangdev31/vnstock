<template>
  <div class="space-y-8">
    <!-- Welcome Header & Live Status -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800/80 border border-slate-800 shadow-xl">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            24/7 Autonomous Research Active
          </span>
          <span class="text-xs text-slate-400 font-mono">Phiên bản 4.0 Nuxt</span>
        </div>
        <h1 class="text-2xl lg:text-3xl font-bold tracking-tight text-white">
          Xin chào, {{ user?.full_name || user?.email?.split('@')[0] || 'Nhà định lượng' }} 👋
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 max-w-2xl">
          Hệ thống tính toán định lượng liên tục, mô hình hóa kịch bản phiên ATC và tối ưu hóa vị thế phái sinh VN30F1M kèm rổ cổ phiếu T+2.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <NuxtLink
          to="/stock"
          class="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 transition-all"
        >
          <UIcon name="i-heroicons-chart-bar" class="w-4 h-4" />
          Xem thị trường CK
        </NuxtLink>
        <NuxtLink
          to="/trd/phase-1"
          class="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all"
        >
          <UIcon name="i-heroicons-document-text" class="w-4 h-4" />
          Đặc tả TRD
        </NuxtLink>
      </div>
    </div>

    <!-- Core Metrics / KPI Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur space-y-3">
        <div class="flex items-center justify-between text-slate-400">
          <span class="text-xs font-medium uppercase tracking-wider">Hợp đồng trọng tâm</span>
          <UIcon name="i-heroicons-arrow-trending-up" class="w-5 h-5 text-emerald-400" />
        </div>
        <div>
          <div class="text-2xl font-bold font-mono text-white">VN30F1M</div>
          <div class="text-[11px] text-slate-400 mt-1 flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-400" />
            T+0 Intraday & Tối ưu vị thế ATO → ATC
          </div>
        </div>
      </div>

      <div class="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur space-y-3">
        <div class="flex items-center justify-between text-slate-400">
          <span class="text-xs font-medium uppercase tracking-wider">Kiến trúc Tri-Engine</span>
          <UIcon name="i-heroicons-cpu-chip" class="w-5 h-5 text-teal-400" />
        </div>
        <div>
          <div class="text-2xl font-bold text-white">3 ENGINES</div>
          <div class="text-[11px] text-slate-400 mt-1">
            Engine 1 (Kỹ thuật) + Engine 2 (Dòng tiền) + Engine 3 (ML)
          </div>
        </div>
      </div>

      <div class="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur space-y-3">
        <div class="flex items-center justify-between text-slate-400">
          <span class="text-xs font-medium uppercase tracking-wider">Chu kỳ Thanh toán</span>
          <UIcon name="i-heroicons-calendar" class="w-5 h-5 text-indigo-400" />
        </div>
        <div>
          <div class="text-2xl font-bold font-mono text-white">CHUẨN T+2</div>
          <div class="text-[11px] text-slate-400 mt-1">
            Cách ly sức mua, cổ phiếu chờ về, margin an toàn
          </div>
        </div>
      </div>

      <div class="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur space-y-3">
        <div class="flex items-center justify-between text-slate-400">
          <span class="text-xs font-medium uppercase tracking-wider">Sổ nhật ký dự báo</span>
          <UIcon name="i-heroicons-archive-box" class="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <div class="text-2xl font-bold text-white">AUDITABLE</div>
          <div class="text-[11px] text-slate-400 mt-1">
            Pending → Resolved → Scored (Zero Look-ahead)
          </div>
        </div>
      </div>
    </div>

    <!-- TRD Blueprints Fast Access -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-bold text-white">Lộ trình triển khai kỹ thuật (TRD 6 Phases)</h2>
          <p class="text-xs text-slate-400">Tài liệu đặc tả chi tiết, ma trận kiểm thử và demo tương tác từng phân hệ</p>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <NuxtLink
          v-for="phase in phases"
          :key="phase.id"
          :to="phase.path"
          class="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-emerald-500/40 hover:bg-slate-900/80 transition-all group flex flex-col justify-between"
        >
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {{ phase.code }}
              </span>
              <span class="text-xs font-semibold text-emerald-400 flex items-center gap-1">
                <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
                Đạt 100%
              </span>
            </div>
            <h3 class="text-sm font-bold text-white group-hover:text-emerald-400 transition-colors">
              {{ phase.title }}
            </h3>
            <p class="text-xs text-slate-400 leading-relaxed line-clamp-2">
              {{ phase.desc }}
            </p>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400 group-hover:text-slate-200">
            <span>Chi tiết đặc tả & Test Matrix</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4 group-hover:translate-x-1 transition-transform text-emerald-400" />
          </div>
        </NuxtLink>
      </div>
    </div>

    <!-- Safeguard Notice -->
    <div class="p-5 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs text-amber-200/90 flex items-start gap-3">
      <UIcon name="i-heroicons-shield-exclamation" class="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
      <div class="space-y-1">
        <p class="font-bold text-amber-300 uppercase tracking-wide">
          Nguyên tắc bất khả xâm phạm (Zero-Tolerance Rules)
        </p>
        <p class="text-slate-300 leading-relaxed">
          Nghiêm cấm tuyệt đối tích hợp bot đặt lệnh tiền thật hoặc lưu trữ API key/mật khẩu công ty chứng khoán. Tất cả vị thế, số dư, PnL nằm hoàn toàn trong môi trường mô phỏng (Paper Trading / Simulation Sandbox).
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
useHead({
  title: "Dashboard - Vnstock Quants & Engine 24/7",
})

const { user } = useAuth()

const phases = [
  {
    id: 1,
    code: "PHASE 1",
    path: "/trd/phase-1",
    title: "Nền tảng dữ liệu & Persistence",
    desc: "PostgreSQL-first storage, rate limiting chống ban IP, schema audit log và models chuẩn timezone aware.",
  },
  {
    id: 2,
    code: "PHASE 2",
    path: "/trd/phase-2",
    title: "Tri-Engine Architecture",
    desc: "Tích hợp 3 Engine: Kỹ thuật Price Action, Dòng tiền khối ngoại & Tự doanh, và Machine Learning xác suất.",
  },
  {
    id: 3,
    code: "PHASE 3",
    path: "/trd/phase-3",
    title: "24/7 Autonomous Daemon",
    desc: "Vòng lặp tính toán liên tục qua các phiên ATO (08:45), Khớp lệnh liên tục, ATC (14:30), và Post-Market T+1.",
  },
  {
    id: 4,
    code: "PHASE 4",
    path: "/trd/phase-4",
    title: "Paper Trading & Chu kỳ T+2",
    desc: "Mô phỏng khớp lệnh VN30F1M không rủi ro, quản lý ký quỹ, tính toán phí thuế và hạn mức mua bán T+2.",
  },
  {
    id: 5,
    code: "PHASE 5",
    path: "/trd/phase-5",
    title: "Sổ nhật ký dự báo (Forecast Journal)",
    desc: "Lưu vết 100% dự báo trước phiên, đối soát kết quả thực tế, chấm điểm MAE/Accuracy và hiệu chuẩn mô hình có kiểm soát.",
  },
  {
    id: 6,
    code: "PHASE 6",
    path: "/trd/phase-6",
    title: "Cockpit & Giám sát thời gian thực",
    desc: "Giao diện Dashboard tổng thể, biểu đồ nến chuyên sâu, cảnh báo biến động bất thường và phân bổ rổ danh mục.",
  },
]
</script>
