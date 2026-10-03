<template>
  <div class="min-h-screen font-sans selection:bg-aave-violet selection:text-aave-charcoal relative overflow-x-hidden antialiased">

    <div class="bg-aave-paper text-aave-obsidian relative">
      <div class="absolute inset-0 bg-surface-lavender opacity-35 pointer-events-none" />

      <header class="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-black/[0.06] transition-colors">
        <div class="max-w-[1200px] mx-auto px-6 py-2 h-18 flex items-center justify-between">
          <NuxtLink to="/" class="flex items-center gap-2 group">
            <span class="font-medium tracking-tight text-base text-aave-obsidian flex items-center gap-2 font-sans group-hover:text-aave-violet transition-colors">
              Vnstock
              <span class="text-xs font-mono uppercase font-medium px-2 py-0.5 rounded-full bg-aave-bone text-aave-iron border border-black/[0.06]">Quants</span>
            </span>
          </NuxtLink>

          <nav class="hidden md:flex items-center gap-7 text-sm font-medium text-aave-iron">
            <a href="#tru-cot" class="hover:text-aave-obsidian transition-colors">Trụ Cột Phân Tích</a>
            <a href="#phien-giao-dich" class="hover:text-aave-obsidian transition-colors">Chu Kỳ Phiên</a>
            <a href="#chien-luoc" class="hover:text-aave-obsidian transition-colors">Chiến Lược</a>
            <a href="#quan-tri-rui-ro" class="hover:text-aave-obsidian transition-colors">Quản Trị Rủi Ro</a>
          </nav>

          <div class="flex items-center gap-3">
            <template v-if="token">
              <NuxtLink
                to="/iboard"
                class="btn-aave-dark text-sm !py-2.5 !px-5"
              >
                <span>Bảng giá</span>
                <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
              </NuxtLink>
            </template>
            <template v-else>
              <NuxtLink
                to="/login"
                class="text-sm font-medium text-aave-iron hover:text-aave-obsidian px-3 py-2 transition-colors"
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
            to="/admin"
            class="btn-aave-violet shadow-sm"
          >
            <span>Vào Cockpit</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>

          <NuxtLink
            to="/iboard"
            class="btn-aave-ghost-light"
          >
            <span>Bảng giá chứng khoán</span>
          </NuxtLink>
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
            to="/admin"
            class="btn-aave-white"
          >
            <span>Mở Cockpit</span>
          </NuxtLink>
          <NuxtLink
            to="/admin/stock"
            class="btn-aave-ghost-dark"
          >
            <span>Tra Cứu Cổ Phiếu</span>
          </NuxtLink>
        </div>
      </section>

      <section id="tru-cot" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <div class="text-xs font-mono font-medium text-aave-violet mb-2">
              TRỤ CỘT ĐỊNH LƯỢNG
            </div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-tight">
              Trụ Cột Phân Tích Cốt Lõi
            </h2>
            <p class="text-sm text-aave-graphite mt-2 max-w-lg">
              Kết hợp hành vi giá, dòng vốn tổ chức và độ lệch phái sinh để tìm kiếm lợi thế thống kê.
            </p>
          </div>
          <NuxtLink
            to="/admin"
            class="btn-aave-outline-violet self-start md:self-auto text-sm !py-2.5 !px-5"
          >
            <span>Xem Cockpit</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

          <div class="card-aave-dark flex flex-col justify-between space-y-5">
            <div class="space-y-3">
              <div class="text-xs font-mono font-medium text-aave-violet">
                TRỤ CỘT 01
              </div>
              <h3 class="text-lg font-medium text-white tracking-tight">
                Hành Vi Giá & Lực Khớp Lệnh
              </h3>
              <p class="text-sm text-aave-ash leading-relaxed">
                Chuỗi nến đa khung, lực mua bán chủ động tức thì và giá bình quân VWAP.
              </p>
            </div>
            <div class="pt-4 border-t border-white/[0.06] text-xs text-aave-graphite font-mono flex items-center justify-between">
              <span>Lực Mua Bán</span>
              <span class="text-aave-violet">Giá Bình Quân VWAP</span>
            </div>
          </div>

          <div class="card-aave-dark flex flex-col justify-between space-y-5">
            <div class="space-y-3">
              <div class="text-xs font-mono font-medium text-aave-violet">
                TRỤ CỘT 02
              </div>
              <h3 class="text-lg font-medium text-white tracking-tight">
                Vốn Khối Ngoại & Chu Kỳ T+2
              </h3>
              <p class="text-sm text-aave-ash leading-relaxed">
                Giao dịch ròng Khối ngoại, Tự doanh và thanh khoản hàng về phiên chiều T+2.
              </p>
            </div>
            <div class="pt-4 border-t border-white/[0.06] text-xs text-aave-graphite font-mono flex items-center justify-between">
              <span>Chu Kỳ T+2</span>
              <span class="text-aave-violet">Dòng Tiền Khối Ngoại</span>
            </div>
          </div>

          <div class="card-aave-dark flex flex-col justify-between space-y-5">
            <div class="space-y-3">
              <div class="text-xs font-mono font-medium text-aave-violet">
                TRỤ CỘT 03
              </div>
              <h3 class="text-lg font-medium text-white tracking-tight">
                Độ Lệch Basis & Cân Bằng ATC
              </h3>
              <p class="text-sm text-aave-ash leading-relaxed">
                Chênh lệch Basis phái sinh với VN30, mở cửa ATO và khối lượng cân bằng ATC.
              </p>
            </div>
            <div class="pt-4 border-t border-white/[0.06] text-xs text-aave-graphite font-mono flex items-center justify-between">
              <span>Độ Lệch Basis</span>
              <span class="text-aave-violet">Cân Bằng ATC</span>
            </div>
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
            to="/admin/stock"
            class="btn-aave-outline-violet self-start md:self-auto text-sm !py-2.5 !px-5"
          >
            <span>Tra Cứu Bảng Giá</span>
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

      <section id="quan-tri-rui-ro" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div class="space-y-6">
            <div class="text-xs font-mono font-medium text-aave-violet">
              QUẢN TRỊ RỦI RO
            </div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-tight">
              Sổ Cái Vị Thế & Hiệu Chỉnh Tỷ Trọng
            </h2>
            <p class="text-sm text-aave-graphite leading-relaxed">
              Ghi nhận kịch bản trước phiên, đối soát kết quả sau phiên để hiệu chỉnh tỷ trọng có kỷ luật.
            </p>

            <div class="space-y-3 pt-1">
              <div class="p-3.5 rounded-[14px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-aave-violet" />
                  <div class="flex items-center gap-1.5">
                    <span>Kiểm định ngoài mẫu 30 phiên</span>
                    <UTooltip text="Tự động điều chỉnh tỷ trọng khi vượt qua các ngưỡng thẩm định rủi ro">
                      <UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" />
                    </UTooltip>
                  </div>
                </div>
                <p class="text-xs text-aave-graphite">
                  Đo lường sai số và tỷ lệ đúng hướng trên dữ liệu thực tế.
                </p>
              </div>

              <div class="p-3.5 rounded-[14px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  <div class="flex items-center gap-1.5">
                    <span>Cơ chế ngắt mạch bảo vệ</span>
                    <UTooltip text="Khóa cập nhật tỷ trọng và hoàn nguyên về phân bổ phòng thủ khi thị trường biến động vượt ngưỡng">
                      <UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" />
                    </UTooltip>
                  </div>
                </div>
                <p class="text-xs text-aave-graphite">
                  Tự động dừng áp dụng khi biến động thị trường vượt ngưỡng.
                </p>
              </div>
            </div>
          </div>

          <ClosedLoopPipelineCard />
        </div>
      </section>

      <section class="max-w-[1200px] mx-auto px-6 py-12">
        <div class="rounded-[20px] bg-surface-midnight border border-aave-violet/30 p-7 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div class="space-y-1.5 max-w-2xl">
            <div class="text-xs font-mono font-medium text-aave-violet flex items-center gap-2">
              <UIcon name="i-heroicons-shield-check" class="w-5 h-5 text-aave-violet" />
              <span>MÔ HÌNH MÔ PHỎNG SANDBOX</span>
            </div>
            <p class="text-xs text-aave-ash leading-relaxed">
              Môi trường nghiên cứu độc lập. Không kết nối tài khoản chứng khoán và không đặt lệnh tiền thật.
            </p>
          </div>

          <NuxtLink
            to="/admin"
            class="btn-aave-violet shrink-0"
          >
            <span>Vào Cockpit</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>
        </div>
      </section>

      <footer class="border-t border-white/[0.08] bg-surface-midnight pt-14 pb-10 text-xs text-aave-graphite">
        <div class="max-w-[1200px] mx-auto px-6">

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 pb-10">

            <div class="lg:col-span-2 space-y-3">
              <NuxtLink to="/" class="flex items-center gap-2 group">
                <span class="font-medium tracking-tight text-lg text-white flex items-center gap-2 font-sans group-hover:text-aave-violet transition-colors">
                  Vnstock
                  <span class="text-xs font-mono uppercase font-medium px-2 py-0.5 rounded-full bg-white/10 text-aave-violet border border-white/[0.1]">Quants</span>
                </span>
              </NuxtLink>

              <p class="text-xs text-aave-ash leading-relaxed max-w-sm">
                Nền tảng phân tích định lượng, dự báo phiên ATC và mô phỏng giao dịch phái sinh VN30F1M cùng rổ cổ phiếu.
              </p>

              <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.08] text-xs font-mono text-aave-ash">
                <span class="relative flex h-2 w-2">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
                </span>
                <span>Vận hành liên tục · Mô phỏng Sandbox 100%</span>
              </div>
            </div>

            <div class="space-y-2.5">
              <div class="text-xs font-mono font-semibold uppercase text-aave-violet tracking-wider">
                Trụ Cột Phân Tích
              </div>
              <ul class="space-y-2 text-xs">
                <li>
                  <a href="#tru-cot" class="hover:text-white transition-colors">Giá & Lực Khớp Lệnh</a>
                </li>
                <li>
                  <a href="#tru-cot" class="hover:text-white transition-colors">Dòng Tiền Khối Ngoại</a>
                </li>
                <li>
                  <a href="#tru-cot" class="hover:text-white transition-colors">Chu Kỳ Thanh Toán T+2</a>
                </li>
                <li>
                  <a href="#tru-cot" class="hover:text-white transition-colors">Độ Lệch Basis</a>
                </li>
                <li>
                  <a href="#phien-giao-dich" class="hover:text-white transition-colors">Cân Bằng Phiên ATC</a>
                </li>
              </ul>
            </div>

            <div class="space-y-2.5">
              <div class="text-xs font-mono font-semibold uppercase text-aave-violet tracking-wider">
                Danh Mục Đầu Tư
              </div>
              <ul class="space-y-2 text-xs">
                <li>
                  <a href="#chien-luoc" class="hover:text-white transition-colors">Phái Sinh VN30F1M T+0</a>
                </li>
                <li>
                  <a href="#chien-luoc" class="hover:text-white transition-colors">Đà Tăng Trưởng Tuần</a>
                </li>
                <li>
                  <a href="#chien-luoc" class="hover:text-white transition-colors">Luân Chuyển Ngành</a>
                </li>
                <li>
                  <a href="#chien-luoc" class="hover:text-white transition-colors">Giá Trị Cơ Bản Quý</a>
                </li>
                <li>
                  <NuxtLink to="/admin/stock" class="hover:text-white transition-colors">Bảng Giá Thị Trường</NuxtLink>
                </li>
              </ul>
            </div>

            <div class="space-y-2.5">
              <div class="text-xs font-mono font-semibold uppercase text-aave-violet tracking-wider">
                Điều Hành
              </div>
              <ul class="space-y-2 text-xs">
                <li>
                  <NuxtLink to="/admin" class="hover:text-white transition-colors">Trạm Cockpit</NuxtLink>
                </li>
                <li>
                  <NuxtLink to="/admin/stock" class="hover:text-white transition-colors">Tra Cứu Cổ Phiếu</NuxtLink>
                </li>
                <li>
                  <NuxtLink to="/admin/items" class="hover:text-white transition-colors">Danh Mục Tài Sản</NuxtLink>
                </li>
                <li>
                  <NuxtLink to="/admin/settings" class="hover:text-white transition-colors">Cấu Hình Tham Số</NuxtLink>
                </li>
                <li>
                  <NuxtLink to="/login" class="hover:text-white transition-colors">Đăng Nhập Sandbox</NuxtLink>
                </li>
              </ul>
            </div>
          </div>

          <div class="p-3.5 rounded-[12px] bg-white/[0.02] border border-white/[0.06] mb-6">
            <div class="flex items-start gap-2.5">
              <UIcon name="i-heroicons-shield-exclamation" class="w-4 h-4 text-aave-violet shrink-0 mt-0.5" />
              <p class="text-xs text-aave-ash leading-relaxed">
                Cảnh báo rủi ro: Mọi kịch bản dự báo và lệnh mô phỏng chỉ phục vụ mục đích nghiên cứu học thuật. Nền tảng không phải công ty chứng khoán, không giao dịch tiền thật và không khuyến nghị đầu tư.
              </p>
            </div>
          </div>

          <div class="pt-5 border-t border-white/[0.06] flex flex-col md:flex-row items-center justify-between gap-3 text-xs font-mono text-aave-iron">
            <div>
              © 2026 Vnstock Quants.
            </div>

            <div class="flex items-center gap-3">
              <span>Chứng khoán Việt Nam</span>
              <span>·</span>
              <span>Chu kỳ T+2 & Phái sinh T+0</span>
              <span>·</span>
              <span>Chuẩn Thiết Kế Tối Giản</span>
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
  title: "Vnstock Quants - Phân Tích Định Lượng & Dự Báo Giao Dịch",
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
