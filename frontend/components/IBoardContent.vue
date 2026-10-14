<script setup lang="ts">
interface Props {
  isDerivatives?: boolean
}

withDefaults(defineProps<Props>(), {
  isDerivatives: false,
})
</script>

<template>
  <main class="flex-1 p-2 sm:p-3 overflow-y-auto flex flex-col gap-3">

    <IBoardMiniChartsBar :is-derivatives="isDerivatives" />

    <div class="w-full">
      <div
        class="rounded-xl border border-white/[0.06] bg-surface-midnight p-6 text-center text-aave-graphite"
      >
        <div class="flex flex-col items-center justify-center gap-3 py-10">
          <UIcon
            :name="
              isDerivatives
                ? 'i-heroicons-bolt'
                : 'i-heroicons-chart-bar-square'
            "
            class="w-10 h-10 text-rose-500/70"
          />
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold text-white">
              {{
                isDerivatives
                  ? "Bảng giá phái sinh VN30F1M"
                  : "Bảng giá cổ phiếu cơ sở Vistock"
              }}
            </h2>
            <span
              class="px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide uppercase"
              :class="
                isDerivatives
                  ? 'bg-rose-600/20 text-rose-400 border border-rose-500/30'
                  : 'bg-white/10 text-aave-ash border border-white/10'
              "
            >
              {{ isDerivatives ? "Phái sinh" : "Cơ sở" }}
            </span>
          </div>
          <p class="text-xs text-aave-graphite max-w-md">
            {{
              isDerivatives
                ? "Không gian theo dõi hợp đồng tương lai chỉ số VN30, độ lệch Basis và sổ lệnh khớp liên tục thời gian thực."
                : "Không gian hiển thị bảng giá khớp lệnh thời gian thực cho các mã HOSE, HNX, UPCOM và rổ chỉ số VN30."
            }}
          </p>
        </div>
      </div>
    </div>
  </main>
</template>
