<template>
  <div class="space-y-6">
    <!-- Top Command Strip (Terminal Header) -->
    <div class="p-6 rounded-2xl bg-[#090d16]/90 border border-white/[0.08] shadow-2xl relative overflow-hidden backdrop-blur-xl">
      <div class="absolute -right-24 -top-24 w-80 h-80 rounded-full bg-emerald-500/5 blur-3xl pointer-events-none" />
      <div class="absolute -left-20 -bottom-20 w-64 h-64 rounded-full bg-teal-500/5 blur-3xl pointer-events-none" />

      <div class="relative flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div class="space-y-2 max-w-3xl">
          <div class="flex items-center gap-2.5">
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              ENGINE 24/7 ACTIVE
            </span>
            <span class="text-[11px] font-mono text-slate-500">TRI-ENGINE QUANTITATIVE ARCHITECTURE</span>
          </div>

          <h1 class="text-xl sm:text-2xl lg:text-3xl font-bold tracking-tight text-white">
            Trạm Phân Tích Định Lượng & Mô Phỏng Phái Sinh VN30F1M
          </h1>
          <p class="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Hệ thống tính toán định lượng liên tục, mô hình hóa kịch bản phiên ATC và tối ưu hóa vị thế phái sinh VN30F1M kèm rổ cổ phiếu T+2 trên nền tảng Nuxt 3 và FastAPI.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-2.5 shrink-0">
          <NuxtLink
            to="/stock"
            class="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 transition-all font-mono"
          >
            <UIcon name="i-heroicons-chart-bar" class="w-4 h-4" />
            <span>Thị trường CK</span>
          </NuxtLink>

          <NuxtLink
            to="/trd/phase-4"
            class="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-200 border border-white/[0.08] transition-all font-mono"
          >
            <UIcon name="i-heroicons-arrows-right-left" class="w-4 h-4 text-emerald-400" />
            <span>Paper Trading</span>
          </NuxtLink>

          <NuxtLink
            to="/trd/phase-5"
            class="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-slate-200 border border-white/[0.08] transition-all font-mono"
          >
            <UIcon name="i-heroicons-document-check" class="w-4 h-4 text-teal-400" />
            <span>Sổ cái dự báo</span>
          </NuxtLink>
        </div>
      </div>
    </div>

    <!-- Asymmetric Bento Cockpit Grid -->
    <div class="grid grid-cols-12 gap-5">
      <!-- Tile 1: Master Tri-Engine Ensemble Telemetry (7 cols) -->
      <div class="col-span-12 lg:col-span-7 p-6 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] space-y-5 shadow-xl">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-4">
          <div>
            <span class="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">ENSEMBLE PULSE</span>
            <h2 class="text-sm font-bold text-white flex items-center gap-2 mt-0.5">
              <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4 text-emerald-400" />
              Tổng Hợp Tín Hiệu 3 Động Cơ (Ensemble Decision)
            </h2>
          </div>

          <div class="flex items-center gap-2">
            <span class="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-mono font-bold flex items-center gap-1.5">
              <UIcon name="i-heroicons-arrow-trending-up" class="w-3.5 h-3.5" />
              LONG BIAS (+64.5 pts)
            </span>
          </div>
        </div>

        <!-- Engine Weights Breakdown -->
        <div class="space-y-3.5 text-xs">
          <!-- Engine 1 -->
          <div class="space-y-1.5">
            <div class="flex justify-between items-center text-slate-300">
              <span class="font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-400" />
                Engine 1: Phân tích Kỹ thuật & Khớp lệnh Tick
              </span>
              <span class="font-mono text-emerald-400 font-semibold">Tỷ trọng: 40% (+48.0)</span>
            </div>
            <div class="w-full bg-white/[0.04] h-2 rounded-full overflow-hidden">
              <div class="bg-gradient-to-r from-emerald-600 to-emerald-400 h-full rounded-full" style="width: 74%" />
            </div>
          </div>

          <!-- Engine 2 -->
          <div class="space-y-1.5">
            <div class="flex justify-between items-center text-slate-300">
              <span class="font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-teal-400" />
                Engine 2: Thanh khoản, Dòng tiền & Mô hình T+2
              </span>
              <span class="font-mono text-teal-400 font-semibold">Tỷ trọng: 35% (+34.0)</span>
            </div>
            <div class="w-full bg-white/[0.04] h-2 rounded-full overflow-hidden">
              <div class="bg-gradient-to-r from-teal-600 to-teal-400 h-full rounded-full" style="width: 62%" />
            </div>
          </div>

          <!-- Engine 3 -->
          <div class="space-y-1.5">
            <div class="flex justify-between items-center text-slate-300">
              <span class="font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-slate-400" />
                Engine 3: Định lượng ML, Basis Spread & Phân loại Regime
              </span>
              <span class="font-mono text-rose-400 font-semibold">Tỷ trọng: 25% (-12.0)</span>
            </div>
            <div class="w-full bg-white/[0.04] h-2 rounded-full overflow-hidden">
              <div class="bg-gradient-to-r from-rose-600 to-rose-400 h-full rounded-full" style="width: 44%" />
            </div>
          </div>
        </div>

        <div class="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between text-xs">
          <span class="text-slate-400 font-mono text-[11px]">Độ tin cậy Ensemble:</span>
          <span class="text-emerald-400 font-mono font-bold">67.8% (Xác suất nghiêng Long ATO/ATC)</span>
        </div>
      </div>

      <!-- Tile 2: VN30F1M Futures Focus (5 cols) -->
      <div class="col-span-12 lg:col-span-5 p-6 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] space-y-4 shadow-xl flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div>
              <span class="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">HỢP ĐỒNG PHÁI SINH</span>
              <h2 class="text-sm font-bold text-white font-mono flex items-center gap-1.5">
                VN30F1M (T+0 Intraday)
              </h2>
            </div>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Theo dõi liên tục
            </span>
          </div>

          <div class="pt-4 space-y-3">
            <div class="flex items-baseline justify-between">
              <span class="text-xs text-slate-400">Giá khớp gần nhất:</span>
              <span class="text-2xl font-mono font-bold text-emerald-400">1,318.50</span>
            </div>

            <div class="grid grid-cols-2 gap-2 text-xs font-mono">
              <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                <div class="text-[10px] text-slate-500">VN30 Cơ sở</div>
                <div class="font-bold text-slate-200 mt-0.5">1,320.80</div>
              </div>
              <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                <div class="text-[10px] text-slate-500">Độ lệch (Basis)</div>
                <div class="font-bold text-rose-400 mt-0.5">-2.30 pts</div>
              </div>
            </div>

            <div class="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] text-[11px] text-slate-400">
              <div class="flex items-center justify-between mb-1">
                <span>Biên độ phiên:</span>
                <span class="font-mono text-slate-300">1,312.00 - 1,326.50</span>
              </div>
              <div class="w-full bg-white/[0.04] h-1.5 rounded-full overflow-hidden">
                <div class="bg-emerald-500 h-full rounded-full" style="width: 45%" />
              </div>
            </div>
          </div>
        </div>

        <div class="pt-2">
          <NuxtLink
            to="/trd/phase-4"
            class="w-full py-2 px-3 text-xs font-mono font-semibold rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-emerald-400 border border-white/[0.08] flex items-center justify-center gap-1.5 transition-colors"
          >
            <span>Mở giả lập vị thế VN30F1M</span>
            <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5" />
          </NuxtLink>
        </div>
      </div>

      <!-- Tile 3: T+2 Equity Settlement Model (4 cols) -->
      <div class="col-span-12 sm:col-span-6 lg:col-span-4 p-5 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">SETTLEMENT CYCLE</span>
          <UIcon name="i-heroicons-calendar" class="w-4 h-4 text-emerald-400" />
        </div>
        <div class="text-base font-bold text-white font-mono">Chuẩn Thanh Toán T+2</div>
        <p class="text-xs text-slate-400 leading-relaxed">
          Mô hình hóa chặt chẽ dòng tiền mua/bán, phân tách cổ phiếu chờ về lúc 13:00 phiên chiều T+2 và hạn chế rủi ro đòn bẩy.
        </p>
        <div class="pt-1 flex items-center gap-2 text-[11px] font-mono text-emerald-400">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>Cách ly sức mua Sandbox</span>
        </div>
      </div>

      <!-- Tile 4: Forecast Journal Audit (4 cols) -->
      <div class="col-span-12 sm:col-span-6 lg:col-span-4 p-5 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">SIGNAL AUDIT LEDGER</span>
          <UIcon name="i-heroicons-archive-box" class="w-4 h-4 text-teal-400" />
        </div>
        <div class="text-base font-bold text-white font-mono">Sổ Nhật Ký Dự Báo</div>
        <p class="text-xs text-slate-400 leading-relaxed">
          Lưu vết 100% tín hiệu tại thời điểm phát sinh (Pending), tự động đối soát sau phiên và tính điểm sai số Brier Score/MAE.
        </p>
        <div class="pt-1 flex items-center gap-2 text-[11px] font-mono text-teal-400">
          <span class="w-1.5 h-1.5 rounded-full bg-teal-400" />
          <span>Zero Look-ahead Bias</span>
        </div>
      </div>

      <!-- Tile 5: Governed Learning Loop (4 cols) -->
      <div class="col-span-12 sm:col-span-12 lg:col-span-4 p-5 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">ANTI-OVERFIT FEEDBACK</span>
          <UIcon name="i-heroicons-arrow-path-rounded-square" class="w-4 h-4 text-amber-400" />
        </div>
        <div class="text-base font-bold text-white font-mono">Tự Học Có Kiểm Soát</div>
        <p class="text-xs text-slate-400 leading-relaxed">
          Hiệu chuẩn trọng số Engine qua Softmax rolling 30 phiên. Giới hạn dịch chuyển tối đa 5%/kỳ kèm cổng phê duyệt của con người.
        </p>
        <div class="pt-1 flex items-center gap-2 text-[11px] font-mono text-amber-400">
          <span class="w-1.5 h-1.5 rounded-full bg-amber-400" />
          <span>Human-in-the-loop Gate</span>
        </div>
      </div>
    </div>

    <!-- Technical Blueprints Roadmap (TRD 6 Phases) -->
    <div class="space-y-4 pt-2">
      <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div>
          <h2 class="text-base font-bold text-white font-mono flex items-center gap-2">
            <UIcon name="i-heroicons-rectangle-stack" class="w-5 h-5 text-emerald-400" />
            Lộ Trình Triển Khai Kỹ Thuật (TRD 6 Phases)
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">Tài liệu đặc tả kiến trúc, ma trận kiểm thử và trạm thử nghiệm tương tác từng phân hệ</p>
        </div>

        <span class="hidden sm:inline-flex text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded border border-emerald-500/20">
          100% SPECS COMPLETE
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <NuxtLink
          v-for="phase in phases"
          :key="phase.id"
          :to="phase.path"
          class="p-5 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] hover:border-emerald-500/40 hover:bg-[#0c121e] transition-all group flex flex-col justify-between space-y-4"
        >
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-400">
                PHASE 0{{ phase.id }}
              </span>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {{ phase.status }}
              </span>
            </div>

            <h3 class="text-sm font-bold text-slate-100 group-hover:text-emerald-300 transition-colors">
              {{ phase.title }}
            </h3>

            <p class="text-xs text-slate-400 leading-relaxed">
              {{ phase.desc }}
            </p>
          </div>

          <div class="pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-slate-400 group-hover:text-emerald-400 transition-colors font-mono">
            <span class="text-[11px]">{{ phase.tech }}</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </div>
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
useHead({
  title: "Dashboard Cockpit - Vnstock Quants & Analytics 24/7",
})

const phases = [
  {
    id: 1,
    path: "/trd/phase-1",
    title: "Nền Tảng Dữ Liệu & Persistence",
    desc: "PostgreSQL-first storage, rate limiting chống ban IP, schema audit log và models chuẩn timezone aware.",
    tech: "PostgreSQL / SQLModel",
    status: "Hoàn tất 100%",
  },
  {
    id: 2,
    path: "/trd/phase-2",
    title: "Tri-Engine Analytics Core & Ensemble",
    desc: "Phối hợp 3 động cơ độc lập: Kỹ thuật, Dòng tiền và Quant ML với trọng số động và thuật toán Softmax.",
    tech: "Tri-Engine Ensemble",
    status: "Hoàn tất 100%",
  },
  {
    id: 3,
    path: "/trd/phase-3",
    title: "Background Session Daemon 24/7",
    desc: "Vòng lặp tính toán tự động không gián đoạn từ ATO, phiên sáng, nghỉ trưa, phiên chiều đến khớp lệnh ATC.",
    tech: "Continuous Daemon 24/7",
    status: "Hoàn tất 100%",
  },
  {
    id: 4,
    path: "/trd/phase-4",
    title: "Paper Trading Engine & Phái Sinh VN30F1M",
    desc: "Mô phỏng vị thế Long/Short phái sinh T+0 và cổ phiếu T+2 trong môi trường cách ly an toàn, tuyệt đối không dùng tiền thật.",
    tech: "Sandbox Simulation",
    status: "Hoàn tất 100%",
  },
  {
    id: 5,
    path: "/trd/phase-5",
    title: "Sổ Nhật Ký Dự Báo & Vòng Lặp Tự Học",
    desc: "Sổ cái lưu vết dự báo bất biến, đối soát kết quả sau phiên, tính điểm Brier Score và hiệu chuẩn chống Overfitting.",
    tech: "Forecast Journal",
    status: "Hoàn tất 100%",
  },
  {
    id: 6,
    path: "/trd/phase-6",
    title: "Frontend Cockpit & Alpha Basket",
    desc: "Giao diện trạm điều hành lượng hóa, kiểm soát luồng dữ liệu thời gian thực và phân bổ rổ danh mục cổ phiếu Tuần/Tháng.",
    tech: "Nuxt 3 Cockpit",
    status: "Hoàn tất 100%",
  },
]
</script>
