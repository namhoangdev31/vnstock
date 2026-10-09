<template>
  <div class="min-h-screen font-sans selection:bg-aave-violet selection:text-aave-charcoal relative overflow-x-hidden antialiased">

    <div class="bg-aave-paper text-aave-obsidian relative theme-light" data-theme="light">
      <div class="absolute inset-0 bg-surface-lavender opacity-35 pointer-events-none" />

      <div class="sticky top-0 z-50">
        <header class="backdrop-blur-xl bg-ticker-bg/95 border-b border-ticker-border transition-colors">
          <div class="max-w-[1200px] mx-auto px-6 py-2 h-18 flex items-center justify-between">
            <NuxtLink to="/" class="flex items-center gap-2 group">
              <span class="font-semibold tracking-tight text-base text-aave-obsidian flex items-center gap-2 font-sans group-hover:text-aave-violet transition-colors">
                Vistock
              </span>
            </NuxtLink>

            <nav class="hidden md:flex items-center gap-7 text-sm font-medium text-aave-iron">
              <a href="/" class="hover:text-aave-obsidian transition-colors">Trang chủ</a>
              <a href="#mo-hinh" class="hover:text-aave-obsidian transition-colors">Mô hình</a>
              <a href="#phien-giao-dich" class="hover:text-aave-obsidian transition-colors">Chu kỳ</a>
              <a href="#chien-luoc" class="hover:text-aave-obsidian transition-colors">Chiến lược</a>
              <a href="#yeu-to" class="hover:text-aave-obsidian transition-colors">Yếu tố</a>
            </nav>

            <div class="flex items-center gap-3">
              <template v-if="token">
                <NuxtLink
                  to="/app"
                  class="btn-aave-dark text-sm !py-2.5 !px-5"
                >
                  <span>Vào Ứng Dụng</span>
                  <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
                </NuxtLink>
              </template>
              <template v-else>
                <NuxtLink
                  to="/login"
                  class="btn-aave-dark text-sm !py-2.5 !px-5"
                >
                  <span>Đăng nhập</span>
                </NuxtLink>
              </template>
            </div>
          </div>
        </header>

        <MarketTickerBar />
      </div>

      <section class="relative z-10 max-w-[1200px] mx-auto px-6 pt-16 pb-24 text-center">
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-aave-bone border border-black/[0.06] text-xs font-medium text-aave-obsidian mb-6">
          <span class="w-2 h-2 rounded-full bg-aave-violet" />
          <span>Nghiên Cứu Định Lượng Chứng Khoán</span>
        </div>

        <h1 class="text-4xl sm:text-5xl lg:text-6xl font-medium text-aave-obsidian tracking-tighter leading-[1.08] max-w-3xl mx-auto">
          Phân Tích Định Lượng & Mô Phỏng Giao Dịch
        </h1>

        <p class="text-base text-aave-iron leading-relaxed max-w-xl mx-auto mt-5">
          Theo dõi dòng lệnh khớp VN30F1M, dòng tiền tổ chức và giá cân bằng phiên ATC.
        </p>

        <div class="flex flex-wrap items-center justify-center gap-4 mt-8">
          <NuxtLink
            to="/app"
            class="btn-aave-violet shadow-sm"
          >
            <span>Vào Ứng Dụng</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>

          <a
            href="#mo-hinh"
            class="btn-aave-ghost-light"
          >
            <span>Tìm Hiểu Mô Hình</span>
          </a>
        </div>

        <QuantPulseCard />
      </section>
    </div>

    <div class="bg-aave-inkwell text-aave-paper relative">

      <section class="max-w-[1200px] mx-auto px-6 pt-24 pb-20 text-center">
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-aave-obsidian border border-white/[0.08] text-xs font-medium text-aave-paper mb-5">
          <span class="w-2 h-2 rounded-full bg-aave-violet" />
          <span>MÔ HÌNH ĐỊNH LƯỢNG</span>
        </div>

        <h2 class="text-3xl sm:text-4xl lg:text-5xl font-medium text-white tracking-tight leading-tight max-w-2xl mx-auto">
          Mô Phỏng Giao Dịch Độc Lập
        </h2>

        <p class="text-base text-aave-graphite max-w-xl mx-auto mt-4 leading-relaxed">
          Tuân thủ chu kỳ thanh toán T+2 cơ sở và T+0 phái sinh dưới hạn mức rủi ro kỷ luật.
        </p>

        <div class="flex items-center justify-center gap-4 mt-8">
          <NuxtLink
            to="/app"
            class="btn-aave-white"
          >
            <span>Bảng giá</span>
          </NuxtLink>
          <a
            href="#mo-hinh"
            class="btn-aave-ghost-dark"
          >
            <span>Mô Hình Định Lượng</span>
          </a>
        </div>
      </section>

      <section id="mo-hinh" class="scroll-mt-20 border-t border-white/[0.08] bg-surface-midnight py-20 md:py-28">
        <div class="mx-auto max-w-4xl px-6 md:px-8">
          <!-- Section Header (VietQuant Style) -->
          <div class="mx-auto max-w-3xl text-center">
            <span class="text-xs font-mono font-semibold uppercase tracking-wider text-aave-violet">
              Phương Pháp & Mô Hình Định Lượng
            </span>
            <h2 class="mt-3 text-balance text-2xl sm:text-3xl md:text-4xl font-semibold text-white tracking-tight leading-tight">
              Từ Dữ Liệu Vi Cấu Trúc Đến Mô Hình Định Lượng & Thực Thi
            </h2>
            <div class="mx-auto my-5 h-0.5 w-16 bg-aave-violet/40" />
            <p class="text-sm text-aave-ash leading-relaxed max-w-xl mx-auto">
              Chuỗi quy trình định lượng khép kín được xây dựng trên cơ sở dữ liệu lệnh thực tế, mô hình xác suất đa tầng và cơ chế tự động tái hiệu chỉnh 24/7.
            </p>
          </div>

          <!-- Timeline Steps with Connecting Vertical Line (VietQuant Style) -->
          <div class="relative mx-auto mt-16 max-w-2xl md:mt-24">
            <!-- Background vertical track line -->
            <div class="absolute left-[70px] top-6 bottom-6 w-0.5 bg-white/10 md:left-[88px]" />
            <!-- Active colored vertical line -->
            <div class="absolute left-[70px] top-6 bottom-6 w-0.5 origin-top bg-aave-violet md:left-[88px]" />
            <!-- Glowing indicator dot at top -->
            <div class="absolute left-[70.5px] top-6 z-20 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-aave-violet shadow-sm ring-4 ring-aave-violet/25 md:left-[88.5px]" />

            <div class="space-y-12 md:space-y-20">
              <!-- Step 01 -->
              <div class="relative flex items-start gap-4 md:gap-6">
                <div class="w-8 shrink-0 pt-2.5 text-right font-mono text-sm md:text-base font-bold transition-colors duration-500 md:w-10">
                  <span class="text-aave-violet">01</span>
                </div>
                <div class="relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-aave-violet text-white shadow-md shadow-aave-violet/20 ring-4 ring-aave-violet/15 md:h-12 md:w-12">
                  <UIcon name="i-heroicons-circle-stack" class="w-5 h-5" />
                </div>
                <div class="flex-1 pt-1 pl-2 md:pl-3">
                  <h3 class="text-lg md:text-xl font-semibold text-white tracking-tight">
                    Thu Thập & Chuẩn Hóa Vi Cấu Trúc
                  </h3>
                  <p class="mt-2 text-sm leading-relaxed text-aave-ash md:max-w-xl">
                    Khai thác dữ liệu qua <code class="text-aave-violet font-mono text-xs px-1 py-0.5 rounded bg-white/[0.05]">vnstock</code>, xử lý lệnh khớp từng tick, delta khối lượng và chuỗi nến đa khung thời gian.
                  </p>
                </div>
              </div>

              <!-- Step 02 -->
              <div class="relative flex items-start gap-4 md:gap-6">
                <div class="w-8 shrink-0 pt-2.5 text-right font-mono text-sm md:text-base font-bold transition-colors duration-500 md:w-10">
                  <span class="text-aave-violet">02</span>
                </div>
                <div class="relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-aave-violet text-white shadow-md shadow-aave-violet/20 ring-4 ring-aave-violet/15 md:h-12 md:w-12">
                  <UIcon name="i-heroicons-cpu-chip" class="w-5 h-5" />
                </div>
                <div class="flex-1 pt-1 pl-2 md:pl-3">
                  <h3 class="text-lg md:text-xl font-semibold text-white tracking-tight">
                    Mô Hình Hồi Quy & Tách Lọc Tín Hiệu
                  </h3>
                  <p class="mt-2 text-sm leading-relaxed text-aave-ash md:max-w-xl">
                    Ứng dụng mô hình Linear Regression và phân tích đa biến nhằm đo lường tương quan giữa hành vi giá, dòng tiền và độ lệch Basis.
                  </p>
                </div>
              </div>

              <!-- Step 03 -->
              <div class="relative flex items-start gap-4 md:gap-6">
                <div class="w-8 shrink-0 pt-2.5 text-right font-mono text-sm md:text-base font-bold transition-colors duration-500 md:w-10">
                  <span class="text-aave-violet">03</span>
                </div>
                <div class="relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-aave-violet text-white shadow-md shadow-aave-violet/20 ring-4 ring-aave-violet/15 md:h-12 md:w-12">
                  <UIcon name="i-heroicons-scale" class="w-5 h-5" />
                </div>
                <div class="flex-1 pt-1 pl-2 md:pl-3">
                  <h3 class="text-lg md:text-xl font-semibold text-white tracking-tight">
                    Mô Hình Hóa Xác Suất & Cân Bằng Phiên ATC
                  </h3>
                  <p class="mt-2 text-sm leading-relaxed text-aave-ash md:max-w-xl">
                    Tổng hợp tín hiệu Ensemble dự báo khoảng trống mở cửa ATO, phân bổ xác suất biến động và mức giá cân bằng phiên ATC.
                  </p>
                </div>
              </div>

              <!-- Step 04 -->
              <div class="relative flex items-start gap-4 md:gap-6">
                <div class="w-8 shrink-0 pt-2.5 text-right font-mono text-sm md:text-base font-bold transition-colors duration-500 md:w-10">
                  <span class="text-aave-violet">04</span>
                </div>
                <div class="relative z-10 flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-aave-violet text-white shadow-md shadow-aave-violet/20 ring-4 ring-aave-violet/15 md:h-12 md:w-12">
                  <UIcon name="i-heroicons-arrow-path-rounded-square" class="w-5 h-5" />
                </div>
                <div class="flex-1 pt-1 pl-2 md:pl-3">
                  <h3 class="text-lg md:text-xl font-semibold text-white tracking-tight">
                    Mô Phỏng Paper Trading & Tự Động Tái Hiệu Chỉnh
                  </h3>
                  <p class="mt-2 text-sm leading-relaxed text-aave-ash md:max-w-xl">
                    Mô phỏng vị thế phái sinh và danh mục độc lập, ghi nhận sổ cái dự báo và tự động tối ưu trọng số qua kiểm định Walk-Forward.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Bottom Navigation Link (VietQuant Style) -->
          <div class="mt-14 flex justify-center md:mt-20">
            <a
              href="#phien-giao-dich"
              class="btn-aave-outline-violet text-sm !py-2.5 !px-6 inline-flex items-center gap-2"
            >
              <span>Xem 5 Pha Chu Kỳ Giao Dịch</span>
              <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      <section id="phien-giao-dich" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="mb-12">
          <div class="text-xs font-mono font-medium text-aave-violet mb-2">
            CHU KỲ PHIÊN
          </div>
          <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-tight">
            Theo Dõi 5 Pha Giao Dịch Trong Ngày
          </h2>
          <p class="text-sm text-aave-graphite mt-2 max-w-lg">
            Giám sát liên tục từ phiên mở cửa ATO đến phiên đóng cửa ATC.
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-xs font-mono text-aave-graphite">08:30 - 08:45</div>
            <h4 class="text-sm font-medium text-white">Trước phiên</h4>
            <p class="text-xs text-aave-graphite leading-relaxed">
              Đồng bộ giá thanh toán và xác định ngưỡng cản Pivot.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-xs font-mono text-aave-violet">08:45 - 09:00</div>
            <h4 class="text-sm font-medium text-white">Khớp lệnh ATO</h4>
            <p class="text-xs text-aave-graphite leading-relaxed">
              Theo dõi giá khớp dự kiến và khoảng trống mở cửa.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-xs font-mono text-aave-paper">09:00 - 11:30</div>
            <h4 class="text-sm font-medium text-white">Khớp liên tục sáng</h4>
            <p class="text-xs text-aave-graphite leading-relaxed">
              Biểu đồ nến 1 phút và bám sát đường bình quân VWAP.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-xs font-mono text-aave-graphite">11:30 - 13:00</div>
            <h4 class="text-sm font-medium text-white">Nghỉ trưa</h4>
            <p class="text-xs text-aave-graphite leading-relaxed">
              Đánh giá rổ chỉ số VN30 và chuẩn bị cho phiên chiều.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2 border !border-aave-violet/40">
            <div class="text-xs font-mono text-aave-violet">14:15 - 14:45</div>
            <h4 class="text-sm font-medium text-white">Khớp lệnh ATC</h4>
            <p class="text-xs text-aave-ash leading-relaxed">
              Dự báo khối lượng tái cơ cấu và giá cân bằng kết phiên.
            </p>
          </div>
        </div>
      </section>

      <section id="chien-luoc" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <div class="text-xs font-mono font-medium text-aave-violet mb-2">
              CHIẾN LƯỢC ĐẦU TƯ
            </div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-tight">
              Phái Sinh VN30F1M & Rổ Cổ Phiếu
            </h2>
            <p class="text-sm text-aave-graphite mt-2 max-w-lg">
              Mô hình hóa vị thế theo từng khung thời gian đầu tư.
            </p>
          </div>
          <NuxtLink
            to="/app"
            class="btn-aave-outline-violet self-start md:self-auto text-sm !py-2.5 !px-5"
          >
            <span>Khám Phá Mô Phỏng</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">

          <div class="card-aave-dark space-y-5">
            <div class="flex items-center justify-between pb-4 border-b border-white/[0.06]">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-aave-violet" />
                <span class="text-sm font-medium text-white">Phái Sinh VN30F1M</span>
              </div>
              <span class="text-xs font-mono px-2 py-0.5 rounded-full bg-aave-obsidian text-aave-violet border border-white/[0.08]">
                CHẾ ĐỘ T+0
              </span>
            </div>

            <div class="space-y-3">
              <div class="p-3.5 rounded-[14px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Vị thế trong phiên</span>
                  <span class="text-xs font-mono text-aave-violet">TRỰC TIẾP</span>
                </div>
                <p class="text-xs text-aave-graphite">
                  Điểm mở vị thế Long/Short kèm mức dừng lỗ động.
                </p>
              </div>

              <div class="p-3.5 rounded-[14px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Chênh lệch Basis</span>
                  <span class="text-xs font-mono text-aave-violet">BASIS</span>
                </div>
                <p class="text-xs text-aave-graphite">
                  Đo lường độ lệch giá giữa phái sinh và rổ chỉ số VN30.
                </p>
              </div>

              <div class="p-3.5 rounded-[14px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Phòng vệ qua đêm</span>
                  <span class="text-xs font-mono text-aave-violet">QUA ĐÊM</span>
                </div>
                <p class="text-xs text-aave-graphite">
                  Ước lượng tỷ lệ vị thế an toàn trước biến động thế giới.
                </p>
              </div>
            </div>
          </div>

          <div class="card-aave-dark space-y-5">
            <div class="flex items-center justify-between pb-4 border-b border-white/[0.06]">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-white" />
                <span class="text-sm font-medium text-white">Rổ Cổ Phiếu Định Lượng</span>
              </div>
              <span class="text-xs font-mono px-2 py-0.5 rounded-full bg-aave-obsidian text-aave-paper border border-white/[0.08]">
                CHẾ ĐỘ T+2
              </span>
            </div>

            <div class="space-y-3">
              <div class="p-3.5 rounded-[14px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Đà tăng trưởng tuần</span>
                  <span class="text-xs font-mono text-white">MOMENTUM</span>
                </div>
                <p class="text-xs text-aave-graphite">
                  Cổ phiếu có sức mạnh giá và dòng tiền đột biến.
                </p>
              </div>

              <div class="p-3.5 rounded-[14px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Luân chuyển ngành tháng</span>
                  <span class="text-xs font-mono text-white">NGÀNH NGHỀ</span>
                </div>
                <p class="text-xs text-aave-graphite">
                  Theo dõi dòng tiền chuyển dịch giữa các nhóm ngành.
                </p>
              </div>

              <div class="p-3.5 rounded-[14px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Giá trị cơ bản quý</span>
                  <span class="text-xs font-mono text-white">CƠ BẢN</span>
                </div>
                <p class="text-xs text-aave-graphite">
                  Doanh nghiệp sinh lời cao, dòng tiền tốt và nợ thấp.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <FactorPerformanceSection />

      <footer class="border-t border-white/[0.08] bg-surface-midnight pt-16 pb-12 text-xs text-aave-graphite">
        <div class="max-w-[1200px] mx-auto px-6">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr] gap-10 lg:gap-12 pb-8">
            <!-- Brand & Institutional Intro Column -->
            <div class="space-y-4">
              <NuxtLink to="/" class="inline-flex items-center gap-2 group">
                <span class="font-semibold tracking-tight text-xl text-white font-sans group-hover:text-aave-violet transition-colors">
                  Vistock
                </span>
              </NuxtLink>

              <p class="text-xs text-aave-ash leading-relaxed max-w-sm">
                Nền tảng nghiên cứu và phân tích định lượng chuyên sâu cho thị trường chứng khoán Việt Nam. Chúng tôi kết hợp vi cấu trúc thị trường, phân tích dữ liệu lệnh khớp thực tế và mô hình hóa danh mục đa chu kỳ.
              </p>

              <!-- Quick Access Links -->
              <div class="pt-2 flex items-center gap-2.5">
                <a
                  href="https://github.com/thinh-vu/vnstock"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="GitHub Repository"
                  class="grid h-8 w-8 place-items-center rounded-lg border border-white/10 bg-white/5 text-aave-ash hover:border-white/20 hover:bg-white/10 hover:text-white transition-all"
                >
                  <UIcon name="i-heroicons-code-bracket" class="w-4 h-4" />
                </a>
                <NuxtLink
                  to="/app"
                  aria-label="Ứng dụng định lượng"
                  class="grid h-8 w-8 place-items-center rounded-lg border border-white/10 bg-white/5 text-aave-ash hover:border-white/20 hover:bg-white/10 hover:text-white transition-all"
                >
                  <UIcon name="i-heroicons-chart-bar" class="w-4 h-4" />
                </NuxtLink>
                <NuxtLink
                  to="/login"
                  aria-label="Đăng nhập hệ thống"
                  class="grid h-8 w-8 place-items-center rounded-lg border border-white/10 bg-white/5 text-aave-ash hover:border-white/20 hover:bg-white/10 hover:text-white transition-all"
                >
                  <UIcon name="i-heroicons-arrow-right-on-rectangle" class="w-4 h-4" />
                </NuxtLink>
              </div>
            </div>


            <div>
              <h4 class="mb-4 text-xs font-semibold uppercase tracking-[0.12em] text-white">
                Chiến Lược & Danh Mục
              </h4>
              <ul class="m-0 flex list-none flex-col gap-2.5 p-0 text-xs">
                <li>
                  <a href="#chien-luoc" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Phái Sinh VN30F1M
                  </a>
                </li>
                <li>
                  <a href="#chien-luoc" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Đà Tăng Trưởng
                  </a>
                </li>
                <li>
                  <a href="#chien-luoc" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Luân Chuyển Ngành
                  </a>
                </li>
                <li>
                  <a href="#chien-luoc" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Giá Trị Cơ Bản
                  </a>
                </li>
                <li>
                  <a href="#mo-hinh" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Mô Hình Quyết Định Đa Tầng
                  </a>
                </li>
              </ul>
            </div>

            <!-- Column 3: Điều Hành & Hệ Thống -->
            <div>
              <h4 class="mb-4 text-xs font-semibold uppercase tracking-[0.12em] text-white">
                Điều Hành & Hệ Thống
              </h4>
              <ul class="m-0 flex list-none flex-col gap-2.5 p-0 text-xs">
                <li>
                  <NuxtLink to="/app" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Ứng Dụng
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink to="/app" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Mô Phỏng Paper Trading
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink to="/login" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Đăng Nhập Hệ Thống
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink to="/signup" class="text-aave-ash hover:text-white transition-colors duration-150 inline-block">
                    Đăng Ký Tài Khoản
                  </NuxtLink>
                </li>
              </ul>
            </div>
          </div>

          <!-- Institutional Disclaimer Section (Inspired by VietQuant) -->
          <div id="tuyen-bo-mien-tru" class="mt-10 scroll-mt-24 border-t border-white/10 pt-8 pb-3">
            <h4 class="mb-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-white">
              Lưu Ý Quan Trọng & Tuyên Bố Miễn Trừ
            </h4>
            <p class="mb-2 max-w-5xl text-xs leading-relaxed text-aave-iron">
              Vistock chỉ vận hành như một nền tảng nghiên cứu định lượng độc lập và môi trường giả lập Paper Trading. Hệ thống không huy động vốn, không nhận ủy thác đầu tư dưới bất kỳ hình thức nào và tuyệt đối không kết nối tài khoản chứng khoán thực để tự động đặt lệnh.
            </p>
            <p class="mb-2 max-w-5xl text-xs leading-relaxed text-aave-iron">
              Số liệu thị trường, bảng yếu tố định lượng và các biểu đồ hiệu suất mô phỏng trên nền tảng nhằm minh họa phương pháp luận nghiên cứu thuật toán. Kết quả trong quá khứ hoặc trong môi trường mô phỏng không đảm bảo cho kết quả giao dịch thực tế trong tương lai.
            </p>
            <p class="max-w-5xl text-xs leading-relaxed text-aave-iron">
              Toàn bộ nội dung hiển thị không phải khuyến nghị mua, bán hoặc nắm giữ bất kỳ loại chứng khoán hay hợp đồng tương lai nào. Nhà đầu tư tự chịu hoàn toàn trách nhiệm đối với các quyết định phân bổ vốn và mức độ chấp nhận rủi ro của mình.
            </p>
          </div>

          <!-- Bottom Footer Bar -->
          <div class="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-white/10 pt-5 text-xs font-mono text-aave-iron">
            <div>
              © 2026 Vistock Quants. Bảo lưu mọi quyền.
            </div>

            <div class="flex flex-wrap items-center justify-center gap-4">
              <span>Thị Trường Việt Nam</span>
              <span>·</span>
              <span>VN30F1M & Rổ VN30</span>
              <span>·</span>
              <span>Chu Kỳ Settlement T+2</span>
              <span>·</span>
              <span>Paper Trading Engine</span>
              <span>·</span>
              <a href="#tuyen-bo-mien-tru" class="hover:text-white transition-colors">Điều khoản</a>
              <span>·</span>
              <a href="#tuyen-bo-mien-tru" class="hover:text-white transition-colors">Bảo mật</a>
            </div>
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
  title: "Vistock Quants - Phân Tích Định Lượng & Dự Báo Giao Dịch",
  meta: [
    {
      name: "description",
      content:
        "Hệ thống phân tích định lượng, dự báo phiên ATC và mô phỏng giao dịch phái sinh VN30F1M cùng rổ cổ phiếu chứng khoán Việt Nam.",
    },
  ],
})

const { token } = useAuth()
</script>
