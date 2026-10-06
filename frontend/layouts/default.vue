<template>
  <div class="flex min-h-screen bg-aave-inkwell text-aave-paper font-sans selection:bg-aave-violet selection:text-aave-charcoal">

    <aside
      class="hidden lg:flex flex-col w-64 shrink-0 border-r border-white/[0.06] bg-aave-obsidian z-20"
    >

      <div class="h-16 flex items-center justify-between px-5 border-b border-white/[0.06]">
        <NuxtLink to="/admin" class="flex flex-col group">
          <span class="font-medium tracking-[-0.3px] text-sm text-white flex items-center gap-1.5 font-sans group-hover:text-aave-violet transition-colors">
            VNSTOCK
            <span class="text-[9px] uppercase font-mono font-bold px-1.5 py-0.2 rounded-full bg-aave-violet/15 text-aave-violet border border-aave-violet/30">PRO</span>
          </span>
          <span class="text-[10px] text-aave-graphite font-mono tracking-tight mt-0.5">Quantitative & Analytics</span>
        </NuxtLink>

        <span class="flex h-2 w-2 relative">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-aave-violet opacity-75" />
          <span class="relative inline-flex rounded-full h-2 w-2 bg-aave-violet" />
        </span>
      </div>

      <div class="flex-1 overflow-y-auto px-3 py-4 space-y-6">

        <div>
          <div class="px-3 mb-2 text-[10px] font-mono font-medium uppercase tracking-wider text-aave-graphite">
            01 // Không gian làm việc
          </div>
          <nav class="space-y-1">
            <NuxtLink
              to="/app"
              class="flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-xl transition-all group"
              :class="route.path.startsWith('/app') ? 'bg-aave-violet/15 text-aave-violet border-l-2 border-aave-violet font-medium shadow-sm' : 'text-aave-graphite hover:text-aave-paper hover:bg-white/[0.04]'"
            >
              <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4 shrink-0 transition-transform group-hover:scale-110 text-aave-violet" />
              <span>Ứng Dụng Sandbox</span>
            </NuxtLink>

            <NuxtLink
              v-if="user?.is_superuser"
              to="/admin"
              class="flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-xl transition-all group"
              :class="route.path === '/admin' ? 'bg-aave-violet/15 text-aave-violet border-l-2 border-aave-violet font-medium shadow-sm' : 'text-aave-graphite hover:text-aave-paper hover:bg-white/[0.04]'"
            >
              <UIcon name="i-heroicons-squares-2x2" class="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
              <span>Tổng quan TRD</span>
            </NuxtLink>


            <NuxtLink
              to="/"
              target="_blank"
              class="flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-xl transition-all group text-aave-graphite hover:text-aave-paper hover:bg-white/[0.04]"
            >
              <UIcon name="i-heroicons-globe-alt" class="w-4 h-4 shrink-0 transition-transform group-hover:scale-110 text-aave-violet" />
              <div class="flex items-center justify-between w-full">
                <span>Landing Page</span>
                <UIcon name="i-heroicons-arrow-top-right-on-square" class="w-3 h-3 text-aave-graphite" />
              </div>
            </NuxtLink>
          </nav>
        </div>

        <div v-if="user?.is_superuser">
          <div class="px-3 mb-2 text-[10px] font-mono font-medium uppercase tracking-wider text-aave-graphite flex items-center justify-between">
            <span>02 // Quản trị & Đặc tả TRD</span>
            <span class="text-[9px] text-aave-violet font-mono">6 Phases</span>
          </div>
          <nav class="space-y-1">
            <NuxtLink
              v-for="phase in trdPhases"
              :key="phase.path"
              :to="phase.path"
              class="flex items-center gap-2.5 px-3 py-1.5 text-xs rounded-xl transition-all"
              :class="route.path === phase.path ? 'bg-aave-violet/15 text-aave-violet border-l-2 border-aave-violet font-medium shadow-sm' : 'text-aave-graphite hover:text-aave-paper hover:bg-white/[0.04]'"
            >
              <UIcon :name="phase.icon" class="w-3.5 h-3.5 shrink-0 opacity-80" />
              <span class="truncate">{{ phase.title }}</span>
            </NuxtLink>
          </nav>
        </div>
      </div>

      <div class="p-3 border-t border-white/[0.06] bg-surface-midnight">
        <div class="flex items-center gap-3 p-2 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <div class="h-8 w-8 rounded-full bg-aave-violet flex items-center justify-center font-mono font-bold text-xs text-aave-charcoal uppercase">
            {{ userInitials }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-medium text-white truncate">
              {{ user?.full_name || user?.email?.split('@')[0] || 'Nhà định lượng' }}
            </p>
            <p class="text-[10px] text-aave-graphite truncate font-mono">
              {{ user?.is_superuser ? 'Superuser' : 'Quant Analyst' }}
            </p>
          </div>
          <button
            title="Đăng xuất"
            class="p-1.5 text-aave-graphite hover:text-rose-400 rounded-lg hover:bg-white/[0.05] transition-colors"
            @click="logout"
          >
            <UIcon name="i-heroicons-arrow-right-on-rectangle" class="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>

    <USlideover v-model="mobileOpen">
      <div class="p-4 flex-1 flex flex-col justify-between bg-aave-obsidian text-white h-full">
        <div>
          <div class="flex items-center justify-between pb-4 border-b border-white/[0.06]">
            <NuxtLink to="/admin" class="flex flex-col" @click="mobileOpen = false">
              <span class="font-medium text-sm text-white flex items-center gap-1.5">
                VNSTOCK
                <span class="text-[9px] uppercase font-mono font-bold px-1.5 py-0.2 rounded-full bg-aave-violet/15 text-aave-violet border border-aave-violet/30">PRO</span>
              </span>
              <span class="text-[10px] text-aave-graphite font-mono">Quantitative & Analytics</span>
            </NuxtLink>
            <UButton
              color="gray"
              variant="ghost"
              icon="i-heroicons-x-mark"
              @click="mobileOpen = false"
            />
          </div>

          <div class="mt-4 space-y-4">
            <NuxtLink
              to="/app"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs"
              :class="route.path.startsWith('/app') ? 'bg-aave-violet/15 text-aave-violet font-medium' : 'text-aave-graphite'"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4 text-aave-violet" />
              <span>Ứng Dụng Sandbox</span>
            </NuxtLink>

            <NuxtLink
              v-if="user?.is_superuser"
              to="/admin"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs"
              :class="route.path === '/admin' ? 'bg-aave-violet/15 text-aave-violet font-medium' : 'text-aave-graphite'"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-squares-2x2" class="w-4 h-4" />
              <span>Tổng quan TRD</span>
            </NuxtLink>

            <NuxtLink
              to="/"
              class="flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-aave-violet hover:text-aave-violet"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-globe-alt" class="w-4 h-4" />
              <span>Landing Page</span>
            </NuxtLink>

            <div v-if="user?.is_superuser" class="pt-2 border-t border-white/[0.06]">
              <p class="text-[10px] uppercase text-aave-graphite font-mono font-medium mb-2">Đặc tả TRD 6 Phases</p>
              <NuxtLink
                v-for="phase in trdPhases"
                :key="phase.path"
                :to="phase.path"
                class="flex items-center gap-2.5 px-3 py-1.5 text-xs rounded-xl"
                :class="route.path === phase.path ? 'bg-aave-violet/15 text-aave-violet font-medium' : 'text-aave-graphite'"
                @click="mobileOpen = false"
              >
                <UIcon :name="phase.icon" class="w-3.5 h-3.5" />
                <span>{{ phase.title }}</span>
              </NuxtLink>
            </div>
          </div>
        </div>

        <div class="pt-4 border-t border-white/[0.06] flex justify-between items-center">
          <span class="text-xs text-aave-graphite">
            {{ user?.full_name || 'Quant Analyst' }}
          </span>
          <button class="text-xs text-rose-400 hover:underline" @click="logout">
            Đăng xuất
          </button>
        </div>
      </div>
    </USlideover>

    <div class="flex-1 flex flex-col min-w-0">

      <header class="h-14 shrink-0 border-b border-white/[0.06] bg-aave-inkwell/85 backdrop-blur-xl px-4 lg:px-8 flex items-center justify-between sticky top-0 z-30">
        <div class="flex items-center gap-4">
          <button
            class="lg:hidden p-1.5 text-aave-graphite hover:text-white rounded-lg hover:bg-white/[0.05]"
            @click="mobileOpen = true"
          >
            <UIcon name="i-heroicons-bars-3" class="w-5 h-5" />
          </button>

          <div class="flex items-center gap-3">
            <div class="flex items-center gap-2 px-3 py-1 rounded-full bg-aave-obsidian border border-white/[0.06]">
              <span class="h-2 w-2 rounded-full" :class="sessionStatus.active ? 'bg-aave-violet animate-pulse' : 'bg-aave-graphite'" />
              <span class="text-[11px] font-mono font-medium tracking-tight text-white uppercase">{{ sessionStatus.label }}</span>
              <span class="text-[10px] font-mono text-aave-graphite">VN_TZ {{ currentTime }}</span>
            </div>

            <div class="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-aave-obsidian border border-white/[0.06]">
              <span class="text-[11px] font-mono text-aave-graphite">VN30F1M:</span>
              <span class="text-[11px] font-mono font-bold text-white">1,318.50</span>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded-full bg-aave-violet/15 text-aave-violet">Basis: -2.30</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3">

          <div class="hidden xl:flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-mono font-medium bg-aave-violet/10 text-aave-violet border border-aave-violet/20">
            <UIcon name="i-heroicons-shield-check" class="w-3.5 h-3.5" />
            <span>SANDBOX 100% ISOLATED</span>
          </div>

          <NuxtLink
            v-if="user?.is_superuser && !route.path.startsWith('/admin')"
            to="/admin"
            class="hidden md:inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-mono text-aave-graphite hover:text-white rounded-full bg-aave-obsidian hover:bg-white/[0.05] transition-colors border border-white/[0.06]"
          >
            <UIcon name="i-heroicons-shield-check" class="w-3.5 h-3.5 text-aave-violet" />
            <span>Khu Vực Quản Trị</span>
          </NuxtLink>

          <NuxtLink
            v-if="route.path.startsWith('/admin')"
            to="/app"
            class="hidden md:inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-mono text-aave-graphite hover:text-white rounded-full bg-aave-obsidian hover:bg-white/[0.05] transition-colors border border-white/[0.06]"
          >
            <UIcon name="i-heroicons-cpu-chip" class="w-3.5 h-3.5 text-aave-violet" />
            <span>Vào Ứng Dụng</span>
          </NuxtLink>

          <div
            class="flex items-center gap-2 pl-1.5 pr-3 py-1 rounded-full bg-aave-obsidian border border-white/[0.06]"
          >
            <div class="w-6 h-6 rounded-full bg-aave-violet text-aave-charcoal font-mono font-bold text-[10px] flex items-center justify-center">
              {{ userInitials }}
            </div>
            <span class="text-xs font-medium text-white max-w-[120px] truncate hidden sm:inline">
              {{ user?.full_name || user?.email?.split('@')[0] || 'Tài khoản' }}
            </span>
          </div>
        </div>
      </header>

      <main class="flex-1 p-4 lg:p-8 overflow-y-auto">
        <div class="mx-auto max-w-[1200px]">
          <slot />
        </div>
      </main>

      <footer class="border-t border-white/[0.06] bg-aave-inkwell px-6 py-4 text-xs text-aave-graphite flex flex-col sm:flex-row items-center justify-between gap-3">
        <div class="flex items-center gap-2 text-[11px] text-aave-graphite">
          <UIcon name="i-heroicons-lock-closed" class="w-3.5 h-3.5 text-aave-graphite shrink-0" />
          <span>Vnstock Quantitative Research & Simulation Engine (Tuân thủ T+2 & Khớp lệnh ATO/ATC). Dữ liệu phục vụ nghiên cứu & mô phỏng.</span>
        </div>
        <div class="flex items-center gap-3 text-[11px] font-mono shrink-0">
          <span class="flex items-center gap-1.5 text-aave-violet">
            <span class="w-1.5 h-1.5 rounded-full bg-aave-violet" />
            TELEMETRY 24/7 ACTIVE
          </span>
          <span class="text-aave-iron">|</span>
          <span class="text-aave-graphite">AAVE DUAL-MOOD ARCHITECTURE</span>
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
  return "U"
})

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
    path: "/admin/trd/phase-1",
    title: "Phase 1: Nền tảng & Data",
    icon: "i-heroicons-circle-stack",
  },
  {
    path: "/admin/trd/phase-2",
    title: "Phase 2: Tri-Engine Arch",
    icon: "i-heroicons-cpu-chip",
  },
  {
    path: "/admin/trd/phase-3",
    title: "Phase 3: Daemon 24/7",
    icon: "i-heroicons-clock",
  },
  {
    path: "/admin/trd/phase-4",
    title: "Phase 4: Phái sinh & T+2",
    icon: "i-heroicons-arrows-right-left",
  },
  {
    path: "/admin/trd/phase-5",
    title: "Phase 5: Sổ cái dự báo",
    icon: "i-heroicons-document-check",
  },
  {
    path: "/admin/trd/phase-6",
    title: "Phase 6: Giao diện Ứng dụng",
    icon: "i-heroicons-computer-desktop",
  },
]
</script>
