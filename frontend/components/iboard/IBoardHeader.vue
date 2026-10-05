<script setup lang="ts">
defineProps<{
  currentTime: string
  isWsConnected: boolean
  isWsConnecting: boolean
}>()

const emit = defineEmits<(e: "open-order-form") => void>()
</script>

<template>
  <header class="h-12 bg-aave-inkwell border-b border-white/[0.08] px-4 flex items-center justify-between shrink-0 z-30">
    <div class="flex items-center gap-5">
      <NuxtLink to="/" class="flex items-center gap-2 group">
        <div class="flex flex-col">
          <span class="font-bold text-sm tracking-tight text-white group-hover:text-rose-500 transition-colors">
            VNSTOCK
          </span>
        </div>
      </NuxtLink>

      <nav class="hidden xl:flex items-center gap-1 text-xs font-medium text-aave-ash">
        <NuxtLink to="/" class="px-2.5 py-1.5 rounded hover:text-white hover:bg-white/[0.04] transition-colors">
          <UIcon name="i-heroicons-home" class="w-4 h-4 inline-block" />
        </NuxtLink>
        <NuxtLink to="/iboard" class="px-2.5 py-1.5 rounded text-white font-semibold border-b-2 border-rose-500 bg-white/[0.04]">
          Bảng giá
        </NuxtLink>
        <button
          type="button"
          class="px-2.5 py-1.5 rounded hover:text-white hover:bg-white/[0.04] transition-colors"
          @click="emit('open-order-form')"
        >
          Đặt lệnh
        </button>
        <NuxtLink to="/admin" class="px-2.5 py-1.5 rounded hover:text-white hover:bg-white/[0.04] transition-colors">
          Phân tích
        </NuxtLink>
        <NuxtLink to="/admin" class="px-2.5 py-1.5 rounded hover:text-white hover:bg-white/[0.04] transition-colors">
          Cockpit
        </NuxtLink>
      </nav>
    </div>

    <div class="flex items-center gap-3">
      <!-- Đồng hồ thời gian thực -->
      <div class="flex items-center gap-2 px-2.5 py-1 rounded bg-white/[0.04] border border-white/[0.06] text-xs font-mono text-aave-ash tabular-nums">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span>{{ currentTime }}</span>
      </div>

      <!-- Badge trạng thái kết nối DNSE WebSocket -->
      <div class="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/[0.04] border border-white/[0.06] text-xs font-mono">
        <span
          class="w-1.5 h-1.5 rounded-full"
          :class="isWsConnected ? 'bg-emerald-500 animate-pulse' : (isWsConnecting ? 'bg-amber-500 animate-pulse' : 'bg-rose-500')"
        />
        <span :class="isWsConnected ? 'text-emerald-400 font-medium' : (isWsConnecting ? 'text-amber-400 font-medium' : 'text-rose-400 font-medium')">
          {{ isWsConnected ? 'Realtime DNSE' : (isWsConnecting ? 'Đang nối DNSE...' : 'Ngoại tuyến') }}
        </span>
      </div>

      <!-- Badge cảnh báo môi trường Sandbox -->
      <div class="hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-xs font-mono text-aave-graphite">
        <UTooltip text="Môi trường kiểm thử giả lập cách ly tuyệt đối khỏi tài khoản tiền thật">
          <span class="text-emerald-400 font-medium">Mô phỏng Sandbox</span>
        </UTooltip>
      </div>

      <NuxtLink to="/admin" class="hidden md:inline-flex items-center gap-1 px-3 py-1 rounded-full bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition-colors">
        <span>Trung tâm định lượng</span>
        <UIcon name="i-heroicons-arrow-right" class="w-3.5 h-3.5" />
      </NuxtLink>
    </div>
  </header>
</template>
