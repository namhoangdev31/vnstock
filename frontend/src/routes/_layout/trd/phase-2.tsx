import { createFileRoute, Link } from "@tanstack/react-router";
import {
  BookOpen,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Cpu,
  Download,
  ExternalLink,
  FileCode,
  Layers,
  Search,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  TrendingUp,
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
import { phase2Markdown } from "./-phase2SpecContent";

export const Route = createFileRoute("/_layout/trd/phase-2")({
  component: Phase2TRDPage,
  head: () => ({
    meta: [
      {
        title: "TRD Phase 2: Tri-Engine Analytics Core - vnstock",
      },
      {
        name: "description",
        content:
          "Technical Requirements Document (TRD), Tri-Engine Analytics Core (Technical, Flow, Quant ML) & Ensemble Decision System for Vnstock.",
      },
    ],
  }),
});

interface TestCase {
  id: string;
  category: "MAIN" | "SUB" | "EDGE";
  group:
    | "Engine 1 (Technical & Orderflow)"
    | "Engine 2 (Liquidity & T+2)"
    | "Engine 3 (Basis & Transitions)"
    | "Ensemble & Audit Ledger";
  scenario: string;
  expectation: string;
  status: "READY" | "SPECIFIED";
}

const testCases: TestCase[] = [
  // --- ENGINE 1: TECHNICAL & ORDERFLOW ---
  {
    id: "TEST-E1-01",
    category: "MAIN",
    group: "Engine 1 (Technical & Orderflow)",
    scenario: "Tính toán RSI 14 & MACD (12, 26, 9) trên chuỗi nến OHLCV chuẩn",
    expectation:
      "Giá trị trả về chính xác theo công thức chuẩn; không bị NaN ở các kỳ tính toán hợp lệ",
    status: "READY",
  },
  {
    id: "TEST-E1-02",
    category: "SUB",
    group: "Engine 1 (Technical & Orderflow)",
    scenario: "Tính toán VWAP đa khung thời gian kết hợp nến 1m, 5m, 15m trong phiên",
    expectation:
      "Đường VWAP tích lũy khối lượng liên tục từ đầu phiên 09:00, không bị lệch pha giữa các khung",
    status: "READY",
  },
  {
    id: "TEST-E1-03",
    category: "EDGE",
    group: "Engine 1 (Technical & Orderflow)",
    scenario: "Tính VWAP trên dữ liệu Intraday có nến thanh khoản = 0",
    expectation:
      "Không gây lỗi chia cho 0 (ZeroDivisionError); VWAP giữ nguyên giá trị nến gần nhất",
    status: "READY",
  },
  {
    id: "TEST-E1-04",
    category: "MAIN",
    group: "Engine 1 (Technical & Orderflow)",
    scenario: "Tính Orderflow Delta với dòng lệnh khớp mua/bán hỗn hợp từ Quote.intraday()",
    expectation:
      "Delta = V_buy - V_sell chuẩn xác từng tick; phản ánh đúng xung lực mua/bán chủ động",
    status: "READY",
  },
  {
    id: "TEST-E1-05",
    category: "EDGE",
    group: "Engine 1 (Technical & Orderflow)",
    scenario: "Tính Order Imbalance với dòng lệnh 100% mua chủ động (Vol_Sell = 0)",
    expectation:
      "Trả về Imbalance Ratio = +1.0 chuẩn xác, không bị lỗi tính toán biên",
    status: "READY",
  },
  {
    id: "TEST-E1-06",
    category: "MAIN",
    group: "Engine 1 (Technical & Orderflow)",
    scenario: "Nhận diện Fair Value Gap (Bullish & Bearish FVG) giữa cụm 3 nến",
    expectation:
      "Xác định đúng khoảng trống giá mất cân bằng; lưu trữ biên trên và biên dưới FVG",
    status: "READY",
  },
  {
    id: "TEST-E1-07",
    category: "SUB",
    group: "Engine 1 (Technical & Orderflow)",
    scenario: "Nhận diện Liquidity Sweep (Quét thanh khoản đỉnh/đáy)",
    expectation:
      "Phát hiện chính xác khi nến chọc thủng đỉnh/đáy cũ nhưng đóng cửa rút râu đảo chiều",
    status: "READY",
  },
  {
    id: "TEST-E1-08",
    category: "EDGE",
    group: "Engine 1 (Technical & Orderflow)",
    scenario: "Chuỗi nến Doji liên tiếp (High = Low = Close) trong vùng thị trường mất thanh khoản",
    expectation:
      "Chỉ báo biến động xử lý an toàn phép chia logarithm; độ biến động tiệm cận 0 mà không crash",
    status: "READY",
  },

  // --- ENGINE 2: LIQUIDITY & T+2 ---
  {
    id: "TEST-E2-01",
    category: "MAIN",
    group: "Engine 2 (Liquidity & T+2)",
    scenario: "Tổng hợp luồng vốn Khối ngoại và Tự doanh trên toàn bộ 30 mã rổ VN30",
    expectation:
      "Cộng gộp giá trị mua/bán ròng chính xác; tính ra điểm Institutional Momentum Score",
    status: "READY",
  },
  {
    id: "TEST-E2-02",
    category: "SUB",
    group: "Engine 2 (Liquidity & T+2)",
    scenario: "Đánh giá áp lực xả hàng T+2 khi phiên T-2 có thanh khoản bắt đáy đột biến x3",
    expectation:
      "Chỉ số t_plus_2_pressure_index tăng vọt cảnh báo nguy cơ rung lắc mạnh phiên chiều",
    status: "READY",
  },
  {
    id: "TEST-E2-03",
    category: "EDGE",
    group: "Engine 2 (Liquidity & T+2)",
    scenario: "Tính Institutional Flow Momentum khi thiếu dữ liệu Tự doanh do công bố trễ",
    expectation:
      "Tự động hạ trọng số Tự doanh về 0 và chuẩn hóa theo Khối ngoại; không throw Exception",
    status: "READY",
  },
  {
    id: "TEST-E2-04",
    category: "MAIN",
    group: "Engine 2 (Liquidity & T+2)",
    scenario: "Phân tích độ rộng thị trường (Advance/Decline Ratio) trên 400 mã sàn HOSE",
    expectation:
      "Tính tỷ lệ mã tăng / mã giảm chuẩn xác; nhận diện độ phân kỳ giữa chỉ số và độ rộng",
    status: "READY",
  },
  {
    id: "TEST-E2-05",
    category: "EDGE",
    group: "Engine 2 (Liquidity & T+2)",
    scenario: "Phân tích độ rộng thị trường khi toàn sàn giảm mạnh (100% decliners)",
    expectation:
      "Trả về Breadth Score tiệm cận -1.0; tín hiệu nghiêng hẳn về Bearish an toàn",
    status: "READY",
  },
  {
    id: "TEST-E2-06",
    category: "SUB",
    group: "Engine 2 (Liquidity & T+2)",
    scenario: "Tính lịch trình thanh toán T+2 cho lệnh mua vào ngày thứ Sáu",
    expectation:
      "Cổ phiếu khả dụng vào phiên chiều thứ Ba tuần sau (loại trừ T7, CN và ngày nghỉ lễ)",
    status: "READY",
  },
  {
    id: "TEST-E2-07",
    category: "EDGE",
    group: "Engine 2 (Liquidity & T+2)",
    scenario: "Tuần giao dịch có kỳ nghỉ lễ Quốc Khánh/Tết Nguyên Đán kéo dài giữa tuần",
    expectation:
      "Tự động dời lịch thanh toán T+2 sang đúng ngày làm việc tiếp theo của thị trường",
    status: "READY",
  },
  {
    id: "TEST-E2-08",
    category: "SUB",
    group: "Engine 2 (Liquidity & T+2)",
    scenario: "Đánh giá tác động tỷ giá USD/VND vượt ngưỡng biến động cảnh báo",
    expectation:
      "Đưa ra điểm trừ thanh khoản ngoại vi tiêu cực đối với rổ chỉ số VN30",
    status: "READY",
  },

  // --- ENGINE 3: BASIS & TRANSITIONS ---
  {
    id: "TEST-E3-01",
    category: "MAIN",
    group: "Engine 3 (Basis & Transitions)",
    scenario: "Tính toán Basis Spread khi giá VN30F1M cao hơn chỉ số cơ sở VN30",
    expectation:
      "Basis mang giá trị dương; Z-score tính đúng theo Mean và Std lăn 20 kỳ",
    status: "READY",
  },
  {
    id: "TEST-E3-02",
    category: "SUB",
    group: "Engine 3 (Basis & Transitions)",
    scenario: "Phát hiện phân kỳ Basis cực đại (Z_basis > +2.5)",
    expectation:
      "Đưa ra tín hiệu Short Bias đảo chiều theo quy luật hồi quy Mean-Reversion",
    status: "READY",
  },
  {
    id: "TEST-E3-03",
    category: "EDGE",
    group: "Engine 3 (Basis & Transitions)",
    scenario: "Chỉ số VN30 dừng cập nhật tạm thời do nghẽn mạng phía sở giao dịch",
    expectation:
      "Engine 3 chuyển sang cơ chế fallback tính synthetic index từ 30 cổ phiếu thành phần",
    status: "READY",
  },
  {
    id: "TEST-E3-04",
    category: "MAIN",
    group: "Engine 3 (Basis & Transitions)",
    scenario: "Dự báo phiên đóng cửa ATC vào lúc 14:20 (Pre-ATC window)",
    expectation:
      "Sinh kịch bản giá dự kiến và phân phối xác suất tăng/giảm kèm biên độ dao động",
    status: "READY",
  },
  {
    id: "TEST-E3-05",
    category: "SUB",
    group: "Engine 3 (Basis & Transitions)",
    scenario: "Phân loại độ lệch ATO Opening Gap lúc 08:45 của hợp đồng VN30F1M",
    expectation:
      "Xác định đúng Bullish Gap, Bearish Gap hay Normal Gap dựa trên phân phối 60 ngày",
    status: "READY",
  },
  {
    id: "TEST-E3-06",
    category: "MAIN",
    group: "Engine 3 (Basis & Transitions)",
    scenario: "Dự báo phiên tiếp theo (T+1) với mô phỏng Monte Carlo 10,000 runs",
    expectation:
      "Dải giá kỳ vọng P_low và P_high tuân thủ nghiêm ngặt biên độ trần/sàn ±7% của VN30F1M",
    status: "READY",
  },
  {
    id: "TEST-E3-07",
    category: "EDGE",
    group: "Engine 3 (Basis & Transitions)",
    scenario: "Các đường đi mô phỏng Monte Carlo vượt quá biên trần/sàn ±7%",
    expectation:
      "Áp dụng rào chắn phản xạ/hấp thụ tại biên trần sàn, không tạo ra kịch bản phi thực tế",
    status: "READY",
  },

  // --- ENSEMBLE & AUDIT LEDGER ---
  {
    id: "TEST-ENS-01",
    category: "MAIN",
    group: "Ensemble & Audit Ledger",
    scenario: "Điều phối trọng số động theo từng khung giờ phiên (ATO, Continuous, ATC, Post-market)",
    expectation:
      "Tổng trọng số w1 + w2 + w3 luôn chuẩn hóa = 1.0; phản ánh đúng trọng tâm từng phiên",
    status: "READY",
  },
  {
    id: "TEST-ENS-02",
    category: "EDGE",
    group: "Ensemble & Audit Ledger",
    scenario: "Xung đột tín hiệu: Engine 1 Bullish (+0.85) nhưng Engine 3 Bearish (-0.80)",
    expectation:
      "Ensemble cân bằng điểm số, nhận diện trạng thái mâu thuẫn và phát tín hiệu NEUTRAL an toàn",
    status: "READY",
  },
  {
    id: "TEST-ENS-03",
    category: "MAIN",
    group: "Ensemble & Audit Ledger",
    scenario: "Tự động ghi nhận tín hiệu vào ForecastJournal khi sinh forecast",
    expectation:
      "Tạo 1 row DB với đầy đủ predicted_at, predicted_direction, engine_weights, status='pending'",
    status: "READY",
  },
  {
    id: "TEST-ENS-04",
    category: "EDGE",
    group: "Ensemble & Audit Ledger",
    scenario: "Kiểm tra Look-Ahead Bias: cung cấp tập dữ liệu cắt tại thời điểm T",
    expectation:
      "Mô hình hoàn toàn không thể truy cập bất kỳ dữ liệu nào có timestamp > T",
    status: "READY",
  },
  {
    id: "TEST-ENS-05",
    category: "SUB",
    group: "Ensemble & Audit Ledger",
    scenario: "Tính toán Stop Loss và Take Profit động theo hệ số k * ATR 14",
    expectation:
      "Giá SL và TP luôn hợp lý theo chiều lệnh (Long: SL < Entry < TP; Short: TP < Entry < SL)",
    status: "READY",
  },
  {
    id: "TEST-ENS-06",
    category: "SUB",
    group: "Ensemble & Audit Ledger",
    scenario: "Cập nhật đường bám Trailing Stop khi giá phái sinh lập đỉnh/đáy mới",
    expectation:
      "Ngưỡng Stop Loss tịnh tiến theo chiều có lãi, khóa chặt lợi nhuận tích lũy",
    status: "READY",
  },
];

const apiEndpoints = [
  {
    method: "GET",
    path: "/api/v1/quant/engine1/technical/{symbol}",
    desc: "Chỉ báo kỹ thuật, VWAP, Orderflow Delta, Liquidity Sweeps của Engine 1",
    auth: "JWT (CurrentUser)",
    engine: "Engine 1",
  },
  {
    method: "GET",
    path: "/api/v1/quant/engine2/flow-liquidity",
    desc: "Dòng tiền Khối ngoại, Tự doanh, Độ rộng thị trường, Áp lực T+2",
    auth: "JWT (CurrentUser)",
    engine: "Engine 2",
  },
  {
    method: "GET",
    path: "/api/v1/quant/engine3/basis-volatility",
    desc: "Chỉ số Basis, Z-score, Volatility và xác suất chuyển phiên",
    auth: "JWT (CurrentUser)",
    engine: "Engine 3",
  },
  {
    method: "POST",
    path: "/api/v1/quant/ensemble/signal",
    desc: "Tính toán tín hiệu hợp nhất VN30F1M & tự động ghi sổ ForecastJournal",
    auth: "JWT (CurrentUser)",
    engine: "Ensemble",
  },
  {
    method: "GET",
    path: "/api/v1/quant/ensemble/atc-forecast",
    desc: "Dự báo phiên ATC thời gian thực (14:15 - 14:45)",
    auth: "JWT (CurrentUser)",
    engine: "Ensemble",
  },
  {
    method: "GET",
    path: "/api/v1/quant/ensemble/next-day-forecast",
    desc: "Dự báo phiên tiếp theo T+1 (Dải giá kỳ vọng và kịch bản xu hướng)",
    auth: "JWT (CurrentUser)",
    engine: "Ensemble",
  },
  {
    method: "GET",
    path: "/api/v1/quant/ensemble/weights",
    desc: "Lấy cấu hình trọng số hiện tại của 3 engine và lịch sử",
    auth: "JWT (CurrentUser)",
    engine: "Ensemble",
  },
  {
    method: "PUT",
    path: "/api/v1/quant/ensemble/weights",
    desc: "Cập nhật cấu hình trọng số w1, w2, w3 (Admin only)",
    auth: "JWT (Admin)",
    engine: "Ensemble",
  },
];

export function Phase2TRDPage() {
  const [copied, setCopied] = useState(false);
  const [testSearch, setTestSearch] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<string>("ALL");

  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(phase2Markdown);
      setCopied(true);
      toast.success("Đã sao chép nội dung TRD Phase 2 vào clipboard!");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error("Không thể sao chép vào clipboard");
    }
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([phase2Markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "phase_2_specification.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Đang tải xuống file phase_2_specification.md");
  };

  const filteredTests = testCases.filter((t) => {
    const matchesSearch =
      t.id.toLowerCase().includes(testSearch.toLowerCase()) ||
      t.scenario.toLowerCase().includes(testSearch.toLowerCase()) ||
      t.expectation.toLowerCase().includes(testSearch.toLowerCase());
    const matchesGroup = selectedGroup === "ALL" || t.group === selectedGroup;
    const matchesCategory = selectedCategory === "ALL" || t.category === selectedCategory;
    return matchesSearch && matchesGroup && matchesCategory;
  });

  return (
    <div className="flex flex-col gap-8 pb-12">
      {/* Header & Breadcrumb */}
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
              PHASE 2
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link to="/trd/phase-1">
                <FileCode className="h-4 w-4 text-blue-500" />
                <span>Xem TRD Phase 1</span>
              </Link>
            </Button>
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
            Đặc Tả Chi Tiết Phase 2: Tri-Engine Analytics Core
          </h1>
          <p className="mt-2 text-base text-muted-foreground">
            Technical Requirements Document (TRD), Kiến trúc 3 Động Cơ Phân Tích Định Lượng &amp; Bộ Hợp Nhất Quyết Định Ensemble cho hệ thống vnstock.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-2">
          <Badge className="bg-blue-600 hover:bg-blue-700 text-white gap-1 px-3 py-1 text-xs font-semibold">
            <Clock className="h-3.5 w-3.5" />
            Trạng thái: Sẵn sàng triển khai (Ready for Implementation)
          </Badge>
          <Badge variant="secondary" className="gap-1 px-3 py-1 text-xs">
            <Cpu className="h-3.5 w-3.5 text-emerald-500" />
            Kiến trúc: 3 Engines + Ensemble Blending
          </Badge>
          <Badge variant="secondary" className="gap-1 px-3 py-1 text-xs">
            <ShieldCheck className="h-3.5 w-3.5 text-purple-500" />
            Charter: AGENTS.md (Section 2 &amp; 9)
          </Badge>
          <Badge variant="secondary" className="gap-1 px-3 py-1 text-xs">
            <Server className="h-3.5 w-3.5 text-amber-500" />
            FastAPI + SQLModel + NumPy / Pandas
          </Badge>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-border/60 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Phân Tích Định Lượng
            </CardTitle>
            <Cpu className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3 Động Cơ</div>
            <p className="text-xs text-muted-foreground mt-1">
              Technical, Flow/Liquidity, Quant ML/Basis
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Bộ Hợp Nhất Ensemble
            </CardTitle>
            <Sliders className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Trọng số động</div>
            <p className="text-xs text-muted-foreground mt-1">
              w1: 45% (Tech) • w2: 25% (Flow) • w3: 30% (ML)
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Mô Hình Thị Trường
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">T+2 &amp; Basis</div>
            <p className="text-xs text-muted-foreground mt-1">
              Chu kỳ thanh toán T+2 &amp; Arbitrage VN30F1M
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Ma Trận Kiểm Thử
            </CardTitle>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">20 Kịch Bản</div>
            <p className="text-xs text-muted-foreground mt-1">
              Đặc tả toàn diện 4 nhóm kiểm thử cốt lõi
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Tabs Navigation */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-6 h-auto p-1 gap-1">
          <TabsTrigger value="overview" className="py-2 text-xs sm:text-sm">
            🏛️ Tổng quan
          </TabsTrigger>
          <TabsTrigger value="engines" className="py-2 text-xs sm:text-sm">
            ⚙️ 3 Động Cơ &amp; Ensemble
          </TabsTrigger>
          <TabsTrigger value="endpoints" className="py-2 text-xs sm:text-sm">
            🔌 API Endpoints
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

        {/* TAB 1: OVERVIEW */}
        <TabsContent value="overview" className="mt-6 flex flex-col gap-6">
          <Card className="border-emerald-500/20 bg-emerald-500/5">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                <CardTitle className="text-base text-emerald-700 dark:text-emerald-400">
                  Định Hướng Kiến Trúc Tri-Engine Analytics Core (Theo AGENTS.md)
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent className="text-sm space-y-3 text-muted-foreground">
              <p>
                Sau khi Phase 1 hoàn tất toàn bộ tầng lưu trữ (Database Models, Forecast Journal, Paper Trading Tables, Vnstock Adapters), <strong>Phase 2 đóng vai trò là "Bộ Não Tính Toán" (Analytics Brain)</strong> của hệ sinh thái vnstock.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div className="p-3 rounded-md bg-background/90 border">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="bg-blue-500/10 text-blue-600">Engine 1</Badge>
                    <span className="font-semibold text-foreground text-sm">Hành Động Giá &amp; Lệnh</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Xử lý đa khung thời gian (1m, 5m, 15m, 1D), chỉ báo kỹ thuật RSI/MACD/Bollinger/ATR/VWAP, Orderflow Volume Delta và các mẫu hình FVG, Liquidity Sweeps.
                  </p>
                </div>
                <div className="p-3 rounded-md bg-background/90 border">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="bg-purple-500/10 text-purple-600">Engine 2</Badge>
                    <span className="font-semibold text-foreground text-sm">Thanh Khoản &amp; T+2</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Bóc tách dòng tiền Khối ngoại &amp; Tự doanh, độ rộng thị trường, mô hình hóa áp lực bán/mua của chu kỳ thanh toán T+2 và ảnh hưởng vĩ mô USD/VND.
                  </p>
                </div>
                <div className="p-3 rounded-md bg-background/90 border">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="bg-amber-500/10 text-amber-600">Engine 3</Badge>
                    <span className="font-semibold text-foreground text-sm">Định Lượng &amp; Xác Suất</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Theo dõi chênh lệch Basis phái sinh - cơ sở, Z-score phân kỳ, biến động Parkinson/HV, xác suất chuyển phiên ATO/ATC và mô phỏng Monte Carlo T+1.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Master Rules Reminder */}
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-amber-500" />
                4 Quy Tắc Cốt Lõi Bắt Buộc Tuân Thủ Tuyệt Đối (Rule 1 đến 4)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-lg border bg-card space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Badge variant="destructive" className="text-xs font-mono">RULE 1</Badge>
                    <h4 className="font-semibold text-sm">Tuyệt Đối Không Bot Tiền Thật</h4>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Hệ thống không tích hợp API đặt lệnh broker thật, không lưu trữ password, trading PIN, OTP. 100% quyết định giải ngân là do con người (Human-in-the-loop).
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border bg-card space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs font-mono bg-blue-500/10 text-blue-600">RULE 2</Badge>
                    <h4 className="font-semibold text-sm">Cách Ly Hoàn Toàn Mô Phỏng</h4>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Tín hiệu từ Phase 2 chỉ được truyền sang môi trường Simulation và Paper Trading schema độc lập, đảm bảo an toàn tuyệt đối.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border bg-card space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs font-mono bg-purple-500/10 text-purple-600">RULE 3</Badge>
                    <h4 className="font-semibold text-sm">Toàn Vẹn Dữ Liệu &amp; Sổ Nhật Ký</h4>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Không bịa đặt số liệu, không Look-ahead bias (chỉ dùng dữ liệu tại thời điểm phát tín hiệu), 100% tín hiệu được tự động ghi vào ForecastJournal để tự học.
                  </p>
                </div>

                <div className="p-3.5 rounded-lg border bg-card space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs font-mono bg-amber-500/10 text-amber-600">RULE 4</Badge>
                    <h4 className="font-semibold text-sm">Thông Tin Tham Khảo, Không Phải Khuyến Nghị</h4>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Toàn bộ đầu ra API kèm disclaimer rõ ràng về việc phục vụ nghiên cứu và mô phỏng giáo dục, không cam kết lợi nhuận.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: ENGINES SPECIFICATION */}
        <TabsContent value="engines" className="mt-6 flex flex-col gap-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Engine 1 */}
            <Card className="border-border/60">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-blue-500/10 text-blue-600">
                      <TrendingUp className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Engine 1: Technical &amp; Price-Action</CardTitle>
                      <CardDescription>Mô-đun: TechnicalEngine</CardDescription>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-xs">w1: 45%</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <h4 className="font-semibold text-foreground mb-1">Chỉ báo kỹ thuật:</h4>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                    <li>RSI 14 (Quá mua/bán, phân kỳ đỉnh/đáy)</li>
                    <li>MACD (12, 26, 9) Histogram &amp; Crosses</li>
                    <li>Bollinger Bands (20, 2) &amp; Squeeze identification</li>
                    <li>ATR 14: Biến động giá tuyệt đối làm mốc Stop Loss</li>
                    <li>VWAP: Tính toán tích lũy theo Typical Price * Volume</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-foreground mb-1">Dòng lệnh &amp; Price Action:</h4>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                    <li>Volume Delta: Chênh lệch Mua chủ động vs. Bán chủ động</li>
                    <li>Order Imbalance: Tỷ lệ mất cân bằng lệnh (-1.0 đến +1.0)</li>
                    <li>Camarilla Pivots: Hỗ trợ / Kháng cự R1..R4, S1..S4</li>
                    <li>Fair Value Gaps (FVG) &amp; Liquidity Sweeps (Quét râu đảo chiều)</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Engine 2 */}
            <Card className="border-border/60">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-purple-500/10 text-purple-600">
                      <Layers className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Engine 2: Liquidity &amp; T+2 Cashflow</CardTitle>
                      <CardDescription>Mô-đun: FlowLiquidityEngine</CardDescription>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-xs">w2: 25%</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <h4 className="font-semibold text-foreground mb-1">Dòng tiền tổ chức &amp; Độ rộng:</h4>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                    <li>Institutional Flow Momentum (IFM): Mua ròng lăn 3d, 5d, 10d</li>
                    <li>Tỷ trọng kết hợp: 60% Khối ngoại + 40% Tự doanh</li>
                    <li>Advance/Decline Ratio &amp; Market Breadth Score</li>
                    <li>Luân chuyển dòng tiền nhóm ngành theo chuẩn ICB</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-foreground mb-1">Ràng buộc chu kỳ T+2 &amp; Vĩ mô:</h4>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                    <li>Mô hình hóa ngày cổ phiếu về tài khoản (13:00 phiên chiều T+2)</li>
                    <li>Áp lực bán tiềm tàng T+2 (T+2 Pressure Index) từ các phiên bắt đáy</li>
                    <li>Tác động tỷ giá USD/VND đối với dòng vốn ngoại FII</li>
                    <li>Chênh lệch giá vàng SJC và thế giới phản ánh khẩu vị rủi ro</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Engine 3 */}
            <Card className="border-border/60">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-amber-500/10 text-amber-600">
                      <Cpu className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Engine 3: Quantitative ML &amp; Basis</CardTitle>
                      <CardDescription>Mô-đun: QuantMLEngine</CardDescription>
                    </div>
                  </div>
                  <Badge variant="outline" className="font-mono text-xs">w3: 30%</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <h4 className="font-semibold text-foreground mb-1">Basis Spread &amp; Arbitrage:</h4>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                    <li>Basis = VN30F1M - VN30 Index (Chênh lệch giá tức thời)</li>
                    <li>Z-score Basis lăn 20 chu kỳ: Nhận diện phân kỳ thống kê</li>
                    <li>Quy tắc Mean-Reversion: Z &gt; +2.0 (Short Bias), Z &lt; -2.0 (Long Bias)</li>
                    <li>Đo lường độ biến động: Historical Volatility (HV) &amp; Parkinson Volatility</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-foreground mb-1">Xác suất chuyển phiên &amp; Mô phỏng:</h4>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                    <li>ATO Transition: Xác suất Gap mở phiên P(Gap &gt; 0)</li>
                    <li>ATC Transition: Dự báo giá khớp cân bằng đóng cửa 14:45</li>
                    <li>Monte Carlo T+1: Mô phỏng 1,000 đường đi giá trong biên độ ±7%</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Ensemble Blending */}
            <Card className="border-border/60">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-600">
                      <Sliders className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">Ensemble Decision Engine</CardTitle>
                      <CardDescription>Mô-đun: EnsembleEngine</CardDescription>
                    </div>
                  </div>
                  <Badge className="bg-emerald-600 text-white font-mono text-xs">Tổng hợp</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <h4 className="font-semibold text-foreground mb-1">Quy tắc sinh tín hiệu tối ưu:</h4>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                    <li>Score = w1*E1 + w2*E2 + w3*E3 (Tự chuẩn hóa sum = 1.0)</li>
                    <li>Score &ge; +0.35 ➔ <strong>LONG</strong> (Độ tin cậy = |Score|)</li>
                    <li>Score &le; -0.35 ➔ <strong>SHORT</strong> (Độ tin cậy = |Score|)</li>
                    <li>-0.35 &lt; Score &lt; +0.35 ➔ <strong>NEUTRAL</strong> (Đứng ngoài)</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-foreground mb-1">Quản trị rủi ro &amp; Lưu vết:</h4>
                  <ul className="list-disc list-inside text-xs text-muted-foreground space-y-1">
                    <li>Cắt lỗ động: Stop Loss = Entry ± 1.5*ATR (kết hợp Pivot gần nhất)</li>
                    <li>Chốt lời: Take Profit với tỷ lệ Risk:Reward tối thiểu 1:2.0</li>
                    <li><strong>Ghi sổ ForecastJournal:</strong> Lưu snapshot trọng số, thông số, status 'pending'</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* TAB 3: API ENDPOINTS */}
        <TabsContent value="endpoints" className="mt-6 flex flex-col gap-6">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base">Danh Sách 8 API Endpoints Mới (FastAPI /api/v1/quant/*)</CardTitle>
              <CardDescription>Tất cả endpoint đều yêu cầu xác thực JWT qua CurrentUser dependency</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[100px]">Method</TableHead>
                      <TableHead>Endpoint</TableHead>
                      <TableHead>Mô tả</TableHead>
                      <TableHead className="w-[130px]">Phân loại</TableHead>
                      <TableHead className="w-[150px]">Xác thực</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {apiEndpoints.map((ep, idx) => (
                      <TableRow key={idx}>
                        <TableCell>
                          <Badge
                            variant={ep.method === "POST" ? "default" : ep.method === "PUT" ? "secondary" : "outline"}
                            className="font-mono text-xs"
                          >
                            {ep.method}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs font-semibold text-primary">
                          {ep.path}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {ep.desc}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {ep.engine}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs font-mono text-muted-foreground">
                          {ep.auth}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: DEFINITION OF DONE */}
        <TabsContent value="dod" className="mt-6 flex flex-col gap-6">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                Tiêu Chuẩn Nghiệm Thu Hoàn Thành (Definition of Done - DoD)
              </CardTitle>
              <CardDescription>
                Bộ tiêu chuẩn chất lượng bắt buộc trước khi đóng Phase 2
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 rounded-lg border bg-card">
                  <div className="p-1 rounded bg-blue-500/10 text-blue-600 mt-0.5">
                    <Check className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">1. Cấu Trúc Module Độc Lập</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Tách biệt hoàn toàn 3 Engine trong <code>backend/app/services/quant/</code> (<code>technical_engine.py</code>, <code>flow_engine.py</code>, <code>quant_ml_engine.py</code>, <code>ensemble_engine.py</code>), không có circular imports.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-lg border bg-card">
                  <div className="p-1 rounded bg-purple-500/10 text-purple-600 mt-0.5">
                    <Check className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">2. Tuân Thủ 4 Điều Lệ Cốt Lõi</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Không có broker API hay tài khoản thật (Rule 1 &amp; 2). 100% dự báo sinh ra đều được ghi vào <code>ForecastJournal</code> với status <code>pending</code> (Rule 3). Mọi response API đều có disclaimer rõ ràng (Rule 4).
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-lg border bg-card">
                  <div className="p-1 rounded bg-emerald-500/10 text-emerald-600 mt-0.5">
                    <Check className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">3. Chuẩn Code Quality (0 Lỗi)</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Chạy <code>uv run ruff check</code> đạt 0 lỗi; <code>uv run ruff format --check</code> đúng chuẩn; <code>uv run ty check app</code> đạt 0 diagnostics (All checks passed).
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-lg border bg-card">
                  <div className="p-1 rounded bg-amber-500/10 text-amber-600 mt-0.5">
                    <Check className="h-4 w-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">4. Unit Test Coverage &ge; 90%</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Có đầy đủ test cases cho toàn bộ 4 mô-đun engine (RSI, MACD, VWAP, Orderflow Delta, Basis Z-score, Volatility, Monte Carlo, Ensemble Blending), tất cả chạy pass 100% qua <code>uv run pytest</code>.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 5: TEST MATRIX */}
        <TabsContent value="tests" className="mt-6 flex flex-col gap-6">
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-base">Ma Trận 27 Kịch Bản Kiểm Thử (Test Matrix Đa Dạng)</CardTitle>
                  <CardDescription>Bao gồm đầy đủ Main Cases (luồng chuẩn), Sub Cases (biến thể) và Edge Cases (biên & ngoại lệ)</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative w-full sm:w-[240px]">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Tìm kiếm kịch bản..."
                      value={testSearch}
                      onChange={(e) => setTestSearch(e.target.value)}
                      className="pl-8 text-xs h-9"
                    />
                  </div>
                </div>
              </div>

              {/* Category Filter Buttons */}
              <div className="flex flex-wrap gap-1.5 pt-3 border-b pb-2.5">
                {[
                  { key: "ALL", label: `Tất cả (${testCases.length})` },
                  { key: "MAIN", label: `Main Cases (${testCases.filter((t) => t.category === "MAIN").length})` },
                  { key: "SUB", label: `Sub Cases (${testCases.filter((t) => t.category === "SUB").length})` },
                  { key: "EDGE", label: `Edge Cases (${testCases.filter((t) => t.category === "EDGE").length})` },
                ].map((cat) => (
                  <Button
                    key={cat.key}
                    variant={selectedCategory === cat.key ? "default" : "secondary"}
                    size="sm"
                    onClick={() => setSelectedCategory(cat.key)}
                    className="text-xs h-7 px-2.5"
                  >
                    {cat.label}
                  </Button>
                ))}
              </div>

              {/* Group Filter Buttons */}
              <div className="flex flex-wrap gap-1.5 pt-2">
                {["ALL", "Engine 1 (Technical & Orderflow)", "Engine 2 (Liquidity & T+2)", "Engine 3 (Basis & Transitions)", "Ensemble & Audit Ledger"].map((grp) => (
                  <Button
                    key={grp}
                    variant={selectedGroup === grp ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedGroup(grp)}
                    className="text-xs h-7 px-2.5"
                  >
                    {grp === "ALL" ? "Tất cả nhóm" : grp}
                  </Button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[120px]">Test ID</TableHead>
                      <TableHead className="w-[100px]">Phân loại</TableHead>
                      <TableHead className="w-[180px]">Nhóm</TableHead>
                      <TableHead>Tình huống kiểm thử</TableHead>
                      <TableHead>Hành vi kỳ vọng</TableHead>
                      <TableHead className="w-[100px] text-right">Trạng thái</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTests.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-6 text-muted-foreground text-xs">
                          Không tìm thấy kịch bản nào khớp với điều kiện tìm kiếm.
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredTests.map((tc) => (
                        <TableRow key={tc.id}>
                          <TableCell className="font-mono text-xs font-semibold text-primary">
                            {tc.id}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={
                                tc.category === "MAIN"
                                  ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[10px]"
                                  : tc.category === "SUB"
                                  ? "bg-blue-500/10 text-blue-600 border-blue-500/30 text-[10px]"
                                  : "bg-rose-500/10 text-rose-600 border-rose-500/30 text-[10px]"
                              }
                            >
                              {tc.category === "MAIN" ? "MAIN" : tc.category === "SUB" ? "SUB" : "EDGE"}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {tc.group}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs font-medium">
                            {tc.scenario}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {tc.expectation}
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge className="bg-blue-600/90 hover:bg-blue-700 text-white text-[11px]">
                              {tc.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 6: RAW MARKDOWN */}
        <TabsContent value="raw" className="mt-6 flex flex-col gap-6">
          <Card className="border-border/60">
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base">Mã Nguồn Markdown Gốc (TRD Phase 2)</CardTitle>
                <CardDescription>Tài liệu chuẩn để copy, chia sẻ hoặc xuất bản tài liệu kỹ thuật</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={handleCopyMarkdown} className="gap-1 text-xs">
                  {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                  <span>{copied ? "Đã sao chép" : "Sao chép"}</span>
                </Button>
                <Button variant="outline" size="sm" onClick={handleDownloadMarkdown} className="gap-1 text-xs">
                  <Download className="h-3.5 w-3.5" />
                  <span>Tải file</span>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <pre className="p-4 rounded-lg bg-muted/60 font-mono text-xs overflow-x-auto max-h-[600px] border whitespace-pre-wrap">
                {phase2Markdown}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
export default Phase2TRDPage;
