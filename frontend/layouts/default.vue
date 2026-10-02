<template>
  <div class="flex min-h-screen bg-slate-950 text-slate-100">
    <!-- Desktop Sidebar -->
    <aside
      class="hidden lg:flex flex-col w-64 shrink-0 border-r border-slate-800/80 bg-slate-900/60 backdrop-blur-md"
    >
      <!-- Sidebar Header -->
      <div class="h-16 flex items-center gap-3 px-5 border-b border-slate-800/80">
        <div class="h-9 w-9 rounded-lg bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 font-bold text-white text-base">
          VN
        </div>
        <div class="flex flex-col">
          <span class="font-bold tracking-tight text-sm text-slate-100 flex items-center gap-1.5">
            VNSTOCK
            <span class="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">PRO</span>
          </span>
          <span class="text-[11px] text-slate-400 font-mono">Quants & Engine 24/7</span>
        </div>
      </div>

      <!-- Navigation Links -->
      <div class="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        <!-- Main Section -->
        <div>
          <div class="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Tổng quan
          </div>
          <nav class="space-y-1">
            <NuxtLink
              to="/"
              class="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors group"
              :class="route.path === '/' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/60'"
            >
              <UIcon name="i-heroicons-home" class="w-4 h-4 shrink-0" />
              <span>Dashboard</span>
            </NuxtLink>

            <NuxtLink
              to="/stock"
              class="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors group"
              :class="route.path.startsWith('/stock') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/60'"
            >
              <UIcon name="i-heroicons-chart-bar" class="w-4 h-4 shrink-0" />
              <span>Thị trường cổ phiếu</span>
            </NuxtLink>

            <NuxtLink
              to="/items"
              class="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors group"
              :class="route.path.startsWith('/items') ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/60'"
            >
              <UIcon name="i-heroicons-folder" class="w-4 h-4 shrink-0" />
              <span>Danh mục Items</span>
            </NuxtLink>
          </nav>
        </div>

        <!-- TRD Blueprints Section -->
        <div>
          <div class="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
            <span>Đặc tả kỹ thuật TRD</span>
            <span class="text-[10px] text-emerald-400 font-mono">6 Phases</span>
          </div>
          <nav class="space-y-1">
            <NuxtLink
              v-for="phase in trdPhases"
              :key="phase.path"
              :to="phase.path"
              class="flex items-center gap-2.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
              :class="route.path === phase.path ? 'bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'"
            >
              <UIcon :name="phase.icon" class="w-3.5 h-3.5 shrink-0" />
              <span class="truncate">{{ phase.title }}</span>
            </NuxtLink>
          </nav>
        </div>

        <!-- Admin Section -->
        <div v-if="user?.is_superuser">
          <div class="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-amber-400/80">
            Quản trị hệ thống
          </div>
          <nav class="space-y-1">
            <NuxtLink
              to="/admin"
              class="flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors"
              :class="route.path.startsWith('/admin') ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/60'"
            >
              <UIcon name="i-heroicons-users" class="w-4 h-4 shrink-0" />
              <span>Quản lý người dùng</span>
            </NuxtLink>
          </nav>
        </div>
      </div>

      <!-- User Profile in Sidebar Footer -->
      <div class="p-3 border-t border-slate-800/80 bg-slate-900/40">
        <div class="flex items-center gap-3 p-2 rounded-lg bg-slate-800/50 border border-slate-800">
          <div class="h-9 w-9 rounded-full bg-slate-700 flex items-center justify-center font-bold text-xs text-slate-200 uppercase">
            {{ userInitials }}
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-xs font-semibold text-slate-200 truncate">
              {{ user?.full_name || user?.email || 'Người dùng' }}
            </p>
            <p class="text-[11px] text-slate-400 truncate font-mono">
              {{ user?.email }}
            </p>
          </div>
          <NuxtLink
            to="/settings"
            title="Cài đặt tài khoản"
            class="p-1.5 text-slate-400 hover:text-slate-200 rounded-md hover:bg-slate-700/60 transition-colors"
          >
            <UIcon name="i-heroicons-cog-6-tooth" class="w-4 h-4" />
          </NuxtLink>
          <button
            title="Đăng xuất"
            class="p-1.5 text-slate-400 hover:text-rose-400 rounded-md hover:bg-slate-700/60 transition-colors"
            @click="logout"
          >
            <UIcon name="i-heroicons-arrow-right-on-rectangle" class="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Mobile Sidebar Drawer -->
    <USlideover v-model="mobileOpen">
      <div class="p-4 flex-1 flex flex-col justify-between bg-slate-950 text-slate-100 h-full">
        <div>
          <div class="flex items-center justify-between pb-4 border-b border-slate-800">
            <div class="flex items-center gap-2">
              <div class="h-8 w-8 rounded-lg bg-emerald-600 flex items-center justify-center font-bold text-white text-sm">
                VN
              </div>
              <span class="font-bold text-slate-100">VNSTOCK QUANTS</span>
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
              class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm"
              :class="route.path === '/' ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-300'"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-home" class="w-4 h-4" />
              <span>Dashboard</span>
            </NuxtLink>

            <NuxtLink
              to="/stock"
              class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm"
              :class="route.path.startsWith('/stock') ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-300'"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-chart-bar" class="w-4 h-4" />
              <span>Thị trường cổ phiếu</span>
            </NuxtLink>

            <NuxtLink
              to="/items"
              class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm"
              :class="route.path.startsWith('/items') ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-300'"
              @click="mobileOpen = false"
            >
              <UIcon name="i-heroicons-folder" class="w-4 h-4" />
              <span>Danh mục Items</span>
            </NuxtLink>

            <div class="pt-2 border-t border-slate-800">
              <p class="text-xs uppercase text-slate-500 font-semibold mb-2">Đặc tả TRD</p>
              <NuxtLink
                v-for="phase in trdPhases"
                :key="phase.path"
                :to="phase.path"
                class="flex items-center gap-2.5 px-3 py-1.5 text-xs rounded-lg"
                :class="route.path === phase.path ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-400'"
                @click="mobileOpen = false"
              >
                <UIcon :name="phase.icon" class="w-3.5 h-3.5" />
                <span>{{ phase.title }}</span>
              </NuxtLink>
            </div>
          </div>
        </div>

        <div class="pt-4 border-t border-slate-800 flex justify-between items-center">
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
      <!-- Top Navbar Header -->
      <header class="h-16 shrink-0 border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-md px-4 lg:px-8 flex items-center justify-between sticky top-0 z-30">
        <div class="flex items-center gap-3">
          <button
            class="lg:hidden p-2 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800"
            @click="mobileOpen = true"
          >
            <UIcon name="i-heroicons-bars-3" class="w-5 h-5" />
          </button>
          <div class="flex items-center gap-2">
            <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span class="text-xs font-mono text-emerald-400 font-medium">VN30F1M Live Engine</span>
            <span class="text-xs text-slate-400 hidden sm:inline">| Phân tích định lượng liên tục</span>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <NuxtLink
            to="/stock"
            class="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors border border-slate-700/60"
          >
            <UIcon name="i-heroicons-magnifying-glass" class="w-3.5 h-3.5 text-slate-400" />
            Tra cứu mã CK
          </NuxtLink>

          <!-- Current User Badge -->
          <NuxtLink
            to="/settings"
            class="flex items-center gap-2 pl-2 pr-3 py-1 rounded-full bg-slate-800/60 border border-slate-700/60 hover:bg-slate-800 transition-colors"
          >
            <div class="w-6 h-6 rounded-full bg-emerald-600/80 text-white font-bold text-[10px] flex items-center justify-center">
              {{ userInitials }}
            </div>
            <span class="text-xs font-medium text-slate-300 max-w-[120px] truncate">
              {{ user?.full_name || user?.email?.split('@')[0] || 'Tài khoản' }}
            </span>
          </NuxtLink>
        </div>
      </header>

      <!-- Page Content -->
      <main class="flex-1 p-4 lg:p-8 overflow-y-auto">
        <div class="mx-auto max-w-7xl">
          <slot />
        </div>
      </main>

      <!-- Footer -->
      <footer class="border-t border-slate-800/60 px-6 py-4 text-center text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2">
        <p>Vnstock Quantitative Research & Simulation Platform &copy; 2026. Tuân thủ chuẩn T+2 & ATO/ATC.</p>
        <div class="flex items-center gap-4 text-xs font-mono">
          <span class="text-emerald-400">Simulation Mode Active</span>
          <span>FastAPI + Nuxt 3</span>
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
    title: "Phase 4: Paper & T+2",
    icon: "i-heroicons-square-3-stack-3d",
  },
  {
    path: "/trd/phase-5",
    title: "Phase 5: Forecast Journal",
    icon: "i-heroicons-archive-box",
  },
  {
    path: "/trd/phase-6",
    title: "Phase 6: Cockpit Preview",
    icon: "i-heroicons-chart-pie",
  },
]
</script>
