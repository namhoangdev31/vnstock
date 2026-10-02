<template>
  <div class="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4 relative overflow-hidden text-slate-100">
    <!-- Atmospheric background glow -->
    <div class="absolute -top-40 -left-40 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
    <div class="absolute -bottom-40 -right-40 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

    <div class="w-full max-w-md relative z-10 space-y-6">
      <!-- Logo & Branding -->
      <div class="text-center space-y-2">
        <div class="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white font-bold text-xl shadow-xl shadow-emerald-500/20 mb-1">
          VN
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-slate-100">
          Vnstock Quants Engine
        </h1>
        <p class="text-xs text-slate-400">
          Nền tảng nghiên cứu định lượng & dự báo phái sinh VN30F1M
        </p>
      </div>

      <!-- Auth Card Slot -->
      <div class="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/50">
        <slot />
      </div>

      <!-- Bottom Disclaimer -->
      <p class="text-center text-[11px] text-slate-400 leading-relaxed max-w-sm mx-auto">
        Tất cả dữ liệu & tín hiệu phục vụ nghiên cứu định lượng và mô phỏng paper trading. Tuân thủ nghiêm ngặt chuẩn T+2 thị trường Việt Nam.
      </p>
    </div>
  </div>
</template>
