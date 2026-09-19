import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Check,
  CheckCircle2,
  Copy,
  Cpu,
  Download,
  FileCode,
  History,
  Layers,
  Scale,
  Search,
  ShieldAlert,
  Sparkles,
  Terminal,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
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
import { phase5Markdown } from "./-phase5SpecContent";

export const Route = createFileRoute("/_layout/trd/phase-5")({
  component: Phase5TRDPage,
  head: () => ({
    meta: [
      {
        title: "TRD Phase 5: Forecast Journal & Self-Learning - vnstock",
      },
      {
        name: "description",
        content:
          "Technical Requirements Document (TRD), Immutable Forecast Journal Ledger, Brier Score / MAE Automated Scoring & Governed Recalibration Loop for Vnstock.",
      },
    ],
  }),
});

interface TestCase {
  id: string;
  category: "MAIN" | "SUB" | "EDGE";
  group:
    | "Forecast Ledger & Immutability"
    | "Automated Scoring (Post-Market)"
    | "Recalibration & Anti-Overfit"
    | "Model Versioning & Rollback";
  scenario: string;
  expectation: string;
  status: "READY" | "SPECIFIED";
}

const testCases: TestCase[] = [
  // --- FORECAST LEDGER & IMMUTABILITY ---
  {
    id: "TEST-JOURNAL-01",
    category: "MAIN",
    group: "Forecast Ledger & Immutability",
    scenario: "Ensemble sinh tín hiệu Long VN30F1M hoặc dự báo ATC",
    expectation:
      "Tự động tạo 1 row trong ForecastJournal với status = PENDING, predicted_at UTC, snapshot model_version và engine_weights",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-02",
    category: "MAIN",
    group: "Forecast Ledger & Immutability",
    scenario: "Kiểm tra quan hệ khóa ngoại (Foreign Key) giữa ForecastJournal và ModelVersionSnapshot",
    expectation:
      "Bản ghi dự báo liên kết chính xác với phiên bản mô hình đang active tại thời điểm phát tín hiệu",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-03",
    category: "SUB",
    group: "Forecast Ledger & Immutability",
    scenario: "Truy vấn lọc ForecastJournal theo horizon (ATC, T+1, WEEKLY, MONTHLY) và trạng thái PENDING/RESOLVED",
    expectation:
      "Trả về đúng tập bản ghi theo bộ lọc, hỗ trợ phân trang chuẩn xác",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-04",
    category: "EDGE",
    group: "Forecast Ledger & Immutability",
    scenario: "Thử gửi lệnh UPDATE trực tiếp lên các trường dự báo (predicted_target_price, predicted_direction, predicted_at)",
    expectation:
      "Hệ thống từ chối cập nhật (HTTP 403 / Database Rule), đảm bảo tính bất biến 100% của sổ nhật ký",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-05",
    category: "EDGE",
    group: "Forecast Ledger & Immutability",
    scenario: "Trùng lặp tín hiệu trong cùng 1 tick hoặc 1 phút khảo sát",
    expectation:
      "Cơ chế Idempotency Key ngăn chặn sinh nhiều bản ghi trùng lặp cho cùng một mốc thời gian",
    status: "READY",
  },

  // --- AUTOMATED SCORING (POST-MARKET) ---
  {
    id: "TEST-JOURNAL-06",
    category: "MAIN",
    group: "Automated Scoring (Post-Market)",
    scenario: "Chạy bộ chấm điểm ATC: Dự báo Tăng (P=0.8), thực tế giá Tăng",
    expectation:
      "directional_correct = True, brier_score = (0.8 - 1.0)^2 = 0.04 chuẩn xác",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-07",
    category: "MAIN",
    group: "Automated Scoring (Post-Market)",
    scenario: "Chạy bộ chấm điểm ATC: Dự báo Tăng (P=0.7), thực tế giá Giảm",
    expectation:
      "directional_correct = False, brier_score = (0.7 - 0.0)^2 = 0.49 chuẩn xác",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-08",
    category: "MAIN",
    group: "Automated Scoring (Post-Market)",
    scenario: "Tính toán sai số tuyệt đối MAE cho dự báo giá 1310 khi thực tế giá đóng cửa là 1305",
    expectation:
      "absolute_error = abs(1310 - 1305) = 5.0 điểm",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-09",
    category: "SUB",
    group: "Automated Scoring (Post-Market)",
    scenario: "Dự báo hòa hoặc giá đóng cửa không đổi (biên độ giá |delta| < 0.2 điểm)",
    expectation:
      "Xác định ngưỡng threshold phân định rõ ràng (neutral), không phạt sai lệch phương hướng",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-10",
    category: "SUB",
    group: "Automated Scoring (Post-Market)",
    scenario: "Tính toán tổng hợp KPI 30 ngày (Directional Accuracy, Mean Brier Score, RMSE) trên 100+ bản ghi resolved",
    expectation:
      "Kết quả trả về khớp chính xác công thức thống kê, sẵn sàng hiển thị trên biểu đồ radar",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-11",
    category: "EDGE",
    group: "Automated Scoring (Post-Market)",
    scenario: "Phiên giao dịch bị hoãn hoặc sự cố kết nối sàn HSX dẫn đến thiếu giá đóng cửa thực tế",
    expectation:
      "Bản ghi giữ trạng thái PENDING_MANUAL_REVIEW, không tự ý tính nhầm điểm 0 hay sai lệch thống kê",
    status: "READY",
  },

  // --- RECALIBRATION & ANTI-OVERFIT ---
  {
    id: "TEST-JOURNAL-12",
    category: "MAIN",
    group: "Recalibration & Anti-Overfit",
    scenario: "Chạy thuật toán Softmax Recalibration trên chu kỳ 30 ngày gần nhất",
    expectation:
      "Trọng số mới w_new của 3 Engine luôn có tổng bằng 1.0 (100%)",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-13",
    category: "MAIN",
    group: "Recalibration & Anti-Overfit",
    scenario: "Trọng số của Engine 1 sau tính toán nằm trong dải ràng buộc kỹ thuật [0.15, 0.60]",
    expectation:
      "Đảm bảo không engine nào bị triệt tiêu hoàn toàn (weight collapse), duy trì tính đa dạng mô hình",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-14",
    category: "SUB",
    group: "Recalibration & Anti-Overfit",
    scenario: "Đề xuất trọng số mới tính ra chênh lệch +12% so với trọng số cũ",
    expectation:
      "Thuật toán clip kẹp biên độ dịch chuyển lại ở mức tối đa +5.0%, chống hiện tượng giật cục",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-15",
    category: "SUB",
    group: "Recalibration & Anti-Overfit",
    scenario: "Sinh phiên bản trọng số mới qua tác vụ định kỳ ban đêm",
    expectation:
      "Bản ghi ModelVersionSnapshot được lưu với is_active = False, chưa tác động luồng live",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-16",
    category: "EDGE",
    group: "Recalibration & Anti-Overfit",
    scenario: "Trong 30 ngày có chuỗi ngoại lai bất thường (Flash Crash -100 điểm)",
    expectation:
      "Thuật toán Winsorization cắt tỉa outlier để không làm méo mó trọng số dài hạn",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-17",
    category: "EDGE",
    group: "Recalibration & Anti-Overfit",
    scenario: "Kiểm định Walk-Forward Validation: Trọng số mới có Brier Score Out-of-Sample tệ hơn trọng số cũ",
    expectation:
      "Hệ thống tự động từ chối đề xuất recalibration, giữ nguyên phiên bản tham số hiện hành",
    status: "READY",
  },

  // --- MODEL VERSIONING & ROLLBACK ---
  {
    id: "TEST-JOURNAL-18",
    category: "MAIN",
    group: "Model Versioning & Rollback",
    scenario: "Admin gọi API POST /promote phiên bản v1.1.0",
    expectation:
      "Phiên bản cũ v1.0.0 chuyển is_active = False, v1.1.0 chuyển is_active = True an toàn",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-19",
    category: "MAIN",
    group: "Model Versioning & Rollback",
    scenario: "Gọi API POST /rollback về phiên bản v1.0.0 trước đó",
    expectation:
      "Hệ thống đổi cờ is_active tức thì, luồng live nhận lại trọng số cũ trong 1 nốt nhạc",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-20",
    category: "SUB",
    group: "Model Versioning & Rollback",
    scenario: "Truy vấn GET /api/v1/quant/versions",
    expectation:
      "Trả về danh sách đầy đủ lịch sử tất cả version kèm engine_weights snapshot và người phê duyệt",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-21",
    category: "EDGE",
    group: "Model Versioning & Rollback",
    scenario: "Cố gắng xóa (DELETE) một bản ghi ModelVersionSnapshot đang active",
    expectation:
      "Bị từ chối với HTTP 400: Active version cannot be deleted",
    status: "READY",
  },
  {
    id: "TEST-JOURNAL-22",
    category: "EDGE",
    group: "Model Versioning & Rollback",
    scenario: "Cố gắng rollback về một version_tag không tồn tại trong DB",
    expectation:
      "Bị từ chối an toàn với HTTP 404 Not Found kèm thông báo lỗi rõ ràng",
    status: "READY",
  },
];

const apiEndpoints = [
  {
    method: "GET",
    path: "/api/v1/quant/journal/history",
    desc: "Truy vấn toàn bộ sổ nhật ký dự báo kèm bộ lọc symbol, horizon, status",
    auth: "JWT (CurrentUser)",
  },
  {
    method: "GET",
    path: "/api/v1/quant/journal/metrics",
    desc: "Lấy báo cáo tổng hợp: Directional Accuracy (Winrate), Brier Score 30 ngày",
    auth: "JWT (CurrentUser)",
  },
  {
    method: "GET",
    path: "/api/v1/quant/versions",
    desc: "Xem danh sách các phiên bản mô hình, snapshot tham số và trạng thái active",
    auth: "JWT (CurrentUser)",
  },
  {
    method: "POST",
    path: "/api/v1/quant/versions/{version_tag}/promote",
    desc: "Phê duyệt áp dụng phiên bản trọng số mới vào luồng tính toán thực tế",
    auth: "JWT (Admin)",
  },
  {
    method: "POST",
    path: "/api/v1/quant/versions/{version_tag}/rollback",
    desc: "Khôi phục 1-click về phiên bản tham số trước đó (Rollback an toàn)",
    auth: "JWT (Admin)",
  },
];

export function Phase5TRDPage() {
  const [copied, setCopied] = useState(false);
  const [testSearch, setTestSearch] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(phase5Markdown);
      setCopied(true);
      toast.success("Đã sao chép nội dung TRD Phase 5 vào clipboard!");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error("Không thể sao chép vào clipboard");
    }
  };

  const handleDownloadMarkdown = () => {
    const blob = new Blob([phase5Markdown], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "phase_5_specification.md";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Đang tải xuống file phase_5_specification.md");
  };

  const testGroups = [
    "ALL",
    "Forecast Ledger & Immutability",
    "Automated Scoring (Post-Market)",
    "Recalibration & Anti-Overfit",
    "Model Versioning & Rollback",
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
            <Badge variant="default" className="bg-purple-600/90 text-xs">
              PHASE 5
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link to="/trd/phase-4">
                <Layers className="h-4 w-4 text-indigo-500" />
                <span>Xem Phase 4</span>
              </Link>
            </Button>
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link to="/trd/phase-6">
                <Cpu className="h-4 w-4 text-cyan-500" />
                <span>Xem Phase 6</span>
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
              className="gap-1.5 bg-purple-600 hover:bg-purple-700 text-white"
            >
              <Download className="h-4 w-4" />
              <span>Tải xuống .MD</span>
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10 text-purple-500 border border-purple-500/20">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                TRD Phase 5: Sổ Nhật Ký Dự Báo & Vòng Lặp Tự Học Có Kiểm Soát
              </h1>
              <p className="text-sm text-muted-foreground">
                Lưu vết 100% tín hiệu, tự động chấm điểm sai số sau phiên và cơ chế đề xuất hiệu chuẩn trọng số engine có kiểm soát (rollback versioning)
              </p>
            </div>
          </div>
        </div>

        {/* Master Rule Reminder Alert */}
        <div className="rounded-lg border border-purple-500/30 bg-purple-500/5 p-4 text-sm">
          <div className="flex items-start gap-3">
            <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-purple-500" />
            <div className="flex flex-col gap-1">
              <span className="font-semibold text-purple-600 dark:text-purple-400">
                Tuân Thủ Master Rule 3: Forecast Auditability & Governed Learning
              </span>
              <p className="text-muted-foreground leading-relaxed">
                Mọi dự báo đều bất biến và lưu tại thời điểm phát sinh (<code>predicted_at</code>), loại bỏ 100% Look-Ahead Bias. Vòng lặp tự học chỉ điều chỉnh <strong>trọng số Ensemble</strong>, tuyệt đối không tự sửa code logic. Cần có sự phê duyệt của con người trước khi áp dụng trọng số mới.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Tabs Layout */}
      <Tabs defaultValue="architecture" className="flex flex-col gap-6">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-5 h-auto p-1 bg-muted/60">
          <TabsTrigger value="architecture" className="gap-2 py-2">
            <Layers className="h-4 w-4 text-purple-500" />
            <span>Kiến Trúc 2 Tầng</span>
          </TabsTrigger>
          <TabsTrigger value="scoring" className="gap-2 py-2">
            <Scale className="h-4 w-4 text-amber-500" />
            <span>Công Thức Chấm Điểm</span>
          </TabsTrigger>
          <TabsTrigger value="recalibration" className="gap-2 py-2">
            <Sparkles className="h-4 w-4 text-emerald-500" />
            <span>Hiệu Chuẩn Softmax</span>
          </TabsTrigger>
          <TabsTrigger value="tests" className="gap-2 py-2">
            <CheckCircle2 className="h-4 w-4 text-blue-500" />
            <span>Ma Trận Test ({testCases.length})</span>
          </TabsTrigger>
          <TabsTrigger value="markdown" className="gap-2 py-2">
            <FileCode className="h-4 w-4 text-cyan-500" />
            <span>Tài Liệu Raw MD</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: ARCHITECTURE */}
        <TabsContent value="architecture" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <History className="h-5 w-5 text-purple-500" />
                Kiến Trúc 2 Tầng: Ghi Sổ (Layer A) & Hiệu Chuẩn (Layer B)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="border rounded-lg p-5 bg-muted/10 flex flex-col gap-3">
                  <Badge className="bg-purple-600 text-white w-fit text-xs">TẦNG A: RECORD & MEASURE</Badge>
                  <h4 className="font-semibold text-base">Bắt Buộc & Thường Trực 100%</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Mỗi khi bộ Ensemble sinh tín hiệu, lập tức ghi 1 bản ghi vào bảng <code>ForecastJournal</code> với trạng thái <code>PENDING</code>. Khi phiên kết thúc, worker tự động lấy giá thực tế để tính Directional Accuracy, Brier Score và MAE.
                  </p>
                </div>

                <div className="border rounded-lg p-5 bg-purple-500/5 border-purple-500/30 flex flex-col gap-3">
                  <Badge className="bg-indigo-600 text-white w-fit text-xs">TẦNG B: GOVERNED RECALIBRATION</Badge>
                  <h4 className="font-semibold text-base">Có Kiểm Soát & Khôi Phục Được</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Dựa trên hiệu năng lăn 30 ngày, thuật toán tự động tính toán trọng số tối ưu mới $w_1, w_2, w_3$. Rào chắn kẹp biên độ dịch chuyển &le; 5% giúp chống hiện tượng Overfitting. Cần Admin bấm duyệt hoặc bấm Rollback khôi phục trong 1 giây.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: SCORING FORMULAS */}
        <TabsContent value="scoring" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Scale className="h-5 w-5 text-amber-500" />
                Công Thức Toán Học Chấm Điểm Sai Số Sau Phiên
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex flex-col gap-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4 bg-muted/10">
                  <h4 className="font-semibold text-sm mb-1">Directional Accuracy (DA)</h4>
                  <p className="text-xs text-muted-foreground">Tỷ lệ % dự đoán đúng hướng tăng / giảm của thị trường:</p>
                  <pre className="p-2 bg-muted rounded font-mono text-xs mt-2 text-emerald-600">
                    DA = Sum(sign(y_hat) == sign(y)) / N
                  </pre>
                </div>

                <div className="border rounded-lg p-4 bg-muted/10">
                  <h4 className="font-semibold text-sm mb-1">Brier Score (Xác Suất)</h4>
                  <p className="text-xs text-muted-foreground">Độ lệch bình phương xác suất so với kết quả thực tế (0 hoặc 1):</p>
                  <pre className="p-2 bg-muted rounded font-mono text-xs mt-2 text-amber-600">
                    BS = Sum((p_i - o_i)^2) / N
                  </pre>
                  <p className="text-[11px] text-muted-foreground mt-1">Càng gần 0.0 càng hoàn hảo (&lt; 0.25 là có ý nghĩa thống kê).</p>
                </div>

                <div className="border rounded-lg p-4 bg-muted/10">
                  <h4 className="font-semibold text-sm mb-1">Sai Số Giá (MAE / RMSE)</h4>
                  <p className="text-xs text-muted-foreground">Độ lệch tuyệt đối giữa mức giá mục tiêu và giá khớp ATC thực tế:</p>
                  <pre className="p-2 bg-muted rounded font-mono text-xs mt-2 text-purple-600">
                    MAE = Sum(|P_pred - P_actual|) / N
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: RECALIBRATION */}
        <TabsContent value="recalibration" className="flex flex-col gap-6 m-0">
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-emerald-500" />
                Thuật Toán Softmax Hiệu Chuẩn Trọng Số Engine
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 flex flex-col gap-4">
              <div className="border rounded-lg p-4 bg-muted/10 flex flex-col gap-2">
                <span className="font-semibold text-sm">Điểm hiệu năng tổng hợp Sk và Softmax Rebalancing:</span>
                <pre className="p-3 bg-muted rounded font-mono text-xs overflow-x-auto text-emerald-600">
                  S_k = alpha * DA_k + (1 - alpha) * (1 - BS_k)
                  w_k* = exp(S_k / tau) / Sum(exp(S_j / tau))
                </pre>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="border rounded-lg p-4 bg-muted/10">
                  <h4 className="font-semibold text-sm mb-1">Giới hạn dịch chuyển (Max Weight Shift)</h4>
                  <p className="text-xs text-muted-foreground">
                    Trọng số không được thay đổi quá <strong>&plusmn; 5.0%</strong> trong một chu kỳ hiệu chuẩn, ngăn chặn hiện tượng Overfitting trên chuỗi ngày nhiễu ngẫu nhiên.
                  </p>
                </div>
                <div className="border rounded-lg p-4 bg-muted/10">
                  <h4 className="font-semibold text-sm mb-1">Ngưỡng biên an toàn (Weight Bounds)</h4>
                  <p className="text-xs text-muted-foreground">
                    Mọi trọng số đều nằm trong khoảng <strong>[0.15, 0.60]</strong>, đảm bảo không triệt tiêu bất kỳ Engine phân tích nào về 0.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* API Endpoints */}
          <Card className="border shadow-sm">
            <CardHeader className="border-b bg-muted/20">
              <CardTitle className="text-lg flex items-center gap-2">
                <Terminal className="h-5 w-5 text-purple-500" />
                Danh Sách API Endpoints Quản Trị & Rollback
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
                <CheckCircle2 className="h-5 w-5 text-blue-500" />
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
              Toàn văn tài liệu đặc tả kỹ thuật phase_5_specification.md
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
            {phase5Markdown}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default Phase5TRDPage;
