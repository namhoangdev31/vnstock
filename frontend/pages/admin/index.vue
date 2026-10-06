<template>
  <div class="space-y-8">

    <div class="card-aave-dark !p-8 relative overflow-hidden">
      <div class="relative flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div class="space-y-3 max-w-3xl">
          <div class="flex items-center gap-2.5">
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-medium bg-aave-violet/15 text-aave-violet border border-aave-violet/30">
              <span class="w-1.5 h-1.5 rounded-full bg-aave-violet animate-pulse" />
              ENGINE 24/7 ACTIVE
            </span>
            <span class="text-[12px] font-mono text-aave-graphite">TRI-ENGINE QUANTITATIVE ARCHITECTURE</span>
          </div>

          <h1 class="text-2xl sm:text-3xl font-medium tracking-[-1px] text-white">
            Trạm phân tích định lượng & mô phỏng phái sinh VN30F1M
          </h1>
          <p class="text-sm text-aave-graphite leading-relaxed">
            Hệ thống tính toán định lượng liên tục, mô hình hóa kịch bản phiên ATC và tối ưu hóa vị thế phái sinh VN30F1M kèm rổ cổ phiếu T+2 trên nền tảng Nuxt 3 và FastAPI.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3 shrink-0">
          <NuxtLink
            to="/admin/trd/phase-1"
            class="btn-aave-violet !py-3 !px-5 text-xs font-mono font-medium"
          >
            <UIcon name="i-heroicons-document-text" class="w-4 h-4" />
            <span>Đặc tả kỹ thuật TRD</span>
          </NuxtLink>

          <NuxtLink
            to="/admin/trd/phase-4"
            class="btn-aave-ghost-dark !py-3 !px-5 text-xs font-mono font-medium"
          >
            <UIcon name="i-heroicons-arrows-right-left" class="w-4 h-4 text-aave-violet" />
            <span>Paper Trading</span>
          </NuxtLink>

          <NuxtLink
            to="/admin/trd/phase-5"
            class="btn-aave-ghost-dark !py-3 !px-5 text-xs font-mono font-medium"
          >
            <UIcon name="i-heroicons-document-check" class="w-4 h-4 text-aave-violet" />
            <span>Sổ cái dự báo</span>
          </NuxtLink>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-12 gap-6">

      <div class="col-span-12 lg:col-span-7 card-aave-dark space-y-6">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-4">
          <div>
            <span class="text-[12px] font-mono uppercase tracking-wider text-aave-violet font-medium">ENSEMBLE PULSE</span>
            <h2 class="text-[18px] font-medium text-white flex items-center gap-2 mt-0.5 tracking-[-0.3px]">
              <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4 text-aave-violet" />
              Tổng hợp tín hiệu 3 động cơ (Ensemble Decision)
            </h2>
          </div>

          <div class="flex items-center gap-2">
            <span class="px-3 py-1 rounded-full bg-aave-violet/15 text-aave-violet border border-aave-violet/30 text-xs font-mono font-medium flex items-center gap-1.5">
              <UIcon name="i-heroicons-arrow-trending-up" class="w-3.5 h-3.5" />
              LONG BIAS (+64.5 pts)
            </span>
          </div>
        </div>

        <div class="space-y-4 text-xs">

          <div class="space-y-1.5">
            <div class="flex justify-between items-center text-slate-300">
              <span class="font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-aave-violet" />
                Engine 1: Phân tích Kỹ thuật & Khớp lệnh Tick
              </span>
              <span class="font-mono text-aave-violet font-medium">Tỷ trọng: 40% (+48.0)</span>
            </div>
            <div class="w-full bg-white/[0.06] h-2 rounded-full overflow-hidden">
              <div class="bg-aave-violet h-full rounded-full" style="width: 74%" />
            </div>
          </div>

          <div class="space-y-1.5">
            <div class="flex justify-between items-center text-slate-300">
              <span class="font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-white/60" />
                Engine 2: Thanh khoản, Dòng tiền & Mô hình T+2
              </span>
              <span class="font-mono text-white/80 font-medium">Tỷ trọng: 35% (+34.0)</span>
            </div>
            <div class="w-full bg-white/[0.06] h-2 rounded-full overflow-hidden">
              <div class="bg-white/60 h-full rounded-full" style="width: 62%" />
            </div>
          </div>

          <div class="space-y-1.5">
            <div class="flex justify-between items-center text-slate-300">
              <span class="font-medium flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-aave-graphite" />
                Engine 3: Định lượng ML, Basis Spread & Phân loại Regime
              </span>
              <span class="font-mono text-rose-400 font-medium">Tỷ trọng: 25% (-12.0)</span>
            </div>
            <div class="w-full bg-white/[0.06] h-2 rounded-full overflow-hidden">
              <div class="bg-aave-graphite h-full rounded-full" style="width: 44%" />
            </div>
          </div>
        </div>

        <div class="p-4 rounded-[14px] bg-black/40 border border-white/[0.06] flex items-center justify-between text-xs">
          <span class="text-aave-graphite font-mono text-[12px]">Độ tin cậy Ensemble:</span>
          <span class="text-aave-violet font-mono font-medium">67.8% (Xác suất nghiêng Long ATO/ATC)</span>
        </div>
      </div>

      <div class="col-span-12 lg:col-span-5 card-aave-dark space-y-4 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div>
              <span class="text-[12px] font-mono uppercase tracking-wider text-aave-violet font-medium">HỢP ĐỒNG PHÁI SINH</span>
              <h2 class="text-[18px] font-medium text-white font-mono flex items-center gap-1.5">
                VN30F1M (T+0 Intraday)
              </h2>
            </div>
            <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-aave-violet/15 text-aave-violet border border-aave-violet/30">
              Theo dõi liên tục
            </span>
          </div>

          <div class="pt-4 space-y-4">
            <div class="flex items-baseline justify-between">
              <span class="text-xs text-aave-graphite">Giá khớp gần nhất:</span>
              <span class="text-3xl font-mono font-medium text-white">1,318.50</span>
            </div>

            <div class="grid grid-cols-2 gap-3 text-xs font-mono">
              <div class="p-3 rounded-[12px] bg-black/40 border border-white/[0.06]">
                <div class="text-[11px] text-aave-graphite">VN30 Cơ sở</div>
                <div class="font-medium text-white mt-1 text-sm">1,320.80</div>
              </div>
              <div class="p-3 rounded-[12px] bg-black/40 border border-white/[0.06]">
                <div class="text-[11px] text-aave-graphite">Độ lệch Basis</div>
                <div class="font-medium text-aave-violet mt-1 text-sm">-2.30 pts</div>
              </div>
            </div>

            <div class="p-3.5 rounded-[12px] bg-black/40 border border-white/[0.06] text-[12px] text-aave-graphite">
              <div class="flex items-center justify-between mb-1.5">
                <span>Biên độ phiên:</span>
                <span class="font-mono text-white">1,312.00 - 1,326.50</span>
              </div>
              <div class="w-full bg-white/[0.06] h-1.5 rounded-full overflow-hidden">
                <div class="bg-aave-violet h-full rounded-full" style="width: 45%" />
              </div>
            </div>
          </div>
        </div>

        <div class="pt-2">
          <NuxtLink
            to="/admin/trd/phase-4"
            class="btn-aave-outline-violet w-full !py-2.5 text-xs font-mono font-medium"
          >
            <span>Mở giả lập vị thế VN30F1M</span>
            <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5" />
          </NuxtLink>
        </div>
      </div>

      <div class="col-span-12 sm:col-span-6 lg:col-span-4 card-aave-dark space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[12px] font-mono uppercase tracking-wider text-aave-violet font-medium">SETTLEMENT CYCLE</span>
          <UIcon name="i-heroicons-calendar" class="w-4 h-4 text-aave-violet" />
        </div>
        <div class="text-[18px] font-medium text-white tracking-[-0.3px]">Chuẩn thanh toán T+2</div>
        <p class="text-xs text-aave-graphite leading-relaxed">
          Mô hình hóa chặt chẽ dòng tiền mua/bán, phân tách cổ phiếu chờ về lúc 13:00 phiên chiều T+2 và hạn chế rủi ro đòn bẩy.
        </p>
        <div class="pt-2 flex items-center gap-2 text-[12px] font-mono text-aave-violet">
          <span class="w-1.5 h-1.5 rounded-full bg-aave-violet" />
          <span>Cách ly sức mua Sandbox</span>
        </div>
      </div>

      <div class="col-span-12 sm:col-span-6 lg:col-span-4 card-aave-dark space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[12px] font-mono uppercase tracking-wider text-aave-violet font-medium">SIGNAL AUDIT LEDGER</span>
          <UIcon name="i-heroicons-archive-box" class="w-4 h-4 text-aave-violet" />
        </div>
        <div class="text-[18px] font-medium text-white tracking-[-0.3px]">Sổ nhật ký dự báo</div>
        <p class="text-xs text-aave-graphite leading-relaxed">
          Lưu vết 100% tín hiệu tại thời điểm phát sinh (Pending), tự động đối soát sau phiên và tính điểm sai số Brier Score/MAE.
        </p>
        <div class="pt-2 flex items-center gap-2 text-[12px] font-mono text-aave-violet">
          <span class="w-1.5 h-1.5 rounded-full bg-aave-violet" />
          <span>Zero Look-ahead Bias</span>
        </div>
      </div>

      <div class="col-span-12 sm:col-span-12 lg:col-span-4 card-aave-dark space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[12px] font-mono uppercase tracking-wider text-aave-violet font-medium">ANTI-OVERFIT FEEDBACK</span>
          <UIcon name="i-heroicons-arrow-path-rounded-square" class="w-4 h-4 text-aave-violet" />
        </div>
        <div class="text-[18px] font-medium text-white tracking-[-0.3px]">Tự học có kiểm soát</div>
        <p class="text-xs text-aave-graphite leading-relaxed">
          Hiệu chuẩn trọng số Engine qua Softmax rolling 30 phiên. Giới hạn dịch chuyển tối đa 5%/kỳ kèm cơ chế Circuit Breaker an toàn.
        </p>
        <div class="pt-2 flex items-center gap-2 text-[12px] font-mono text-aave-violet">
          <span class="w-1.5 h-1.5 rounded-full bg-aave-violet" />
          <span>Auto-Promote & Safety Switch</span>
        </div>
      </div>
    </div>

    <div class="space-y-5 pt-4">
      <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
        <div>
          <h2 class="text-xl font-medium text-white tracking-[-0.5px] flex items-center gap-2">
            <UIcon name="i-heroicons-rectangle-stack" class="w-5 h-5 text-aave-violet" />
            Lộ trình triển khai kỹ thuật (TRD 6 Phases)
          </h2>
          <p class="text-xs text-aave-graphite mt-0.5">Tài liệu đặc tả kiến trúc, ma trận kiểm thử và trạm thử nghiệm tương tác từng phân hệ</p>
        </div>

        <span class="hidden sm:inline-flex text-[11px] font-mono font-medium text-aave-violet bg-aave-violet/10 px-3 py-1 rounded-full border border-aave-violet/20">
          100% SPECS COMPLETE
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <NuxtLink
          v-for="phase in phases"
          :key="phase.id"
          :to="phase.path"
          class="card-aave-dark hover:border-aave-violet/50 transition-all group flex flex-col justify-between space-y-4"
        >
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-mono font-medium uppercase tracking-wider text-aave-violet">
                PHASE 0{{ phase.id }}
              </span>
              <span class="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-white/[0.04] text-aave-graphite">
                {{ phase.status }}
              </span>
            </div>

            <h3 class="text-base font-medium text-white group-hover:text-aave-violet transition-colors tracking-[-0.3px]">
              {{ phase.title }}
            </h3>

            <p class="text-xs text-aave-graphite leading-relaxed">
              {{ phase.desc }}
            </p>
          </div>

          <div class="pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-aave-graphite group-hover:text-white transition-colors font-mono">
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
  title: "Bảng Điều Khiển Quản Trị - Vnstock TRD 24/7",
})

const phases = [
  {
    id: 1,
    path: "/admin/trd/phase-1",
    title: "Nền Tảng Dữ Liệu & Persistence",
    desc: "PostgreSQL-first storage, rate limiting chống ban IP, schema audit log và models chuẩn timezone aware.",
    tech: "PostgreSQL / SQLModel",
    status: "Hoàn tất 100%",
  },
  {
    id: 2,
    path: "/admin/trd/phase-2",
    title: "Tri-Engine Analytics Core & Ensemble",
    desc: "Phối hợp 3 động cơ độc lập: Kỹ thuật, Dòng tiền và Quant ML với trọng số động và thuật toán Softmax.",
    tech: "Tri-Engine Ensemble",
    status: "Hoàn tất 100%",
  },
  {
    id: 3,
    path: "/admin/trd/phase-3",
    title: "Background Session Daemon 24/7",
    desc: "Vòng lặp tính toán tự động không gián đoạn từ ATO, phiên sáng, nghỉ trưa, phiên chiều đến khớp lệnh ATC.",
    tech: "Continuous Daemon 24/7",
    status: "Hoàn tất 100%",
  },
  {
    id: 4,
    path: "/admin/trd/phase-4",
    title: "Paper Trading Engine & Phái Sinh VN30F1M",
    desc: "Mô phỏng vị thế Long/Short phái sinh T+0 và cổ phiếu T+2 trong môi trường cách ly an toàn, tuyệt đối không dùng tiền thật.",
    tech: "Sandbox Simulation",
    status: "Hoàn tất 100%",
  },
  {
    id: 5,
    path: "/admin/trd/phase-5",
    title: "Sổ Nhật Ký Dự Báo & Vòng Lặp Tự Học",
    desc: "Sổ cái lưu vết dự báo bất biến, đối soát kết quả sau phiên, tính điểm Brier Score và hiệu chuẩn chống Overfitting.",
    tech: "Forecast Journal",
    status: "Hoàn tất 100%",
  },
  {
    id: 6,
    path: "/admin/trd/phase-6",
    title: "Giao Diện Ứng Dụng & Alpha Basket",
    desc: "Giao diện trạm điều hành lượng hóa, kiểm soát luồng dữ liệu thời gian thực và phân bổ rổ danh mục cổ phiếu Tuần/Tháng.",
    tech: "Nuxt 3 App",
    status: "Hoàn tất 100%",
  },
]
</script>
