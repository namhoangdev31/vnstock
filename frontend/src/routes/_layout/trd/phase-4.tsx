import { createFileRoute, Link } from "@tanstack/react-router";
import {
  BookOpen,
  Briefcase,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  FileCode,
  Layers,
  Search,
  ShieldAlert,
  TrendingUp,
  Wallet,
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
import { phase4Markdown } from "./-phase4SpecContent";

export const Route = createFileRoute("/_layout/trd/phase-4")({
  component: Phase4TRDPage,
  head: () => ({
    meta: [
      {
        title: "TRD Phase 4: Paper Trading & T+2 Portfolio - vnstock",
      },
      {
        name: "description",
        content:
          "Technical Requirements Document (TRD), Isolated Paper Trading Simulation Engine, Derivatives Margin & Multi-Horizon T+2 Equity Screener for Vnstock.",
      },
    ],
  }),
});

interface TestCase {
  id: string;
  category: "MAIN" | "SUB" | "EDGE";
  group:
    | "Paper Execution & Order Matching"
    | "Derivatives Margin & Liquidation"
    | "T+2 Settlement Cycle"
    | "Multi-Horizon Alpha Screener";
  scenario: string;
  expectation: string;
  status: "READY" | "SPECIFIED";
}

const testCases: TestCase[] = [
  // --- PAPER EXECUTION & ORDER MATCHING ---
  {
    id: "TEST-PAPER-01",
    category: "MAIN",
    group: "Paper Execution & Order Matching",
    scenario: "Đặt lệnh Long LO VN30F1M giá 1300 khi thị trường đang giao dịch ở mức 1305",
    expectation:
      "Lệnh ở trạng thái PENDING, tiền ký quỹ 17% bị khóa tạm tính khỏi sức mua",
    status: "READY",
  },
  {
    id: "TEST-PAPER-02",
    category: "MAIN",
    group: "Paper Execution & Order Matching",
    scenario: "Thị trường xuất hiện tick khớp giá 1299 từ Quote.intraday()",
    expectation:
      "Lệnh lập tức khớp (FILLED), sinh ra vị thế Long mới với giá vốn trung bình 1300",
    status: "READY",
  },
  {
    id: "TEST-PAPER-03",
    category: "MAIN",
    group: "Paper Execution & Order Matching",
    scenario: "Đặt lệnh thị trường MP Bán 2 hợp đồng khi Best Bid là 1302.5",
    expectation:
      "Lệnh khớp ngay lập tức tại 1302.5 (hoặc kèm trượt giá slippage mô phỏng 0.1 điểm = 1302.4)",
    status: "READY",
  },
  {
    id: "TEST-PAPER-04",
    category: "SUB",
    group: "Paper Execution & Order Matching",
    scenario: "Đặt lệnh mua 10 HĐ nhưng thanh khoản sổ lệnh ảo chỉ có 4 HĐ tại mức giá limit",
    expectation:
      "Khớp 1 phần (PARTIALLY_FILLED 4 HĐ), 6 HĐ còn lại tiếp tục chờ ở trạng thái PENDING",
    status: "READY",
  },
  {
    id: "TEST-PAPER-05",
    category: "SUB",
    group: "Paper Execution & Order Matching",
    scenario: "Hủy lệnh khi đang ở trạng thái PENDING",
    expectation:
      "Chuyển sang CANCELLED, hoàn trả 100% tiền ký quỹ tạm khóa vào sức mua khả dụng",
    status: "READY",
  },
  {
    id: "TEST-PAPER-06",
    category: "EDGE",
    group: "Paper Execution & Order Matching",
    scenario: "Đặt lệnh mua phái sinh hoặc cổ phiếu vượt quá sức mua tài khoản ảo",
    expectation:
      "Hệ thống từ chối ngay lập tức với mã lỗi HTTP 400: Insufficient simulated buying power",
    status: "READY",
  },
  {
    id: "TEST-PAPER-07",
    category: "EDGE",
    group: "Paper Execution & Order Matching",
    scenario: "Đặt lệnh với mức giá vượt quá biên độ trần/sàn trong ngày (HOSE ±7%, Phái sinh ±7%)",
    expectation:
      "Bị từ chối với thông báo lỗi: Price out of daily trading price band",
    status: "READY",
  },

  // --- DERIVATIVES MARGIN & LIQUIDATION ---
  {
    id: "TEST-PAPER-08",
    category: "MAIN",
    group: "Derivatives Margin & Liquidation",
    scenario: "Tính toán tiền ký quỹ ban đầu (Initial Margin - IM 17%) khi mở vị thế 2 HĐ tại giá 1320",
    expectation:
      "IM khóa chính xác: 2 * 1320 * 100,000 * 17% = 44,880,000 VND",
    status: "READY",
  },
  {
    id: "TEST-PAPER-09",
    category: "MAIN",
    group: "Derivatives Margin & Liquidation",
    scenario: "Giá thị trường giảm từ 1300 xuống 1290 trên 1 hợp đồng Long",
    expectation:
      "PnL tạm tính giảm chính xác: 1 * (1290 - 1300) * 100,000 = -1,000,000 VND",
    status: "READY",
  },
  {
    id: "TEST-PAPER-10",
    category: "MAIN",
    group: "Derivatives Margin & Liquidation",
    scenario: "Đóng toàn bộ vị thế Short 1 HĐ mở tại 1315 với giá thị trường 1305",
    expectation:
      "PnL thực nhận dương +1,000,000 VND, tiền ký quỹ 17% được giải phóng cộng vào số dư khả dụng",
    status: "READY",
  },
  {
    id: "TEST-PAPER-11",
    category: "SUB",
    group: "Derivatives Margin & Liquidation",
    scenario: "Tỷ lệ ký quỹ duy trì (Maintenance Margin MM 13%) giảm xuống mức cảnh báo (Margin Ratio < 80%)",
    expectation:
      "Hệ thống kích hoạt cảnh báo Margin Call ảo, ngăn mở thêm vị thế mới",
    status: "READY",
  },
  {
    id: "TEST-PAPER-12",
    category: "EDGE",
    group: "Derivatives Margin & Liquidation",
    scenario: "Tỷ lệ ký quỹ giảm sâu dưới ngưỡng thanh lý bắt buộc (Margin Ratio < 65%)",
    expectation:
      "Kích hoạt cơ chế Force Liquidation ảo: tự động đóng vị thế với lệnh thị trường MP",
    status: "READY",
  },
  {
    id: "TEST-PAPER-13",
    category: "EDGE",
    group: "Derivatives Margin & Liquidation",
    scenario: "Thị trường ATO mở cửa nhảy gap giảm sàn kịch biên -7% gây âm vốn tài khoản ảo",
    expectation:
      "Ghi nhận PnL âm thực tế, khóa tài khoản mô phỏng và cung cấp nút reset số dư ban đầu",
    status: "READY",
  },

  // --- T+2 SETTLEMENT CYCLE ---
  {
    id: "TEST-PAPER-14",
    category: "MAIN",
    group: "T+2 Settlement Cycle",
    scenario: "Đặt lệnh Mua cổ phiếu HPG vào 10:00 sáng Thứ Hai (T+0)",
    expectation:
      "Lệnh khớp, tiền mặt bị trừ ngay lập tức, cổ phiếu ghi nhận trạng thái PENDING_T2",
    status: "READY",
  },
  {
    id: "TEST-PAPER-15",
    category: "MAIN",
    group: "T+2 Settlement Cycle",
    scenario: "Đến 13:00 chiều Thứ Tư (T+2) của giao dịch mua ở Test 14",
    expectation:
      "Cổ phiếu tự động chuyển sang SETTLED_AVAILABLE, sẵn sàng bán trong phiên chiều",
    status: "READY",
  },
  {
    id: "TEST-PAPER-16",
    category: "MAIN",
    group: "T+2 Settlement Cycle",
    scenario: "Bán cổ phiếu đã có sẵn (SETTLED_AVAILABLE) vào sáng Thứ Ba",
    expectation:
      "Cổ phiếu bị trừ ngay, tiền bán về ở trạng thái PENDING_CASH_T2 cho đến chiều T+2",
    status: "READY",
  },
  {
    id: "TEST-PAPER-17",
    category: "SUB",
    group: "T+2 Settlement Cycle",
    scenario: "Thử đặt lệnh Bán cổ phiếu đang trong chu kỳ chờ về T+1",
    expectation:
      "Hệ thống từ chối lệnh với mã lỗi 400 Bad Request: Shares are pending T+2 settlement",
    status: "READY",
  },
  {
    id: "TEST-PAPER-18",
    category: "SUB",
    group: "T+2 Settlement Cycle",
    scenario: "Đặt lệnh Mua cổ phiếu vào 14:00 chiều Thứ Sáu",
    expectation:
      "Chu kỳ T+2 bỏ qua Thứ Bảy và Chủ Nhật, ngày khả dụng bán là 13:00 chiều Thứ Ba tuần kế tiếp",
    status: "READY",
  },
  {
    id: "TEST-PAPER-19",
    category: "EDGE",
    group: "T+2 Settlement Cycle",
    scenario: "Giao dịch mua thực hiện liền trước kỳ nghỉ Tết Nguyên Đán 5 ngày làm việc",
    expectation:
      "Hệ thống tự động bù trừ ngày nghỉ lễ theo Holiday Calendar, xác định ngày T+2 chính xác",
    status: "READY",
  },

  // --- MULTI-HORIZON ALPHA SCREENER ---
  {
    id: "TEST-PAPER-20",
    category: "MAIN",
    group: "Multi-Horizon Alpha Screener",
    scenario: "Lọc cổ phiếu Weekly Alpha với điều kiện Vol > 200% SMA20 và Bullish FVG",
    expectation:
      "Trả về danh sách chính xác các mã đạt tiêu chí, loại trừ penny có thanh khoản < 15 tỷ VND",
    status: "READY",
  },
  {
    id: "TEST-PAPER-21",
    category: "MAIN",
    group: "Multi-Horizon Alpha Screener",
    scenario: "Lọc cổ phiếu Monthly Alpha với điều kiện dòng tiền Khối ngoại mua ròng 5 phiên liên tiếp và MA20 > MA50",
    expectation:
      "Trả về danh mục tích lũy trung hạn kèm tỷ trọng phân bổ khuyến nghị",
    status: "READY",
  },
  {
    id: "TEST-PAPER-22",
    category: "MAIN",
    group: "Multi-Horizon Alpha Screener",
    scenario: "Tính toán điểm Piotroski F-Score cho rổ Quarterly Alpha",
    expectation:
      "Trả về điểm từ 0 đến 9 chính xác dựa trên báo cáo tài chính từ Finance.ratio() và income_statement()",
    status: "READY",
  },
  {
    id: "TEST-PAPER-23",
    category: "SUB",
    group: "Multi-Horizon Alpha Screener",
    scenario: "Lọc cổ phiếu có vốn hóa nhỏ hoặc thanh khoản thấp (< 5,000 VND hoặc GTGD < 10 tỷ VND/phiên)",
    expectation:
      "Bộ lọc thanh khoản tự động loại bỏ để tránh rủi ro thao túng giá",
    status: "READY",
  },
  {
    id: "TEST-PAPER-24",
    category: "EDGE",
    group: "Multi-Horizon Alpha Screener",
    scenario: "Dữ liệu báo cáo tài chính quý gần nhất của một mã bị thiếu hoặc chậm công bố",
    expectation:
      "Hệ thống gắn cờ DATA_PENDING, sử dụng báo cáo quý liền trước có chiết khấu độ tin cậy",
    status: "READY",
  },
];

const apiEndpoints = [
  {
    method: "POST",
    path: "/api/v1/simulation/orders",
    desc: "Gửi lệnh đặt mô phỏng mới (Hỗ trợ LO, MP, ATO, ATC, STOP_LOSS)",
    auth: "JWT (CurrentUser)",
  },
  {
    method: "GET",
    path: "/api/v1/simulation/portfolio",
    desc: "Lấy tổng quan tài khoản mô phỏng: số dư tiền, ký quỹ đã khóa, PnL",
    auth: "JWT (CurrentUser)",
  },
  {
    method: "GET",
    path: "/api/v1/simulation/positions",
    desc: "Lấy danh sách các vị thế phái sinh và cổ phiếu đang nắm giữ",
    auth: "JWT (CurrentUser)",
  },
  {
    method: "DELETE",
    path: "/api/v1/simulation/orders/{order_id}",
    desc: "Hủy một lệnh đang ở trạng thái PENDING trong sổ lệnh ảo",
    auth: "JWT (CurrentUser)",
  },
  {
    method: "GET",
    path: "/api/v1/simulation/alpha/baskets",
    desc: "Truy vấn danh mục cổ phiếu khuyến nghị theo Tuần / Tháng / Quý",
    auth: "JWT (CurrentUser)",
  },
];

export function Phase4TRDPage() {
  const [copied, setCopied] = useState(false);
  const [testSearch, setTestSearch] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(phase4Markdown);
      setCopied(true);
      toast.success("Đã sao chép nội dung TRD Phase 4 vào clipboard!");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error("Không thể sao chép vào clipboard");
    }
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([phase4Markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "phase_4_specification.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Đang tải xuống file phase_4_specification.md");
  };

  const testGroups = [
    "ALL",
    "Paper Execution & Order Matching",
    "Derivatives Margin & Liquidation",
    "T+2 Settlement Cycle",
    "Multi-Horizon Alpha Screener",
  ];

  const filteredTests = testCases.filter((t) => {
    const matchesSearch =
      t.id.toLowerCase().includes(testSearch.toLowerCase()) ||
      t.scenario.toLowerCase().includes(testSearch.toLowerCase()) ||
      t.expectation.toLowerCase().includes(testSearch.toLowerCase());
    const matchesGroup = selectedGroup === "ALL" || t.group === selectedGroup;
    const matchesCategory =
      selectedCategory === "ALL" || t.category === selectedCategory;
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
            <Badge variant="default" className="bg-indigo-600/90 text-xs">
              PHASE 4
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link to="/trd/phase-3">
                <Clock className="h-4 w-4 text-amber-500" />
                <span>Xem Phase 3</span>
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link to="/trd/phase-5">
                <BookOpen className="h-4 w-4 text-purple-500" />
                <span>Xem Phase 5</span>
              </Link>
            </Button>
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
              <span>{copied ? "Đã chép" : "Sao chép TRD"}</span>
            </Button>
            <Button
              size="sm"
              onClick={handleDownloadMarkdown}
              className="gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              <Download className="h-4 w-4" />
              <span>Tải xuống .MD</span>
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
              <Wallet className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                TRD Phase 4: Paper Trading Engine & Danh Mục Đa Khung Thời Gian (T+2)
              </h1>
              <p className="text-sm text-muted-foreground">
                Hệ thống giả lập giao dịch phái sinh độc lập (cách ly 100% tiền thật) và bộ lọc cổ phiếu cơ sở theo tuần/tháng/quý tuân thủ quy tắc bán T+2
              </p>
            </div>
          </div>
        </div>

        {/* Master Rule Reminder Alert */}
        <div className="rounded-lg border border-indigo-500/30 bg-indigo-500/5 p-4 text-sm">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-indigo-500" />
            <div className="flex flex-col gap-1">
              <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                Tuân Thủ Tuyệt Đối Master Rule 2 (Strict Isolation)
              </span>
              <p className="text-muted-foreground leading-relaxed">
                Mọi thực thể giao dịch mô phỏng (Tài khoản, Lệnh, Vị thế) nằm hoàn toàn trong các bảng độc lập (<code>PaperPortfolio</code>, <code>PaperOrder</code>, <code>PaperPosition</code>). Khớp lệnh phải căn cứ theo <strong>dòng lệnh thực tế từ Quote.intraday()</strong>, không khớp lệnh ảo tưởng. Cổ phiếu mua vào ngày T bắt buộc phải khóa đến 13:00 chiều ngày T+2 mới được phép bán.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Tabs Layout */}
      <Tabs defaultValue="architecture" className="flex flex-col gap-6">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5 h-auto p-1 bg-muted/60">
          <TabsTrigger value="architecture" className="gap-2 py-2">
            <Layers className="h-4 w-4 text-indigo-500" />
            <span>Chu Kỳ Khóa T+2</span>
          </TabsTrigger>
          <TabsTrigger value="margin" className="gap-2 py-2">
            <Wallet className="h-4 w-4 text-emerald-500" />
            <span>Ký Quỹ Phái Sinh</span>
          </TabsTrigger>
          <TabsTrigger value="alpha" className="gap-2 py-2">
            <TrendingUp className="h-4 w-4 text-amber-500" />
            <span>Alpha 3 Chân Trời</span>
          </TabsTrigger>
          <TabsTrigger value="tests" className="gap-2 py-2">
            <CheckCircle2 className="h-4 w-4 text-purple-500" />
            <span>Ma Trận Test ({testCases.length})</span>
          </TabsTrigger>
          <TabsTrigger value="markdown" className="gap-2 py-2">
            <FileCode className="h-4 w-4 text-cyan-500" />
            <span>Tài Liệu Raw MD</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: ARCHITECTURE & T+2 */}
        <TabsContent value="architecture" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5 text-indigo-500" />
                Quy Trình Quản Lý Vòng Đời Cổ Phiếu T+2
              </CardTitle>
              <CardDescription>
                Mô hình hóa chính xác quy chuẩn thanh toán chứng khoán cơ sở tại Việt Nam
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                  <Badge variant="outline" className="w-fit">NGÀY T (Ngày Mua)</Badge>
                  <h4 className="font-semibold text-sm">Khớp Lệnh Mua</h4>
                  <p className="text-xs text-muted-foreground">Tiền bị trừ khỏi sức mua. Cổ phiếu ghi nhận vào EquitySettlementLedger với status = PENDING_T2.</p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                  <Badge variant="outline" className="w-fit">NGÀY T+1</Badge>
                  <h4 className="font-semibold text-sm">Đang Chờ Về</h4>
                  <p className="text-xs text-muted-foreground">Cổ phiếu tiếp tục bị khóa. Mọi lệnh bán đặt cho lượng cổ phiếu này đều bị hệ thống từ chối.</p>
                </div>

                <div className="border rounded-lg p-4 bg-amber-500/5 border-amber-500/30 flex flex-col gap-2">
                  <Badge className="bg-amber-600 text-white text-xs w-fit">NGÀY T+2: Sáng</Badge>
                  <h4 className="font-semibold text-sm">Tiếp Tục Bị Khóa</h4>
                  <p className="text-xs text-muted-foreground">Từ 09:00 đến 11:30 sáng phiên T+2, cổ phiếu vẫn chưa về tới tài khoản.</p>
                </div>

                <div className="border rounded-lg p-4 bg-emerald-500/5 border-emerald-500/30 flex flex-col gap-2">
                  <Badge className="bg-emerald-600 text-white text-xs w-fit">NGÀY T+2: 13:00</Badge>
                  <h4 className="font-semibold text-sm">Cổ Phiếu Khả Dụng!</h4>
                  <p className="text-xs text-muted-foreground">Daemon tự động chuyển status = SETTLED_AVAILABLE. Cổ phiếu chính thức có thể đặt lệnh Bán.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: MARGIN */}
        <TabsContent value="margin" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Wallet className="h-5 w-5 text-emerald-500" />
                Công Thức Ký Quỹ & Thanh Lý Cưỡng Bức Phái Sinh (VN30F1M)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex flex-col gap-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4 bg-muted/10">
                  <h4 className="font-semibold text-sm mb-1">Ký Quỹ Ban Đầu (IM)</h4>
                  <p className="text-2xl font-bold text-emerald-600 font-mono">17%</p>
                  <p className="text-xs text-muted-foreground mt-1">Hệ số nhân 100,000 VND/điểm. Required Margin = N * Entry * 100,000 * 17%</p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/10">
                  <h4 className="font-semibold text-sm mb-1">Ký Quỹ Duy Trì (MM)</h4>
                  <p className="text-2xl font-bold text-amber-600 font-mono">13%</p>
                  <p className="text-xs text-muted-foreground mt-1">Khi Margin Ratio &lt; 13%: Kích hoạt cảnh báo Call Margin ảo đến người dùng.</p>
                </div>

                <div className="border rounded-lg p-4 bg-rose-500/5 border-rose-500/30">
                  <h4 className="font-semibold text-sm mb-1 text-rose-600">Force Liquidation</h4>
                  <p className="text-2xl font-bold text-rose-600 font-mono">&lt; 10%</p>
                  <p className="text-xs text-muted-foreground mt-1">Tự động kích hoạt lệnh thị trường MP đóng toàn bộ vị thế ảo để bảo toàn vốn.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: ALPHA SCREENER */}
        <TabsContent value="alpha" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-amber-500" />
                Bộ Lọc Danh Mục Cổ Phiếu Đa Khung Thời Gian
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                  <Badge className="bg-amber-600 text-white w-fit text-xs">WEEKLY ALPHA</Badge>
                  <h4 className="font-semibold text-sm">Động Lượng & Bùng Nổ Vol</h4>
                  <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1">
                    <li>Khối lượng nổ &ge; 200% SMA20(V)</li>
                    <li>Giá đóng cửa trên SMA20 và SMA50</li>
                    <li>Xuất hiện Bullish FVG trong 3 phiên</li>
                    <li>Thanh khoản bình quân &gt; 15 tỷ VND</li>
                  </ul>
                </div>

                <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                  <Badge className="bg-indigo-600 text-white w-fit text-xs">MONTHLY ALPHA</Badge>
                  <h4 className="font-semibold text-sm">CANSLIM & Sóng Ngành ICB</h4>
                  <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1">
                    <li>Sức mạnh giá RS Rating &ge; 80</li>
                    <li>Top 3 ngành khối ngoại mua ròng 2 tuần</li>
                    <li>Mô hình thu hẹp biên độ VCP &lt; 8%</li>
                  </ul>
                </div>

                <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                  <Badge className="bg-purple-600 text-white w-fit text-xs">QUARTERLY ALPHA</Badge>
                  <h4 className="font-semibold text-sm">Cơ Bản & Điểm Piotroski</h4>
                  <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1">
                    <li>Tăng trưởng Doanh thu & LNST YoY &ge; 20%</li>
                    <li>ROE &ge; 15%, Nợ/VCSH D/E &lt; 1.5</li>
                    <li>Điểm Piotroski F-Score &ge; 7/9</li>
                    <li>P/E thấp hơn trung bình 3 năm</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* API Endpoints */}
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Briefcase className="h-5 w-5 text-indigo-500" />
                Danh Sách API Endpoints Paper Trading
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-24">Method</TableHead>
                    <TableHead className="w-80">Path</TableHead>
                    <TableHead>Mô tả chức năng</TableHead>
                    <TableHead className="w-36">Quyền truy cập</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apiEndpoints.map((ep) => (
                    <TableRow key={ep.path}>
                      <TableCell>
                        <Badge variant={ep.method === "GET" ? "secondary" : "default"}>
                          {ep.method}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{ep.path}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{ep.desc}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">{ep.auth}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: TEST MATRIX */}
        <TabsContent value="tests" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-purple-500" />
                Ma Trận Kịch Bản Kiểm Thử (Test Acceptance Matrix)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex flex-col gap-4">
              <div className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="relative flex-1 min-w-[240px]">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Tìm kiếm kịch bản test hoặc mã test..."
                      value={testSearch}
                      onChange={(e) => setTestSearch(e.target.value)}
                      className="pl-8"
                    />
                  </div>
                  {/* Category Filter Tabs */}
                  <div className="flex items-center gap-1.5 bg-muted/60 p-1 rounded-lg border">
                    {(
                      [
                        { id: "ALL", label: `Tất cả (${testCases.length})` },
                        {
                          id: "MAIN",
                          label: `Main Cases (${testCases.filter((t) => t.category === "MAIN").length})`,
                        },
                        {
                          id: "SUB",
                          label: `Sub Cases (${testCases.filter((t) => t.category === "SUB").length})`,
                        },
                        {
                          id: "EDGE",
                          label: `Edge Cases (${testCases.filter((t) => t.category === "EDGE").length})`,
                        },
                      ] as const
                    ).map((cat) => (
                      <Button
                        key={cat.id}
                        variant={selectedCategory === cat.id ? "default" : "ghost"}
                        size="sm"
                        onClick={() => setSelectedCategory(cat.id)}
                        className={`h-7 text-xs px-2.5 ${
                          selectedCategory === cat.id
                            ? cat.id === "MAIN"
                              ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                              : cat.id === "SUB"
                              ? "bg-blue-600 hover:bg-blue-700 text-white"
                              : cat.id === "EDGE"
                              ? "bg-rose-600 hover:bg-rose-700 text-white"
                              : ""
                            : ""
                        }`}
                      >
                        {cat.label}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Group Filter Chips */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="text-xs font-medium text-muted-foreground mr-1">
                    Nhóm kiểm thử:
                  </span>
                  {testGroups.map((grp) => (
                    <Button
                      key={grp}
                      variant={selectedGroup === grp ? "secondary" : "ghost"}
                      size="sm"
                      onClick={() => setSelectedGroup(grp)}
                      className={`h-6 text-[11px] px-2 rounded-md ${
                        selectedGroup === grp
                          ? "border border-primary/30 font-semibold"
                          : "text-muted-foreground"
                      }`}
                    >
                      {grp === "ALL" ? "Tất cả nhóm" : grp}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="border rounded-md overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-36">Mã Test</TableHead>
                      <TableHead className="w-24">Phân loại</TableHead>
                      <TableHead className="w-56">Phân nhóm</TableHead>
                      <TableHead>Kịch bản thử nghiệm</TableHead>
                      <TableHead>Kết quả kỳ vọng</TableHead>
                      <TableHead className="w-24 text-right">Trạng thái</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTests.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={6}
                          className="text-center py-6 text-muted-foreground text-xs"
                        >
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
                              {tc.category}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {tc.group}
                          </TableCell>
                          <TableCell className="text-xs font-medium">
                            {tc.scenario}
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">
                            {tc.expectation}
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[10px]">
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

        {/* TAB 5: MARKDOWN RAW */}
        <TabsContent value="markdown" className="flex flex-col gap-4 m-0">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              Toàn văn tài liệu đặc tả kỹ thuật phase_4_specification.md
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyMarkdown}
              className="gap-1.5"
            >
              {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
              <span>{copied ? "Đã chép" : "Sao chép Markdown"}</span>
            </Button>
          </div>
          <pre className="p-4 bg-muted/40 border rounded-lg font-mono text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[700px] overflow-y-auto">
            {phase4Markdown}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default Phase4TRDPage;
