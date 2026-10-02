<template>
  <div class="card-aave-dark relative overflow-hidden rounded-[24px] p-6 sm:p-7 border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.4)] space-y-5">

    <div class="flex items-center justify-between pb-4 border-b border-white/[0.08]">
      <div class="flex items-center gap-3">
        <span class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-aave-violet opacity-75" />
          <span class="relative inline-flex rounded-full h-2 w-2 bg-aave-violet" />
        </span>
        <div class="flex flex-col">
          <span class="font-mono text-xs font-semibold tracking-wider text-white uppercase">
            SỔ CÁI VỊ THẾ & HIỆU CHỈNH CHIẾN LƯỢC
          </span>
          <span class="text-xs font-mono text-aave-graphite">
            SỔ CÁI BẤT BIẾN MINH BẠCH
          </span>
        </div>
      </div>

      <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-aave-violet/15 border border-aave-violet/30 text-xs font-mono font-medium text-aave-violet">
        <span class="w-1.5 h-1.5 rounded-full bg-aave-violet" />
        <span>TỰ ĐỘNG THÍCH ỨNG</span>
      </div>
    </div>

    <div class="space-y-3 font-mono text-xs">

      <div class="p-4 rounded-[16px] bg-black/50 border border-white/[0.08] space-y-2.5 hover:border-white/[0.15] transition-colors">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded bg-white/10 text-white font-bold text-xs">
              01
            </span>
            <span class="text-white font-medium text-sm">
              Ghi Nhận Kịch Bản Dự Báo
            </span>
          </div>
          <span class="text-xs px-2 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-500/20">
            CHỜ KHỚP LỆNH ATC
          </span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1 text-xs">
          <div class="p-2 rounded-[10px] bg-white/[0.03] border border-white/[0.04]">
            <div class="text-aave-graphite text-xs">Mục tiêu ATC</div>
            <div class="text-white font-medium mt-0.5">1,321.20</div>
          </div>
          <div class="p-2 rounded-[10px] bg-white/[0.03] border border-white/[0.04]">
            <div class="text-aave-graphite text-xs">Xác suất Long</div>
            <div class="text-aave-violet font-medium mt-0.5">68.4%</div>
          </div>
          <div class="p-2 rounded-[10px] bg-white/[0.03] border border-white/[0.04] col-span-2 sm:col-span-1">
            <div class="text-aave-graphite text-xs">Tỷ Trọng Trụ Cột</div>
            <div class="text-aave-ash mt-0.5">38% · 32% · 30%</div>
          </div>
        </div>

        <div class="flex items-center justify-between text-xs text-aave-graphite pt-1 border-t border-white/[0.04]">
          <span>Khóa tham số trước thời điểm khớp lệnh</span>
          <span class="text-aave-ash">Minh Bạch Đối Soát</span>
        </div>
      </div>

      <div class="flex items-center justify-center gap-2 text-aave-graphite text-xs py-0.5">
        <div class="h-4 w-px bg-white/[0.12]" />
        <span class="text-xs uppercase tracking-wider text-aave-iron">Phiên ATC kết thúc · Giá khớp thực tế: 1,320.50</span>
        <div class="h-4 w-px bg-white/[0.12]" />
      </div>

      <div class="p-4 rounded-[16px] bg-black/50 border border-white/[0.08] space-y-2.5 hover:border-white/[0.15] transition-colors">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded bg-white/10 text-white font-bold text-xs">
              02
            </span>
            <span class="text-white font-medium text-sm">
              Đối Soát Thực Tế & Chấm Điểm
            </span>
          </div>
          <span class="text-xs px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-500/20">
            ĐÃ ĐỐI SOÁT & CHẤM ĐIỂM
          </span>
        </div>

        <div class="grid grid-cols-3 gap-2 pt-1 text-xs">
          <div class="p-2 rounded-[10px] bg-white/[0.03] border border-white/[0.04]">
            <div class="text-aave-graphite text-xs">Sai số Brier</div>
            <div class="text-emerald-400 font-medium mt-0.5">0.082</div>
          </div>
          <div class="p-2 rounded-[10px] bg-white/[0.03] border border-white/[0.04]">
            <div class="text-aave-graphite text-xs">Độ lệch giá</div>
            <div class="text-white font-medium mt-0.5">0.70 điểm</div>
          </div>
          <div class="p-2 rounded-[10px] bg-white/[0.03] border border-white/[0.04]">
            <div class="text-aave-graphite text-xs">Xu hướng</div>
            <div class="text-emerald-400 font-medium mt-0.5">Đạt Chuẩn</div>
          </div>
        </div>

        <div class="flex items-center justify-between text-xs text-aave-graphite pt-1 border-t border-white/[0.04]">
          <span>Kiểm định ngoài mẫu 30 phiên thực tế</span>
          <span class="text-emerald-400">Đạt Chuẩn Thẩm Định</span>
        </div>
      </div>

      <div class="flex items-center justify-center gap-2 text-aave-graphite text-xs py-0.5">
        <div class="h-4 w-px bg-white/[0.12]" />
        <span class="text-xs uppercase tracking-wider text-aave-violet">Vượt Chuẩn Thẩm Định · Biên Độ Điều Chỉnh Dưới 5%</span>
        <div class="h-4 w-px bg-white/[0.12]" />
      </div>

      <div class="p-4 rounded-[16px] bg-aave-violet/10 border border-aave-violet/40 space-y-2.5">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded bg-aave-violet text-aave-obsidian font-bold text-xs">
              03
            </span>
            <span class="text-white font-medium text-sm">
              Tối Ưu Tỷ Trọng Danh Mục
            </span>
          </div>
          <span class="text-xs px-2 py-0.5 rounded bg-aave-violet/20 text-aave-violet border border-aave-violet/40 font-bold">
            KÍCH HOẠT TRỌNG SỐ MỚI
          </span>
        </div>

        <div class="p-2.5 rounded-[10px] bg-black/40 border border-aave-violet/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div>
            <span class="text-aave-graphite">Phiên bản danh mục: </span>
            <span class="text-white font-medium">v4.2.2</span>
          </div>
          <div class="text-aave-violet">
            Kỹ thuật 37% · Dòng tiền 34% · Định lượng 29%
          </div>
        </div>

        <div class="flex items-center justify-between text-xs text-aave-ash pt-1 border-t border-white/[0.06]">
          <span>Cơ chế ngắt mạch: Tự động kích hoạt khi rủi ro vượt ngưỡng</span>
          <span class="text-aave-violet">Bảo Toàn Vốn</span>
        </div>
      </div>
    </div>

    <div class="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs border-t border-white/[0.08]">
      <div class="flex items-center gap-2 text-aave-graphite text-xs font-mono">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
        <span>Hiệu suất 30 phiên: Ổn định · Cơ chế ngắt mạch sẵn sàng</span>
      </div>

      <NuxtLink
        to="/admin"
        class="inline-flex items-center gap-1.5 text-aave-violet hover:text-white font-mono text-xs transition-colors group self-start sm:self-auto"
      >
        <span>Đối Soát Sổ Cái Vị Thế</span>
        <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>
