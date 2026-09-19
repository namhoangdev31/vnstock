import { createFileRoute, Link } from "@tanstack/react-router";
import {
  BarChart3,
  BookOpen,
  Check,
  CheckCircle2,
  Copy,
  Download,
  FileCode,
  Layers,
  LineChart,
  PieChart,
  Search,
  Server,
  ShieldAlert,
  Wallet,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { phase6Markdown } from "./-phase6SpecContent";

export const Route = createFileRoute("/_layout/trd/phase-6")({
  component: Phase6TRDPage,
  head: () => ({
    meta: [
      {
        title: "TRD Phase 6: Frontend Dashboards - vnstock",
      },
      {
        name: "description",
        content:
          "Technical Requirements Document (TRD), Real-time Derivatives Command Station, Flow & Breadth Radar, ATC Terminal & Paper Trading Cockpit for Vnstock.",
      },
    ],
  }),
});

interface TestCase {
  id: string;
  category: "MAIN" | "SUB" | "EDGE";
  group:
    | "Derivatives Command Station"
    | "Flow & Breadth Radar"
    | "ATC & Monte Carlo Terminal"
    | "Paper Trading Cockpit";
  scenario: string;
  expectation: string;
  status: "READY" | "SPECIFIED";
}

const testCases: TestCase[] = [
  // --- DERIVATIVES COMMAND STATION ---
  {
    id: "TEST-FE-01",
    category: "MAIN",
    group: "Derivatives Command Station",
    scenario: "Mở màn hình Trạm Phái Sinh trên trình duyệt",
    expectation:
      "Biểu đồ nến tải mượt mà, giá nhảy realtime từ luồng cập nhật mà không bị chớp nháy toàn màn hình",
    status: "READY",
  },
  {
    id: "TEST-FE-02",
    category: "MAIN",
    group: "Derivatives Command Station",
    scenario: "Chuyển đổi khung thời gian nến (1m, 5m, 15m, 1D)",
    expectation:
      "Biểu đồ cập nhật lại chuỗi nến đúng khung thời gian tương ứng và tự động canh chỉnh trục giá",
    status: "READY",
  },
  {
    id: "TEST-FE-03",
    category: "SUB",
    group: "Derivatives Command Station",
    scenario: "Bật/Tắt các lớp chỉ báo kỹ thuật (RSI, Bollinger Bands, VWAP, FVG)",
    expectation:
      "Các layer indicator hiển thị hoặc ẩn chính xác mà không làm gián đoạn hay giật lag biểu đồ nến",
    status: "READY",
  },
  {
    id: "TEST-FE-04",
    category: "SUB",
    group: "Derivatives Command Station",
    scenario: "Hiển thị widget Basis Spread (VN30F1M - VN30 Index)",
    expectation:
      "Giá trị basis hiển thị kèm màu sắc động (Xanh lá khi Premium > 0, Đỏ khi Discount < 0)",
    status: "READY",
  },
  {
    id: "TEST-FE-05",
    category: "EDGE",
    group: "Derivatives Command Station",
    scenario: "Mất kết nối mạng tạm thời (Network Offline)",
    expectation:
      "Hiển thị thanh thông báo cảnh báo mất kết nối màu vàng (Reconnecting...) và tự phục hồi khi có mạng lại",
    status: "READY",
  },
  {
    id: "TEST-FE-06",
    category: "EDGE",
    group: "Derivatives Command Station",
    scenario: "Dữ liệu tick đổ về với tần số cao (> 50 ticks/giây trong phút ATC)",
    expectation:
      "Cơ chế throttle/requestAnimationFrame gom cụm render, CPU trình duyệt sử dụng tối ưu dưới 15%",
    status: "READY",
  },

  // --- FLOW & BREADTH RADAR ---
  {
    id: "TEST-FE-07",
    category: "MAIN",
    group: "Flow & Breadth Radar",
    scenario: "Xem biểu đồ ròng Khối ngoại và Tự doanh trên 30 mã VN30",
    expectation:
      "Hiển thị thanh ngang 2 màu (Xanh lá mua ròng, Đỏ bán ròng) chuẩn xác theo từng mã rổ VN30",
    status: "READY",
  },
  {
    id: "TEST-FE-08",
    category: "MAIN",
    group: "Flow & Breadth Radar",
    scenario: "Xem biểu đồ độ rộng thị trường (Advance/Decline/Unchanged)",
    expectation:
      "Tỷ lệ mã tăng/giảm/tham chiếu hiển thị trực quan dưới dạng thanh tỷ lệ phần trăm",
    status: "READY",
  },
  {
    id: "TEST-FE-09",
    category: "SUB",
    group: "Flow & Breadth Radar",
    scenario: "Xem widget Macro & Ngoại hối (Tỷ giá USD/VND, Giá vàng SJC)",
    expectation:
      "Cập nhật xu hướng tăng/giảm trong phiên kèm chênh lệch phần trăm biến động",
    status: "READY",
  },
  {
    id: "TEST-FE-10",
    category: "SUB",
    group: "Flow & Breadth Radar",
    scenario: "Đồng hồ đo áp lực cung hàng T+2 phiên chiều (13:00)",
    expectation:
      "Tự động tính toán lượng hàng bắt đáy phiên T-2 có lãi/lỗ và cảnh báo áp lực chốt lời",
    status: "READY",
  },
  {
    id: "TEST-FE-11",
    category: "EDGE",
    group: "Flow & Breadth Radar",
    scenario: "Toàn bộ rổ VN30 đều bị bán ròng hoặc thị trường đóng cửa (ngày nghỉ lễ)",
    expectation:
      "Radar hiển thị trạng thái Empty State thông minh, không phát sinh lỗi vỡ layout giao diện",
    status: "READY",
  },

  // --- ATC & MONTE CARLO TERMINAL ---
  {
    id: "TEST-FE-12",
    category: "MAIN",
    group: "ATC & Monte Carlo Terminal",
    scenario: "Xem biểu đồ phân phối xác suất Monte Carlo phiên ATC",
    expectation:
      "Thấy rõ dải xác suất P10 - P50 - P90 nằm hoàn toàn trong biên trần/sàn ±7% của VN30F1M",
    status: "READY",
  },
  {
    id: "TEST-FE-13",
    category: "MAIN",
    group: "ATC & Monte Carlo Terminal",
    scenario: "Xem ma trận 3 kịch bản dự báo ATC (Bullish / Base / Bearish)",
    expectation:
      "Hiển thị chi tiết xác suất xảy ra, mức giá mục tiêu và khuyến nghị vị thế",
    status: "READY",
  },
  {
    id: "TEST-FE-14",
    category: "SUB",
    group: "ATC & Monte Carlo Terminal",
    scenario: "Bấm chọn xem chi tiết đóng góp của 3 Engine trong kịch bản dự báo",
    expectation:
      "Hiển thị biểu đồ phân bổ trọng số Engine 1 (Tech), Engine 2 (Flow), Engine 3 (ML) rõ ràng",
    status: "READY",
  },
  {
    id: "TEST-FE-15",
    category: "EDGE",
    group: "ATC & Monte Carlo Terminal",
    scenario: "Dữ liệu phân phối Monte Carlo gặp lỗi tính toán hoặc thiếu giá trị đầu vào",
    expectation:
      "Giao diện fallback sang kịch bản trung tính (Neutral), hiển thị thông báo cảnh báo rõ ràng",
    status: "READY",
  },

  // --- PAPER TRADING COCKPIT ---
  {
    id: "TEST-FE-16",
    category: "MAIN",
    group: "Paper Trading Cockpit",
    scenario: "Nhập form đặt lệnh Mua 1 hợp đồng VN30F1M giá LO",
    expectation:
      "Form tính toán chính xác số tiền ký quỹ yêu cầu tạm tính (P * 100,000 * 17%)",
    status: "READY",
  },
  {
    id: "TEST-FE-17",
    category: "MAIN",
    group: "Paper Trading Cockpit",
    scenario: "Đặt lệnh mô phỏng thành công",
    expectation:
      "Danh sách vị thế đang mở và sổ lệnh ảo lập tức cập nhật lệnh mới với status PENDING hoặc FILLED",
    status: "READY",
  },
  {
    id: "TEST-FE-18",
    category: "MAIN",
    group: "Paper Trading Cockpit",
    scenario: "Xem bảng vị thế phái sinh đang nắm giữ",
    expectation:
      "Hiển thị PnL chưa thực hiện (Unrealized PnL) cập nhật realtime theo biến động giá thị trường",
    status: "READY",
  },
  {
    id: "TEST-FE-19",
    category: "SUB",
    group: "Paper Trading Cockpit",
    scenario: "Thao tác Đóng vị thế nhanh (Close Position button)",
    expectation:
      "Bật modal xác nhận, đóng vị thế bằng lệnh MP và cập nhật lại số dư tiền mặt khả dụng tức thì",
    status: "READY",
  },
  {
    id: "TEST-FE-20",
    category: "SUB",
    group: "Paper Trading Cockpit",
    scenario: "Số dư tiền ảo không đủ mức ký quỹ 17%",
    expectation:
      "Nút đặt lệnh bị vô hiệu hóa kèm tooltip cảnh báo: Số dư khả dụng không đủ để ký quỹ",
    status: "READY",
  },
  {
    id: "TEST-FE-21",
    category: "EDGE",
    group: "Paper Trading Cockpit",
    scenario: "Nhập khối lượng đặt lệnh âm, số thập phân hoặc chữ cái vào ô Khối lượng",
    expectation:
      "Form validation chặn gửi lệnh ngay lập tức, hiển thị thông báo lỗi inline màu đỏ",
    status: "READY",
  },
  {
    id: "TEST-FE-22",
    category: "EDGE",
    group: "Paper Trading Cockpit",
    scenario: "Kiểm thử trên thiết bị di động hoặc màn hình hẹp (Mobile / Tablet 375px - 768px)",
    expectation:
      "Toàn bộ bảng dữ liệu hỗ trợ cuộn ngang linh hoạt, nút bấm đạt kích thước tối thiểu dễ chạm",
    status: "READY",
  },
];

export function Phase6TRDPage() {
  const [copied, setCopied] = useState(false);
  const [testSearch, setTestSearch] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(phase6Markdown);
      setCopied(true);
      toast.success("Đã sao chép nội dung TRD Phase 6 vào clipboard!");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error("Không thể sao chép vào clipboard");
    }
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([phase6Markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "phase_6_specification.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Đang tải xuống file phase_6_specification.md");
  };

  const testGroups = [
    "ALL",
    "Derivatives Command Station",
    "Flow & Breadth Radar",
    "ATC & Monte Carlo Terminal",
    "Paper Trading Cockpit",
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
            <Badge variant="default" className="bg-cyan-600/90 text-xs">
              PHASE 6
            </Badge>
          </div>
          <div className="flex items-center gap-2">
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
              className="gap-1.5 bg-cyan-600 hover:bg-cyan-700 text-white"
            >
              <Download className="h-4 w-4" />
              <span>Tải xuống .MD</span>
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-500 border border-cyan-500/20">
              <LineChart className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                TRD Phase 6: Frontend Dashboards & Trạm Điều Hành Giao Dịch
              </h1>
              <p className="text-sm text-muted-foreground">
                Xây dựng trạm điều hành phái sinh, radar dòng tiền, bảng kịch
                bản ATC/T+1 và terminal giao dịch mô phỏng trên giao diện React
                + TailwindCSS
              </p>
            </div>
          </div>
        </div>

        {/* Master Rule Reminder Alert */}
        <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/5 p-4 text-sm">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-cyan-500" />
            <div className="flex flex-col gap-1">
              <span className="font-semibold text-cyan-600 dark:text-cyan-400">
                Giao Diện Minh Bạch & Cảnh Báo Rủi Ro (Master Rule 4)
              </span>
              <p className="text-muted-foreground leading-relaxed">
                Toàn bộ màn hình giao dịch và số dư đều phải gắn nhãn{" "}
                <strong>[MÔ PHỎNG / PAPER TRADING 100%]</strong>. Mọi tín hiệu
                chiến lược, dải giá mục tiêu và rổ cổ phiếu gợi ý chỉ mang tính
                chất nghiên cứu định lượng, không phải lời khuyên đầu tư tài
                chính.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Tabs Layout */}
      <Tabs defaultValue="screens" className="flex flex-col gap-6">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-4 h-auto p-1 bg-muted/60">
          <TabsTrigger value="screens" className="gap-2 py-2">
            <Layers className="h-4 w-4 text-cyan-500" />
            <span>4 Màn Hình Cốt Lõi</span>
          </TabsTrigger>
          <TabsTrigger value="blueprint" className="gap-2 py-2">
            <Server className="h-4 w-4 text-emerald-500" />
            <span>Blueprint 6 Bước Dev</span>
          </TabsTrigger>
          <TabsTrigger value="tests" className="gap-2 py-2">
            <CheckCircle2 className="h-4 w-4 text-purple-500" />
            <span>Ma Trận Test ({testCases.length})</span>
          </TabsTrigger>
          <TabsTrigger value="markdown" className="gap-2 py-2">
            <FileCode className="h-4 w-4 text-amber-500" />
            <span>Tài Liệu Raw MD</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: 4 CORE SCREENS */}
        <TabsContent value="screens" className="flex flex-col gap-6 m-0">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="border shadow-sm">
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="text-base flex items-center gap-2">
                  <LineChart className="h-4 w-4 text-emerald-500" />
                  Màn Hình 1: Trạm Điều Hành Phái Sinh Live
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 flex flex-col gap-2 text-xs text-muted-foreground">
                <p>
                  • Biểu đồ nến tương tác 1m, 5m, 15m với thư viện Lightweight
                  Charts.
                </p>
                <p>
                  • Biểu đồ cột Orderflow Delta ($V_{"{buy}"} - V_{"{sell}"}$)
                  theo từng phút.
                </p>
                <p>
                  • Đồ thị Basis Spread ($P_{"{F1M}"} - I_{"{VN30}"}$) thời gian
                  thực.
                </p>
                <p>
                  • Thẻ tín hiệu Ensemble: Badge LONG/SHORT, điểm Stop Loss động
                  theo k * ATR(14) và đường bám Trailing Stop.
                </p>
              </CardContent>
            </Card>

            <Card className="border shadow-sm">
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="text-base flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-indigo-500" />
                  Màn Hình 2: Radar Dòng Tiền & Độ Rộng Thị Trường
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 flex flex-col gap-2 text-xs text-muted-foreground">
                <p>
                  • Biểu đồ mua/bán ròng Khối ngoại và Tự doanh trên 30 mã VN30.
                </p>
                <p>• Thước đo độ rộng Advance/Decline Ratio toàn sàn HOSE.</p>
                <p>
                  • Thước đo áp lực T+2 phiên chiều (đo lượng hàng bắt đáy T-2
                  về tài khoản lúc 13:00).
                </p>
                <p>• Ticker tỷ giá USD/VND và giá vàng miếng SJC.</p>
              </CardContent>
            </Card>

            <Card className="border shadow-sm">
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="text-base flex items-center gap-2">
                  <PieChart className="h-4 w-4 text-purple-500" />
                  Màn Hình 3: Bảng Kịch Bản Dự Báo ATC & T+1
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 flex flex-col gap-2 text-xs text-muted-foreground">
                <p>
                  • Khối lượng mất cân bằng cung cầu dự kiến rổ VN30 trước
                  14:30.
                </p>
                <p>
                  • Đồ thị phân phối xác suất Monte Carlo 10,000 kịch bản: dải
                  giá P10 - P50 - P90.
                </p>
                <p>• Giới hạn trần/sàn biên độ $\pm 7\%$ cho phái sinh.</p>
                <p>
                  • Bảng lịch sử đối soát kết quả dự báo và điểm Brier Score.
                </p>
              </CardContent>
            </Card>

            <Card className="border shadow-sm">
              <CardHeader className="border-b bg-muted/20">
                <CardTitle className="text-base flex items-center gap-2">
                  <Wallet className="h-4 w-4 text-amber-500" />
                  Màn Hình 4: Terminal Giao Dịch Mô Phỏng
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 flex flex-col gap-2 text-xs text-muted-foreground">
                <p>
                  • Thẻ tổng quan số dư tiền ảo, ký quỹ bị khóa, PnL tạm tính và
                  PnL đã chốt.
                </p>
                <p>
                  • Form đặt lệnh ảo (LO, MP, ATO, ATC, STOP_LOSS) có tính trước
                  tiền ký quỹ 17%.
                </p>
                <p>• Bảng vị thế đang mở kèm nút đóng vị thế nhanh.</p>
                <p>
                  • Bảng rổ cổ phiếu Alpha Tuần / Tháng / Quý kèm nút mua theo
                  tỷ trọng ảo.
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* TAB 2: DEV BLUEPRINT */}
        <TabsContent value="blueprint" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Server className="h-5 w-5 text-emerald-500" />
                Checklist 6 Bước Tự Code Frontend Dashboards
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="flex flex-col gap-4">
                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 font-bold text-xs flex-shrink-0">
                    1
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">
                      Cài đặt thư viện biểu đồ
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      Chạy: bun add lightweight-charts recharts lucide-react
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 font-bold text-xs flex-shrink-0">
                    2
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">
                      Tạo Custom Hooks dữ liệu
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      Viết useDerivativesLive, useMarketBreadth, usePaperTrading
                      với TanStack Query.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 font-bold text-xs flex-shrink-0">
                    3
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">
                      Xây dựng Component nến InteractiveCandleChart
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      Tích hợp TradingView Lightweight Charts hiển thị nến
                      xanh/đỏ và đường VWAP.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 font-bold text-xs flex-shrink-0">
                    4
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">
                      Xây dựng Form đặt lệnh ảo OrderPlacementForm
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      Kiểm tra ký quỹ 17% trước khi gửi; hiển thị toast thông
                      báo thành công.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 font-bold text-xs flex-shrink-0">
                    5
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">
                      Xây dựng Component MonteCarloDistributionChart
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      Vẽ dải diện tích Recharts AreaChart từ P10 đến P90 kèm
                      đường giới hạn trần/sàn ±7%.
                    </p>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500 font-bold text-xs flex-shrink-0">
                    6
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm">
                      Tích hợp vào Route Chính
                    </h4>
                    <p className="text-xs text-muted-foreground">
                      Tạo route trading.tsx sử dụng Tabs chuyển đổi 4 màn hình
                      mượt mà.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: TEST MATRIX */}
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

        {/* TAB 4: MARKDOWN RAW */}
        <TabsContent value="markdown" className="flex flex-col gap-4 m-0">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              Toàn văn tài liệu đặc tả kỹ thuật phase_6_specification.md
            </span>
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
              <span>{copied ? "Đã chép" : "Sao chép Markdown"}</span>
            </Button>
          </div>
          <pre className="p-4 bg-muted/40 border rounded-lg font-mono text-xs overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[700px] overflow-y-auto">
            {phase6Markdown}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default Phase6TRDPage;
