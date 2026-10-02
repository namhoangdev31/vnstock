<template>
  <div class="min-h-screen font-sans selection:bg-aave-violet selection:text-aave-charcoal relative overflow-x-hidden antialiased">

    <div class="bg-aave-paper text-aave-obsidian relative">

      <div class="absolute inset-0 bg-surface-lavender opacity-35 pointer-events-none" />

      <header class="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-black/[0.06] transition-colors">
        <div class="max-w-[1200px] mx-auto px-6 h-18 flex items-center justify-between">

          <NuxtLink to="/" class="flex items-center gap-2 group">
            <span class="font-medium tracking-[-0.4px] text-[17px] text-aave-obsidian flex items-center gap-2 font-sans group-hover:text-aave-violet transition-colors">
              Vnstock
              <span class="text-[10px] font-mono uppercase font-medium px-2 py-0.5 rounded-full bg-aave-bone text-aave-iron border border-black/[0.06]">Quants</span>
            </span>
          </NuxtLink>

          <nav class="hidden md:flex items-center gap-7 text-[14px] font-medium text-aave-iron">
            <a href="#tri-engine" class="hover:text-aave-obsidian transition-colors">Tri-Engine Core</a>
            <a href="#full-session" class="hover:text-aave-obsidian transition-colors">Chu kỳ ATO-ATC</a>
            <a href="#self-learning" class="hover:text-aave-obsidian transition-colors">Tự học & Sổ cái</a>
            <a href="#trd-specs" class="hover:text-aave-obsidian transition-colors">Đặc tả 6 Phases</a>
          </nav>

          <div class="flex items-center gap-3">
            <template v-if="token">
              <NuxtLink
                to="/admin"
                class="btn-aave-dark text-sm !py-2.5 !px-5"
              >
                <span>Vào Cockpit Điều Hành</span>
                <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
              </NuxtLink>
            </template>
            <template v-else>
              <NuxtLink
                to="/login"
                class="text-[14px] font-medium text-aave-iron hover:text-aave-obsidian px-3 py-2 transition-colors"
              >
                Đăng nhập
              </NuxtLink>
              <NuxtLink
                to="/signup"
                class="btn-aave-dark text-sm !py-2.5 !px-5"
              >
                <span>Mở Sandbox</span>
              </NuxtLink>
            </template>
          </div>
        </div>
      </header>

      <section class="relative z-10 max-w-[1200px] mx-auto px-6 pt-16 pb-24 text-center">

        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-aave-bone border border-black/[0.06] text-[13px] font-medium text-aave-obsidian mb-6">
          <span class="w-2 h-2 rounded-full bg-aave-violet" />
          <span>Hệ thống lượng hóa 24/7 dành riêng cho thị trường Việt Nam</span>
        </div>

        <h1 class="text-4xl sm:text-5xl lg:text-[62px] font-medium text-aave-obsidian tracking-[-2.5px] leading-[1.08] max-w-4xl mx-auto">
          Động cơ lượng hóa phái sinh VN30F1M và rổ cổ phiếu T+2
        </h1>

        <p class="text-[18px] text-aave-iron leading-relaxed max-w-2xl mx-auto mt-6">
          Nền tảng tính toán chạy nền liên tục kết hợp 3 Động cơ độc lập: Hành vi giá & Tick Khớp lệnh, Dòng vốn tổ chức & Chu kỳ T+2, cùng Học máy xác suất với cơ chế Auto-Promote tự động.
        </p>

        <div class="flex flex-wrap items-center justify-center gap-4 mt-8">
          <NuxtLink
            to="/admin"
            class="btn-aave-violet shadow-sm"
          >
            <span>Truy cập Trạm Cockpit</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>

          <a
            href="#trd-specs"
            class="btn-aave-ghost-light"
          >
            <span>Khám phá 6 Phase TRD</span>
          </a>
        </div>

        <div class="mt-14 max-w-3xl mx-auto bg-white rounded-[20px] p-6 sm:p-8 border border-black/[0.06] shadow-[rgba(0,0,0,0.04)_0px_8px_30px_0px] text-left relative overflow-hidden">

          <div class="flex items-center justify-between pb-5 border-b border-black/[0.06]">
            <div class="flex items-center gap-2.5">
              <span class="w-2.5 h-2.5 rounded-full bg-aave-violet animate-pulse" />
              <span class="text-xs font-mono font-medium text-aave-iron uppercase tracking-wider">
                VN30F1M // DESK PULSE PREVIEW
              </span>
            </div>
            <span class="text-[11px] font-mono px-2.5 py-1 rounded-full bg-aave-bone text-aave-obsidian border border-black/[0.06]">
              TELEMETRY 24/7
            </span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 py-6 border-b border-black/[0.06]">
            <div>
              <div class="text-[13px] font-medium text-aave-iron mb-1">Hợp đồng VN30F1M</div>
              <div class="text-4xl font-medium tracking-[-1px] text-aave-obsidian font-mono tabular-nums">
                1,318.50
              </div>
              <div class="text-[13px] font-medium text-aave-violet mt-1 font-mono">
                +6.40 / +0.49%
              </div>
            </div>

            <div>
              <div class="text-[13px] font-medium text-aave-iron mb-1">Độ lệch Basis Spread</div>
              <div class="text-4xl font-medium tracking-[-1px] text-aave-obsidian font-mono tabular-nums">
                -2.30
              </div>
              <div class="text-[13px] font-medium text-aave-violet mt-1 font-mono">
                Arbitrage Range Safe
              </div>
            </div>

            <div>
              <div class="text-[13px] font-medium text-aave-iron mb-1">Khớp lệnh ATC Dự Báo</div>
              <div class="text-4xl font-medium tracking-[-1px] text-aave-obsidian font-mono tabular-nums">
                1,321.2
              </div>
              <div class="text-[13px] font-medium text-aave-violet mt-1 font-mono">
                Xác suất Long 68.4%
              </div>
            </div>
          </div>

          <div class="pt-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <span class="text-[13px] text-aave-iron">Trọng số 3 Engine:</span>
              <div class="flex items-center gap-1.5 text-xs font-mono font-medium">
                <span class="px-2 py-0.5 rounded-full bg-aave-bone text-aave-obsidian">W1: 38%</span>
                <span class="px-2 py-0.5 rounded-full bg-aave-bone text-aave-obsidian">W2: 32%</span>
                <span class="px-2 py-0.5 rounded-full bg-aave-bone text-aave-obsidian">W3: 30%</span>
              </div>
            </div>

            <NuxtLink
              to="/admin"
              class="text-[13px] font-medium text-aave-violet hover:underline flex items-center gap-1 self-start sm:self-auto"
            >
              <span>Xem Cockpit chi tiết</span>
              <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5" />
            </NuxtLink>
          </div>
        </div>
      </section>
    </div>

    <div class="bg-aave-inkwell text-aave-paper relative">

      <section class="max-w-[1200px] mx-auto px-6 pt-24 pb-20 text-center">
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-aave-obsidian border border-white/[0.08] text-[13px] font-medium text-aave-paper mb-5">
          <span class="w-2 h-2 rounded-full bg-aave-violet" />
          <span>VNSTOCK QUANT PRO ARCHITECTURE</span>
        </div>

        <h2 class="text-3xl sm:text-4xl lg:text-[44px] font-medium text-white tracking-[-1.5px] leading-tight max-w-3xl mx-auto">
          Môi trường mô phỏng & phân tích định lượng chuyên sâu
        </h2>

        <p class="text-[16px] text-aave-graphite max-w-2xl mx-auto mt-4 leading-relaxed">
          Được thiết kế theo chuẩn Aave mixed dual-mood system, cách ly 100% trong Sandbox, bảo đảm an toàn dữ liệu và tuân thủ tuyệt đối quy định thị trường chứng khoán Việt Nam.
        </p>

        <div class="flex items-center justify-center gap-4 mt-8">
          <NuxtLink
            to="/admin"
            class="btn-aave-white"
          >
            <span>Mở Trạm Cockpit</span>
          </NuxtLink>
          <NuxtLink
            to="/admin/stock"
            class="btn-aave-ghost-dark"
          >
            <span>Tra cứu mã cổ phiếu</span>
          </NuxtLink>
        </div>
      </section>

      <section id="tri-engine" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">

        <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-[-1.2px]">
              Tam trụ động cơ định lượng
            </h2>
            <p class="text-[16px] text-aave-graphite mt-2 max-w-xl">
              Ba động cơ hoạt động độc lập và tổng hợp theo phân phối Softmax để lọc nhiễu tín hiệu.
            </p>
          </div>
          <NuxtLink
            to="/admin/trd/phase-2"
            class="btn-aave-outline-violet self-start md:self-auto text-sm !py-2.5 !px-5"
          >
            <span>Đặc tả Phase 2</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

          <div class="card-aave-dark flex flex-col justify-between space-y-6">
            <div class="space-y-4">
              <div class="text-[14px] font-medium text-aave-violet">
                ĐỘNG CƠ 01 // KỸ THUẬT
              </div>
              <h3 class="text-[20px] font-medium text-white tracking-[-0.4px]">
                Price-Action & Lệnh Khớp
              </h3>
              <p class="text-[14px] text-aave-ash leading-relaxed">
                Xử lý nến đa khung thời gian (1m, 5m, 15m, Daily), quét thanh khoản (Liquidity Sweeps), Fair Value Gaps và đo lường áp lực mua/bán chủ động qua dữ liệu tick realtime.
              </p>
            </div>
            <div class="pt-4 border-t border-white/[0.06] text-[13px] text-aave-graphite font-mono flex items-center justify-between">
              <span>Order Flow Delta</span>
              <span class="text-aave-violet">VWAP / ATR</span>
            </div>
          </div>

          <div class="card-aave-dark flex flex-col justify-between space-y-6">
            <div class="space-y-4">
              <div class="text-[14px] font-medium text-aave-violet">
                ĐỘNG CƠ 02 // DÒNG TIỀN T+2
              </div>
              <h3 class="text-[20px] font-medium text-white tracking-[-0.4px]">
                Khối Ngoại & Vĩ Mô
              </h3>
              <p class="text-[14px] text-aave-ash leading-relaxed">
                Theo dõi dòng tiền tổ chức Khối ngoại và Tự doanh, biến động vĩ mô (Tỷ giá USD/VND, vàng SJC) và giải tỏa thanh khoản cổ phiếu lúc 13:00 phiên chiều T+2.
              </p>
            </div>
            <div class="pt-4 border-t border-white/[0.06] text-[13px] text-aave-graphite font-mono flex items-center justify-between">
              <span>T+2 Settlement</span>
              <span class="text-aave-violet">Institutional Flow</span>
            </div>
          </div>

          <div class="card-aave-dark flex flex-col justify-between space-y-6">
            <div class="space-y-4">
              <div class="text-[14px] font-medium text-aave-violet">
                ĐỘNG CƠ 03 // QUANT ML
              </div>
              <h3 class="text-[20px] font-medium text-white tracking-[-0.4px]">
                Xác Suất & Arbitrage Basis
              </h3>
              <p class="text-[14px] text-aave-ash leading-relaxed">
                Theo dõi độ lệch Basis Spread VN30F1M so với rổ chỉ số VN30 cơ sở, mô hình hóa phân phối Opening Gap phiên ATO và dự báo khối lượng cơ cấu cân bằng phiên ATC.
              </p>
            </div>
            <div class="pt-4 border-t border-white/[0.06] text-[13px] text-aave-graphite font-mono flex items-center justify-between">
              <span>Basis Arbitrage</span>
              <span class="text-aave-violet">ATC Equilibrium</span>
            </div>
          </div>
        </div>
      </section>

      <section id="full-session" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="mb-12">
          <div class="text-[14px] font-medium text-aave-violet mb-2">
            CHU TRÌNH 24/7
          </div>
          <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-[-1.2px]">
            Chuỗi theo dõi toàn diện phiên giao dịch
          </h2>
          <p class="text-[16px] text-aave-graphite mt-2 max-w-xl">
            Vòng lặp tính toán liên tục qua 5 giai đoạn không gián đoạn để nhận diện biến động bất thường.
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-[12px] font-mono text-aave-graphite">08:30 - 08:45</div>
            <h4 class="text-[16px] font-medium text-white">Chuẩn bị ATO</h4>
            <p class="text-[13px] text-aave-graphite leading-relaxed">
              Đồng bộ giá thanh toán phiên trước, cập nhật điểm Pivot và độ lệch cơ sở qua đêm.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-[12px] font-mono text-aave-violet">08:45 - 09:00</div>
            <h4 class="text-[16px] font-medium text-white">Phiên khớp ATO</h4>
            <p class="text-[13px] text-aave-graphite leading-relaxed">
              Theo dõi lệnh ước lượng khớp ATO, phân loại Opening Gap và nhận diện sớm xu hướng.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-[12px] font-mono text-aave-paper">09:00 - 11:30</div>
            <h4 class="text-[16px] font-medium text-white">Khớp lệnh sáng</h4>
            <p class="text-[13px] text-aave-graphite leading-relaxed">
              Tính nến 1m, theo dõi VWAP, bắt điểm Breakout và ghi nhận lệnh giấy trong Sandbox.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-[12px] font-mono text-aave-graphite">11:30 - 13:00</div>
            <h4 class="text-[16px] font-medium text-white">Nghỉ trưa</h4>
            <p class="text-[13px] text-aave-graphite leading-relaxed">
              Tái tính toán ngầm, đánh giá rổ VN30 và chuẩn bị kịch bản biến động phiên chiều.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2 border !border-aave-violet/40">
            <div class="text-[12px] font-mono text-aave-violet">14:15 - 14:45</div>
            <h4 class="text-[16px] font-medium text-white">Phiên Khớp ATC</h4>
            <p class="text-[13px] text-aave-ash leading-relaxed">
              Kích hoạt Engine dự báo ATC, tính khối lượng cơ cấu và xác định giá đóng cửa tối ưu.
            </p>
          </div>
        </div>
      </section>

      <section id="self-learning" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div class="space-y-6">
            <div class="text-[14px] font-medium text-aave-violet">
              TỰ HỌC BẤT BIẾN // PHASE 5
            </div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-[-1.2px]">
              Sổ cái dự báo & vòng lặp Auto-Promote
            </h2>
            <p class="text-[16px] text-aave-graphite leading-relaxed">
              Mọi dự báo đều được ghi nhận vĩnh viễn vào SQLModel Ledger trước khi thực tế diễn ra (loại bỏ hoàn toàn Look-ahead bias). Sau phiên, hệ thống tự động đối soát kết quả, tính điểm Brier Score và tự động nâng cấp trọng số khi qua cổng Out-Of-Sample.
            </p>

            <div class="space-y-3 pt-2">
              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-aave-violet" />
                  <div class="flex items-center gap-1.5"><span>Tự động nâng cấp trọng số</span><UTooltip text="Auto-Promote"><UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" /></UTooltip></div>
                </div>
                <p class="text-[13px] text-aave-graphite">
                  Đạt chuẩn kiểm định Out-of-sample 30 phiên thì tự động áp dụng trọng số mới vào luồng tính toán trực tiếp mà không cần can thiệp thủ công.
                </p>
              </div>

              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  <div class="flex items-center gap-1.5"><span>Cầu dao an toàn tự động</span><UTooltip text="Circuit Breaker"><UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" /></UTooltip></div>
                </div>
                <p class="text-[13px] text-aave-graphite">
                  Nếu sai số vượt ngưỡng hoặc 3 phiên liên tiếp không đạt, hệ thống lập tức khóa Auto-Promote và hoàn nguyên về trọng số an toàn mặc định (0.33, 0.33, 0.34).
                </p>
              </div>
            </div>
          </div>

          <div class="card-aave-dark space-y-5 font-mono text-xs">
            <div class="text-[13px] font-medium text-aave-graphite pb-3 border-b border-white/[0.06] flex items-center justify-between">
              <span>CLOSED-LOOP ML PIPELINE</span>
              <span class="text-aave-violet">AUTONOMOUS</span>
            </div>

            <div class="space-y-3">
              <div class="p-3.5 rounded-[12px] bg-black/40 border border-white/[0.06] flex items-center justify-between">
                <div class="flex items-center gap-1.5"><span class="text-white">1. Phát sinh dự báo</span><UTooltip text="Trạng thái Pending"><UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" /></UTooltip></div>
                <span class="text-aave-violet">Ghi Ledger bất biến</span>
              </div>

              <div class="text-center text-aave-graphite">↓ Kết thúc phiên ATC</div>

              <div class="p-3.5 rounded-[12px] bg-black/40 border border-white/[0.06] flex items-center justify-between">
                <span class="text-white">2. Đối soát thực tế & Chấm điểm</span>
                <span class="text-aave-violet">Brier Score / MAE</span>
              </div>

              <div class="text-center text-aave-graphite">↓ Kiểm tra OOS Gate (30 phiên)</div>

              <div class="p-3.5 rounded-[12px] bg-aave-violet/10 border border-aave-violet/30 flex items-center justify-between">
                <span class="text-white font-medium">3. Auto-Promote Model Version</span>
                <span class="text-aave-violet font-bold">Kích hoạt tức thì</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="trd-specs" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-6 mb-12">
          <div>
            <div class="text-[14px] font-medium text-aave-violet mb-2">
              ĐẶC TẢ KỸ THUẬT
            </div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-[-1.2px]">
              Tài liệu kiến trúc 6 Phases (TRD)
            </h2>
            <p class="text-[16px] text-aave-graphite mt-2 max-w-xl">
              Đặc tả kiến trúc hoàn chỉnh, ma trận kiểm thử và trạm thử nghiệm tương tác từng phân hệ.
            </p>
          </div>
          <span class="text-[13px] font-mono px-3.5 py-1.5 rounded-full bg-aave-obsidian text-aave-paper border border-white/[0.08] self-start sm:self-auto">
            100% SPECS COMPLETE
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <NuxtLink
            v-for="phase in trdPhases"
            :key="phase.path"
            :to="phase.path"
            class="card-aave-dark hover:border-aave-violet/50 transition-all flex flex-col justify-between space-y-4 group"
          >
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-[12px] font-mono font-medium text-aave-violet">
                  {{ phase.id }}
                </span>
                <UIcon :name="phase.icon" class="w-4 h-4 text-aave-graphite group-hover:text-aave-violet transition-colors" />
              </div>
              <h3 class="text-[18px] font-medium text-white group-hover:text-aave-violet transition-colors tracking-[-0.4px]">
                {{ phase.title }}
              </h3>
              <p class="text-[13px] text-aave-graphite leading-relaxed">
                {{ phase.desc }}
              </p>
            </div>

            <div class="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[12px] font-mono text-aave-graphite group-hover:text-white transition-colors">
              <span>{{ phase.tech }}</span>
              <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
            </div>
          </NuxtLink>
        </div>
      </section>

      <section class="max-w-[1200px] mx-auto px-6 py-12">
        <div class="rounded-[20px] bg-surface-midnight border border-aave-violet/30 p-8 sm:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
          <div class="space-y-2 max-w-2xl">
            <div class="text-[14px] font-medium text-aave-violet flex items-center gap-2">
              <UIcon name="i-heroicons-shield-check" class="w-5 h-5 text-aave-violet" />
              <span>CAM KẾT CÁCH LY SANDBOX 100% // RULE 1 & RULE 2</span>
            </div>
            <p class="text-[14px] text-aave-ash leading-relaxed">
              Hệ thống tuyệt đối không tích hợp API đặt lệnh tiền thật với bất kỳ công ty chứng khoán nào. Mọi tính toán chỉ phục vụ nghiên cứu lượng hóa và môi trường mô phỏng Paper Trading độc lập.
            </p>
          </div>

          <NuxtLink
            to="/admin"
            class="btn-aave-violet shrink-0"
          >
            <span>Trải nghiệm Trạm Cockpit</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>
        </div>
      </section>

      <footer class="border-t border-white/[0.06] bg-aave-inkwell py-12 text-[13px] text-aave-graphite">
        <div class="max-w-[1200px] mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div class="flex items-center gap-3">
            <NuxtLink to="/" class="hover:text-white transition-colors">
              <span class="text-white font-medium text-[15px] tracking-[-0.3px]">Vnstock Quants</span>
            </NuxtLink>
            <span class="text-aave-iron">|</span>
            <span class="text-aave-graphite">Quantitative Research & Simulation Engine</span>
          </div>

          <div class="flex items-center gap-6 font-medium text-[13px]">
            <NuxtLink to="/admin" class="hover:text-white transition-colors">Trạm Cockpit</NuxtLink>
            <NuxtLink to="/admin/stock" class="hover:text-white transition-colors">Thị trường CK</NuxtLink>
            <NuxtLink to="/admin/trd/phase-1" class="hover:text-white transition-colors">Đặc tả TRD</NuxtLink>
            <NuxtLink to="/login" class="hover:text-white transition-colors">Đăng nhập</NuxtLink>
          </div>

          <div class="font-mono text-[12px] text-aave-iron">
            Aave Design System // Mixed Dual-Mood
          </div>
        </div>
      </footer>
    </div>
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
    title: "Nền tảng & Data",
    desc: "PostgreSQL-first storage, rate-limiting chống ban IP, schema audit log và models chuẩn timezone aware.",
    tech: "PostgreSQL / SQLModel",
    icon: "i-heroicons-circle-stack",
  },
  {
    id: "PHASE 02",
    path: "/admin/trd/phase-2",
    title: "Tri-Engine Arch",
    desc: "Phối hợp 3 động cơ độc lập: Kỹ thuật, Dòng tiền và Quant ML với trọng số động và thuật toán Softmax.",
    tech: "Tri-Engine Ensemble",
    icon: "i-heroicons-cpu-chip",
  },
  {
    id: "PHASE 03",
    path: "/admin/trd/phase-3",
    title: "Daemon 24/7",
    desc: "Vòng lặp tính toán tự động không gián đoạn từ ATO, phiên sáng, nghỉ trưa, phiên chiều đến khớp lệnh ATC.",
    tech: "Continuous Daemon 24/7",
    icon: "i-heroicons-clock",
  },
  {
    id: "PHASE 04",
    path: "/admin/trd/phase-4",
    title: "Phái sinh & T+2",
    desc: "Mô phỏng vị thế Long/Short phái sinh T+0 và cổ phiếu T+2 trong môi trường cách ly an toàn, tuyệt đối không dùng tiền thật.",
    tech: "Sandbox Simulation",
    icon: "i-heroicons-arrows-right-left",
  },
  {
    id: "PHASE 05",
    path: "/admin/trd/phase-5",
    title: "Sổ cái dự báo",
    desc: "Sổ cái lưu vết dự báo bất biến, đối soát kết quả sau phiên, tính điểm Brier Score và hiệu chuẩn chống Overfitting.",
    tech: "Forecast Journal",
    icon: "i-heroicons-document-check",
  },
  {
    id: "PHASE 06",
    path: "/admin/trd/phase-6",
    title: "Trạm Cockpit",
    desc: "Giao diện trạm điều hành lượng hóa, kiểm soát luồng dữ liệu thời gian thực và phân bổ rổ danh mục cổ phiếu Tuần/Tháng.",
    tech: "Nuxt 3 Cockpit",
    icon: "i-heroicons-computer-desktop",
  },
]
</script>
