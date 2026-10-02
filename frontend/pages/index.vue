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
            <a href="#tri-engine" class="hover:text-aave-obsidian transition-colors">Động cơ Lượng hóa</a>
            <a href="#full-session" class="hover:text-aave-obsidian transition-colors">Chu kỳ ATO-ATC</a>
            <a href="#strategies" class="hover:text-aave-obsidian transition-colors">Chiến lược Đầu tư</a>
            <a href="#self-learning" class="hover:text-aave-obsidian transition-colors">Hệ thống Tự học</a>
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
          <span>Hệ thống lượng hóa 24/7 thị trường chứng khoán Việt Nam</span>
        </div>

        <h1 class="text-4xl sm:text-5xl lg:text-[62px] font-medium text-aave-obsidian tracking-[-2.5px] leading-[1.08] max-w-4xl mx-auto">
          Nền tảng định lượng và dự báo xu hướng giao dịch độc lập
        </h1>

        <p class="text-[18px] text-aave-iron leading-relaxed max-w-2xl mx-auto mt-6">
          Vận hành liên tục không gián đoạn kết hợp 3 động cơ độc lập: Hành vi giá và dòng lệnh tick, Dòng vốn tổ chức và chu kỳ bù trừ, cùng Mô hình xác suất định lượng với cơ chế thích ứng thị trường.
        </p>

        <div class="flex flex-wrap items-center justify-center gap-4 mt-8">
          <NuxtLink
            to="/admin"
            class="btn-aave-violet shadow-sm"
          >
            <span>Truy cập Trạm Cockpit</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>

          <NuxtLink
            to="/admin/stock"
            class="btn-aave-ghost-light"
          >
            <span>Bảng Dữ liệu Thị trường</span>
          </NuxtLink>
        </div>

        <div class="mt-14 max-w-3xl mx-auto bg-white rounded-[20px] p-6 sm:p-8 border border-black/[0.06] shadow-[rgba(0,0,0,0.04)_0px_8px_30px_0px] text-left relative overflow-hidden">

          <div class="flex items-center justify-between pb-5 border-b border-black/[0.06]">
            <div class="flex items-center gap-2.5">
              <span class="w-2.5 h-2.5 rounded-full bg-aave-violet animate-pulse" />
              <span class="text-xs font-mono font-medium text-aave-iron uppercase tracking-wider">
                VN30F1M // QUANT TELEMETRY PULSE
              </span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="text-[11px] font-mono px-2.5 py-1 rounded-full bg-aave-bone text-aave-obsidian border border-black/[0.06]">
                SANDBOX SIMULATION
              </span>
              <UTooltip text="Môi trường mô phỏng độc lập cách ly hoàn toàn với tiền thật">
                <UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-iron cursor-help" />
              </UTooltip>
            </div>
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
              <span>Vào Cockpit điều hành</span>
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
          <span>VNSTOCK QUANTITATIVE SUITE</span>
        </div>

        <h2 class="text-3xl sm:text-4xl lg:text-[44px] font-medium text-white tracking-[-1.5px] leading-tight max-w-3xl mx-auto">
          Môi trường mô phỏng và phân tích định lượng chuyên sâu
        </h2>

        <p class="text-[16px] text-aave-graphite max-w-2xl mx-auto mt-4 leading-relaxed">
          Được thiết kế theo phong cách tối giản thanh lịch, vận hành cách ly hoàn toàn trong Sandbox, đảm bảo an toàn tuyệt đối và tuân thủ các quy định giao dịch chứng khoán Việt Nam.
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
            <div class="text-[14px] font-medium text-aave-violet mb-2">
              KIẾN TRÚC LƯỢNG HÓA
            </div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-[-1.2px]">
              Tam trụ động cơ định lượng độc lập
            </h2>
            <p class="text-[16px] text-aave-graphite mt-2 max-w-xl">
              Ba động cơ phân tích dữ liệu đa chiều hoạt động độc lập và tổng hợp qua thuật toán Softmax để thanh lọc tín hiệu nhiễu.
            </p>
          </div>
          <NuxtLink
            to="/admin"
            class="btn-aave-outline-violet self-start md:self-auto text-sm !py-2.5 !px-5"
          >
            <span>Xem Cockpit điều hành</span>
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
                Hành vi Giá và Khớp lệnh
              </h3>
              <p class="text-[14px] text-aave-ash leading-relaxed">
                Xử lý chuỗi nến đa khung thời gian từ 1 phút đến đồ thị ngày, quét các vùng thanh khoản, khoảng trống giá và đo lường áp lực mua bán chủ động theo thời gian thực.
              </p>
            </div>
            <div class="pt-4 border-t border-white/[0.06] text-[13px] text-aave-graphite font-mono flex items-center justify-between">
              <span>Order Flow Delta</span>
              <span class="text-aave-violet">VWAP & ATR</span>
            </div>
          </div>

          <div class="card-aave-dark flex flex-col justify-between space-y-6">
            <div class="space-y-4">
              <div class="text-[14px] font-medium text-aave-violet">
                ĐỘNG CƠ 02 // DÒNG VỐN TỔ CHỨC
              </div>
              <h3 class="text-[20px] font-medium text-white tracking-[-0.4px]">
                Dòng tiền Khối ngoại và Vĩ mô
              </h3>
              <p class="text-[14px] text-aave-ash leading-relaxed">
                Giám sát giao dịch ròng của Khối ngoại và Khối Tự doanh, biến động tỷ giá USD và giá vàng SJC, đồng thời mô hình hóa áp lực bán giải tỏa thanh khoản trong phiên chiều.
              </p>
            </div>
            <div class="pt-4 border-t border-white/[0.06] text-[13px] text-aave-graphite font-mono flex items-center justify-between">
              <span>Chu kỳ T+2</span>
              <span class="text-aave-violet">Institutional Flow</span>
            </div>
          </div>

          <div class="card-aave-dark flex flex-col justify-between space-y-6">
            <div class="space-y-4">
              <div class="text-[14px] font-medium text-aave-violet">
                ĐỘNG CƠ 03 // XÁC SUẤT ĐỊNH LƯỢNG
              </div>
              <h3 class="text-[20px] font-medium text-white tracking-[-0.4px]">
                Xác suất và Độ lệch Cơ sở
              </h3>
              <p class="text-[14px] text-aave-ash leading-relaxed">
                Theo dõi liên tục khoảng chênh lệch giữa hợp đồng phái sinh và chỉ số cơ sở, phân loại khoảng trống giá mở cửa và ước lượng khối lượng cân bằng trong phiên đóng cửa.
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
            THEO DÕI LIÊN TỤC 24/7
          </div>
          <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-[-1.2px]">
            Chuỗi giám sát toàn diện phiên giao dịch
          </h2>
          <p class="text-[16px] text-aave-graphite mt-2 max-w-xl">
            Vòng lặp tính toán tự động xuyên suốt 5 pha của phiên giao dịch để phát hiện kịp thời các biến động bất thường.
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-[12px] font-mono text-aave-graphite">08:30 - 08:45</div>
            <h4 class="text-[16px] font-medium text-white">Chuẩn bị trước phiên</h4>
            <p class="text-[13px] text-aave-graphite leading-relaxed">
              Đồng bộ giá thanh toán phiên trước, cập nhật các ngưỡng Pivot và đo lường khoảng lệch cơ sở qua đêm.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-[12px] font-mono text-aave-violet">08:45 - 09:00</div>
            <h4 class="text-[16px] font-medium text-white">Khớp lệnh ATO</h4>
            <p class="text-[13px] text-aave-graphite leading-relaxed">
              Theo dõi lệnh khớp ước tính ATO, phân loại khoảng trống mở cửa và xác định thiên hướng tâm lý đầu ngày.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-[12px] font-mono text-aave-paper">09:00 - 11:30</div>
            <h4 class="text-[16px] font-medium text-white">Khớp lệnh sáng</h4>
            <p class="text-[13px] text-aave-graphite leading-relaxed">
              Tính toán dữ liệu nến 1 phút, bám sát đường trung bình VWAP và nhận diện các điểm bứt phá xu hướng.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2">
            <div class="text-[12px] font-mono text-aave-graphite">11:30 - 13:00</div>
            <h4 class="text-[16px] font-medium text-white">Nghỉ giữa phiên</h4>
            <p class="text-[13px] text-aave-graphite leading-relaxed">
              Tái tính toán ngầm, đánh giá rổ cổ phiếu cơ sở và hoạch định trước các kịch bản cho phiên buổi chiều.
            </p>
          </div>

          <div class="card-aave-dark !p-5 space-y-2 border !border-aave-violet/40">
            <div class="text-[12px] font-mono text-aave-violet">14:15 - 14:45</div>
            <h4 class="text-[16px] font-medium text-white">Khớp lệnh ATC</h4>
            <p class="text-[13px] text-aave-ash leading-relaxed">
              Kích hoạt thuật toán dự báo ATC, ước tính khối lượng cơ cấu và xác định vùng giá đóng cửa tối ưu.
            </p>
          </div>
        </div>
      </section>

      <section id="strategies" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <div class="text-[14px] font-medium text-aave-violet mb-2">
              CHIẾN LƯỢC MÔ PHỎNG
            </div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-[-1.2px]">
              Tối ưu vị thế phái sinh và rổ cổ phiếu
            </h2>
            <p class="text-[16px] text-aave-graphite mt-2 max-w-xl">
              Mô hình hóa chiến lược định lượng hai nhánh giúp phân bổ rủi ro và tìm kiếm cơ hội trên thị trường.
            </p>
          </div>
          <NuxtLink
            to="/admin/stock"
            class="btn-aave-outline-violet self-start md:self-auto text-sm !py-2.5 !px-5"
          >
            <span>Xem Danh mục Cổ phiếu</span>
            <UIcon name="i-heroicons-arrow-right" class="w-4 h-4" />
          </NuxtLink>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">

          <div class="card-aave-dark space-y-6">
            <div class="flex items-center justify-between pb-4 border-b border-white/[0.06]">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-aave-violet" />
                <span class="text-sm font-medium text-white">Phái sinh VN30F1M</span>
              </div>
              <span class="text-xs font-mono px-2 py-0.5 rounded-full bg-aave-obsidian text-aave-violet border border-white/[0.08]">
                CHẾ ĐỘ T+0
              </span>
            </div>

            <div class="space-y-4">
              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1.5">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Tín hiệu Vị thế Trong phiên</span>
                  <span class="text-xs font-mono text-aave-violet">REALTIME</span>
                </div>
                <p class="text-[13px] text-aave-graphite leading-relaxed">
                  Cung cấp các điểm kích hoạt vị thế mua hoặc bán kèm vùng dừng lỗ động dựa trên độ biến động thực tế.
                </p>
              </div>

              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1.5">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Giám sát Khoảng cách Cơ sở</span>
                  <span class="text-xs font-mono text-aave-violet">ARBITRAGE</span>
                </div>
                <p class="text-[13px] text-aave-graphite leading-relaxed">
                  Đo lường độ lệch giá giữa hợp đồng tương lai và rổ chỉ số cơ sở để nhận diện vùng rủi ro đảo chiều.
                </p>
              </div>

              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1.5">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Khuyến nghị Vị thế Qua đêm</span>
                  <span class="text-xs font-mono text-aave-violet">OVERNIGHT</span>
                </div>
                <p class="text-[13px] text-aave-graphite leading-relaxed">
                  Mô phỏng các kịch bản biến động thị trường quốc tế nhằm đưa ra tỷ lệ phòng vệ tài khoản phù hợp.
                </p>
              </div>
            </div>
          </div>

          <div class="card-aave-dark space-y-6">
            <div class="flex items-center justify-between pb-4 border-b border-white/[0.06]">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-white" />
                <span class="text-sm font-medium text-white">Rổ Cổ phiếu Lượng hóa</span>
              </div>
              <span class="text-xs font-mono px-2 py-0.5 rounded-full bg-aave-obsidian text-aave-paper border border-white/[0.08]">
                CHẾ ĐỘ T+2
              </span>
            </div>

            <div class="space-y-4">
              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1.5">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Danh mục Tuần</span>
                  <span class="text-xs font-mono text-white">MOMENTUM</span>
                </div>
                <p class="text-[13px] text-aave-graphite leading-relaxed">
                  Ưu tiên các mã cổ phiếu có dòng tiền bứt phá mạnh, thanh khoản gia tăng và đà tăng giá ngắn hạn.
                </p>
              </div>

              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1.5">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Danh mục Tháng</span>
                  <span class="text-xs font-mono text-white">SECTOR ROTATION</span>
                </div>
                <p class="text-[13px] text-aave-graphite leading-relaxed">
                  Theo dõi sự dịch chuyển của dòng vốn giữa các nhóm ngành nghề và tích lũy cổ phiếu có triển vọng tốt.
                </p>
              </div>

              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1.5">
                <div class="text-sm font-medium text-white flex items-center justify-between">
                  <span>Danh mục Quý</span>
                  <span class="text-xs font-mono text-white">FUNDAMENTAL</span>
                </div>
                <p class="text-[13px] text-aave-graphite leading-relaxed">
                  Sàng lọc doanh nghiệp có hiệu quả sử dụng vốn cao, dòng tiền hoạt động dồi dào và cơ cấu tài chính lành mạnh.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="self-learning" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div class="space-y-6">
            <div class="text-[14px] font-medium text-aave-violet">
              HỌC MÁY KHÉP KÍN // TỰ HỌC BẤT BIẾN
            </div>
            <h2 class="text-3xl sm:text-4xl font-medium text-white tracking-[-1.2px]">
              Sổ cái dự báo và cơ chế tự điều chỉnh trọng số
            </h2>
            <p class="text-[16px] text-aave-graphite leading-relaxed">
              Mọi kịch bản dự báo đều được ghi nhận vĩnh viễn vào sổ cái trước khi phiên giao dịch kết thúc. Sau phiên, hệ thống tự động đối soát kết quả thực tế, tính toán sai số và tự cập nhật trọng số khi thỏa mãn điều kiện kiểm định.
            </p>

            <div class="space-y-3 pt-2">
              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-aave-violet" />
                  <div class="flex items-center gap-1.5">
                    <span>Tự động cập nhật mô hình</span>
                    <UTooltip text="Cơ chế tự nâng cấp trọng số khi qua cổng kiểm định">
                      <UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" />
                    </UTooltip>
                  </div>
                </div>
                <p class="text-[13px] text-aave-graphite">
                  Khi vượt qua kỳ kiểm tra ngoài mẫu 30 phiên gần nhất, hệ thống tự áp dụng bộ trọng số mới vào luồng tính toán trực tiếp.
                </p>
              </div>

              <div class="p-4 rounded-[16px] bg-aave-obsidian border border-white/[0.05] space-y-1">
                <div class="text-sm font-medium text-white flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  <div class="flex items-center gap-1.5">
                    <span>Cầu dao an toàn tự động</span>
                    <UTooltip text="Cơ chế ngắt mạch bảo vệ khi sai số vượt ngưỡng an toàn">
                      <UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-aave-graphite cursor-help" />
                    </UTooltip>
                  </div>
                </div>
                <p class="text-[13px] text-aave-graphite">
                  Nếu phát sinh sai lệch vượt ngưỡng quy định, hệ thống tự động ngắt tính năng nâng cấp và hoàn nguyên về trọng số cân bằng an toàn.
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
                <div class="flex items-center gap-1.5">
                  <span class="text-white">1. Phát sinh kịch bản dự báo</span>
                  <UTooltip text="Trạng thái chờ phiên giao dịch thực tế kết thúc">
                    <UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help" />
                  </UTooltip>
                </div>
                <span class="text-aave-violet">Ghi nhận vào Sổ cái</span>
              </div>

              <div class="text-center text-aave-graphite">
                <UIcon name="i-heroicons-arrow-down" class="w-4 h-4 mx-auto text-aave-graphite" />
              </div>

              <div class="p-3.5 rounded-[12px] bg-black/40 border border-white/[0.06] flex items-center justify-between">
                <span class="text-white">2. Đối soát thực tế và Chấm điểm</span>
                <span class="text-aave-violet">Brier Score / MAE</span>
              </div>

              <div class="text-center text-aave-graphite">
                <UIcon name="i-heroicons-arrow-down" class="w-4 h-4 mx-auto text-aave-graphite" />
              </div>

              <div class="p-3.5 rounded-[12px] bg-aave-violet/10 border border-aave-violet/30 flex items-center justify-between">
                <span class="text-white font-medium">3. Tự động nâng cấp phiên bản mô hình</span>
                <span class="text-aave-violet font-bold">Kích hoạt trực tiếp</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="max-w-[1200px] mx-auto px-6 py-12">
        <div class="rounded-[20px] bg-surface-midnight border border-aave-violet/30 p-8 sm:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
          <div class="space-y-2 max-w-2xl">
            <div class="text-[14px] font-medium text-aave-violet flex items-center gap-2">
              <UIcon name="i-heroicons-shield-check" class="w-5 h-5 text-aave-violet" />
              <span>CAM KẾT CÁCH LY SANDBOX // AN TOÀN TUYỆT ĐỐI</span>
            </div>
            <p class="text-[14px] text-aave-ash leading-relaxed">
              Hệ thống tuyệt đối không tích hợp cổng đặt lệnh tiền thật với bất kỳ công ty chứng khoán nào. Mọi phân tích chỉ phục vụ mục đích nghiên cứu lượng hóa và môi trường mô phỏng độc lập. Quyền quyết định giao dịch thực tế hoàn toàn thuộc về con người.
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
            <span class="text-aave-graphite">Continuous Quantitative Research & Predictive Analytics Engine</span>
          </div>

          <div class="flex items-center gap-6 font-medium text-[13px]">
            <NuxtLink to="/admin" class="hover:text-white transition-colors">Trạm Cockpit</NuxtLink>
            <NuxtLink to="/admin/stock" class="hover:text-white transition-colors">Thị trường CK</NuxtLink>
            <NuxtLink to="/admin/items" class="hover:text-white transition-colors">Quản lý Hàng hóa</NuxtLink>
            <NuxtLink to="/admin/settings" class="hover:text-white transition-colors">Cài đặt</NuxtLink>
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
  title: "Vnstock Quants Engine - Nền Tảng Định Lượng & Dự Báo Xu Hướng 24/7",
  meta: [
    {
      name: "description",
      content:
        "Hệ thống nghiên cứu định lượng, dự báo phiên ATC và mô phỏng giao dịch phái sinh VN30F1M cùng rổ cổ phiếu hoạt động liên tục 24/7.",
    },
  ],
})

const { token } = useAuth()
</script>
