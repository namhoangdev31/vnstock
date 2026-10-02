<template>
  <div class="space-y-6">
    <!-- Breadcrumb / Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs text-slate-400 font-mono mb-1">
          <NuxtLink to="/" class="hover:text-emerald-400">Dashboard</NuxtLink>
          <span>/</span>
          <span class="text-emerald-400">TRD Phase 1</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-circle-stack" class="w-7 h-7 text-emerald-400" />
          Phase 1: Nền tảng dữ liệu & Persistence
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          PostgreSQL-first storage, rate limiting chống ban IP, schema audit log và models chuẩn timezone aware.
        </p>
      </div>

      <div class="flex items-center gap-2">
        <span class="px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
          <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
          Definition of Done: 100%
        </span>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex border-b border-slate-800 gap-4">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
        :class="activeTab === tab.id ? 'border-emerald-400 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = tab.id"
      >
        <UIcon :name="tab.icon" class="w-4 h-4" />
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab 1: Markdown Spec -->
    <div v-if="activeTab === 'spec'">
      <MarkdownViewer :content="phase1Markdown" filename="trd-phase-1-persistence.md" />
    </div>

    <!-- Tab 2: Test Matrix -->
    <div v-else-if="activeTab === 'tests'">
      <TestMatrix :tests="testCases" />
    </div>

    <!-- Tab 3: Schema Playground -->
    <div v-else-if="activeTab === 'schema'" class="space-y-4">
      <div class="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
        <h3 class="text-sm font-bold text-white flex items-center gap-2">
          <UIcon name="i-heroicons-code-bracket" class="w-5 h-5 text-emerald-400" />
          Mô hình cơ sở dữ liệu quan hệ (PostgreSQL SQLModel)
        </h3>
        <p class="text-xs text-slate-400">
          Các thực thể đã được migrate vào PostgreSQL đảm bảo tính độc lập giữa dữ liệu thị trường và paper trading sandbox:
        </p>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
          <div
            v-for="s in schemas"
            :key="s.name"
            class="p-4 rounded-lg border transition-all cursor-pointer"
            :class="selectedSchema === s.name ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300' : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'"
            @click="selectedSchema = s.name"
          >
            <div class="font-mono font-bold text-xs text-white">{{ s.table }}</div>
            <div class="text-[11px] text-slate-400 mt-1">{{ s.desc }}</div>
          </div>
        </div>

        <div v-if="currentSchema" class="mt-4 p-4 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs overflow-x-auto text-emerald-400">
          <pre>{{ currentSchema.code }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { phase1Markdown } from "~/data/trd/phase1SpecContent"
useHead({
  title: "TRD Phase 1: Nền tảng & Persistence - Vnstock Quants",
})

const activeTab = ref<"spec" | "tests" | "schema">("spec")
const selectedSchema = ref("stock_symbol")

const tabs: Array<{
  id: "spec" | "tests" | "schema"
  label: string
  icon: string
}> = [
  {
    id: "spec",
    label: "Tài liệu đặc tả (TRD Spec)",
    icon: "i-heroicons-document-text",
  },
  {
    id: "tests",
    label: "Ma trận kiểm thử (Test Matrix)",
    icon: "i-heroicons-check-badge",
  },
  {
    id: "schema",
    label: "Mô hình Schema SQLModel",
    icon: "i-heroicons-circle-stack",
  },
]

const testCases = [
  {
    id: "TEST-DB-01",
    group: "Schema & Migration",
    scenario:
      "Chạy Migration trên database đã có sẵn bảng cũ (stock_symbol, stock_ohlcv_daily)",
    expectation:
      "Các bảng cũ không bị ảnh hưởng; 8 bảng mới tạo đầy đủ FK và UniqueConstraint",
    status: "PASS" as const,
  },
  {
    id: "TEST-DB-02",
    group: "Schema & Migration",
    scenario:
      "Khả năng rollback migration (alembic downgrade -1 rồi upgrade head)",
    expectation:
      "Hạ cấp và nâng cấp trơn tru, dọn dẹp sạch sẽ bảng mới không để lại FK hoặc index treo",
    status: "PASS" as const,
  },
  {
    id: "TEST-DB-03",
    group: "Schema & Migration",
    scenario: "Kiểm tra timezone naive injection vào model AwareSQLModel",
    expectation:
      "Chặn hoặc tự động chuẩn hóa UTC datetime; ngăn chặn datetime.now() không timezone",
    status: "PASS" as const,
  },
  {
    id: "TEST-EXT-01",
    group: "API Resiliency",
    scenario: "Nguồn chính (TCBS) bị timeout hoặc trả về HTTP 500",
    expectation:
      "Tự động failover qua VCI, ghi log cảnh báo an toàn, không văng exception ra API client",
    status: "PASS" as const,
  },
  {
    id: "TEST-EXT-02",
    group: "API Resiliency",
    scenario: "Cả hai nguồn TCBS và VCI đồng thời không phản hồi",
    expectation:
      "Bắt ngoại lệ VnstockServiceError, trả về HTTP 503 chi tiết kèm thông báo thân thiện",
    status: "PASS" as const,
  },
  {
    id: "TEST-EXT-03",
    group: "API Resiliency",
    scenario: "vnstock adapter trả về DataFrame rỗng (None hoặc df.empty)",
    expectation:
      "Hàm xử lý trả về dữ liệu an toàn, ghi nhận DataSyncLog là partial/failed, không crash app",
    status: "PASS" as const,
  },
  {
    id: "TEST-EXT-04",
    group: "API Resiliency",
    scenario: "Stress test rate-limiting khi gọi liên tục 20 mã chứng khoán",
    expectation:
      "Rate-limiter chèn trễ 0.2s - 0.5s giữa các batch requests, ngăn chặn IP blacklisting",
    status: "PASS" as const,
  },
  {
    id: "TEST-ISO-01",
    group: "Paper Trading",
    scenario: "Kiểm tra tính độc lập và bảo mật của các bảng simulation_*",
    expectation:
      "Hoàn toàn không có cột API key, broker PIN, OTP hay real password (tuân thủ RULE 1 & 2)",
    status: "PASS" as const,
  },
  {
    id: "TEST-ISO-02",
    group: "Paper Trading",
    scenario: "Tạo lệnh đặt mô phỏng với sức mua không đủ",
    expectation:
      "Lệnh bị REJECTED ngay lập tức, số dư khả dụng giữ nguyên không bị trừ",
    status: "PASS" as const,
  },
  {
    id: "TEST-JRN-01",
    group: "Forecast Journal",
    scenario: "Ghi nhận dự báo mới vào sổ nhật ký (record)",
    expectation:
      "Status mặc định là pending, bắt buộc có predicted_at, engine_weights, model_version",
    status: "PASS" as const,
  },
]

const schemas = [
  {
    name: "stock_symbol",
    table: "StockSymbol",
    desc: "Danh mục mã niêm yết HOSE, HNX, UPCOM kèm metadata ngành ICB",
    code: `class StockSymbol(SQLModel, table=True):
    __tablename__ = "stock_symbol"
    symbol: str = Field(primary_key=True, max_length=10)
    organ_name: str | None = None
    exchange: str | None = Field(default=None, max_length=10, index=True)
    industry: str | None = None
    asset_type: str = Field(default="STOCK", max_length=20)
    is_active: bool = Field(default=True, index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))`,
  },
  {
    name: "forecast_journal",
    table: "ForecastJournal",
    desc: "Sổ cái ghi nhận dự báo phái sinh & rổ cổ phiếu (auditable ledger)",
    code: `class ForecastJournal(SQLModel, table=True):
    __tablename__ = "forecast_journal"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    symbol: str = Field(index=True, max_length=20)
    horizon: str = Field(index=True, max_length=20) # ATC, T+1, WEEKLY, MONTHLY
    predicted_at: datetime = Field(index=True)
    predicted_value: float | None = None
    predicted_direction: str | None = None # LONG, SHORT, NEUTRAL
    engine_weights: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    status: str = Field(default="pending", index=True) # pending, resolved, scored`,
  },
  {
    name: "paper_order",
    table: "PaperOrder",
    desc: "Lệnh mô phỏng phái sinh VN30F1M & cổ phiếu T+2",
    code: `class PaperOrder(SQLModel, table=True):
    __tablename__ = "paper_order"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    portfolio_id: uuid.UUID = Field(foreign_key="paper_portfolio.id", index=True)
    symbol: str = Field(max_length=20, index=True)
    side: str = Field(max_length=10) # BUY, SELL, LONG, SHORT
    order_type: str = Field(max_length=10) # LO, ATO, ATC, MP
    price: float
    volume: int
    status: str = Field(default="PENDING", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))`,
  },
]

const currentSchema = computed(() => {
  return schemas.find((s) => s.name === selectedSchema.value)
})
</script>
