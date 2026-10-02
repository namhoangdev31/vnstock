<template>
  <div class="flex min-h-screen bg-[#07090e] text-slate-100 font-sans selection:bg-emerald-500 selection:text-white">
    <!-- Desktop Sidebar -->
    <aside
      class="hidden lg:flex flex-col w-64 shrink-0 border-r border-white/[0.06] bg-[#090d16]/95 backdrop-blur-xl z-20"
    >
      <!-- Sidebar Header -->
      <div class="h-16 flex items-center justify-between px-5 border-b border-white/[0.06]">
        <div class="flex items-center gap-3">
          <div class="h-8 w-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center font-mono font-bold text-white text-xs shadow-md shadow-emerald-500/20 ring-1 ring-white/10">
            VN
          </div>
          <div class="flex flex-col">
            <span class="font-bold tracking-tight text-xs text-white flex items-center gap-1.5 font-mono">
              VNSTOCK
              <span class="text-[9px] uppercase font-mono font-bold px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">PRO</span>
            </span>
            <span class="text-[10px] text-slate-400 font-mono tracking-tight">Quantitative & Analytics</span>
          </div>
        </div>

        <span class="flex h-2 w-2 relative">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
        </span>
      </div>

      <!-- Navigation Links -->
      <div class="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        <!-- Main Section -->
        <div>
          <div class="px-3 mb-2 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500">
            01 // Tổng quan
          </div>
          <nav class="space-y-1">
            <NuxtLink
              to="/"
              class="flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-lg transition-all group"
              :class="route.path === '/' ? 'bg-emerald-500/10 text-emerald-300 border-l-2 border-emerald-400 font-semibold shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'"
            >
              <UIcon name="i-heroicons-squares-2x2" class="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
              <span>Dashboard Cockpit</span>
            </NuxtLink>

            <NuxtLink
              to="/stock"
              class="flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-lg transition-all group"
              :class="route.path.startsWith('/stock') ? 'bg-emerald-500/10 text-emerald-300 border-l-2 border-emerald-400 font-semibold shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'"
            >
              <UIcon name="i-heroicons-chart-bar" class="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
              <span>Thị trường cổ phiếu</span>
            </NuxtLink>

            <NuxtLink
              to="/items"
              class="flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-lg transition-all group"
              :class="route.path.startsWith('/items') ? 'bg-emerald-500/10 text-emerald-300 border-l-2 border-emerald-400 font-semibold shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'"
            >
              <UIcon name="i-heroicons-archive-box" class="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
              <span>Danh mục Items</span>
            </NuxtLink>
          </nav>
        </div>

        <!-- TRD Blueprints Section -->
        <div>
          <div class="px-3 mb-2 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500 flex items-center justify-between">
            <span>02 // Đặc tả TRD</span>
            <span class="text-[9px] text-emerald-400 font-mono">6 Phases</span>
          </div>
          <nav class="space-y-1">
            <NuxtLink
              v-for="phase in trdPhases"
              :key="phase.path"
              :to="phase.path"
              class="flex items-center gap-2.5 px-3 py-1.5 text-xs rounded-lg transition-all"
              :class="route.path === phase.path ? 'bg-emerald-500/10 text-emerald-300 border-l-2 border-emerald-400 font-semibold shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'"
            >
              <UIcon :name="phase.icon" class="w-3.5 h-3.5 shrink-0 opacity-80" />
              <span class="truncate">{{ phase.title }}</span>
            </NuxtLink>
          </nav>
        </div>

        <!-- Admin Section -->
        <div v-if="user?.is_superuser">
          <div class="px-3 mb-2 text-[10px] font-mono font-semibold uppercase tracking-wider text-amber-500/80">
            03 // Quản trị hệ thống
          </div>
          <nav class="space-y-1">
            <NuxtLink
              to="/admin"
              class="flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-lg transition-all"
              :class="route.path.startsWith('/admin') ? 'bg-amber-500/10 text-amber-300 border-l-2 border-amber-400 font-semibold' : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]'"
            >
              <UIcon name="i-heroicons-shield-check" class="w-4 h-4 shrink-0" />
              <span>Quản lý người dùng</span>
            </NuxtLink>
          </nav>
        </div>
      </div>

      <!-- User Profile in Sidebar Footer -->
      <div class="p-3 border-t border-white/[0.06] bg-[#07090e]/60">
        <div class="flex items-center gap-3 p-2 rounded-lg bg-white/[0.02] border border-white/[0.06]">
          <div class="h-8 w-8 rounded-md bg-slate-800 flex items-center justify-center font-mono font-bold text-xs text-slate-200 ring-1 ring-white/10 uppercase">
            {{ userInitials }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-slate-200 truncate">
              {{ user?.full_name || user?.email?.split('@')[0] || 'Nhà định lượng' }}
            </p>
            <p class="text-[10px] text-slate-500 truncate font-mono">
              {{ user?.is_superuser ? 'Superuser' : 'Quant Analyst' }}
            </p>
          </div>
          <NuxtLink
            to="/settings"
            title="Cài đặt tài khoản"
            class="p-1.5 text-slate-400 hover:text-slate-200 rounded-md hover:bg-white/[0.05] transition-colors"
          >
            <UIcon name="i-heroicons-cog-6-tooth" class="w-4 h-4" />
          </NuxtLink>
          <button
            title="Đăng xuất"
            class="p-1.5 text-slate-400 hover:text-rose-400 rounded-md hover:bg-white/[0.05] transition-colors"
            @click="logout"
          >
            <UIcon name="i-heroicons-arrow-right-on-rectangle" class="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Mobile Sidebar Drawer -->
    <USlideover v-model="mobileOpen">
      <div class="p-4 flex-1 flex flex-col justify-between bg-[#090d16] text-slate-100 h-full">
        <div>
          <div class="flex items-center justify-between pb-4 border-b border-white/[0.06]">
            <div class="flex items-center gap-2">
              <div class="h-8 w-8 rounded-lg bg-emerald-600 flex items-center justify-center font-mono font-bold text-white text-xs">
                VN
              </div>
              <span class="font-bold text-slate-100 font-mono text-sm">VNSTOCK QUANTS</span>
            </div>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="mobileOpen = false"
            />
          </div>

          <div class="mt-4 space-y-4">
            <NuxtLink
              to="/"
              class="flex items-center gap-3 px-3 py-2 rounded-lg text-xs"
              :class="route.path === '/' ? 'bg-emerald-500/10 text-emerald-400 font-semibold' : 'text-slate-300'"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-squares-2x2" class="w-4 h-4" />
              <span>Dashboard Cockpit</span>
            </NuxtLink>

            <NuxtLink
              to="/stock"
              class="flex items-center gap-3 px-3 py-2 rounded-lg text-xs"
              :class="route.path.startsWith('/stock') ? 'bg-emerald-500/10 text-emerald-400 font-semibold' : 'text-slate-300'"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-chart-bar" class="w-4 h-4" />
              <span>Thị trường cổ phiếu</span>
            </NuxtLink>

            <NuxtLink
              to="/items"
              class="flex items-center gap-3 px-3 py-2 rounded-lg text-xs"
              :class="route.path.startsWith('/items') ? 'bg-emerald-500/10 text-emerald-400 font-semibold' : 'text-slate-300'"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-archive-box" class="w-4 h-4" />
              <span>Danh mục Items</span>
            </NuxtLink>

            <div class="pt-2 border-t border-white/[0.06]">
              <p class="text-[10px] uppercase text-slate-500 font-mono font-semibold mb-2">Đặc tả TRD 6 Phases</p>
              <NuxtLink
                v-for="phase in trdPhases"
                :key="phase.path"
                :to="phase.path"
                class="flex items-center gap-2.5 px-3 py-1.5 text-xs rounded-lg"
                :class="route.path === phase.path ? 'bg-emerald-500/10 text-emerald-400 font-semibold' : 'text-slate-400'"
                @click="mobileOpen = false"
              >
                <UIcon :name="phase.icon" class="w-3.5 h-3.5" />
                <span>{{ phase.title }}</span>
              </NuxtLink>
            </div>
          </div>
        </div>

        <div class="pt-4 border-t border-white/[0.06] flex justify-between items-center">
          <NuxtLink to="/settings" class="text-xs text-slate-400 hover:text-slate-200" @click="mobileOpen = false">
            Cài đặt tài khoản
          </NuxtLink>
          <button class="text-xs text-rose-400 hover:underline" @click="logout">
            Đăng xuất
          </button>
        </div>
      </div>
    </USlideover>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Top Institutional Trading Desk Header -->
      <header class="h-14 shrink-0 border-b border-white/[0.06] bg-[#07090e]/85 backdrop-blur-xl px-4 lg:px-8 flex items-center justify-between sticky top-0 z-30">
        <div class="flex items-center gap-4">
          <button
            class="lg:hidden p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-white/[0.05]"
            @click="mobileOpen = true"
          >
            <UIcon name="i-heroicons-bars-3" class="w-5 h-5" />
          </button>

          <!-- Market Session Telemetry Status -->
          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2 px-2.5 py-1 rounded-md bg-white/[0.02] border border-white/[0.06]">
              <span class="h-2 w-2 rounded-full" :class="sessionStatus.active ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'" />
              <span class="text-[11px] font-mono font-bold tracking-tight text-white uppercase">{{ sessionStatus.label }}</span>
              <span class="text-[10px] font-mono text-slate-400">VN_TZ {{ currentTime }}</span>
            </div>

            <!-- VN30F1M Basis Badge -->
            <div class="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-white/[0.02] border border-white/[0.06]">
              <span class="text-[11px] font-mono text-slate-400">VN30F1M:</span>
              <span class="text-[11px] font-mono font-bold text-emerald-400">1,318.50</span>
              <span class="text-[10px] font-mono px-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">Basis: -2.30</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <!-- Sandbox Isolation Guarantee Tag -->
          <div class="hidden xl:flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <UIcon name="i-heroicons-shield-check" class="w-3.5 h-3.5" />
            <span>SANDBOX 100% ISOLATED</span>
          </div>

          <!-- Quick Stock Lookup -->
          <NuxtLink
            to="/stock"
            class="hidden md:inline-flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-slate-300 rounded-lg bg-white/[0.02] hover:bg-white/[0.05] transition-colors border border-white/[0.08]"
          >
            <UIcon name="i-heroicons-magnifying-glass" class="w-3.5 h-3.5 text-slate-400" />
            <span>Tra cứu mã CK</span>
            <kbd class="px-1.5 py-0.5 text-[9px] rounded bg-white/[0.06] text-slate-400 border border-white/[0.1] font-mono">Ctrl+K</kbd>
          </NuxtLink>

          <!-- Current User Badge -->
          <NuxtLink
            to="/settings"
            class="flex items-center gap-2 pl-1.5 pr-2.5 py-1 rounded-lg bg-white/[0.02] border border-white/[0.08] hover:bg-white/[0.05] transition-colors"
          >
            <div class="w-6 h-6 rounded bg-emerald-600/80 text-white font-mono font-bold text-[10px] flex items-center justify-center ring-1 ring-white/10">
              {{ userInitials }}
            </div>
            <span class="text-xs font-medium text-slate-300 max-w-[120px] truncate hidden sm:inline">
              {{ user?.full_name || user?.email?.split('@')[0] || 'Tài khoản' }}
            </span>
          </NuxtLink>
        </div>
      </header>

      <!-- Page Content -->
      <main class="flex-1 p-4 lg:p-6 overflow-y-auto">
        <div class="mx-auto max-w-[1400px]">
          <slot />
        </div>
      </main>

      <!-- Institutional Footer -->
      <footer class="border-t border-white/[0.06] bg-[#07090e]/90 px-6 py-3.5 text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div class="flex items-center gap-2 text-[11px] text-slate-400">
          <UIcon name="i-heroicons-lock-closed" class="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span>Vnstock Quantitative Research & Simulation Engine (Tuân thủ T+2 & Khớp lệnh ATO/ATC). Dữ liệu phục vụ nghiên cứu & mô phỏng.</span>
        </div>
        <div class="flex items-center gap-3 text-[11px] font-mono shrink-0">
          <span class="flex items-center gap-1.5 text-emerald-400">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            TELEMETRY 24/7 ACTIVE
          </span>
          <span class="text-slate-500">|</span>
          <span class="text-slate-400">NUXT 3 + FASTAPI DDD</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { user, logout } = useAuth()
const mobileOpen = ref(false)

const userInitials = computed(() => {
  if (user.value?.full_name) {
    const parts = user.value.full_name.trim().split(" ")
    return parts.length > 1
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : parts[0].slice(0, 2).toUpperCase()
  }
  if (user.value?.email) {
    return user.value.email.slice(0, 2).toUpperCase()
  }
  return "VN"
})

// Clock and market session tracker
const currentTime = ref("")
const sessionStatus = computed(() => {
  const now = new Date()
  const hours = now.getHours()
  const minutes = now.getMinutes()
  const timeNum = hours * 100 + minutes

  if (timeNum >= 845 && timeNum < 900) {
    return { label: "Phiên ATO (08:45 - 09:00)", active: true }
  }
  if (timeNum >= 900 && timeNum < 1130) {
    return { label: "Khớp lệnh sáng (09:00 - 11:30)", active: true }
  }
  if (timeNum >= 1130 && timeNum < 1300) {
    return { label: "Nghỉ trưa (11:30 - 13:00)", active: false }
  }
  if (timeNum >= 1300 && timeNum < 1430) {
    return { label: "Khớp lệnh chiều (13:00 - 14:30)", active: true }
  }
  if (timeNum >= 1430 && timeNum < 1445) {
    return { label: "Phiên ATC (14:30 - 14:45)", active: true }
  }
  return { label: "Sau giờ giao dịch (24/7 Daemon)", active: false }
})

const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString("vi-VN", { hour12: false })
}

let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  updateClock()
  timer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const trdPhases = [
  {
    path: "/trd/phase-1",
    title: "Phase 1: Nền tảng & Data",
    icon: "i-heroicons-circle-stack",
  },
  {
    path: "/trd/phase-2",
    title: "Phase 2: Tri-Engine Arch",
    icon: "i-heroicons-cpu-chip",
  },
  {
    path: "/trd/phase-3",
    title: "Phase 3: Daemon 24/7",
    icon: "i-heroicons-clock",
  },
  {
    path: "/trd/phase-4",
    title: "Phase 4: Phái sinh & T+2",
    icon: "i-heroicons-arrows-right-left",
  },
  {
    path: "/trd/phase-5",
    title: "Phase 5: Sổ cái dự báo",
    icon: "i-heroicons-document-check",
  },
  {
    path: "/trd/phase-6",
    title: "Phase 6: Trạm Cockpit",
    icon: "i-heroicons-computer-desktop",
  },
]
</script>
