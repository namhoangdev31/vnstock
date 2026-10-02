<template>
  <div class="min-h-screen bg-[#07090e] flex flex-col justify-center items-center p-4 relative overflow-hidden text-slate-100 terminal-grid-bg font-sans">
    <!-- Atmospheric background glow -->
    <div class="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
    <div class="absolute -bottom-40 -right-40 w-96 h-96 bg-teal-500/5 rounded-full blur-3xl pointer-events-none" />

    <div class="w-full max-w-md relative z-10 space-y-6">
      <!-- Logo & Branding -->
      <div class="text-center space-y-2">
        <div class="inline-flex items-center justify-center h-11 w-11 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 text-white font-mono font-bold text-lg shadow-lg shadow-emerald-500/20 ring-1 ring-white/10 mb-1">
          VN
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white font-mono">
          Vnstock Quants Engine
        </h1>
        <p class="text-xs text-slate-400">
          Nền tảng phân tích lượng hóa & mô phỏng phái sinh VN30F1M
        </p>
      </div>

      <!-- Auth Card Slot -->
      <div class="bg-[#090d16]/90 backdrop-blur-2xl border border-white/[0.08] rounded-2xl p-6 sm:p-8 shadow-2xl">
        <slot />
      </div>

      <!-- Bottom Disclaimer -->
      <p class="text-center text-[11px] text-slate-400 leading-relaxed max-w-sm mx-auto">
        Tất cả dữ liệu & tín hiệu phục vụ nghiên cứu định lượng và mô phỏng paper trading. Tuân thủ nghiêm ngặt chuẩn T+2 thị trường Việt Nam.
      </p>
    </div>
  </div>
</template>
