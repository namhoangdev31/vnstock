<template>
  <div class="min-h-screen bg-[#07090e] text-slate-100 font-sans selection:bg-emerald-500 selection:text-white relative overflow-x-hidden">
    <!-- Atmospheric Ambient Lighting -->
    <div class="absolute -top-32 left-1/2 -translate-x-1/2 w-[1000px] h-[450px] bg-gradient-to-b from-emerald-500/10 via-teal-500/5 to-transparent rounded-full blur-3xl pointer-events-none" />
    <div class="absolute top-[800px] -left-64 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
    <div class="absolute top-[1600px] -right-64 w-96 h-96 bg-teal-500/5 rounded-full blur-3xl pointer-events-none" />

    <!-- Top Public Navigation Header -->
    <header class="sticky top-0 z-50 backdrop-blur-xl bg-[#07090e]/85 border-b border-white/[0.06]">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <!-- Brand -->
        <NuxtLink to="/" class="flex items-center gap-3 group">
          <div class="h-9 w-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center font-mono font-bold text-white text-sm shadow-md shadow-emerald-500/20 ring-1 ring-white/10 group-hover:scale-105 transition-transform">
            VN
          </div>
          <div class="flex flex-col">
            <span class="font-bold tracking-tight text-sm text-white flex items-center gap-1.5 font-mono">
              VNSTOCK
              <span class="text-[9px] uppercase font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">QUANTS</span>
            </span>
            <span class="text-[10px] text-slate-400 font-mono tracking-tight">Quantitative & Analytics 24/7</span>
          </div>
        </NuxtLink>

        <!-- Center Nav Links (Desktop) -->
        <nav class="hidden md:flex items-center gap-6 text-xs font-mono">
          <a href="#tri-engine" class="text-slate-400 hover:text-emerald-400 transition-colors">Tri-Engine Core</a>
          <a href="#full-session" class="text-slate-400 hover:text-emerald-400 transition-colors">Chu kỳ ATO-ATC</a>
          <a href="#self-learning" class="text-slate-400 hover:text-emerald-400 transition-colors">Tự học & Sổ cái</a>
          <a href="#trd-specs" class="text-slate-400 hover:text-emerald-400 transition-colors">Đặc tả 6 Phases</a>
        </nav>

        <!-- Right Action CTAs -->
        <div class="flex items-center gap-3">
          <div class="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-white/[0.03] border border-white/[0.06] text-[11px] font-mono">
            <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span class="text-emerald-400 font-bold">LIVE TELEMETRY</span>
          </div>

          <template v-if="token">
            <NuxtLink
              to="/admin"
              class="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold font-mono rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/25 transition-all"
            >
              <UIcon name="i-heroicons-squares-2x2" class="w-4 h-4" />
              <span>Vào Cockpit Điều Hành</span>
            </NuxtLink>
          </template>
          <template v-else>
            <NuxtLink
              to="/login"
              class="px-3.5 py-2 text-xs font-medium font-mono text-slate-300 hover:text-white rounded-lg hover:bg-white/[0.05] transition-colors"
            >
              Đăng nhập
            </NuxtLink>
            <NuxtLink
              to="/signup"
              class="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold font-mono rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/25 transition-all"
            >
              <span>Mở Sandbox</span>
              <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5" />
            </NuxtLink>
          </template>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main>
      <!-- Hero Section -->
      <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-20 lg:pt-24 lg:pb-28">
        <div class="grid grid-cols-12 gap-8 lg:gap-12 items-center">
          <!-- Hero Left Column: Positioning & CTAs -->
          <div class="col-span-12 lg:col-span-7 space-y-6">
            <!-- Institutional Badge -->
            <div class="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>HỆ THỐNG ĐỊNH LƯỢNG 24/7 DÀNH RIÊNG CHO THỊ TRƯỜNG VIỆT NAM</span>
            </div>

            <!-- Headline: strictly <= 2 lines -->
            <h1 class="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight leading-tight">
              Động Cơ Lượng Hóa Phái Sinh VN30F1M Và Cổ Phiếu T+2
            </h1>

            <!-- Value Proposition Statement -->
            <p class="text-sm sm:text-base text-slate-300 leading-relaxed max-w-2xl">
              Nền tảng chạy nền liên tục kết hợp 3 Động cơ độc lập: Hành vi giá & Tick Khớp lệnh, Dòng vốn tổ chức & Chu kỳ T+2, cùng Học máy xác suất với cơ chế Auto-Promote và Circuit Breaker tự động.
            </p>

            <!-- Metrics Strip -->
            <div class="grid grid-cols-3 gap-3 pt-2 max-w-xl">
              <div class="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div class="text-[10px] font-mono text-slate-400 uppercase">Chu kỳ khớp lệnh</div>
                <div class="text-lg font-bold font-mono text-emerald-400 tabular-nums">08:45 - 14:45</div>
                <div class="text-[10px] text-slate-400">Từ ATO tới ATC</div>
              </div>

              <div class="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div class="text-[10px] font-mono text-slate-400 uppercase">Tần suất dữ liệu</div>
                <div class="text-lg font-bold font-mono text-teal-400 tabular-nums">1m & Tick Delta</div>
                <div class="text-[10px] text-slate-400">VCI / TCBS API</div>
              </div>

              <div class="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                <div class="text-[10px] font-mono text-slate-400 uppercase">Cách ly Sandbox</div>
                <div class="text-lg font-bold font-mono text-white tabular-nums">100% Paper</div>
                <div class="text-[10px] text-slate-400">Tuân thủ Rule 1 & 2</div>
              </div>
            </div>

            <!-- Hero Action Buttons -->
            <div class="flex flex-wrap items-center gap-3.5 pt-2">
              <NuxtLink
                to="/admin"
                class="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl text-sm font-bold font-mono bg-emerald-600 hover:bg-emerald-500 text-white shadow-xl shadow-emerald-600/30 transition-all group"
              >
                <UIcon name="i-heroicons-computer-desktop" class="w-5 h-5 transition-transform group-hover:scale-110" />
                <span>Truy cập Trạm Cockpit</span>
              </NuxtLink>

              <NuxtLink
                to="/admin/trd/phase-1"
                class="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium font-mono text-slate-200 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] transition-all"
              >
                <UIcon name="i-heroicons-document-text" class="w-4 h-4 text-emerald-400" />
                <span>Khám phá 6 Phase TRD</span>
              </NuxtLink>
            </div>

            <div class="flex items-center gap-4 text-xs text-slate-400 font-mono">
              <span class="flex items-center gap-1.5">
                <UIcon name="i-heroicons-check-circle" class="w-4 h-4 text-emerald-400" />
                Không kết nối lệnh tiền thật
              </span>
              <span class="flex items-center gap-1.5">
                <UIcon name="i-heroicons-check-circle" class="w-4 h-4 text-emerald-400" />
                Lưu vết Sổ nhật ký dự báo
              </span>
            </div>
          </div>

          <!-- Hero Right Column: Live Simulated Terminal Widget -->
          <div class="col-span-12 lg:col-span-5">
            <div class="rounded-2xl bg-[#090d16] border border-white/[0.1] shadow-2xl overflow-hidden relative group">
              <!-- Window Top Bar -->
              <div class="p-3 bg-[#0b101c] border-b border-white/[0.06] flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <div class="flex gap-1.5">
                    <div class="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                    <div class="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                    <div class="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                  </div>
                  <span class="text-[11px] font-mono text-slate-400 pl-2">VN30F1M // LIVE DESK PULSE</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-[10px] font-mono text-emerald-400 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                    ONLINE
                  </span>
                </div>
              </div>

              <!-- Terminal Body Content -->
              <div class="p-5 space-y-4">
                <!-- Instrument Main Line -->
                <div class="flex items-baseline justify-between">
                  <div>
                    <span class="text-2xl font-bold font-mono text-white tracking-tight">1,318.50</span>
                    <span class="ml-2 text-xs font-mono font-bold text-emerald-400">+6.40 (+0.49%)</span>
                  </div>
                  <div class="text-right">
                    <div class="text-[10px] font-mono text-slate-400 uppercase">Basis Spread</div>
                    <div class="text-xs font-bold font-mono text-rose-400">-2.30 pts</div>
                  </div>
                </div>

                <!-- Tri-Engine Weights Bar -->
                <div class="space-y-1.5 pt-1">
                  <div class="flex items-center justify-between text-[11px] font-mono">
                    <span class="text-slate-400">Trọng số 3 Engine:</span>
                    <span class="text-emerald-400">W1: 38% | W2: 32% | W3: 30%</span>
                  </div>
                  <div class="h-2 w-full rounded-full bg-white/[0.06] overflow-hidden flex">
                    <div class="h-full bg-emerald-500" style="width: 38%" title="Engine 1: Technical" />
                    <div class="h-full bg-teal-400" style="width: 32%" title="Engine 2: Flow & T+2" />
                    <div class="h-full bg-cyan-400" style="width: 30%" title="Engine 3: Quant ML" />
                  </div>
                </div>

                <!-- Order Flow Delta Box -->
                <div class="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
                  <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                    <div class="text-[10px] text-slate-400">LỆNH MUA CHỦ ĐỘNG</div>
                    <div class="text-emerald-400 font-bold mt-0.5">14,820 HĐ (56%)</div>
                  </div>
                  <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                    <div class="text-[10px] text-slate-400">LỆNH BÁN CHỦ ĐỘNG</div>
                    <div class="text-rose-400 font-bold mt-0.5">11,640 HĐ (44%)</div>
                  </div>
                </div>

                <!-- Scenario Analysis Output -->
                <div class="p-3 rounded-xl bg-emerald-500/[0.05] border border-emerald-500/20 space-y-1.5">
                  <div class="flex items-center justify-between text-[11px] font-mono">
                    <span class="text-emerald-400 font-bold">TÍN HIỆU KHỚP LỆNH ATC DỰ BÁO</span>
                    <span class="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">LONG BIAS</span>
                  </div>
                  <p class="text-xs text-slate-300 leading-relaxed font-sans">
                    Xác suất nghiêng về phe Mua 68.4%. Giá đóng cửa kỳ vọng: <span class="font-mono text-emerald-400 font-bold">1,321.2</span>. Dòng tiền Tự doanh tích lũy ròng +1,450 HĐ.
                  </p>
                </div>

                <!-- Quick Terminal Action -->
                <NuxtLink
                  to="/admin"
                  class="w-full py-2.5 text-xs font-mono font-semibold rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-emerald-400 border border-white/[0.08] flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span>Mở bảng điều khiển chi tiết</span>
                  <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5" />
                </NuxtLink>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Section 1: Tri-Engine Analytics Architecture -->
      <section id="tri-engine" class="py-20 border-t border-white/[0.06] bg-[#080c14]">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div class="text-center max-w-3xl mx-auto space-y-3">
            <span class="text-[10px] font-mono uppercase tracking-widest text-emerald-400 font-bold">
              KIẾN TRÚC LÕI
            </span>
            <h2 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Tam Trụ Động Cơ Định Lượng Độc Lập
            </h2>
            <p class="text-xs sm:text-sm text-slate-400 leading-relaxed">
              Mọi quyết định dự báo và khuyến nghị vị thế đều được kiểm chứng chéo qua 3 động cơ độc lập để triệt tiêu độ nhiễu và loại trừ bias đơn lẻ.
            </p>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Engine 1 -->
            <div class="p-6 rounded-2xl bg-[#090d16] border border-white/[0.08] hover:border-emerald-500/40 transition-all flex flex-col justify-between space-y-4">
              <div class="space-y-3">
                <div class="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <UIcon name="i-heroicons-chart-bar" class="w-5 h-5 text-emerald-400" />
                </div>
                <div class="text-[10px] font-mono text-emerald-400 font-bold uppercase tracking-wider">ENGINE 01</div>
                <h3 class="text-lg font-bold text-white font-mono">Kỹ Thuật & Price-Action</h3>
                <p class="text-xs text-slate-400 leading-relaxed font-sans">
                  Xử lý nến đa khung thời gian (1m, 5m, 15m, 1D), quét thanh khoản (Liquidity Sweeps), Fair Value Gaps và phân tích dòng khớp lệnh tick-by-tick chủ động.
                </p>
              </div>
              <ul class="text-[11px] font-mono text-slate-400 space-y-1.5 pt-3 border-t border-white/[0.06]">
                <li class="flex items-center gap-2">
                  <UIcon name="i-heroicons-chevron-right" class="w-3 h-3 text-emerald-400" />
                  <span>Order Matching Delta & VWAP</span>
                </li>
                <li class="flex items-center gap-2">
                  <UIcon name="i-heroicons-chevron-right" class="w-3 h-3 text-emerald-400" />
                  <span>Bollinger Bands & Dynamic ATR</span>
                </li>
              </ul>
            </div>

            <!-- Engine 2 -->
            <div class="p-6 rounded-2xl bg-[#090d16] border border-white/[0.08] hover:border-teal-500/40 transition-all flex flex-col justify-between space-y-4">
              <div class="space-y-3">
                <div class="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center">
                  <UIcon name="i-heroicons-banknotes" class="w-5 h-5 text-teal-400" />
                </div>
                <div class="text-[10px] font-mono text-teal-400 font-bold uppercase tracking-wider">ENGINE 02</div>
                <h3 class="text-lg font-bold text-white font-mono">Dòng Tiền & Chu Kỳ T+2</h3>
                <p class="text-xs text-slate-400 leading-relaxed font-sans">
                  Giám sát dòng vốn Khối ngoại và Tự doanh, độ rộng thị trường, biến động vĩ mô (Tỷ giá USD/VND, vàng SJC) và giải tỏa dòng tiền cổ phiếu T+2 phiên chiều.
                </p>
              </div>
              <ul class="text-[11px] font-mono text-slate-400 space-y-1.5 pt-3 border-t border-white/[0.06]">
                <li class="flex items-center gap-2">
                  <UIcon name="i-heroicons-chevron-right" class="w-3 h-3 text-teal-400" />
                  <span>Dòng tiền tổ chức Khối ngoại & Tự doanh</span>
                </li>
                <li class="flex items-center gap-2">
                  <UIcon name="i-heroicons-chevron-right" class="w-3 h-3 text-teal-400" />
                  <span>Mô hình hóa thanh khoản cổ phiếu T+2</span>
                </li>
              </ul>
            </div>

            <!-- Engine 3 -->
            <div class="p-6 rounded-2xl bg-[#090d16] border border-white/[0.08] hover:border-cyan-500/40 transition-all flex flex-col justify-between space-y-4">
              <div class="space-y-3">
                <div class="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
                  <UIcon name="i-heroicons-cpu-chip" class="w-5 h-5 text-cyan-400" />
                </div>
                <div class="text-[10px] font-mono text-cyan-400 font-bold uppercase tracking-wider">ENGINE 03</div>
                <h3 class="text-lg font-bold text-white font-mono">Định Lượng Xác Suất & ML</h3>
                <p class="text-xs text-slate-400 leading-relaxed font-sans">
                  Đo lường độ lệch Basis Spread (VN30F1M so với rổ chỉ số VN30), mô hình hóa xác suất dịch chuyển gap ATO và tính toán cân bằng cung cầu phiên ATC.
                </p>
              </div>
              <ul class="text-[11px] font-mono text-slate-400 space-y-1.5 pt-3 border-t border-white/[0.06]">
                <li class="flex items-center gap-2">
                  <UIcon name="i-heroicons-chevron-right" class="w-3 h-3 text-cyan-400" />
                  <span>Biên độ kinh doanh chênh lệch Basis</span>
                </li>
                <li class="flex items-center gap-2">
                  <UIcon name="i-heroicons-chevron-right" class="w-3 h-3 text-cyan-400" />
                  <span>Dự báo cân bằng khớp lệnh ATC</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <!-- Section 2: Full-Session ATO-ATC Protocol -->
      <section id="full-session" class="py-20 border-t border-white/[0.06]">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
          <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <span class="text-[10px] font-mono uppercase tracking-widest text-emerald-400 font-bold">
                CHU TRÌNH PHIÊN GIAO DỊCH
              </span>
              <h2 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
                Theo Dõi Toàn Diện Mọi Giai Đoạn Phiên
              </h2>
            </div>
            <p class="text-xs text-slate-400 max-w-md">
              Hệ thống xử lý liên tục qua 5 giai đoạn phiên, không bỏ sót bất kỳ biến động nào từ giá mở cửa ATO tới giá đóng cửa ATC.
            </p>
          </div>

          <!-- Session Timeline Steps -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div class="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
              <div class="text-[11px] font-mono font-bold text-slate-400">08:30 - 08:45</div>
              <div class="text-xs font-bold text-white font-mono">Chuẩn bị ATO</div>
              <p class="text-[11px] text-slate-400 leading-relaxed font-sans">
                Đồng bộ giá thanh toán phiên trước, cập nhật điểm Pivot và độ lệch cơ sở qua đêm.
              </p>
            </div>

            <div class="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
              <div class="text-[11px] font-mono font-bold text-amber-400">08:45 - 09:00</div>
              <div class="text-xs font-bold text-white font-mono">Phiên khớp ATO</div>
              <p class="text-[11px] text-slate-400 leading-relaxed font-sans">
                Theo dõi lệnh ước lượng khớp ATO, phân loại Opening Gap và xác định tâm lý phiên sớm.
              </p>
            </div>

            <div class="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
              <div class="text-[11px] font-mono font-bold text-emerald-400">09:00 - 11:30</div>
              <div class="text-xs font-bold text-white font-mono">Khớp lệnh sáng</div>
              <p class="text-[11px] text-slate-400 leading-relaxed font-sans">
                Tính toán nến 1m, theo dõi VWAP, bắt điểm Breakout và ghi nhận lệnh giấy trong Sandbox.
              </p>
            </div>

            <div class="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
              <div class="text-[11px] font-mono font-bold text-slate-400">11:30 - 13:00</div>
              <div class="text-xs font-bold text-white font-mono">Nghỉ trưa</div>
              <p class="text-[11px] text-slate-400 leading-relaxed font-sans">
                Tái tính toán ngầm, đánh giá rổ VN30 và chuẩn bị kịch bản biến động phiên chiều.
              </p>
            </div>

            <div class="p-4 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/30 space-y-2">
              <div class="text-[11px] font-mono font-bold text-emerald-400">14:15 - 14:45</div>
              <div class="text-xs font-bold text-white font-mono">Phiên Khớp ATC</div>
              <p class="text-[11px] text-slate-300 leading-relaxed font-sans">
                Kích hoạt Engine dự báo ATC, tính khối lượng cơ cấu và xác định giá đóng cửa tối ưu.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- Section 3: Self-Learning Loop & Forecast Journal -->
      <section id="self-learning" class="py-20 border-t border-white/[0.06] bg-[#080c14]">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div class="grid grid-cols-12 gap-8 items-center">
            <div class="col-span-12 lg:col-span-6 space-y-5">
              <span class="text-[10px] font-mono uppercase tracking-widest text-emerald-400 font-bold">
                TỰ HỌC BẤT BIẾN (PHASE 5)
              </span>
              <h2 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Sổ Cái Dự Báo & Vòng Lặp Hiệu Chuẩn Tự Động
              </h2>
              <p class="text-xs sm:text-sm text-slate-300 leading-relaxed">
                Mọi dự báo đều được ghi nhận vĩnh viễn vào SQLModel Ledger trước khi thực tế diễn ra (chống Look-ahead bias tuyệt đối). Sau phiên, hệ thống tự đối soát kết quả thực tế, tính Brier Score và tự động nâng cấp trọng số khi qua cổng Out-Of-Sample.
              </p>

              <div class="space-y-3 pt-2">
                <div class="flex items-start gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <UIcon name="i-heroicons-arrow-path" class="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <div class="text-xs font-bold text-white font-mono">Tự Động Nâng Cấp Trọng Số (Auto-Promote)</div>
                    <p class="text-[11px] text-slate-400 mt-0.5">
                      Đạt chuẩn kiểm định Out-of-sample 30 phiên, cải thiện Brier score thì tự động áp dụng trọng số mới mà không cần can thiệp thủ công.
                    </p>
                  </div>
                </div>

                <div class="flex items-start gap-3 p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06]">
                  <UIcon name="i-heroicons-shield-exclamation" class="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <div class="text-xs font-bold text-white font-mono">Cầu Dao An Toàn Tự Động (Circuit Breaker)</div>
                    <p class="text-[11px] text-slate-400 mt-0.5">
                      Nếu sai số vượt ngưỡng hoặc 3 phiên liên tiếp không đạt, hệ thống lập tức khóa Auto-Promote và hoàn nguyên về trọng số an toàn mặc định (0.33, 0.33, 0.34).
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Visual Flow Illustration -->
            <div class="col-span-12 lg:col-span-6">
              <div class="p-6 rounded-2xl bg-[#090d16] border border-white/[0.08] space-y-4 font-mono text-xs">
                <div class="text-[11px] text-slate-400 uppercase border-b border-white/[0.06] pb-2">
                  QUY TRÌNH HỌC MÁY KHÉP KÍN // CLOSED-LOOP ML
                </div>

                <div class="space-y-3">
                  <div class="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] flex items-center justify-between">
                    <span class="text-slate-300">1. Phát sinh dự báo (Pending)</span>
                    <span class="text-emerald-400">Ghi Ledger bất biến</span>
                  </div>

                  <div class="text-center text-slate-500">↓ Thị trường đóng cửa (ATC)</div>

                  <div class="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] flex items-center justify-between">
                    <span class="text-slate-300">2. Đối soát thực tế & Chấm điểm</span>
                    <span class="text-teal-400">Brier Score / MAE</span>
                  </div>

                  <div class="text-center text-slate-500">↓ Kiểm tra OOS Gate (30 phiên)</div>

                  <div class="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between">
                    <span class="text-emerald-300 font-bold">3. Auto-Promote Model Version</span>
                    <span class="text-emerald-400 font-bold">Kích hoạt tức thì</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Section 4: Technical TRD Roadmap (6 Phases) -->
      <section id="trd-specs" class="py-20 border-t border-white/[0.06]">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span class="text-[10px] font-mono uppercase tracking-widest text-emerald-400 font-bold">
                TÀI LIỆU KỸ THUẬT & KIỂM THỬ
              </span>
              <h2 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mt-1">
                Bộ Đặc Tả Kỹ Thuật 6 Phases (TRD)
              </h2>
            </div>
            <span class="text-xs font-mono px-3 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 self-start sm:self-auto">
              100% SPECIFICATIONS READY
            </span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <NuxtLink
              v-for="phase in trdPhases"
              :key="phase.path"
              :to="phase.path"
              class="p-5 rounded-2xl bg-[#090d16] border border-white/[0.08] hover:border-emerald-500/40 hover:bg-[#0c121e] transition-all group flex flex-col justify-between space-y-4"
            >
              <div class="space-y-2">
                <div class="flex items-center justify-between">
                  <span class="text-[10px] font-mono font-bold uppercase text-emerald-400">
                    {{ phase.id }}
                  </span>
                  <UIcon :name="phase.icon" class="w-4 h-4 text-slate-400 group-hover:text-emerald-400 transition-colors" />
                </div>
                <h3 class="text-sm font-bold text-white group-hover:text-emerald-300 transition-colors">
                  {{ phase.title }}
                </h3>
                <p class="text-xs text-slate-400 leading-relaxed font-sans">
                  {{ phase.desc }}
                </p>
              </div>

              <div class="pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs font-mono text-slate-400 group-hover:text-emerald-400 transition-colors">
                <span class="text-[11px]">{{ phase.tech }}</span>
                <UIcon name="i-heroicons-arrow-right" class="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </div>
            </NuxtLink>
          </div>
        </div>
      </section>

      <!-- Institutional Safety & Zero-Real-Money Banner (Rule 1 & Rule 2) -->
      <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div class="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-emerald-950/30 via-[#090d16] to-[#07090e] border border-emerald-500/30 flex flex-col md:flex-row items-center justify-between gap-6">
          <div class="space-y-2 max-w-2xl">
            <div class="flex items-center gap-2 text-xs font-mono font-bold text-emerald-400">
              <UIcon name="i-heroicons-shield-check" class="w-5 h-5 text-emerald-400 shrink-0" />
              <span>CAM KẾT CÁCH LY 100% // ZERO REAL-MONEY TRADING BOTS</span>
            </div>
            <p class="text-xs text-slate-300 leading-relaxed">
              Hệ thống tuyệt đối không tích hợp API đặt lệnh tiền thật với bất kỳ công ty chứng khoán nào (VPS, SSI, TCBS, VND). Mọi tính toán chỉ phục vụ nghiên cứu lượng hóa và môi trường mô phỏng Paper Trading độc lập.
            </p>
          </div>

          <NuxtLink
            to="/admin"
            class="shrink-0 px-6 py-3 rounded-xl text-xs font-bold font-mono bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 transition-all flex items-center gap-2"
          >
            <span>Trải Nghiệm Trạm Cockpit</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="border-t border-white/[0.06] bg-[#07090e] py-10 text-xs text-slate-400">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <div class="h-6 w-6 rounded-md bg-emerald-600 flex items-center justify-center font-mono font-bold text-white text-[10px]">
            VN
          </div>
          <span class="font-mono text-slate-300 font-semibold">Vnstock Quantitative Research & Simulation Engine</span>
        </div>

        <div class="flex items-center gap-6 font-mono text-[11px]">
          <NuxtLink to="/admin" class="hover:text-emerald-400 transition-colors">Trạm Cockpit</NuxtLink>
          <NuxtLink to="/admin/stock" class="hover:text-emerald-400 transition-colors">Thị trường CK</NuxtLink>
          <NuxtLink to="/admin/trd/phase-1" class="hover:text-emerald-400 transition-colors">Đặc tả TRD</NuxtLink>
          <NuxtLink to="/login" class="hover:text-emerald-400 transition-colors">Đăng nhập</NuxtLink>
        </div>

        <div class="text-[11px] font-mono text-slate-400">
          Nuxt 3 + FastAPI DDD // 24/7 Telemetry
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: false,
})

useHead({
  title:
    "Vnstock Quants Engine - Nền Tảng Định Lượng & Mô Phỏng Phái Sinh VN30F1M 24/7",
  meta: [
    {
      name: "description",
      content:
        "Hệ thống nghiên cứu định lượng, dự báo phiên ATC và mô phỏng giao dịch phái sinh VN30F1M, cổ phiếu T+2 hoạt động 24/7.",
    },
  ],
})

const { token } = useAuth()

const trdPhases = [
  {
    id: "PHASE 01",
    path: "/admin/trd/phase-1",
    title: "Phase 1: Nền tảng & Data",
    desc: "PostgreSQL-first storage, rate-limiting chống ban IP, schema audit log và models chuẩn timezone aware.",
    tech: "PostgreSQL / SQLModel",
    icon: "i-heroicons-circle-stack",
  },
  {
    id: "PHASE 02",
    path: "/admin/trd/phase-2",
    title: "Phase 2: Tri-Engine Arch",
    desc: "Phối hợp 3 động cơ độc lập: Kỹ thuật, Dòng tiền và Quant ML với trọng số động và thuật toán Softmax.",
    tech: "Tri-Engine Ensemble",
    icon: "i-heroicons-cpu-chip",
  },
  {
    id: "PHASE 03",
    path: "/admin/trd/phase-3",
    title: "Phase 3: Daemon 24/7",
    desc: "Vòng lặp tính toán tự động không gián đoạn từ ATO, phiên sáng, nghỉ trưa, phiên chiều đến khớp lệnh ATC.",
    tech: "Continuous Daemon 24/7",
    icon: "i-heroicons-clock",
  },
  {
    id: "PHASE 04",
    path: "/admin/trd/phase-4",
    title: "Phase 4: Phái sinh & T+2",
    desc: "Mô phỏng vị thế Long/Short phái sinh T+0 và cổ phiếu T+2 trong môi trường cách ly an toàn, tuyệt đối không dùng tiền thật.",
    tech: "Sandbox Simulation",
    icon: "i-heroicons-arrows-right-left",
  },
  {
    id: "PHASE 05",
    path: "/admin/trd/phase-5",
    title: "Phase 5: Sổ cái dự báo",
    desc: "Sổ cái lưu vết dự báo bất biến, đối soát kết quả sau phiên, tính điểm Brier Score và hiệu chuẩn chống Overfitting.",
    tech: "Forecast Journal",
    icon: "i-heroicons-document-check",
  },
  {
    id: "PHASE 06",
    path: "/admin/trd/phase-6",
    title: "Phase 6: Trạm Cockpit",
    desc: "Giao diện trạm điều hành lượng hóa, kiểm soát luồng dữ liệu thời gian thực và phân bổ rổ danh mục cổ phiếu Tuần/Tháng.",
    tech: "Nuxt 3 Cockpit",
    icon: "i-heroicons-computer-desktop",
  },
]
</script>
