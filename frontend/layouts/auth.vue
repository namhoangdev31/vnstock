<template>
  <div class="min-h-screen bg-aave-inkwell flex flex-col justify-center items-center p-4 relative overflow-hidden text-white font-sans selection:bg-aave-violet selection:text-aave-charcoal">

    <div class="absolute -top-40 -left-40 w-96 h-96 bg-aave-violet/5 rounded-full blur-3xl pointer-events-none" />
    <div class="absolute -bottom-40 -right-40 w-96 h-96 bg-aave-violet/5 rounded-full blur-3xl pointer-events-none" />

    <div class="w-full max-w-md relative z-10 space-y-6">

      <div class="text-center space-y-2">
        <NuxtLink to="/" class="inline-block hover:opacity-90 transition-opacity">
          <h1 class="text-2xl font-medium tracking-[-0.6px] text-white">
            Vnstock Quants Engine
          </h1>
        </NuxtLink>
        <p class="text-xs text-aave-graphite">
          Nền tảng phân tích lượng hóa & mô phỏng phái sinh VN30F1M
        </p>
      </div>

      <div class="bg-aave-obsidian border border-white/[0.06] rounded-[20px] p-6 sm:p-8 shadow-sm">
        <slot />
      </div>

      <p class="text-center text-[12px] text-aave-iron leading-relaxed max-w-sm mx-auto">
        Tất cả dữ liệu & tín hiệu phục vụ nghiên cứu định lượng và mô phỏng paper trading. Tuân thủ nghiêm ngặt chuẩn T+2 thị trường Việt Nam.
      </p>
    </div>
  </div>
</template>
