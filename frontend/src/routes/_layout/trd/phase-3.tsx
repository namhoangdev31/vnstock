import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Cpu,
  Download,
  FileCode,
  Layers,
  Radio,
  Search,
  Server,
  ShieldAlert,
  ShieldCheck,
  Terminal,
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
import { phase3Markdown } from "./-phase3SpecContent";

export const Route = createFileRoute("/_layout/trd/phase-3")({
  component: Phase3TRDPage,
  head: () => ({
    meta: [
      {
        title: "TRD Phase 3: Background Session Daemon (24/7) - vnstock",
      },
      {
        name: "description",
        content:
          "Technical Requirements Document (TRD), 24/7 Background Session Daemon Loop, Adaptive Polling, Circuit Breaker & Resilient Market Engine for Vnstock.",
      },
    ],
  }),
});

interface TestCase {
  id: string;
  category: "MAIN" | "SUB" | "EDGE";
  group:
    | "State Machine (Clock & Sessions)"
    | "Resilience & Circuit Breaker"
    | "Asyncio Loop & Dispatcher"
    | "Audit & Heartbeat API";
  scenario: string;
  expectation: string;
  status: "READY" | "SPECIFIED";
}

const testCases: TestCase[] = [
  // --- STATE MACHINE (CLOCK & SESSIONS) ---
  {
    id: "TEST-DAEMON-01",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Chạy hàm get_current_session_state với mock time là 08:35 sáng thứ Hai",
    expectation:
      "Trả về chính xác SessionState.PRE_ATO_SETUP, đồng bộ giá tham chiếu và FVG mới",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-02",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Chạy hàm get_current_session_state với mock time là 08:47 sáng thứ Hai",
    expectation:
      "Trả về chính xác SessionState.ATO_AUCTION, kích hoạt nến mở màn phái sinh VN30F1M",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-03",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Chạy hàm get_current_session_state với mock time là 09:15 sáng",
    expectation:
      "Trả về chính xác SessionState.MORNING_CONTINUOUS, bắt đầu chu kỳ nến 1m và Orderflow",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-04",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Chạy hàm get_current_session_state với mock time là 11:45 trưa",
    expectation:
      "Trả về chính xác SessionState.MIDDAY_INTERMISSION, giảm tần suất polling xuống 60 giây",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-05",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Chạy hàm get_current_session_state với mock time là 13:05 chiều",
    expectation:
      "Trả về chính xác SessionState.AFTERNOON_CONTINUOUS, kích hoạt đo lường áp lực T+2",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-06",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Chạy hàm get_current_session_state với mock time là 14:22 chiều",
    expectation:
      "Trả về chính xác SessionState.PRE_ATC_SETUP, kích hoạt bộ dự báo đóng cửa ATC",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-07",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Chạy hàm get_current_session_state với mock time là 14:35 chiều",
    expectation:
      "Trả về chính xác SessionState.ATC_AUCTION, theo dõi đợt khớp lệnh định kỳ đóng cửa",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-08",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Chạy hàm get_current_session_state với mock time là 14:50 chiều",
    expectation:
      "Trả về chính xác SessionState.POST_MARKET_EVAL, đối soát và chấm điểm ForecastJournal",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-09",
    category: "MAIN",
    group: "State Machine (Clock & Sessions)",
    scenario: "Mock thời gian lúc 22:00 hoặc ngày Thứ 7, Chủ Nhật",
    expectation:
      "Trả về chính xác SessionState.OVERNIGHT_SIMULATION, chạy mô phỏng Monte Carlo 24/7",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-10",
    category: "SUB",
    group: "State Machine (Clock & Sessions)",
    scenario: "Ngày nghỉ lễ Quốc khánh hoặc Tết Nguyên Đán (ngày làm việc trong tuần nhưng sàn đóng cửa)",
    expectation:
      "Hệ thống nhận biết lịch nghỉ lễ từ Holiday Calendar và giữ trạng thái OVERNIGHT_SIMULATION",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-11",
    category: "EDGE",
    group: "State Machine (Clock & Sessions)",
    scenario: "Khởi động Daemon tại thời điểm giữa phiên (ví dụ 10:15:32)",
    expectation:
      "Daemon tự động đồng bộ ngay vào MORNING_CONTINUOUS mà không cần chờ chu kỳ mới",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-12",
    category: "EDGE",
    group: "State Machine (Clock & Sessions)",
    scenario: "Hệ thống bị trôi giờ máy chủ hoặc dịch lùi thời gian do đồng bộ NTP",
    expectation:
      "Sử dụng monotonic clock tính toán khoảng cách thời gian, không bị lặp hoặc nhảy lùi state",
    status: "READY",
  },

  // --- RESILIENCE & CIRCUIT BREAKER ---
  {
    id: "TEST-DAEMON-13",
    category: "MAIN",
    group: "Resilience & Circuit Breaker",
    scenario: "Polling trong phiên liên tục (MORNING_CONTINUOUS)",
    expectation:
      "Tần suất đo được ổn định trong dải 1.0s ± 200ms, không làm nghẽn Event Loop",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-14",
    category: "SUB",
    group: "Resilience & Circuit Breaker",
    scenario: "Tự động tăng tần suất lấy dữ liệu lên 500ms khi bước vào khung giờ PRE_ATC_SETUP",
    expectation:
      "Chu kỳ rút ngắn chính xác xuống 500ms để kịp thời cập nhật lệnh mất cân bằng ATC",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-15",
    category: "MAIN",
    group: "Resilience & Circuit Breaker",
    scenario: "Thực hiện 2 request liên tiếp tới cùng một nguồn cung cấp dữ liệu (VCI)",
    expectation:
      "Bộ Rate-Limiter chèn độ trễ tối thiểu 250ms giữa 2 request để chống ban IP",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-16",
    category: "EDGE",
    group: "Resilience & Circuit Breaker",
    scenario: "Giả lập nguồn cấp dữ liệu ném lỗi HTTP 429 Too Many Requests 5 lần liên tiếp",
    expectation:
      "Circuit Breaker chuyển sang trạng thái OPEN, log lỗi an toàn, đọc dữ liệu từ cache DB",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-17",
    category: "SUB",
    group: "Resilience & Circuit Breaker",
    scenario: "Sau 60 giây ở trạng thái OPEN, request kế tiếp thành công",
    expectation:
      "Circuit Breaker tự động chuyển về HALF_OPEN rồi đóng lại CLOSED, khôi phục luồng live",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-18",
    category: "EDGE",
    group: "Resilience & Circuit Breaker",
    scenario: "Mất kết nối Internet toàn bộ (DNS failure / No Route to Host)",
    expectation:
      "Daemon tiếp tục ghi nhận heartbeat, cảnh báo lỗi mạng và tự phục hồi khi có mạng lại",
    status: "READY",
  },

  // --- ASYNCIO LOOP & DISPATCHER ---
  {
    id: "TEST-DAEMON-19",
    category: "MAIN",
    group: "Asyncio Loop & Dispatcher",
    scenario: "Dispatcher nhận tick mới từ Quote.intraday()",
    expectation:
      "Phân phối dữ liệu song song tới 3 Engine trong thời gian < 50ms",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-20",
    category: "SUB",
    group: "Asyncio Loop & Dispatcher",
    scenario: "Lượng tick đổ về dồn dập trong đợt ATC (> 500 ticks/giây)",
    expectation:
      "Hàng đợi asyncio.Queue đệm dữ liệu an toàn, không gây rò rỉ bộ nhớ (Memory Leak)",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-21",
    category: "EDGE",
    group: "Asyncio Loop & Dispatcher",
    scenario: "Khi nhận lệnh SIGTERM hoặc SIGINT tắt server Uvicorn",
    expectation:
      "Daemon hoàn tất vòng lặp hiện tại, hủy an toàn các tác vụ con và shutdown sạch sẽ",
    status: "READY",
  },

  // --- AUDIT & HEARTBEAT API ---
  {
    id: "TEST-DAEMON-22",
    category: "MAIN",
    group: "Audit & Heartbeat API",
    scenario: "Gọi API GET /api/v1/quant/daemon/status",
    expectation:
      "Trả về HTTP 200 kèm JSON chứa state, uptime_seconds, ticks_processed, circuit_breaker_status",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-23",
    category: "SUB",
    group: "Audit & Heartbeat API",
    scenario: "Admin gọi API POST /api/v1/quant/daemon/pause",
    expectation:
      "Daemon tạm dừng thu thập dữ liệu ngầm, heartbeat ghi nhận trạng thái PAUSED",
    status: "READY",
  },
  {
    id: "TEST-DAEMON-24",
    category: "EDGE",
    group: "Audit & Heartbeat API",
    scenario: "Kích hoạt thủ công 1 chu kỳ POST /api/v1/quant/daemon/trigger-cycle vào ban đêm",
    expectation:
      "Thực thi trọn vẹn 1 vòng lặp thử nghiệm và trả về kết quả JSON mà không đổi state hệ thống",
    status: "READY",
  },
];

const apiEndpoints = [
  {
    method: "GET",
    path: "/api/v1/quant/daemon/status",
    desc: "Lấy thông số nhịp tim Heartbeat, trạng thái phiên và bộ ngắt mạch của Daemon",
    auth: "JWT (CurrentUser)",
  },
  {
    method: "POST",
    path: "/api/v1/quant/daemon/pause",
    desc: "Tạm dừng tiến trình thu thập ngầm (Dành cho Admin gỡ lỗi / bảo trì)",
    auth: "JWT (Admin)",
  },
  {
    method: "POST",
    path: "/api/v1/quant/daemon/resume",
    desc: "Kích hoạt tiếp tục chu kỳ thu thập dữ liệu ngầm",
    auth: "JWT (Admin)",
  },
  {
    method: "POST",
    path: "/api/v1/quant/daemon/trigger-cycle",
    desc: "Kích hoạt thủ công 1 chu kỳ thu thập và tính toán (Manual Test)",
    auth: "JWT (Admin)",
  },
  {
    method: "GET",
    path: "/api/v1/quant/daemon/logs",
    desc: "Truy vấn lịch sử các chu kỳ chuyển trạng thái trong ngày",
    auth: "JWT (CurrentUser)",
  },
];

export function Phase3TRDPage() {
  const [copied, setCopied] = useState(false);
  const [testSearch, setTestSearch] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(phase3Markdown);
      setCopied(true);
      toast.success("Đã sao chép nội dung TRD Phase 3 vào clipboard!");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error("Không thể sao chép vào clipboard");
    }
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([phase3Markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "phase_3_specification.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Đang tải xuống file phase_3_specification.md");
  };

  const testGroups = [
    "ALL",
    "State Machine (Clock & Sessions)",
    "Resilience & Circuit Breaker",
    "Asyncio Loop & Dispatcher",
    "Audit & Heartbeat API",
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
            <Badge variant="default" className="bg-amber-600/90 text-xs">
              PHASE 3
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link to="/trd/phase-2">
                <Cpu className="h-4 w-4 text-emerald-500" />
                <span>Xem Phase 2</span>
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link to="/trd/phase-4">
                <Layers className="h-4 w-4 text-indigo-500" />
                <span>Xem Phase 4</span>
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
              className="gap-1.5 bg-amber-600 hover:bg-amber-700 text-white"
            >
              <Download className="h-4 w-4" />
              <span>Tải xuống .MD</span>
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500 border border-amber-500/20">
              <Clock className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                TRD Phase 3: Background Session Daemon (24/7 Loop)
              </h1>
              <p className="text-sm text-muted-foreground">
                Vòng lặp giám sát tự động bám sát chu kỳ phiên thực tế (08:30 Pre-ATO → 08:45 ATO → Liên tục → 14:15 Pre-ATC/ATC → 24/7 Phân tích qua đêm)
              </p>
            </div>
          </div>
        </div>

        {/* Master Rule Reminder Alert */}
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-500" />
            <div className="flex flex-col gap-1">
              <span className="font-semibold text-amber-600 dark:text-amber-400">
                Tuân Thủ Quy Chuẩn Master Rules Trong Session Daemon
              </span>
              <p className="text-muted-foreground leading-relaxed">
                Daemon vận hành 24/7 nhưng <strong>tuyệt đối chỉ thu thập dữ liệu, chạy mô hình dự báo và ghi nhận sổ nhật ký</strong>. Tuyệt đối không tích hợp webhook hay gọi broker API để đặt lệnh tiền thật. Tần suất lấy dữ liệu được phân tầng để bảo vệ IP khỏi cơ chế rate-limit.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Tabs Layout */}
      <Tabs defaultValue="overview" className="flex flex-col gap-6">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5 h-auto p-1 bg-muted/60">
          <TabsTrigger value="overview" className="gap-2 py-2">
            <Radio className="h-4 w-4 text-amber-500" />
            <span>Sơ Đồ State Machine</span>
          </TabsTrigger>
          <TabsTrigger value="resilience" className="gap-2 py-2">
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
            <span>Circuit Breaker & Polling</span>
          </TabsTrigger>
          <TabsTrigger value="blueprint" className="gap-2 py-2">
            <Server className="h-4 w-4 text-blue-500" />
            <span>Blueprint 6 Bước Dev</span>
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

        {/* TAB 1: OVERVIEW & FSM */}
        <TabsContent value="overview" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5 text-amber-500" />
                Vòng Đời 9 Trạng Thái Phiên Giao Dịch Việt Nam (FSM)
              </CardTitle>
              <CardDescription>
                Daemon tự động nhận biết trạng thái phiên theo thời gian thực (Asia/Ho_Chi_Minh) để điều chỉnh tác vụ
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="text-amber-500 border-amber-500/40">08:30 - 08:45</Badge>
                    <span className="text-xs font-mono text-muted-foreground">30s / poll</span>
                  </div>
                  <h4 className="font-semibold text-sm">PRE_ATO_SETUP</h4>
                  <p className="text-xs text-muted-foreground">Đồng bộ giá tham chiếu, tính Basis qua đêm giữa VN30F1M và VN30, cập nhật mốc FVG mới.</p>
                </div>

                <div className="border rounded-lg p-4 bg-amber-500/5 border-amber-500/30 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge className="bg-amber-600 text-white text-xs">08:45 - 09:00</Badge>
                    <span className="text-xs font-mono text-muted-foreground">1.0s / poll</span>
                  </div>
                  <h4 className="font-semibold text-sm">ATO_AUCTION</h4>
                  <p className="text-xs text-muted-foreground">Giám sát mở cửa phái sinh VN30F1M, đo lường Gap Severity, khởi tạo Engine 1.</p>
                </div>

                <div className="border rounded-lg p-4 bg-emerald-500/5 border-emerald-500/30 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge className="bg-emerald-600 text-white text-xs">09:00 - 11:30</Badge>
                    <span className="text-xs font-mono text-muted-foreground">1.0s / poll</span>
                  </div>
                  <h4 className="font-semibold text-sm">MORNING_CONTINUOUS</h4>
                  <p className="text-xs text-muted-foreground">Khớp lệnh liên tục: tính Orderflow Delta, VWAP, quét nến 1m, kiểm tra StopLoss / TakeProfit.</p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline">11:30 - 13:00</Badge>
                    <span className="text-xs font-mono text-muted-foreground">60s / poll</span>
                  </div>
                  <h4 className="font-semibold text-sm">MIDDAY_INTERMISSION</h4>
                  <p className="text-xs text-muted-foreground">Nghỉ trưa: tái tính toán tương quan ngành, dự phóng áp lực hàng T+2 cho phiên chiều.</p>
                </div>

                <div className="border rounded-lg p-4 bg-emerald-500/5 border-emerald-500/30 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge className="bg-emerald-600 text-white text-xs">13:00 - 14:15</Badge>
                    <span className="text-xs font-mono text-muted-foreground">1.0s / poll</span>
                  </div>
                  <h4 className="font-semibold text-sm">AFTERNOON_CONTINUOUS</h4>
                  <p className="text-xs text-muted-foreground">Hàng T-2 về tài khoản lúc 13:00: theo dõi chỉ số t_plus_2_pressure_index, quét quét thanh khoản.</p>
                </div>

                <div className="border rounded-lg p-4 bg-purple-500/5 border-purple-500/30 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge className="bg-purple-600 text-white text-xs">14:15 - 14:30</Badge>
                    <span className="text-xs font-mono text-muted-foreground">0.5s / poll</span>
                  </div>
                  <h4 className="font-semibold text-sm">PRE_ATC_SETUP</h4>
                  <p className="text-xs text-muted-foreground">Kích hoạt Engine dự báo đóng cửa ATC, tính khối lượng mất cân bằng rổ VN30.</p>
                </div>

                <div className="border rounded-lg p-4 bg-rose-500/5 border-rose-500/30 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge className="bg-rose-600 text-white text-xs">14:30 - 14:45</Badge>
                    <span className="text-xs font-mono text-muted-foreground">0.5s / poll</span>
                  </div>
                  <h4 className="font-semibold text-sm">ATC_AUCTION</h4>
                  <p className="text-xs text-muted-foreground">Đợt khớp lệnh đóng cửa: ghi nhận giá khớp ATC thực tế, khớp các lệnh ảo phiên ATC.</p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline">14:45 - 15:30</Badge>
                    <span className="text-xs font-mono text-muted-foreground">60s / poll</span>
                  </div>
                  <h4 className="font-semibold text-sm">POST_MARKET_EVAL</h4>
                  <p className="text-xs text-muted-foreground">Đối soát toàn bộ tín hiệu trong ngày ghi sổ ForecastJournal, tính Brier Score, MAE.</p>
                </div>

                <div className="border rounded-lg p-4 bg-blue-500/5 border-blue-500/30 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Badge className="bg-blue-600 text-white text-xs">15:30 - 08:30 (T+1)</Badge>
                    <span className="text-xs font-mono text-muted-foreground">5 - 15 phút</span>
                  </div>
                  <h4 className="font-semibold text-sm">OVERNIGHT_SIMULATION</h4>
                  <p className="text-xs text-muted-foreground">Chạy 24/7 mô phỏng Monte Carlo 10k kịch bản T+1, lọc cổ phiếu Alpha Tuần/Tháng/Quý.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: RESILIENCE & CIRCUIT BREAKER */}
        <TabsContent value="resilience" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-emerald-500" />
                Cơ Chế Bảo Vệ Chống Khóa IP & Circuit Breaker
              </CardTitle>
              <CardDescription>
                Đảm bảo hệ thống không bị nhà mạng hay nhà cung cấp dữ liệu chặn truy cập khi có sự cố
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6 flex flex-col gap-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4 bg-emerald-500/5 border-emerald-500/30">
                  <Badge className="bg-emerald-600 text-white mb-2">CLOSED (Bình thường)</Badge>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Mọi request được gửi trực tiếp tới các adapter vnstock (VCI/TCBS). Mỗi request cách nhau tối thiểu 250ms.
                  </p>
                </div>
                <div className="border rounded-lg p-4 bg-rose-500/5 border-rose-500/30">
                  <Badge className="bg-rose-600 text-white mb-2">OPEN (Ngắt mạch)</Badge>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Nếu thất bại liên tiếp &ge; 5 lần: ngắt mạch trong 60 giây, hoàn toàn không gọi API bên ngoài, trả về dữ liệu cache DB.
                  </p>
                </div>
                <div className="border rounded-lg p-4 bg-amber-500/5 border-amber-500/30">
                  <Badge className="bg-amber-600 text-white mb-2">HALF-OPEN (Thử nghiệm)</Badge>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Sau 60s, cho phép 1 request thử nghiệm. Nếu thành công chuyển về CLOSED, nếu thất bại tiếp tục ngắt mạch 60s.
                  </p>
                </div>
              </div>

              <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                <span className="font-semibold text-sm">Công thức tính thời gian chờ Exponential Backoff kèm Jitter:</span>
                <pre className="p-3 bg-muted rounded font-mono text-xs overflow-x-auto text-amber-500">
                  t_sleep = min(10.0, 0.5 * (2 ** retry_count) + random(0, 0.5))
                </pre>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: BLUEPRINT */}
        <TabsContent value="blueprint" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Server className="h-5 w-5 text-blue-500" />
                Checklist 6 Bước Tự Code Backend Session Daemon
              </CardTitle>
              <CardDescription>
                Lập trình viên chỉ cần làm tuần tự theo 6 bước này để hoàn thiện Phase 3
              </CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <div className="flex flex-col gap-4">
                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-500/10 text-blue-500 font-bold text-xs flex-shrink-0">1</div>
                  <div>
                    <h4 className="font-semibold text-sm">Tạo module market_clock.py</h4>
                    <p className="text-xs text-muted-foreground">Khai báo Enum 9 trạng thái phiên và viết hàm get_current_session_state() theo múi giờ Asia/Ho_Chi_Minh.</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-500/10 text-blue-500 font-bold text-xs flex-shrink-0">2</div>
                  <div>
                    <h4 className="font-semibold text-sm">Tạo module circuit_breaker.py</h4>
                    <p className="text-xs text-muted-foreground">Xử lý 3 trạng thái CLOSED, OPEN, HALF_OPEN; tự động ngắt khi lỗi mạng liên tiếp 5 lần.</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-500/10 text-blue-500 font-bold text-xs flex-shrink-0">3</div>
                  <div>
                    <h4 className="font-semibold text-sm">Tạo module poller.py lấy dữ liệu</h4>
                    <p className="text-xs text-muted-foreground">Thu thập tick phái sinh Quote.intraday() và nến cơ sở Quote.history() có bọc Rate-Limiter.</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-500/10 text-blue-500 font-bold text-xs flex-shrink-0">4</div>
                  <div>
                    <h4 className="font-semibold text-sm">Tạo module dispatcher.py</h4>
                    <p className="text-xs text-muted-foreground">Phân phối dữ liệu vào Engine 1, 2, 3 và đẩy tín hiệu sang ForecastJournal.</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start border-b pb-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-500/10 text-blue-500 font-bold text-xs flex-shrink-0">5</div>
                  <div>
                    <h4 className="font-semibold text-sm">Viết vòng lặp Asyncio chính trong session_daemon.py</h4>
                    <p className="text-xs text-muted-foreground">Tạo task asyncio.create_task() với chu kỳ sleep động; bắt tín hiệu SIGTERM/SIGINT để Graceful Shutdown.</p>
                  </div>
                </div>

                <div className="flex gap-4 items-start">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-500/10 text-blue-500 font-bold text-xs flex-shrink-0">6</div>
                  <div>
                    <h4 className="font-semibold text-sm">Tích hợp vào FastAPI lifespan</h4>
                    <p className="text-xs text-muted-foreground">Khởi động Daemon trong @asynccontextmanager lifespan tại backend/app/main.py.</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* API Endpoints */}
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Terminal className="h-5 w-5 text-indigo-500" />
                Danh Sách API Endpoints Của Daemon
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
              <CardDescription>
                Các ca kiểm thử tự động đảm bảo Daemon chạy chuẩn xác 24/7
              </CardDescription>
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
              Toàn văn tài liệu đặc tả kỹ thuật phase_3_specification.md
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
            {phase3Markdown}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default Phase3TRDPage;
