import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  Building2,
  Calendar,
  Globe,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { type FinancialReportItem, StockService } from "@/client";

export const Route = createFileRoute("/_layout/stock/$symbol")({
  component: StockDetail,
  head: ({ params }) => ({
    meta: [{ title: `${params.symbol} - Stock Detail` }],
  }),
});

function StockDetail() {
  const { symbol } = Route.useParams();
  const [dateRange, setDateRange] = useState("3M");

  const getStartDate = (range: string) => {
    const now = new Date();
    switch (range) {
      case "1W":
        now.setDate(now.getDate() - 7);
        break;
      case "1M":
        now.setMonth(now.getMonth() - 1);
        break;
      case "3M":
        now.setMonth(now.getMonth() - 3);
        break;
      case "6M":
        now.setMonth(now.getMonth() - 6);
        break;
      case "1Y":
        now.setFullYear(now.getFullYear() - 1);
        break;
      case "3Y":
        now.setFullYear(now.getFullYear() - 3);
        break;
      default:
        now.setMonth(now.getMonth() - 3);
    }
    return now.toISOString().split("T")[0];
  };

  const { data: priceData, isLoading: priceLoading } = useQuery({
    queryKey: ["stock-price", symbol, dateRange],
    queryFn: () =>
      StockService.getDailyPrice({
        path: { symbol },
        query: {
          start: getStartDate(dateRange),
          end: new Date().toISOString().split("T")[0],
        },
      }),
    staleTime: 60_000,
  });

  const { data: overview } = useQuery({
    queryKey: ["stock-overview", symbol],
    queryFn: () => StockService.getCompanyOverview({ path: { symbol } }),
    staleTime: 86_400_000,
  });

  const { data: financials } = useQuery({
    queryKey: ["stock-financials", symbol],
    queryFn: () =>
      StockService.getFinancials({
        path: { symbol },
        query: { report_type: "income_statement", period: "quarterly" },
      }),
    staleTime: 86_400_000,
  });

  const ohlcvData = priceData?.data ?? [];
  const lastPrice =
    ohlcvData.length > 0 ? ohlcvData[ohlcvData.length - 1] : null;

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div className="flex items-center gap-4">
        <Link to="/stock">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <TrendingUp className="h-6 w-6" />
            {symbol}
          </h1>
          <p className="text-muted-foreground">
            {overview?.company_name || "Đang tải..."}
          </p>
        </div>
        {lastPrice && (
          <div className="ml-auto text-right">
            <p className="text-3xl font-bold tabular-nums">
              {lastPrice.close.toLocaleString("vi-VN")}
            </p>
            <p className="text-sm text-muted-foreground">
              {lastPrice.trading_date}
            </p>
          </div>
        )}
      </div>

      {/* Price Chart */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Biểu đồ giá</CardTitle>
            <div className="flex gap-1">
              {["1W", "1M", "3M", "6M", "1Y", "3Y"].map((range) => (
                <Button
                  key={range}
                  variant={dateRange === range ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDateRange(range)}
                >
                  {range}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {priceLoading ? (
            <div className="flex items-center justify-center h-[400px]">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : ohlcvData.length === 0 ? (
            <div className="flex items-center justify-center h-[400px] text-muted-foreground">
              Không có dữ liệu cho khoảng thời gian này
            </div>
          ) : (
            <PriceChart data={ohlcvData} />
          )}
        </CardContent>
      </Card>

      {/* Tabs: Overview + Financials */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Tổng quan</TabsTrigger>
          <TabsTrigger value="financials">Tài chính</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          {overview ? (
            <div className="grid gap-4 md:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Building2 className="h-4 w-4" />
                    Thông tin công ty
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <InfoRow label="Tên" value={overview.company_name} />
                  <InfoRow label="Tên ngắn" value={overview.short_name} />
                  <InfoRow label="Ngành" value={overview.industry_name} />
                  <InfoRow label="Ngày niêm yết" value={overview.listed_date} />
                  {overview.website && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Website</span>
                      <a
                        href={overview.website}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline flex items-center gap-1"
                      >
                        <Globe className="h-3 w-3" />
                        {overview.website}
                      </a>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Calendar className="h-4 w-4" />
                    Chỉ số tài chính
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <InfoRow
                    label="Vốn hóa"
                    value={
                      overview.market_cap
                        ? `${(overview.market_cap / 1e9).toFixed(1)} tỷ VND`
                        : undefined
                    }
                  />
                  <InfoRow
                    label="Vốn điều lệ"
                    value={
                      overview.charter_capital
                        ? `${(overview.charter_capital / 1e9).toFixed(1)} tỷ VND`
                        : undefined
                    }
                  />
                  <InfoRow
                    label="KL lưu hành"
                    value={
                      overview.outstanding_shares
                        ? `${(overview.outstanding_shares / 1e6).toFixed(1)}M CP`
                        : undefined
                    }
                  />
                </CardContent>
              </Card>

              {overview.description && (
                <Card className="md:col-span-2">
                  <CardHeader>
                    <CardTitle className="text-base">Mô tả</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {overview.description}
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}
        </TabsContent>

        <TabsContent value="financials" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Báo cáo tài chính</CardTitle>
              <CardDescription>Kết quả kinh doanh theo quý</CardDescription>
            </CardHeader>
            <CardContent>
              {financials && financials.data.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Kỳ</TableHead>
                      <TableHead>Năm</TableHead>
                      <TableHead>Quý</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {financials.data
                      .slice(0, 12)
                      .map((r: FinancialReportItem, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell className="font-mono">
                            {r.report_type}
                          </TableCell>
                          <TableCell>{r.year}</TableCell>
                          <TableCell>{r.quarter ?? "Cả năm"}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  Chưa có dữ liệu tài chính
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

/* --- Sub-components --- */

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value || "—"}</span>
    </div>
  );
}

/**
 * Simple line chart using canvas.
 * Can be replaced with lightweight-charts when installed.
 */
function PriceChart({
  data,
}: {
  data: Array<{
    trading_date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const padding = { top: 20, right: 60, bottom: 30, left: 10 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    const closes = data.map((d) => d.close);
    const minPrice = Math.min(...closes) * 0.998;
    const maxPrice = Math.max(...closes) * 1.002;
    const priceRange = maxPrice - minPrice;

    // Background
    ctx.fillStyle =
      getComputedStyle(canvas).getPropertyValue("--background") || "#fff";
    ctx.fillRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = "#e5e7eb";
    ctx.lineWidth = 0.5;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + (i / gridLines) * chartH;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();

      // Price labels
      const price = maxPrice - (i / gridLines) * priceRange;
      ctx.fillStyle = "#6b7280";
      ctx.font = "11px system-ui";
      ctx.textAlign = "left";
      ctx.fillText(price.toFixed(0), w - padding.right + 8, y + 4);
    }

    // Gradient fill
    const gradient = ctx.createLinearGradient(
      0,
      padding.top,
      0,
      h - padding.bottom,
    );
    gradient.addColorStop(0, "rgba(59, 130, 246, 0.15)");
    gradient.addColorStop(1, "rgba(59, 130, 246, 0)");

    ctx.beginPath();
    data.forEach((d, i) => {
      const x = padding.left + (i / (data.length - 1)) * chartW;
      const y = padding.top + ((maxPrice - d.close) / priceRange) * chartH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    // Fill
    const lastX = padding.left + chartW;
    ctx.lineTo(lastX, h - padding.bottom);
    ctx.lineTo(padding.left, h - padding.bottom);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line
    ctx.beginPath();
    data.forEach((d, i) => {
      const x = padding.left + (i / (data.length - 1)) * chartW;
      const y = padding.top + ((maxPrice - d.close) / priceRange) * chartH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Date labels
    ctx.fillStyle = "#6b7280";
    ctx.font = "10px system-ui";
    ctx.textAlign = "center";
    const labelCount = Math.min(6, data.length);
    for (let i = 0; i < labelCount; i++) {
      const idx = Math.floor((i / (labelCount - 1)) * (data.length - 1));
      const x = padding.left + (idx / (data.length - 1)) * chartW;
      const dateStr = data[idx].trading_date.slice(5); // MM-DD
      ctx.fillText(dateStr, x, h - 8);
    }
  }, [data]);

  return (
    <canvas ref={canvasRef} className="w-full" style={{ height: "400px" }} />
  );
}
