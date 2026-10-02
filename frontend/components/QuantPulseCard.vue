<template>
  <div class="mt-12 max-w-4xl mx-auto bg-white rounded-[24px] p-6 sm:p-8 border border-black/[0.08] shadow-[rgba(0,0,0,0.06)_0px_12px_40px_0px] text-left relative overflow-hidden transition-all">

    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-black/[0.06]">
      <div class="flex items-center gap-3">
        <span class="relative flex h-2.5 w-2.5">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-aave-violet opacity-75" />
          <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-aave-violet" />
        </span>
        <div class="flex items-center gap-2">
          <span class="text-xs font-mono font-medium text-aave-obsidian uppercase tracking-wider">
            VN30F1M // BẢNG DÒNG LỆNH KHỚP TRỰC TIẾP
          </span>
          <span class="text-xs font-mono px-2 py-0.5 rounded-full bg-aave-bone text-aave-iron border border-black/[0.06]">
            VẬN HÀNH LIÊN TỤC 24/7
          </span>
        </div>
      </div>

      <div class="flex items-center gap-2 self-start sm:self-auto">
        <div class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-aave-bone border border-black/[0.06] text-xs font-mono font-medium text-aave-obsidian">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          <span>MÔ PHỎNG GIẢ LẬP SANDBOX</span>
          <UTooltip text="Môi trường mô phỏng độc lập hoàn toàn tách biệt với tài khoản chứng khoán tiền thật">
            <UIcon name="i-heroicons-information-circle" class="w-3.5 h-3.5 text-aave-graphite cursor-help hover:text-aave-obsidian transition-colors ml-0.5" />
          </UTooltip>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 py-6 border-b border-black/[0.06]">

      <div class="p-5 rounded-[18px] bg-aave-bone border border-black/[0.04] flex flex-col justify-between space-y-4 hover:border-aave-violet/30 transition-colors">
        <div>
          <div class="flex items-center justify-between text-xs font-medium text-aave-iron mb-2">
            <span>Hợp đồng VN30F1M</span>
            <span class="font-mono text-xs px-1.5 py-0.5 rounded bg-white text-aave-obsidian border border-black/[0.06]">T+0</span>
          </div>
          <div class="text-3xl font-medium tracking-tight text-aave-obsidian font-mono tabular-nums leading-none">
            1,318.50
          </div>
          <div class="flex items-center gap-2 mt-2">
            <span class="text-xs font-mono font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
              +6.40 · +0.49%
            </span>
            <span class="text-xs font-mono text-aave-graphite">
              VN30 Cơ Sở: 1,320.80
            </span>
          </div>
        </div>

        <div class="pt-2">
          <div class="flex items-center justify-between text-xs font-mono text-aave-graphite mb-1">
            <span>Xu thế trong phiên</span>
            <span class="text-emerald-700">Đà Tăng Trưởng</span>
          </div>
          <div class="h-6 w-full flex items-end">
            <svg class="w-full h-5 text-aave-violet" viewBox="0 0 100 20" preserveAspectRatio="none" fill="none">
              <path d="M0,16 L15,14 L30,17 L45,11 L60,13 L75,8 L90,6 L100,3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
        </div>
      </div>

      <div class="p-5 rounded-[18px] bg-aave-bone border border-black/[0.04] flex flex-col justify-between space-y-4 hover:border-aave-violet/30 transition-colors">
        <div>
          <div class="flex items-center justify-between text-xs font-medium text-aave-iron mb-2">
            <span>Độ lệch Basis</span>
            <span class="font-mono text-xs px-1.5 py-0.5 rounded bg-white text-aave-obsidian border border-black/[0.06]">CHÊNH LỆCH GIÁ</span>
          </div>
          <div class="text-3xl font-medium tracking-tight text-aave-obsidian font-mono tabular-nums leading-none">
            -2.30
          </div>
          <div class="flex items-center gap-2 mt-2">
            <span class="text-xs font-mono font-medium text-aave-violet bg-aave-violet/10 px-2 py-0.5 rounded-full">
              Biên Độ Basis: Ổn Định
            </span>
          </div>
        </div>

        <div class="pt-2 space-y-1.5">
          <div class="flex items-center justify-between text-xs font-mono text-aave-graphite">
            <span>-5.0 điểm</span>
            <span class="text-aave-obsidian font-semibold">0.0</span>
            <span>+5.0 điểm</span>
          </div>
          <div class="w-full bg-white h-2 rounded-full border border-black/[0.06] relative overflow-hidden flex items-center">
            <div class="absolute left-1/2 top-0 bottom-0 w-0.5 bg-black/[0.15]" />
            <div class="h-2 rounded-full bg-aave-violet absolute" style="left: 27%; width: 23%;" />
          </div>
          <div class="text-xs font-mono text-aave-graphite text-center">
            Chiết khấu nhẹ so với chỉ số VN30
          </div>
        </div>
      </div>

      <div class="p-5 rounded-[18px] bg-aave-bone border border-black/[0.04] flex flex-col justify-between space-y-4 hover:border-aave-violet/30 transition-colors">
        <div>
          <div class="flex items-center justify-between text-xs font-medium text-aave-iron mb-2">
            <span>Dự Báo Kết Phiên ATC</span>
            <span class="font-mono text-xs px-1.5 py-0.5 rounded bg-white text-aave-obsidian border border-black/[0.06]">PHIÊN ATC</span>
          </div>
          <div class="text-3xl font-medium tracking-tight text-aave-obsidian font-mono tabular-nums leading-none">
            1,321.20
          </div>
          <div class="flex items-center gap-2 mt-2">
            <span class="text-xs font-mono font-medium text-aave-obsidian bg-white px-2 py-0.5 rounded-full border border-black/[0.06]">
              Xác suất tăng 68.4%
            </span>
          </div>
        </div>

        <div class="pt-2 space-y-1 text-xs font-mono">
          <div class="flex items-center justify-between text-aave-graphite">
            <span>Khối lượng ước tính</span>
            <span class="text-aave-obsidian font-medium">14.8M cổ phiếu</span>
          </div>
          <div class="flex items-center justify-between text-aave-graphite">
            <span>Vùng giá cân bằng</span>
            <span class="text-aave-violet font-medium">1,319.5 · 1,323.0</span>
          </div>
        </div>
      </div>
    </div>

    <div class="py-5 border-b border-black/[0.06] grid grid-cols-1 md:grid-cols-2 gap-6">

      <div class="space-y-2">
        <div class="flex items-center justify-between text-xs font-mono">
          <div class="flex items-center gap-2 text-aave-obsidian font-medium">
            <span class="w-2 h-2 rounded-full bg-aave-violet" />
            <span>Chênh Lệch Lực Mua Bán Chủ Động</span>
          </div>
          <div class="flex items-center gap-3 text-aave-iron">
            <span>Mua chủ động 58%</span>
            <span>·</span>
            <span>Bán chủ động 42%</span>
          </div>
        </div>
        <div class="h-2 w-full bg-black/[0.04] rounded-full overflow-hidden flex">
          <div class="bg-aave-violet h-full rounded-l-full" style="width: 58%;" />
          <div class="bg-aave-iron/40 h-full rounded-r-full" style="width: 42%;" />
        </div>
        <div class="flex items-center justify-between text-xs font-mono text-aave-graphite">
          <span>Chênh lệch: Thặng dư lực mua +16%</span>
          <span>Khối lượng khớp: 182,450 HĐ</span>
        </div>
      </div>

      <div class="space-y-2">
        <div class="flex items-center justify-between text-xs font-mono">
          <div class="flex items-center gap-2 text-aave-obsidian font-medium">
            <span class="w-2 h-2 rounded-full bg-aave-obsidian" />
            <span>Phân Bổ Tỷ Trọng 3 Trụ Cột</span>
          </div>
          <div class="flex items-center gap-2 text-xs text-aave-iron">
            <span>Kỹ thuật: 38%</span>
            <span>·</span>
            <span>Dòng tiền: 32%</span>
            <span>·</span>
            <span>Định lượng: 30%</span>
          </div>
        </div>
        <div class="h-2 w-full bg-black/[0.04] rounded-full overflow-hidden flex gap-0.5">
          <div class="bg-aave-obsidian h-full rounded-l-full" style="width: 38%;" />
          <div class="bg-aave-iron h-full" style="width: 32%;" />
          <div class="bg-aave-violet h-full rounded-r-full" style="width: 30%;" />
        </div>
        <div class="flex items-center justify-between text-xs font-mono text-aave-graphite">
          <span>Kỹ thuật 38% · Dòng tiền 32% · Định lượng 30%</span>
          <span class="text-aave-violet">Tối Ưu Hóa Phân Bổ</span>
        </div>
      </div>
    </div>

    <div class="pt-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div class="flex items-center gap-2.5 text-xs font-mono text-aave-iron">
        <span class="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
        <span>Chiến lược áp dụng: v4.2.1 · Đạt Chuẩn Kiểm Định Ngoài Mẫu</span>
      </div>

      <NuxtLink
        to="/admin"
        class="inline-flex items-center gap-1.5 text-sm font-medium text-aave-violet hover:text-aave-obsidian transition-colors group self-start sm:self-auto"
      >
        <span>Vào Cockpit Điều Hành</span>
        <UIcon name="i-heroicons-arrow-right" class="w-4 h-4 transition-transform group-hover:translate-x-1" />
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>
