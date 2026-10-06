<template>
  <div class="space-y-6">

    <div class="card-aave-dark !p-6 relative overflow-hidden">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div class="space-y-2 max-w-3xl">
          <div class="flex items-center gap-2.5">
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-medium bg-aave-violet/15 text-aave-violet border border-aave-violet/30">
              <span class="w-1.5 h-1.5 rounded-full bg-aave-violet animate-pulse" />
              SANDBOX ISOLATED 100%
            </span>
            <span class="text-[12px] font-mono text-aave-graphite">CHẾ ĐỘ MÔ PHỎNG AN TOÀN TUÂN THỦ T+2 VÀ T+0</span>
          </div>

          <h1 class="text-2xl sm:text-3xl font-medium tracking-[-1px] text-white">
            Ứng Dụng Phân Tích Định Lượng & Mô Phỏng Sandbox
          </h1>
          <p class="text-sm text-aave-graphite leading-relaxed">
            Môi trường tính toán độc lập phục vụ nghiên cứu định lượng phái sinh VN30F1M và cổ phiếu cơ sở Việt Nam. Mọi giao dịch và số dư đều là mô phỏng, tuyệt đối không sử dụng tiền thật.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3 shrink-0">
          <button
            type="button"
            class="btn-aave-ghost-dark !py-2.5 !px-4 text-xs font-mono font-medium"
            @click="resetSandbox"
          >
            <UIcon name="i-heroicons-arrow-path" class="w-4 h-4 text-aave-violet" />
            <span>Làm Mới Số Dư</span>
          </button>

          <NuxtLink
            v-if="user?.is_superuser"
            to="/admin"
            class="btn-aave-violet !py-2.5 !px-4 text-xs font-mono font-medium"
          >
            <UIcon name="i-heroicons-shield-check" class="w-4 h-4" />
            <span>Khu Vực Quản Trị</span>
          </NuxtLink>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="card-aave-dark space-y-1.5">
        <div class="flex items-center justify-between text-xs text-aave-graphite">
          <span>Số Dư Tiền Khả Dụng</span>
          <UIcon name="i-heroicons-banknotes" class="w-4 h-4 text-aave-violet" />
        </div>
        <div class="text-xl font-mono font-semibold text-white">
          {{ formatCurrency(account.cash) }}
        </div>
        <div class="text-[11px] font-mono text-aave-graphite">
          Tiền ảo sandbox ban đầu: 100.000.000 đ
        </div>
      </div>

      <div class="card-aave-dark space-y-1.5">
        <div class="flex items-center justify-between text-xs text-aave-graphite">
          <span>Tổng Giá Trị Tài Sản (NAV)</span>
          <UIcon name="i-heroicons-circle-stack" class="w-4 h-4 text-aave-violet" />
        </div>
        <div class="text-xl font-mono font-semibold text-white">
          {{ formatCurrency(totalNav) }}
        </div>
        <div class="text-[11px] font-mono" :class="totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'">
          {{ totalPnl >= 0 ? '+' : '' }}{{ formatCurrency(totalPnl) }} ({{ pnlPercentage }}%)
        </div>
      </div>

      <div class="card-aave-dark space-y-1.5">
        <div class="flex items-center justify-between text-xs text-aave-graphite">
          <span>Ký Quỹ Đã Dùng</span>
          <UIcon name="i-heroicons-scale" class="w-4 h-4 text-aave-violet" />
        </div>
        <div class="text-xl font-mono font-semibold text-white">
          {{ formatCurrency(marginUsed) }}
        </div>
        <div class="text-[11px] font-mono text-aave-ash">
          Tỷ lệ an toàn: {{ marginRatio }}%
        </div>
      </div>

      <div class="card-aave-dark space-y-1.5">
        <div class="flex items-center justify-between text-xs text-aave-graphite">
          <span>Vị Thế Đang Mở</span>
          <UIcon name="i-heroicons-bolt" class="w-4 h-4 text-aave-violet" />
        </div>
        <div class="text-xl font-mono font-semibold text-white">
          {{ positions.length }} vị thế
        </div>
        <div class="text-[11px] font-mono text-aave-graphite">
          {{ orders.length }} lệnh đã thực hiện
        </div>
      </div>
    </div>

    <div class="flex items-center gap-2 border-b border-white/[0.08] pb-1">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="px-4 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-2"
        :class="activeTab === tab.id ? 'bg-aave-violet/15 text-aave-violet' : 'text-aave-graphite hover:text-white hover:bg-white/[0.03]'"
        @click="activeTab = tab.id"
      >
        <UIcon :name="tab.icon" class="w-4 h-4" />
        <span>{{ tab.label }}</span>
      </button>
    </div>

    <div v-if="activeTab === 'trading'" class="grid grid-cols-12 gap-6">

      <div class="col-span-12 lg:col-span-5 card-aave-dark space-y-5">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <UIcon name="i-heroicons-calculator" class="w-5 h-5 text-aave-violet" />
            <h2 class="text-base font-medium text-white">Đặt Lệnh Mô Phỏng Sandbox</h2>
          </div>
          <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-aave-violet/10 text-aave-violet border border-aave-violet/20">
            T+0 / T+2
          </span>
        </div>

        <form class="space-y-4" @submit.prevent="handlePlaceOrder">
          <div>
            <label class="block text-xs font-medium text-aave-ash mb-1.5">
              Mã Tài Sản
            </label>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="sym in availableSymbols"
                :key="sym"
                type="button"
                class="py-1.5 px-3 text-xs font-mono rounded-lg border text-center transition-all"
                :class="form.symbol === sym ? 'border-aave-violet bg-aave-violet/15 text-aave-violet font-semibold' : 'border-white/[0.08] bg-white/[0.02] text-aave-graphite hover:text-white'"
                @click="selectSymbol(sym)"
              >
                {{ sym }}
              </button>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-aave-ash mb-1.5">
                Chiều Giao Dịch
              </label>
              <div class="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  class="py-2 text-xs font-semibold rounded-lg transition-colors"
                  :class="form.side === 'LONG' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold' : 'bg-white/[0.03] text-aave-graphite border border-white/[0.06] hover:text-white'"
                  @click="form.side = 'LONG'"
                >
                  LONG / MUA
                </button>
                <button
                  type="button"
                  class="py-2 text-xs font-semibold rounded-lg transition-colors"
                  :class="form.side === 'SHORT' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30 font-bold' : 'bg-white/[0.03] text-aave-graphite border border-white/[0.06] hover:text-white'"
                  @click="form.side = 'SHORT'"
                >
                  SHORT / BÁN
                </button>
              </div>
            </div>

            <div>
              <label class="block text-xs font-medium text-aave-ash mb-1.5">
                Loại Lệnh
              </label>
              <select
                v-model="form.orderType"
                class="w-full h-[38px] px-3 text-xs rounded-lg bg-surface-midnight border border-white/[0.08] text-white focus:outline-none focus:border-aave-violet font-mono"
              >
                <option value="LO">LO - Giới Hạn</option>
                <option value="ATO">ATO - Phiên Mở Cửa</option>
                <option value="ATC">ATC - Phiên Đóng Cửa</option>
                <option value="MP">MP - Thị Trường</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-aave-ash mb-1.5">
                Giá Đặt (VND / Điểm)
              </label>
              <input
                v-model.number="form.price"
                type="number"
                step="0.1"
                min="1"
                required
                class="w-full h-10 px-3 text-xs font-mono rounded-lg bg-surface-midnight border border-white/[0.08] text-white focus:outline-none focus:border-aave-violet"
              >
            </div>

            <div>
              <label class="block text-xs font-medium text-aave-ash mb-1.5">
                Khối Lượng
              </label>
              <input
                v-model.number="form.quantity"
                type="number"
                min="1"
                required
                class="w-full h-10 px-3 text-xs font-mono rounded-lg bg-surface-midnight border border-white/[0.08] text-white focus:outline-none focus:border-aave-violet"
              >
            </div>
          </div>

          <div class="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06] space-y-1.5 text-xs font-mono">
            <div class="flex justify-between text-aave-graphite">
              <span>Giá trị ước tính:</span>
              <span class="text-white">{{ formatCurrency(estimatedOrderValue) }}</span>
            </div>
            <div class="flex justify-between text-aave-graphite">
              <span>Ký quỹ yêu cầu (17%):</span>
              <span class="text-aave-violet font-semibold">{{ formatCurrency(estimatedRequiredMargin) }}</span>
            </div>
          </div>

          <button
            type="submit"
            :disabled="isSubmittingOrder || estimatedRequiredMargin > account.cash"
            class="btn-aave-violet w-full !py-3 text-xs font-mono font-semibold"
            :class="estimatedRequiredMargin > account.cash ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <UIcon name="i-heroicons-arrow-up-right" class="w-4 h-4" />
            <span>{{ estimatedRequiredMargin > account.cash ? 'Số dư không đủ ký quỹ' : 'Xác Nhận Đặt Lệnh Mô Phỏng' }}</span>
          </button>
        </form>
      </div>

      <div class="col-span-12 lg:col-span-7 space-y-6">

        <div class="card-aave-dark space-y-4">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div class="flex items-center gap-2">
              <UIcon name="i-heroicons-briefcase" class="w-5 h-5 text-aave-violet" />
              <h2 class="text-base font-medium text-white">Danh Mục Vị Thế Đang Mở</h2>
            </div>
            <span class="text-xs font-mono text-aave-graphite">{{ positions.length }} vị thế</span>
          </div>

          <div v-if="positions.length === 0" class="py-8 text-center text-xs text-aave-graphite">
            Chưa có vị thế nào đang mở. Hãy đặt lệnh mô phỏng từ biểu mẫu bên cạnh.
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-left text-xs font-mono">
              <thead class="text-aave-graphite border-b border-white/[0.06]">
                <tr>
                  <th class="pb-2">Mã</th>
                  <th class="pb-2">Vị Thế</th>
                  <th class="pb-2 text-right">Khối Lượng</th>
                  <th class="pb-2 text-right">Giá Vốn</th>
                  <th class="pb-2 text-right">Giá Hiện Tại</th>
                  <th class="pb-2 text-right">Lãi/Lỗ (PnL)</th>
                  <th class="pb-2 text-right">Thao Tác</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/[0.04]">
                <tr v-for="pos in positions" :key="pos.id" class="hover:bg-white/[0.02]">
                  <td class="py-3 font-semibold text-white">{{ pos.symbol }}</td>
                  <td class="py-3">
                    <span
                      class="px-2 py-0.5 rounded text-[10px] font-bold"
                      :class="pos.side === 'LONG' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'"
                    >
                      {{ pos.side }}
                    </span>
                  </td>
                  <td class="py-3 text-right">{{ pos.quantity }}</td>
                  <td class="py-3 text-right">{{ formatNumber(pos.entryPrice) }}</td>
                  <td class="py-3 text-right text-white">{{ formatNumber(pos.currentPrice) }}</td>
                  <td class="py-3 text-right font-semibold" :class="pos.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'">
                    {{ pos.pnl >= 0 ? '+' : '' }}{{ formatCurrency(pos.pnl) }}
                  </td>
                  <td class="py-3 text-right">
                    <button
                      type="button"
                      class="px-2.5 py-1 text-[11px] rounded bg-white/[0.04] text-rose-300 hover:bg-rose-500/20 transition-colors"
                      @click="closePosition(pos.id)"
                    >
                      Đóng Vị Thế
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card-aave-dark space-y-4">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div class="flex items-center gap-2">
              <UIcon name="i-heroicons-clock" class="w-5 h-5 text-aave-violet" />
              <h2 class="text-base font-medium text-white">Sổ Lệnh Giao Dịch Gần Đây</h2>
            </div>
            <span class="text-xs font-mono text-aave-graphite">{{ orders.length }} lệnh</span>
          </div>

          <div v-if="orders.length === 0" class="py-8 text-center text-xs text-aave-graphite">
            Chưa có lệnh nào được tạo trong phiên mô phỏng này.
          </div>

          <div v-else class="space-y-2 max-h-64 overflow-y-auto pr-1">
            <div
              v-for="ord in orders"
              :key="ord.id"
              class="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.06] flex items-center justify-between text-xs font-mono"
            >
              <div class="flex items-center gap-2.5">
                <span
                  class="px-2 py-0.5 rounded text-[10px] font-bold"
                  :class="ord.side === 'LONG' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'"
                >
                  {{ ord.side }}
                </span>
                <span class="font-semibold text-white">{{ ord.symbol }}</span>
                <span class="text-aave-graphite">{{ ord.orderType }}</span>
                <span class="text-aave-ash">{{ ord.quantity }} @ {{ formatNumber(ord.price) }}</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="text-[11px] text-aave-graphite">{{ ord.time }}</span>
                <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400">ĐÃ KHỚP</span>
              </div>
            </div>
          </div>
        </div>

      </div>

    </div>

    <div v-else-if="activeTab === 'quant'" class="grid grid-cols-12 gap-6">

      <div class="col-span-12 lg:col-span-4 card-aave-dark space-y-4">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <UIcon name="i-heroicons-chart-bar" class="w-5 h-5 text-aave-violet" />
            <h2 class="text-base font-medium text-white">Engine 1: Kỹ Thuật & Khớp Lệnh</h2>
          </div>
          <span class="text-xs font-mono text-emerald-400 font-semibold">+48.0 pts</span>
        </div>
        <p class="text-xs text-aave-graphite leading-relaxed">
          Đo lường mất cân bằng khối lượng khớp chủ động, VWAP và mô hình nến 1m phái sinh VN30F1M.
        </p>
        <div class="space-y-3 text-xs font-mono pt-2">
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Khớp Mua Chủ Động:</span>
            <span class="text-emerald-400">62.4% (Áp đảo)</span>
          </div>
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Độ Lệch VWAP Intraday:</span>
            <span class="text-white">+2.45 pts</span>
          </div>
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Trạng Thái Xu Hướng:</span>
            <span class="text-aave-violet font-semibold">BULLISH BREAKOUT</span>
          </div>
        </div>
      </div>

      <div class="col-span-12 lg:col-span-4 card-aave-dark space-y-4">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <UIcon name="i-heroicons-banknotes" class="w-5 h-5 text-aave-violet" />
            <h2 class="text-base font-medium text-white">Engine 2: Thanh Khoản & T+2</h2>
          </div>
          <span class="text-xs font-mono text-emerald-400 font-semibold">+34.0 pts</span>
        </div>
        <p class="text-xs text-aave-graphite leading-relaxed">
          Theo dõi dòng tiền Khối Ngoại, Tự Doanh và áp lực cung hàng về phiên chiều T+2 cơ sở.
        </p>
        <div class="space-y-3 text-xs font-mono pt-2">
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Khối Ngoại Ròng:</span>
            <span class="text-emerald-400">+142.8 tỷ VND</span>
          </div>
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Tự Doanh Ròng:</span>
            <span class="text-white">+58.2 tỷ VND</span>
          </div>
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Áp Lực Cung T+2 Chiều:</span>
            <span class="text-emerald-400">Thấp (Hấp thụ tốt)</span>
          </div>
        </div>
      </div>

      <div class="col-span-12 lg:col-span-4 card-aave-dark space-y-4">
        <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div class="flex items-center gap-2">
            <UIcon name="i-heroicons-cpu-chip" class="w-5 h-5 text-aave-violet" />
            <h2 class="text-base font-medium text-white">Engine 3: Quant ML & Basis</h2>
          </div>
          <span class="text-xs font-mono text-aave-violet font-semibold">+64.5 pts</span>
        </div>
        <p class="text-xs text-aave-graphite leading-relaxed">
          Mô hình Monte Carlo và phân phối xác suất cân bằng phiên ATC, độ lệch Basis VN30F1M.
        </p>
        <div class="space-y-3 text-xs font-mono pt-2">
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Độ Lệch Basis VN30:</span>
            <span class="text-aave-violet">-2.30 pts (Hội tụ)</span>
          </div>
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Giá Cân Bằng ATC Dự Báo:</span>
            <span class="text-white">1.321,50 pts</span>
          </div>
          <div class="flex justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
            <span class="text-aave-graphite">Xác Suất Tăng T+1:</span>
            <span class="text-emerald-400">72.4%</span>
          </div>
        </div>
      </div>

      <div class="col-span-12 card-aave-dark !p-6 space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-mono uppercase text-aave-violet font-semibold tracking-wider">
            QUYẾT ĐỊNH TỔNG HỢP TRI-ENGINE (ENSEMBLE CONSENSUS)
          </span>
          <span class="px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-400 font-mono text-xs font-bold border border-emerald-500/30">
            TÍN HIỆU: LONG BIAS (+64.5)
          </span>
        </div>
        <p class="text-xs text-aave-ash leading-relaxed">
          Cả 3 động cơ đều xác nhận xu hướng đồng thuận với độ tin cậy cao (Ensemble Weight: Kỹ thuật 40%, Dòng tiền 35%, Quant ML 25%). Khuyến nghị duy trì vị thế Long phái sinh VN30F1M với mục tiêu 1.325,0 và mức cắt lỗ kỷ luật tại 1.312,0.
        </p>
      </div>

    </div>

    <div v-else-if="activeTab === 'baskets'" class="space-y-6">

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

        <div class="card-aave-dark space-y-4">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div>
              <span class="text-[10px] font-mono uppercase text-aave-violet">T+2 HORIZON</span>
              <h3 class="text-base font-medium text-white">Rổ Cổ Phiếu Tuần</h3>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-aave-violet/15 text-aave-violet">Alpha Momentum</span>
          </div>
          <p class="text-xs text-aave-graphite">
            Chiến lược bám theo đà tăng trưởng ngắn hạn, tối ưu thanh toán T+2 và khối lượng khớp lệnh đột biến.
          </p>
          <div class="space-y-2 font-mono text-xs">
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">FPT</span>
              <span class="text-emerald-400 font-semibold">+3.8%</span>
              <span class="text-aave-graphite">Tỷ trọng: 35%</span>
            </div>
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">TCB</span>
              <span class="text-emerald-400 font-semibold">+2.9%</span>
              <span class="text-aave-graphite">Tỷ trọng: 35%</span>
            </div>
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">HPG</span>
              <span class="text-emerald-400 font-semibold">+2.1%</span>
              <span class="text-aave-graphite">Tỷ trọng: 30%</span>
            </div>
          </div>
          <button
            type="button"
            class="btn-aave-ghost-dark w-full !py-2 text-xs font-mono"
            @click="allocateBasket('Tuần', ['FPT', 'TCB', 'HPG'])"
          >
            <span>Phân Bổ Vào Sandbox</span>
          </button>
        </div>

        <div class="card-aave-dark space-y-4">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div>
              <span class="text-[10px] font-mono uppercase text-aave-violet">SECTOR ROTATION</span>
              <h3 class="text-base font-medium text-white">Rổ Cổ Phiếu Tháng</h3>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-aave-violet/15 text-aave-violet">Dòng Tiền Tổ Chức</span>
          </div>
          <p class="text-xs text-aave-graphite">
            Chiến lược luân chuyển dòng tiền các ngành dẫn dắt (Ngân hàng, Bán lẻ, Công nghệ) trong chu kỳ 30 ngày.
          </p>
          <div class="space-y-2 font-mono text-xs">
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">MWG</span>
              <span class="text-emerald-400 font-semibold">+5.4%</span>
              <span class="text-aave-graphite">Tỷ trọng: 40%</span>
            </div>
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">MBB</span>
              <span class="text-emerald-400 font-semibold">+4.1%</span>
              <span class="text-aave-graphite">Tỷ trọng: 30%</span>
            </div>
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">SSI</span>
              <span class="text-emerald-400 font-semibold">+3.5%</span>
              <span class="text-aave-graphite">Tỷ trọng: 30%</span>
            </div>
          </div>
          <button
            type="button"
            class="btn-aave-ghost-dark w-full !py-2 text-xs font-mono"
            @click="allocateBasket('Tháng', ['MWG', 'MBB', 'SSI'])"
          >
            <span>Phân Bổ Vào Sandbox</span>
          </button>
        </div>

        <div class="card-aave-dark space-y-4">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div>
              <span class="text-[10px] font-mono uppercase text-aave-violet">VALUE & ROE</span>
              <h3 class="text-base font-medium text-white">Rổ Cổ Phiếu Quý</h3>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-aave-violet/15 text-aave-violet">Tăng Trưởng Bền Vững</span>
          </div>
          <p class="text-xs text-aave-graphite">
            Sàng lọc cổ phiếu cơ bản có ROE > 20%, định giá P/E hấp dẫn và tỷ lệ chi trả cổ tức tiền mặt đều đặn.
          </p>
          <div class="space-y-2 font-mono text-xs">
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">FPT</span>
              <span class="text-emerald-400 font-semibold">+8.2%</span>
              <span class="text-aave-graphite">Tỷ trọng: 40%</span>
            </div>
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">VNM</span>
              <span class="text-emerald-400 font-semibold">+4.6%</span>
              <span class="text-aave-graphite">Tỷ trọng: 30%</span>
            </div>
            <div class="flex justify-between items-center p-2 rounded bg-white/[0.02]">
              <span class="font-bold text-white">VHM</span>
              <span class="text-emerald-400 font-semibold">+3.9%</span>
              <span class="text-aave-graphite">Tỷ trọng: 30%</span>
            </div>
          </div>
          <button
            type="button"
            class="btn-aave-ghost-dark w-full !py-2 text-xs font-mono"
            @click="allocateBasket('Quý', ['FPT', 'VNM', 'VHM'])"
          >
            <span>Phân Bổ Vào Sandbox</span>
          </button>
        </div>

      </div>

    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useAuth } from "~/composables/useAuth"
import { useCustomToast } from "~/composables/useCustomToast"

useHead({
  title: "Ứng Dụng Phân Tích Định Lượng & Mô Phỏng Sandbox - Vnstock",
})

const { user } = useAuth()
const { showSuccessToast, showErrorToast } = useCustomToast()

const activeTab = ref<"trading" | "quant" | "baskets">("trading")
const tabs = [
  {
    id: "trading",
    label: "Mô Phỏng Sandbox",
    icon: "i-heroicons-chart-bar-square",
  },
  { id: "quant", label: "Tín Hiệu Định Lượng", icon: "i-heroicons-cpu-chip" },
  { id: "baskets", label: "Rổ Cổ Phiếu Alpha", icon: "i-heroicons-sparkles" },
] as const

interface SandboxPosition {
  id: string
  symbol: string
  side: "LONG" | "SHORT"
  quantity: number
  entryPrice: number
  currentPrice: number
  pnl: number
}

interface SandboxOrder {
  id: string
  symbol: string
  side: "LONG" | "SHORT"
  orderType: string
  quantity: number
  price: number
  time: string
}

const defaultCash = 100_000_000

const account = reactive({
  cash: defaultCash,
})

const positions = ref<SandboxPosition[]>([
  {
    id: "pos-1",
    symbol: "VN30F1M",
    side: "LONG",
    quantity: 2,
    entryPrice: 1315.0,
    currentPrice: 1318.5,
    pnl: 700_000,
  },
])

const orders = ref<SandboxOrder[]>([
  {
    id: "ord-1",
    symbol: "VN30F1M",
    side: "LONG",
    orderType: "LO",
    quantity: 2,
    price: 1315.0,
    time: "09:30:15",
  },
])

const availableSymbols = ["VN30F1M", "FPT", "HPG", "TCB", "MWG", "VNM"]

const form = reactive({
  symbol: "VN30F1M",
  side: "LONG" as "LONG" | "SHORT",
  orderType: "LO",
  price: 1318.5,
  quantity: 1,
})

const isSubmittingOrder = ref(false)

const estimatedOrderValue = computed(() => {
  if (form.symbol === "VN30F1M") {
    return form.price * 100_000 * form.quantity
  }
  return form.price * 1_000 * form.quantity
})

const estimatedRequiredMargin = computed(() => {
  if (form.symbol === "VN30F1M") {
    return estimatedOrderValue.value * 0.17
  }
  return estimatedOrderValue.value
})

const totalPnl = computed(() => {
  return positions.value.reduce((acc, pos) => acc + pos.pnl, 0)
})

const totalNav = computed(() => {
  return account.cash + marginUsed.value + totalPnl.value
})

const pnlPercentage = computed(() => {
  const base = defaultCash
  return ((totalPnl.value / base) * 100).toFixed(2)
})

const marginUsed = computed(() => {
  return positions.value.reduce((acc, pos) => {
    if (pos.symbol === "VN30F1M") {
      return acc + pos.entryPrice * 100_000 * pos.quantity * 0.17
    }
    return acc + pos.entryPrice * 1_000 * pos.quantity
  }, 0)
})

const marginRatio = computed(() => {
  if (totalNav.value <= 0) return "0.0"
  return ((marginUsed.value / totalNav.value) * 100).toFixed(1)
})

const selectSymbol = (sym: string) => {
  form.symbol = sym
  if (sym === "VN30F1M") {
    form.price = 1318.5
    form.quantity = 1
  } else if (sym === "FPT") {
    form.price = 138.5
    form.quantity = 100
  } else if (sym === "HPG") {
    form.price = 28.2
    form.quantity = 200
  } else if (sym === "TCB") {
    form.price = 24.5
    form.quantity = 200
  } else if (sym === "MWG") {
    form.price = 65.0
    form.quantity = 100
  } else {
    form.price = 72.0
    form.quantity = 100
  }
}

const handlePlaceOrder = () => {
  if (estimatedRequiredMargin.value > account.cash) {
    showErrorToast(
      "Lỗi ký quỹ",
      "Số dư tiền ảo không đủ để thực hiện lệnh mô phỏng.",
    )
    return
  }

  isSubmittingOrder.value = true
  try {
    account.cash -= estimatedRequiredMargin.value

    const newOrder: SandboxOrder = {
      id: `ord-${Date.now()}`,
      symbol: form.symbol,
      side: form.side,
      orderType: form.orderType,
      quantity: form.quantity,
      price: form.price,
      time: new Date().toLocaleTimeString("vi-VN"),
    }
    orders.value.unshift(newOrder)

    const existingPos = positions.value.find(
      (p) => p.symbol === form.symbol && p.side === form.side,
    )
    if (existingPos) {
      const totalQty = existingPos.quantity + form.quantity
      existingPos.entryPrice = Number(
        (
          (existingPos.entryPrice * existingPos.quantity +
            form.price * form.quantity) /
          totalQty
        ).toFixed(2),
      )
      existingPos.quantity = totalQty
    } else {
      positions.value.push({
        id: `pos-${Date.now()}`,
        symbol: form.symbol,
        side: form.side,
        quantity: form.quantity,
        entryPrice: form.price,
        currentPrice: form.price,
        pnl: 0,
      })
    }

    saveState()
    showSuccessToast(
      "Đặt lệnh thành công",
      `Đã khớp mô phỏng ${form.side} ${form.quantity} ${form.symbol} tại giá ${formatNumber(form.price)}.`,
    )
  } catch (err: unknown) {
    showErrorToast("Lỗi", "Không thể hoàn tất lệnh mô phỏng.")
  } finally {
    isSubmittingOrder.value = false
  }
}

const closePosition = (id: string) => {
  const index = positions.value.findIndex((p) => p.id === id)
  if (index === -1) return

  const pos = positions.value[index]
  const returnedMargin =
    pos.symbol === "VN30F1M"
      ? pos.entryPrice * 100_000 * pos.quantity * 0.17
      : pos.entryPrice * 1_000 * pos.quantity

  account.cash += returnedMargin + pos.pnl
  positions.value.splice(index, 1)

  orders.value.unshift({
    id: `ord-close-${Date.now()}`,
    symbol: pos.symbol,
    side: pos.side === "LONG" ? "SHORT" : "LONG",
    orderType: "MP",
    quantity: pos.quantity,
    price: pos.currentPrice,
    time: new Date().toLocaleTimeString("vi-VN"),
  })

  saveState()
  showSuccessToast(
    "Đóng vị thế",
    `Đã đóng vị thế ${pos.symbol} với lợi nhuận ${formatCurrency(pos.pnl)}.`,
  )
}

const allocateBasket = (name: string, basketSymbols: string[]) => {
  showSuccessToast(
    `Phân bổ rổ ${name}`,
    `Đã ghi nhận chiến lược phân bổ thử nghiệm cho các mã: ${basketSymbols.join(", ")}.`,
  )
}

const resetSandbox = () => {
  account.cash = defaultCash
  positions.value = [
    {
      id: "pos-1",
      symbol: "VN30F1M",
      side: "LONG",
      quantity: 2,
      entryPrice: 1315.0,
      currentPrice: 1318.5,
      pnl: 700_000,
    },
  ]
  orders.value = [
    {
      id: "ord-1",
      symbol: "VN30F1M",
      side: "LONG",
      orderType: "LO",
      quantity: 2,
      price: 1315.0,
      time: "09:30:15",
    },
  ]
  saveState()
  showSuccessToast(
    "Làm mới thành công",
    "Số dư tiền ảo đã được đặt lại 100.000.000 đ.",
  )
}

const saveState = () => {
  if (process.client) {
    localStorage.setItem(
      "vnstock_sandbox_state",
      JSON.stringify({
        cash: account.cash,
        positions: positions.value,
        orders: orders.value,
      }),
    )
  }
}

const loadState = () => {
  if (process.client) {
    const raw = localStorage.getItem("vnstock_sandbox_state")
    if (raw) {
      try {
        const parsed = JSON.parse(raw)
        if (typeof parsed.cash === "number") account.cash = parsed.cash
        if (Array.isArray(parsed.positions)) positions.value = parsed.positions
        if (Array.isArray(parsed.orders)) orders.value = parsed.orders
      } catch {
        // ignore parse error
      }
    }
  }
}

onMounted(() => {
  loadState()
})

const formatCurrency = (val: number) => {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(val)
}

const formatNumber = (val: number) => {
  return new Intl.NumberFormat("vi-VN", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(val)
}
</script>
