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
  {
    id: "TEST-PAPER-01",
    group: "Paper Execution & Order Matching",
    scenario: "Đặt lệnh Long VN30F1M giá 1300 khi thị trường đang giao dịch ở mức 1305",
    expectation:
      "Lệnh ở trạng thái PENDING, tiền ký quỹ 17% bị khóa tạm tính khỏi sức mua",
    status: "READY",
  },
  {
    id: "TEST-PAPER-02",
    group: "Paper Execution & Order Matching",
    scenario: "Thị trường xuất hiện tick khớp giá 1299 từ Quote.intraday()",
    expectation:
      "Lệnh lập tức khớp (FILLED), sinh ra vị thế Long mới với giá vốn trung bình 1300",
    status: "READY",
  },
  {
    id: "TEST-PAPER-03",
    group: "Derivatives Margin & Liquidation",
    scenario: "Giá thị trường giảm từ 1300 xuống 1290 trên 1 hợp đồng Long",
    expectation:
      "PnL tạm tính giảm chính xác: 1 * (1290 - 1300) * 100,000 = -1,000,000 VND",
    status: "READY",
  },
  {
    id: "TEST-PAPER-04",
    group: "Derivatives Margin & Liquidation",
    scenario: "Tỷ lệ Margin Ratio giảm xuống dưới ngưỡng duy trì 10%",
    expectation:
      "Kích hoạt cơ chế Force Liquidation ảo: tự động đóng vị thế với lệnh thị trường MP",
    status: "READY",
  },
  {
    id: "TEST-PAPER-05",
    group: "T+2 Settlement Cycle",
    scenario: "Đặt lệnh Mua cổ phiếu HPG vào 10:00 sáng Thứ Sáu",
    expectation:
      "Lệnh khớp, tạo row trong EquitySettlementLedger với thời điểm đáo hạn là 13:00 Thứ Ba tuần sau",
    status: "READY",
  },
  {
    id: "TEST-PAPER-06",
    group: "T+2 Settlement Cycle",
    scenario: "Thử đặt lệnh Bán cổ phiếu vừa mua ở Test 05 vào sáng Thứ Hai",
    expectation:
      "Hệ thống từ chối lệnh với mã lỗi 400 Bad Request: Shares are pending T+2 settlement",
    status: "READY",
  },
  {
    id: "TEST-PAPER-07",
    group: "T+2 Settlement Cycle",
    scenario: "Đến 13:01 chiều Thứ Ba tuần sau",
    expectation:
      "Cổ phiếu tự động chuyển thành SETTLED_AVAILABLE, cho phép đặt lệnh Bán bình thường",
    status: "READY",
  },
  {
    id: "TEST-PAPER-08",
    group: "Multi-Horizon Alpha Screener",
    scenario: "Lọc cổ phiếu Weekly Alpha với điều kiện Vol > 200% SMA20 và Bullish FVG",
    expectation:
      "Trả về danh sách chính xác các mã đạt tiêu chí, loại trừ penny có thanh khoản < 15 tỷ VND",
    status: "READY",
  },
  {
    id: "TEST-PAPER-09",
    group: "Multi-Horizon Alpha Screener",
    scenario: "Tính toán điểm Piotroski F-Score cho rổ Quarterly Alpha",
    expectation:
      "Trả về điểm từ 0 đến 9 chính xác dựa trên báo cáo tài chính từ Finance.ratio() và income_statement()",
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
                <div className="flex items-center gap-2">
                  <Button
                    variant={selectedGroup === "ALL" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedGroup("ALL")}
                  >
                    Tất cả ({testCases.length})
                  </Button>
                </div>
              </div>

              <div className="border rounded-md overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-36">Mã Test</TableHead>
                      <TableHead className="w-56">Phân nhóm</TableHead>
                      <TableHead>Kịch bản thử nghiệm</TableHead>
                      <TableHead>Kết quả kỳ vọng</TableHead>
                      <TableHead className="w-24 text-right">Trạng thái</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTests.map((tc) => (
                      <TableRow key={tc.id}>
                        <TableCell className="font-mono text-xs font-semibold">{tc.id}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{tc.group}</TableCell>
                        <TableCell className="text-xs font-medium">{tc.scenario}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{tc.expectation}</TableCell>
                        <TableCell className="text-right">
                          <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 text-[10px]">
                            {tc.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
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
