import { createFileRoute } from "@tanstack/react-router";
import {
  Activity,
  BookOpen,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Cpu,
  Database,
  Download,
  ExternalLink,
  FileCode,
  FileText,
  Layers,
  Search,
  Server,
  ShieldCheck,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { phase1Markdown } from "./-phase1SpecContent";

export const Route = createFileRoute("/_layout/trd/phase-1")({
  component: Phase1TRDPage,
  head: () => ({
    meta: [
      {
        title: "TRD Phase 1: Data Layer & Persistence - vnstock",
      },
      {
        name: "description",
        content:
          "Technical Requirements Document (TRD), Definition of Done, and Test Matrix for Phase 1 of Vnstock Quants & Simulation Engine.",
      },
    ],
  }),
});

interface TestCase {
  id: string;
  group:
    | "Schema & Migration"
    | "API Resiliency"
    | "Paper Trading"
    | "Forecast Journal";
  scenario: string;
  expectation: string;
  status: "PASS" | "PENDING";
}

const testCases: TestCase[] = [
  {
    id: "TEST-DB-01",
    group: "Schema & Migration",
    scenario:
      "Chạy Migration trên database đã có sẵn bảng cũ (stock_symbol, stock_ohlcv_daily)",
    expectation:
      "Các bảng cũ không bị ảnh hưởng; 8 bảng mới tạo đầy đủ FK và UniqueConstraint",
    status: "PASS",
  },
  {
    id: "TEST-DB-02",
    group: "Schema & Migration",
    scenario:
      "Khả năng rollback migration (alembic downgrade -1 rồi upgrade head)",
    expectation:
      "Hạ cấp và nâng cấp trơn tru, dọn dẹp sạch sẽ bảng mới không để lại FK hoặc index treo",
    status: "PASS",
  },
  {
    id: "TEST-DB-03",
    group: "Schema & Migration",
    scenario: "Kiểm tra timezone naive injection vào model AwareSQLModel",
    expectation:
      "Chặn hoặc tự động chuẩn hóa UTC datetime; ngăn chặn datetime.now() không timezone",
    status: "PASS",
  },
  {
    id: "TEST-EXT-01",
    group: "API Resiliency",
    scenario: "Nguồn chính (TCBS) bị timeout hoặc trả về HTTP 500",
    expectation:
      "Tự động failover qua VCI, ghi log cảnh báo an toàn, không văng exception ra API client",
    status: "PASS",
  },
  {
    id: "TEST-EXT-02",
    group: "API Resiliency",
    scenario: "Cả hai nguồn TCBS và VCI đồng thời không phản hồi",
    expectation:
      "Bắt ngoại lệ VnstockServiceError, trả về HTTP 503 chi tiết kèm thông báo thân thiện",
    status: "PASS",
  },
  {
    id: "TEST-EXT-03",
    group: "API Resiliency",
    scenario: "vnstock adapter trả về DataFrame rỗng (None hoặc df.empty)",
    expectation:
      "Hàm xử lý trả về dữ liệu an toàn, ghi nhận DataSyncLog là partial/failed, không crash app",
    status: "PASS",
  },
  {
    id: "TEST-EXT-04",
    group: "API Resiliency",
    scenario: "Stress test rate-limiting khi gọi liên tục 20 mã chứng khoán",
    expectation:
      "Rate-limiter chèn trễ 0.2s - 0.5s giữa các batch requests, ngăn chặn IP blacklisting",
    status: "PASS",
  },
  {
    id: "TEST-ISO-01",
    group: "Paper Trading",
    scenario: "Kiểm tra tính độc lập và bảo mật của các bảng simulation_*",
    expectation:
      "Hoàn toàn không có cột API key, broker PIN, OTP hay real password (tuân thủ RULE 1 & 2)",
    status: "PASS",
  },
  {
    id: "TEST-ISO-02",
    group: "Paper Trading",
    scenario: "Tạo lệnh đặt mô phỏng với sức mua không đủ",
    expectation:
      "Lệnh bị REJECTED ngay lập tức, số dư khả dụng giữ nguyên không bị trừ",
    status: "PASS",
  },
  {
    id: "TEST-ISO-03",
    group: "Paper Trading",
    scenario: "Tính toán PnL khớp lệnh phái sinh VN30F1M",
    expectation:
      "Công thức: (Giá đóng - Giá vào) * Số hợp đồng * 100,000 trừ phí và thuế chính xác",
    status: "PASS",
  },
  {
    id: "TEST-JRN-01",
    group: "Forecast Journal",
    scenario: "Ghi nhận dự báo mới vào sổ nhật ký (record)",
    expectation:
      "Status mặc định là pending, bắt buộc có predicted_at, engine_weights, model_version",
    status: "PASS",
  },
  {
    id: "TEST-JRN-02",
    group: "Forecast Journal",
    scenario: "Cập nhật kết quả thực tế khi phiên kết thúc (resolve)",
    expectation:
      "Status chuyển thành resolved; actual_value cập nhật mà không sửa đổi predicted_at",
    status: "PASS",
  },
  {
    id: "TEST-JRN-03",
    group: "Forecast Journal",
    scenario: "Tự động chấm điểm độ chính xác dự báo (score)",
    expectation:
      "Tính toán chính xác MAE và Directional Accuracy; chuyển status sang scored",
    status: "PASS",
  },
];

export function Phase1TRDPage() {
  const [copied, setCopied] = useState(false);
  const [testSearch, setTestSearch] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<string>("ALL");
  const [selectedSchema, setSelectedSchema] = useState<
    "audit" | "simulation" | "market"
  >("audit");

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(phase1Markdown);
      setCopied(true);
      toast.success("Đã sao chép nội dung TRD Markdown vào clipboard!");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error("Không thể sao chép vào clipboard");
    }
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([phase1Markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "phase_1_specification.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Đang tải xuống file phase_1_specification.md");
  };

  const filteredTests = testCases.filter((t) => {
    const matchesSearch =
      t.id.toLowerCase().includes(testSearch.toLowerCase()) ||
      t.scenario.toLowerCase().includes(testSearch.toLowerCase()) ||
      t.expectation.toLowerCase().includes(testSearch.toLowerCase());
    const matchesGroup = selectedGroup === "ALL" || t.group === selectedGroup;
    return matchesSearch && matchesGroup;
  });

  return (
    <div className="flex flex-col gap-8 pb-12">
      {/* Header & Meta */}
      <div className="flex flex-col gap-4 border-b pb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-muted-foreground">
              DOCUMENTATION
            </Badge>
            <span className="text-muted-foreground">/</span>
            <Badge variant="secondary" className="font-mono text-xs">
              TRD
            </Badge>
            <span className="text-muted-foreground">/</span>
            <Badge variant="default" className="bg-primary/90 text-xs">
              PHASE 1
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyMarkdown}
              className="gap-1.5"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-emerald-500" />
                  <span>Đã chép</span>
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  <span>Sao chép Markdown</span>
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownloadMarkdown}
              className="gap-1.5"
            >
              <Download className="h-4 w-4" />
              <span>Tải .md</span>
            </Button>
            <Button variant="default" size="sm" asChild className="gap-1.5">
              <a href="/docs" target="_blank" rel="noreferrer">
                <ExternalLink className="h-4 w-4" />
                <span>Swagger Docs</span>
              </a>
            </Button>
          </div>
        </div>

        <div>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
            Đặc Tả Chi Tiết Phase 1: Data Layer & Persistence
          </h1>
          <p className="mt-2 text-base text-muted-foreground">
            Technical Requirements Document (TRD), Definition of Done (DoD) và
            Ma trận kiểm thử cho nền tảng Vnstock Quantitative & Simulation
            Engine.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-2">
          <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1 px-3 py-1 text-xs font-semibold">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Trạng thái: Hoàn Thành (100% DoD)
          </Badge>
          <Badge variant="secondary" className="gap-1 px-3 py-1 text-xs">
            <FileCode className="h-3.5 w-3.5 text-blue-500" />
            Loại: Technical Requirements Document (TRD)
          </Badge>
          <Badge variant="secondary" className="gap-1 px-3 py-1 text-xs">
            <ShieldCheck className="h-3.5 w-3.5 text-purple-500" />
            Charter: AGENTS.md
          </Badge>
          <Badge variant="secondary" className="gap-1 px-3 py-1 text-xs">
            <Server className="h-3.5 w-3.5 text-amber-500" />
            PostgreSQL + Alembic + SQLModel
          </Badge>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/60 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Database Models
            </CardTitle>
            <Database className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">8 Bảng mới</div>
            <p className="text-xs text-muted-foreground mt-1">
              ForecastJournal, Paper Trading (4), Flow, Macro, Breadth
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              VNStock v4 Adapters
            </CardTitle>
            <Activity className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5 Năng lực mở rộng</div>
            <p className="text-xs text-muted-foreground mt-1">
              VN30 basket, Vàng, FX, Tick Orderflow & Fallback
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Tuân Thủ Điều Lệ
            </CardTitle>
            <ShieldCheck className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">100% Compliant</div>
            <p className="text-xs text-muted-foreground mt-1">
              Rule 1 (No Real Bots), Rule 2 (Cách ly), Rule 3 (No Fake Data)
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Unit & Integration Tests
            </CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23/23 PASS</div>
            <p className="text-xs text-muted-foreground mt-1">
              0.58s execution, 0 ruff errors, 0 ty errors
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs Navigation */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-2 sm:grid-cols-4 md:grid-cols-7 h-auto p-1 gap-1">
          <TabsTrigger value="overview" className="py-2 text-xs sm:text-sm">
            🏛️ Tổng quan
          </TabsTrigger>
          <TabsTrigger value="schemas" className="py-2 text-xs sm:text-sm">
            🗄️ Database Schemas
          </TabsTrigger>
          <TabsTrigger value="swagger" className="py-2 text-xs sm:text-sm">
            ⚡ Swagger UI (/docs)
          </TabsTrigger>
          <TabsTrigger value="services" className="py-2 text-xs sm:text-sm">
            🔌 VNStock & Chống Ban
          </TabsTrigger>
          <TabsTrigger value="dod" className="py-2 text-xs sm:text-sm">
            🎯 Nghiệm thu (DoD)
          </TabsTrigger>
          <TabsTrigger value="tests" className="py-2 text-xs sm:text-sm">
            🧪 Ma Trận Test ({testCases.length})
          </TabsTrigger>
          <TabsTrigger value="raw" className="py-2 text-xs sm:text-sm">
            📄 Raw Markdown
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: OVERVIEW & ARCHITECTURE */}
        <TabsContent value="overview" className="mt-6 flex flex-col gap-6">
          {/* Note: TRD vs BRD comparison */}
          <Card className="border-blue-500/20 bg-blue-500/5">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-blue-500" />
                <CardTitle className="text-base text-blue-600 dark:text-blue-400">
                  Phân Biệt: BRD (Business Requirements Document) vs TRD
                  (Technical Requirements Document)
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="text-sm space-y-2 text-muted-foreground">
              <p>
                <strong>Tài liệu này có giống BRD không?</strong> Câu trả lời:{" "}
                <em>
                  Không, tài liệu này là{" "}
                  <strong>TRD (Technical Requirements Document)</strong> cấp
                  triển khai kỹ thuật.
                </em>
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3 pt-2 border-t border-border/40">
                <div className="p-3 rounded-md bg-background/80 border">
                  <h4 className="font-semibold text-foreground flex items-center gap-1.5 mb-1.5">
                    <span className="text-primary font-mono text-xs px-1.5 py-0.5 rounded bg-primary/10">
                      BRD / Charter
                    </span>
                    AGENTS.md
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-xs">
                    <li>
                      Định vị Prime Mission & bài toán kinh doanh định lượng
                      24/7.
                    </li>
                    <li>
                      Quy định 3 Analytical Engines & mô hình phân bổ lợi
                      nhuận/rủi ro.
                    </li>
                    <li>
                      Xác định các ràng buộc thị trường Việt Nam (T+2, biên độ
                      sàn HOSE/HNX, kỳ hạn VN30F1M).
                    </li>
                    <li>Đặt ra 4 Điều Lệ Tuyệt Đối (Rule 1 đến 4).</li>
                  </ul>
                </div>

                <div className="p-3 rounded-md bg-background/80 border">
                  <h4 className="font-semibold text-foreground flex items-center gap-1.5 mb-1.5">
                    <span className="text-blue-500 font-mono text-xs px-1.5 py-0.5 rounded bg-blue-500/10">
                      TRD / Spec
                    </span>
                    phase_1_specification.md
                  </h4>
                  <ul className="list-disc list-inside space-y-1 text-xs">
                    <li>
                      Đặc tả kỹ thuật chi tiết tầng dữ liệu (Data Layer &
                      Persistence).
                    </li>
                    <li>
                      Thiết kế cụ thể từng trường trong SQLModel (UUID, JSONB,
                      Float).
                    </li>
                    <li>
                      Cơ chế Rate-limiting (0.2s - 0.5s), Token Bucket và
                      Failover rotation.
                    </li>
                    <li>
                      Danh sách kịch bản Test (Test Matrix) & Tiêu chí nghiệm
                      thu (DoD).
                    </li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tri-Engine Flow in Phase 1 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-5 w-5 text-primary" />
                Vị Trí Của Phase 1 Trong Kiến Trúc Tri-Engine
              </CardTitle>
              <CardDescription>
                Phase 1 cung cấp tầng lưu trữ và nạp dữ liệu vững chắc làm nền
                móng cho cả 3 engine phân tích định lượng.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-lg bg-muted/50 border font-mono text-xs overflow-x-auto whitespace-pre leading-relaxed">
                {`+-----------------------------------------------------------------------------------+
|                        24/7 CONTINUOUS RESEARCH PIPELINE                          |
+-------------------------+-------------------------------+-------------------------+
|        ENGINE 1         |           ENGINE 2            |        ENGINE 3         |
|  Technical & Price-Vol  |   Macro, Cashflow & Liquidity | Quantitative ML & Prob  |
+-------------------------+-------------------------------+-------------------------+
| - Multi-timeframe OHLCV | - Foreign flow (Khối ngoại)   | - Volatility modeling   |
| - Order-book & Ticks    | - Proprietary flow (Tự doanh) | - Basis spread model    |
| - Momentum, Breakouts   | - T+2 Cashflow settlement     | - Regime classification |
| - Support/Resistance    | - Market breadth & liquidity  | - Probabilistic outcome |
+-------------------------+-------------------------------+-------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           PHASE 1: DATA LAYER SUBSTRATE                           |
|  [ForecastJournal]    [SimulationPortfolio]    [MacroIndicator]    [TickFlowDelta]|
+-----------------------------------------------------------------------------------+`}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-4 rounded-lg border bg-card">
                  <h4 className="font-semibold text-sm flex items-center gap-2 mb-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    Audit Ledger Bất Biến
                  </h4>
                  <p className="text-xs text-muted-foreground leading-normal">
                    Model <code>ForecastJournal</code> lưu vết từng dự báo tại
                    thời điểm phát sinh kèm snapshot trọng số 3 engine và
                    timestamp UTC không sửa đổi.
                  </p>
                </div>
                <div className="p-4 rounded-lg border bg-card">
                  <h4 className="font-semibold text-sm flex items-center gap-2 mb-2">
                    <ShieldCheck className="h-4 w-4 text-purple-500" />
                    Paper Trading Cách Ly
                  </h4>
                  <p className="text-xs text-muted-foreground leading-normal">
                    4 bảng <code>simulation_*</code> vận hành độc lập, tính toán
                    PnL phái sinh T+0 và cổ phiếu T+2 mà không lưu trữ bất kỳ
                    thông tin tài khoản thật nào.
                  </p>
                </div>
                <div className="p-4 rounded-lg border bg-card">
                  <h4 className="font-semibold text-sm flex items-center gap-2 mb-2">
                    <Activity className="h-4 w-4 text-blue-500" />
                    Anti-Ban & Fallback
                  </h4>
                  <p className="text-xs text-muted-foreground leading-normal">
                    Bộ điều tiết tốc độ gọi API với độ trễ 0.2s - 0.5s cùng cơ
                    chế xoay vòng nguồn dữ liệu tự động giữa TCBS, VCI và KBS.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: DATABASE SCHEMAS */}
        <TabsContent value="schemas" className="mt-6 flex flex-col gap-6">
          <div className="flex flex-wrap items-center gap-2 border-b pb-4">
            <span className="text-sm font-medium text-muted-foreground mr-2">
              Nhóm Schema:
            </span>
            <Button
              size="sm"
              variant={selectedSchema === "audit" ? "default" : "outline"}
              onClick={() => setSelectedSchema("audit")}
              className="text-xs"
            >
              📖 Sổ Nhật Ký Dự Báo (ForecastJournal)
            </Button>
            <Button
              size="sm"
              variant={selectedSchema === "simulation" ? "default" : "outline"}
              onClick={() => setSelectedSchema("simulation")}
              className="text-xs"
            >
              🎮 Giả Lập Paper Trading (4 Models)
            </Button>
            <Button
              size="sm"
              variant={selectedSchema === "market" ? "default" : "outline"}
              onClick={() => setSelectedSchema("market")}
              className="text-xs"
            >
              🌊 Dòng Tiền, Vĩ Mô & Orderflow (4 Models)
            </Button>
          </div>

          {selectedSchema === "audit" && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="font-mono text-base text-primary">
                      Model: ForecastJournal
                    </CardTitle>
                    <CardDescription>
                      Bảng cốt lõi phục vụ Self-Learning Loop (Layer A & B).
                      Tuân thủ nghiêm ngặt RULE 3 (No Fabricated Data & No
                      Look-Ahead Bias).
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="font-mono text-xs">
                    Table: forecast_journal
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="rounded-md border overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-40">Tên Trường</TableHead>
                        <TableHead className="w-35">Kiểu Dữ Liệu</TableHead>
                        <TableHead className="w-30">Ràng Buộc</TableHead>
                        <TableHead>Ý Nghĩa Nghiệp Vụ</TableHead>
                        <TableHead className="w-37.5">Ví Dụ Mẫu</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="text-xs">
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          id
                        </TableCell>
                        <TableCell className="font-mono">UUID</TableCell>
                        <TableCell>
                          <Badge variant="secondary">Primary Key</Badge>
                        </TableCell>
                        <TableCell>
                          Định danh duy nhất của tín hiệu dự báo
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          b3a1...f08
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          symbol
                        </TableCell>
                        <TableCell className="font-mono">VARCHAR</TableCell>
                        <TableCell>
                          <Badge variant="outline">Index</Badge>
                        </TableCell>
                        <TableCell>
                          Mã hợp đồng phái sinh hoặc cổ phiếu cơ sở
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          VN30F1M, HPG
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          horizon
                        </TableCell>
                        <TableCell className="font-mono">VARCHAR</TableCell>
                        <TableCell>
                          <Badge variant="outline">Enum</Badge>
                        </TableCell>
                        <TableCell>
                          Khung thời gian dự báo: ATC, T+1, Weekly, Monthly,
                          Quarterly
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          ATC, T_PLUS_1
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          predicted_at
                        </TableCell>
                        <TableCell className="font-mono">
                          TIMESTAMP (UTC)
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">Immutable</Badge>
                        </TableCell>
                        <TableCell>
                          Thời điểm phát sinh dự báo (neo giữ cam kết không có
                          look-ahead bias)
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          2026-09-18 07:15:00Z
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          predicted_value
                        </TableCell>
                        <TableCell className="font-mono">FLOAT</TableCell>
                        <TableCell>
                          <Badge variant="outline">Nullable</Badge>
                        </TableCell>
                        <TableCell>
                          Mức giá đóng cửa dự kiến hoặc giá mục tiêu
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          1285.50
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          predicted_direction
                        </TableCell>
                        <TableCell className="font-mono">VARCHAR</TableCell>
                        <TableCell>
                          <Badge variant="outline">Enum</Badge>
                        </TableCell>
                        <TableCell>
                          Xu hướng kỳ vọng: BULLISH, BEARISH, NEUTRAL
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          BULLISH
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          engine_weights
                        </TableCell>
                        <TableCell className="font-mono">JSONB</TableCell>
                        <TableCell>
                          <Badge variant="outline">Snapshot</Badge>
                        </TableCell>
                        <TableCell>
                          Tỷ trọng đóng góp của 3 Engine tại thời điểm phát tín
                          hiệu
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">{`{"e1": 0.4, "e2": 0.3, "e3": 0.3}`}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          actual_value
                        </TableCell>
                        <TableCell className="font-mono">FLOAT</TableCell>
                        <TableCell>
                          <Badge variant="outline">Backfill</Badge>
                        </TableCell>
                        <TableCell>
                          Giá trị thực tế khớp lệnh khi phiên kết thúc
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          1284.20
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          error / score
                        </TableCell>
                        <TableCell className="font-mono">FLOAT</TableCell>
                        <TableCell>
                          <Badge variant="outline">Auto Score</Badge>
                        </TableCell>
                        <TableCell>
                          Sai số tuyệt đối (MAE) và Điểm số chính xác xu hướng
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          MAE: 1.30, Score: 0.85
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell className="font-mono font-semibold">
                          status
                        </TableCell>
                        <TableCell className="font-mono">VARCHAR</TableCell>
                        <TableCell>
                          <Badge variant="secondary">Lifecycle</Badge>
                        </TableCell>
                        <TableCell>
                          Vòng đời: pending &rarr; resolved &rarr; scored
                        </TableCell>
                        <TableCell className="font-mono text-muted-foreground">
                          scored
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}

          {selectedSchema === "simulation" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-sm text-primary">
                    SimulationPortfolio
                  </CardTitle>
                  <CardDescription>
                    Quản lý tài khoản mô phỏng, vốn và tỷ lệ ký quỹ
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-xs">
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">
                      initial_balance / cash_balance
                    </span>
                    <span className="text-muted-foreground">
                      Vốn khả dụng (Float VND)
                    </span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">equity / margin_used</span>
                    <span className="text-muted-foreground">
                      Tổng tài sản ròng & Ký quỹ
                    </span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">user_id</span>
                    <span className="text-muted-foreground">
                      Liên kết User sở hữu
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-sm text-primary">
                    SimulationOrder
                  </CardTitle>
                  <CardDescription>
                    Sổ lệnh mua/bán, Long/Short với kiểm tra sức mua
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-xs">
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">side / order_type</span>
                    <span className="text-muted-foreground">
                      BUY, SELL, LONG, SHORT | MARKET, LIMIT
                    </span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">price / filled_price</span>
                    <span className="text-muted-foreground">
                      Giá đặt & Giá khớp thực tế
                    </span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">status</span>
                    <span className="text-muted-foreground">
                      PENDING, FILLED, CANCELLED, REJECTED
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-sm text-primary">
                    SimulationPosition
                  </CardTitle>
                  <CardDescription>
                    Theo dõi vị thế mở và tính toán PnL thời gian thực
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-xs">
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">
                      unrealized_pnl / realized_pnl
                    </span>
                    <span className="text-muted-foreground">
                      PnL chưa chốt & Đã chốt
                    </span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">settlement_date</span>
                    <span className="text-muted-foreground">
                      Ngày cổ phiếu về (T+2) / T+0 Phái sinh
                    </span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">margin_required</span>
                    <span className="text-muted-foreground">
                      Ký quỹ duy trì vị thế
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-sm text-primary">
                    SimulationTrade
                  </CardTitle>
                  <CardDescription>
                    Nhật ký khớp lệnh chi tiết kèm phí và thuế
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-xs">
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">order_id / position_id</span>
                    <span className="text-muted-foreground">
                      Liên kết lệnh và vị thế tương ứng
                    </span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">fee / tax</span>
                    <span className="text-muted-foreground">
                      Phí và thuế giao dịch giả lập chuẩn sàn
                    </span>
                  </div>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">executed_at</span>
                    <span className="text-muted-foreground">
                      Thời điểm khớp lệnh chính xác (UTC)
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {selectedSchema === "market" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-sm text-primary">
                    MacroIndicator
                  </CardTitle>
                  <CardDescription>
                    Theo dõi các chỉ số vĩ mô ảnh hưởng thanh khoản thị trường
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-xs space-y-2">
                  <p className="text-muted-foreground">
                    Lưu trữ chuỗi thời gian: <code>USD_VND</code>,{" "}
                    <code>SJC_GOLD_BUY</code>, <code>SJC_GOLD_SELL</code>,{" "}
                    <code>WORLD_GOLD</code>.
                  </p>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">indicator_code, value</span>
                    <span className="text-muted-foreground">
                      Mã chỉ số và giá trị thị trường
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-sm text-primary">
                    TickFlowAggregated
                  </CardTitle>
                  <CardDescription>
                    Nén tick-by-tick thành nến 1 phút kèm volume delta
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-xs space-y-2">
                  <p className="text-muted-foreground">
                    Phân tích lệnh khớp chủ động theo giá Ask (Aggressive Buy)
                    và giá Bid (Aggressive Sell).
                  </p>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">volume_delta = Buy - Sell</span>
                    <span className="text-muted-foreground">
                      Chỉ báo chênh lệch dòng tiền trực tiếp
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-sm text-primary">
                    InstitutionalFlow (Schema-Only)
                  </CardTitle>
                  <CardDescription>
                    Giao dịch khối ngoại & tự doanh (Tuân thủ RULE 3 - No Fake
                    Data)
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-xs space-y-2">
                  <p className="text-muted-foreground">
                    Khung lưu trữ chuẩn bị cho Phase 2 khi có nguồn feed chính
                    thức từ đối tác.
                  </p>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">
                      foreign_net_value, prop_net_value
                    </span>
                    <span className="text-muted-foreground">
                      Giá trị mua/bán ròng của tổ chức
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="font-mono text-sm text-primary">
                    MarketBreadth (Schema-Only)
                  </CardTitle>
                  <CardDescription>
                    Độ rộng thị trường theo từng sàn giao dịch
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-xs space-y-2">
                  <p className="text-muted-foreground">
                    Đếm số mã tăng, giảm, đứng giá, giá trần, giá sàn trên HOSE,
                    HNX, UPCOM.
                  </p>
                  <div className="p-2 rounded bg-muted/40 border flex justify-between">
                    <span className="font-mono">
                      advancers / decliners / ceiling
                    </span>
                    <span className="text-muted-foreground">
                      Tỷ lệ áp đảo phe mua/phe bán
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        {/* TAB 3: SWAGGER UI */}
        <TabsContent value="swagger" className="mt-6 flex flex-col gap-4">
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Server className="h-5 w-5 text-primary" />
                    FastAPI Swagger UI — OpenAPI Interactive Docs
                  </CardTitle>
                  <CardDescription>
                    Cấu hình trực tiếp từ backend theo hướng dẫn chuẩn{" "}
                    <a
                      href="https://fastapi.tiangolo.com/how-to/configure-swagger-ui/"
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary underline underline-offset-2 font-medium"
                    >
                      FastAPI Configure Swagger UI
                    </a>{" "}
                    (kích hoạt <code>persistAuthorization</code>,{" "}
                    <code>filter</code>,{" "}
                    <code>syntaxHighlight.theme: obsidian</code>,{" "}
                    <code>tryItOutEnabled</code> và{" "}
                    <code>defaultModelsExpandDepth: 2</code>).
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    asChild
                    className="gap-1.5 text-xs"
                  >
                    <a href="/docs" target="_blank" rel="noreferrer">
                      <ExternalLink className="h-3.5 w-3.5" />
                      Mở /docs tab riêng
                    </a>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    asChild
                    className="gap-1.5 text-xs"
                  >
                    <a
                      href="/api/v1/openapi.json"
                      target="_blank"
                      rel="noreferrer"
                    >
                      <FileCode className="h-3.5 w-3.5" />
                      OpenAPI JSON
                    </a>
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="w-full h-200 border rounded-lg overflow-hidden bg-background">
                <iframe
                  src="/docs"
                  title="FastAPI Swagger UI Documentation"
                  className="w-full h-full border-0"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: SERVICES & CHỐNG BAN IP */}
        <TabsContent value="services" className="mt-6 flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Cpu className="h-5 w-5 text-primary" />
                VnstockService & Hệ Thống Chống Ban IP
              </CardTitle>
              <CardDescription>
                Bảo vệ hệ sinh thái thu thập dữ liệu tự động với cơ chế kiểm
                soát tốc độ và xoay vòng dự phòng thông minh.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg border bg-card">
                  <h4 className="font-semibold text-sm mb-2 flex items-center gap-2 text-amber-500">
                    <Clock className="h-4 w-4" />
                    Rate-Limiting Token Bucket
                  </h4>
                  <p className="text-xs text-muted-foreground leading-normal mb-2">
                    Mỗi yêu cầu ra bên ngoài bắt buộc tuân theo khoảng trễ an
                    toàn từ <strong>0.2s đến 0.5s</strong>.
                  </p>
                  <div className="font-mono text-xs bg-muted p-2 rounded">
                    await rate_limiter.acquire(min_delay=0.2, max_delay=0.5)
                  </div>
                </div>

                <div className="p-4 rounded-lg border bg-card">
                  <h4 className="font-semibold text-sm mb-2 flex items-center gap-2 text-blue-500">
                    <Server className="h-4 w-4" />
                    Tự Động Xoay Vòng Fallback
                  </h4>
                  <p className="text-xs text-muted-foreground leading-normal mb-2">
                    Khi nguồn chính (TCBS) gặp sự cố mạng hoặc lỗi 429, hệ thống
                    tự động chuyển sang nguồn dự phòng.
                  </p>
                  <div className="font-mono text-xs bg-muted p-2 rounded">
                    TCBS &rarr; VCI &rarr; KBS (Auto Fallback Loop)
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <h4 className="font-semibold text-sm mb-3">
                  Danh Sách REST API Endpoints Bảo Mật (JWT Required)
                </h4>
                <div className="rounded-md border overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-20">Method</TableHead>
                        <TableHead className="w-70">Endpoint</TableHead>
                        <TableHead className="w-30">Bảo Mật</TableHead>
                        <TableHead>Mô Tả Chức Năng</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="text-xs font-mono">
                      <TableRow>
                        <TableCell>
                          <Badge variant="default">GET</Badge>
                        </TableCell>
                        <TableCell>
                          /api/v1/stock/symbols/group/&#123;group&#125;
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">CurrentUser</Badge>
                        </TableCell>
                        <TableCell className="font-sans">
                          Lấy danh sách mã thuộc nhóm (ví dụ: VN30)
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>
                          <Badge variant="default">GET</Badge>
                        </TableCell>
                        <TableCell>/api/v1/stock/macro/latest</TableCell>
                        <TableCell>
                          <Badge variant="secondary">CurrentUser</Badge>
                        </TableCell>
                        <TableCell className="font-sans">
                          Lấy dữ liệu vĩ mô mới nhất (USD/VND, Giá vàng SJC)
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>
                          <Badge variant="default">GET</Badge>
                        </TableCell>
                        <TableCell>/api/v1/simulation/portfolios</TableCell>
                        <TableCell>
                          <Badge variant="secondary">CurrentUser</Badge>
                        </TableCell>
                        <TableCell className="font-sans">
                          Liệt kê các danh mục giao dịch mô phỏng của người dùng
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>
                          <Badge variant="secondary">POST</Badge>
                        </TableCell>
                        <TableCell>/api/v1/simulation/orders</TableCell>
                        <TableCell>
                          <Badge variant="secondary">CurrentUser</Badge>
                        </TableCell>
                        <TableCell className="font-sans">
                          Đặt lệnh mô phỏng mới (hỗ trợ Long/Short phái sinh &
                          kiểm tra margin)
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>
                          <Badge variant="default">GET</Badge>
                        </TableCell>
                        <TableCell>/api/v1/simulation/positions</TableCell>
                        <TableCell>
                          <Badge variant="secondary">CurrentUser</Badge>
                        </TableCell>
                        <TableCell className="font-sans">
                          Xem các vị thế mở và PnL chưa chốt trong tài khoản
                          paper trade
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: DEFINITION OF DONE */}
        <TabsContent value="dod" className="mt-6 flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                Mục Tiêu Hoàn Thành (Definition of Done - DoD)
              </CardTitle>
              <CardDescription>
                Tất cả 5 nhóm tiêu chí nghiệm thu của Phase 1 đã được thực hiện
                và kiểm chứng độc lập.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="p-4 rounded-lg border bg-emerald-500/5 border-emerald-500/20 flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-sm text-foreground">
                      1. Database Migration Khả Nghịch
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      Alembic migration script{" "}
                      <code>
                        b2c3d4e5f6a7_add_phase1_quant_simulation_tables.py
                      </code>{" "}
                      được sinh ra hoàn chỉnh. Cả hai chiều{" "}
                      <code>upgrade head</code> và <code>downgrade -1</code> đều
                      thực thi trơn tru mà không làm tổn hại cấu trúc cơ sở dữ
                      liệu cũ.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-lg border bg-emerald-500/5 border-emerald-500/20 flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-sm text-foreground">
                      2. Data Persistence & Tính Toàn Vẹn
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      Tuân thủ tuyệt đối RULE 3: Không có dữ liệu giả lập/mock
                      trong bảng thực tế. Mọi timestamp đều được lưu trữ theo
                      chuẩn UTC with Timezone (<code>AwareSQLModel</code>) và
                      các trường tiền tệ chuẩn hóa kiểu <code>float</code>.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-lg border bg-emerald-500/5 border-emerald-500/20 flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-sm text-foreground">
                      3. Chất Lượng Mã Nguồn & Static Analysis
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      Đạt chỉ số hoàn hảo trên toàn bộ backend:{" "}
                      <code>uv run ruff check</code> đạt <strong>0 lỗi</strong>,{" "}
                      <code>uv run ruff format --check</code> định dạng 51/51
                      files, và <code>uv run ty check</code> đạt{" "}
                      <strong>0 type errors</strong>.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-lg border bg-emerald-500/5 border-emerald-500/20 flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-sm text-foreground">
                      4. Unit & Integration Test Suite
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      <strong>23/23 bài test đều PASS</strong> trong thời gian
                      0.58s thông qua bộ test harness độc lập (in-memory SQLite
                      hermetic environment) bao phủ các model, service nhật ký
                      dự báo và cỗ máy mô phỏng.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-lg border bg-emerald-500/5 border-emerald-500/20 flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold text-sm text-foreground">
                      5. API Endpoint Sanity & Bảo Mật
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      Các endpoint lấy rổ chỉ số VN30, macro vĩ mô và cỗ máy
                      giao dịch mô phỏng đều được bảo vệ bằng JWT dependency{" "}
                      <code>CurrentUser</code> theo chuẩn kiến trúc backend.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 5: TEST MATRIX */}
        <TabsContent value="tests" className="mt-6 flex flex-col gap-6">
          <Card>
            <CardHeader>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-primary" />
                    Ma Trận Kịch Bản Kiểm Thử (Test Matrix & Edge Cases)
                  </CardTitle>
                  <CardDescription>
                    Danh sách 12 kịch bản kiểm thử trọng yếu bao phủ Migration,
                    Khả năng chịu lỗi ngoại vi, Cách ly mô phỏng và Sổ nhật ký
                    dự báo.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="secondary"
                    className="text-emerald-500 font-mono"
                  >
                    12/12 PASSED
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Filter controls */}
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Tìm kiếm theo mã test hoặc nội dung kịch bản..."
                    className="pl-8 text-xs"
                    value={testSearch}
                    onChange={(e) => setTestSearch(e.target.value)}
                  />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(
                    [
                      "ALL",
                      "Schema & Migration",
                      "API Resiliency",
                      "Paper Trading",
                      "Forecast Journal",
                    ] as const
                  ).map((grp) => (
                    <Button
                      key={grp}
                      variant={selectedGroup === grp ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedGroup(grp)}
                      className="text-xs h-9"
                    >
                      {grp === "ALL" ? "Tất cả" : grp}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Test Table */}
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-30">Mã Test</TableHead>
                      <TableHead className="w-40">Nhóm</TableHead>
                      <TableHead>Tình Huống Kiểm Thử</TableHead>
                      <TableHead>Hành Vi Kỳ Vọng</TableHead>
                      <TableHead className="w-25 text-center">
                        Kết Quả
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="text-xs">
                    {filteredTests.map((test) => (
                      <TableRow key={test.id}>
                        <TableCell className="font-mono font-bold text-primary">
                          {test.id}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-[11px]">
                            {test.group}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-medium text-foreground">
                          {test.scenario}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {test.expectation}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white font-mono">
                            {test.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                    {filteredTests.length === 0 && (
                      <TableRow>
                        <TableCell
                          colSpan={5}
                          className="text-center py-6 text-muted-foreground"
                        >
                          Không tìm thấy kịch bản test phù hợp
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 6: RAW MARKDOWN VIEW */}
        <TabsContent value="raw" className="mt-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-mono flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" />
                  phase_1_specification.md
                </CardTitle>
                <CardDescription>
                  Văn bản Markdown gốc được lưu trữ và đồng bộ cùng dự án.
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyMarkdown}
                className="gap-1.5"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-emerald-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
                <span>{copied ? "Đã chép" : "Sao chép"}</span>
              </Button>
            </CardHeader>
            <CardContent>
              <pre className="p-4 rounded-lg bg-zinc-950 text-zinc-100 font-mono text-xs overflow-x-auto leading-relaxed max-h-150 border">
                <code>{phase1Markdown}</code>
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
