import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  RefreshCw,
  Search,
} from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { type StockSymbolItem, StockService } from "@/client"

export const Route = createFileRoute("/_layout/stock")({
  component: StockMarket,
  head: () => ({
    meta: [
      {
        title: "Stock Market - vnstock",
      },
    ],
  }),
})

function StockMarket() {
  const [search, setSearch] = useState("")
  const [exchange, setExchange] = useState<string | undefined>(undefined)
  const [page, setPage] = useState(0)
  const limit = 50

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["stock-symbols", search, exchange, page],
    queryFn: () =>
      StockService.listSymbols({
        query: {
          skip: page * limit,
          limit,
          search: search || undefined,
          exchange: exchange === "all" ? undefined : exchange,
        },
      }),
    staleTime: 60_000,
  })

  const symbols = data?.data ?? []
  const total = data?.count ?? 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Stock Market</h1>
          <p className="text-muted-foreground">
            Dữ liệu chứng khoán Việt Nam — {total} mã
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Tìm mã CK hoặc tên công ty..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(0)
            }}
            className="pl-10"
          />
        </div>
        <Select
          value={exchange ?? "all"}
          onValueChange={(v) => {
            setExchange(v === "all" ? undefined : v)
            setPage(0)
          }}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Sàn" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tất cả</SelectItem>
            <SelectItem value="HOSE">HOSE</SelectItem>
            <SelectItem value="HNX">HNX</SelectItem>
            <SelectItem value="UPCOM">UPCOM</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Stock Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Danh sách mã chứng khoán
          </CardTitle>
          <CardDescription>
            Click vào mã CK để xem chi tiết biểu đồ và thông tin công ty
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">Mã CK</TableHead>
                <TableHead>Tên công ty</TableHead>
                <TableHead className="w-[80px]">Sàn</TableHead>
                <TableHead className="w-[120px]">Ngành</TableHead>
                <TableHead className="w-[80px]">Loại</TableHead>
                <TableHead className="w-[80px] text-center">
                  Trạng thái
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <RefreshCw className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                  </TableCell>
                </TableRow>
              ) : symbols.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center py-8 text-muted-foreground"
                  >
                    Không tìm thấy kết quả
                  </TableCell>
                </TableRow>
              ) : (
                symbols.map((sym: StockSymbolItem) => (
                  <TableRow key={sym.symbol} className="cursor-pointer">
                    <TableCell>
                      <Link
                        to="/stock/$symbol"
                        params={{ symbol: sym.symbol }}
                        className="font-mono font-semibold text-primary hover:underline"
                      >
                        {sym.symbol}
                      </Link>
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate">
                      {sym.organ_name || "—"}
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center rounded-md bg-secondary px-2 py-1 text-xs font-medium">
                        {sym.exchange || "—"}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground truncate max-w-[120px]">
                      {sym.asset_type}
                    </TableCell>
                    <TableCell className="text-sm">
                      {sym.asset_type}
                    </TableCell>
                    <TableCell className="text-center">
                      {sym.is_active ? (
                        <ArrowUpRight className="mx-auto h-4 w-4 text-green-500" />
                      ) : (
                        <ArrowDownRight className="mx-auto h-4 w-4 text-red-500" />
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          {/* Pagination */}
          {total > limit && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Trang {page + 1} / {Math.ceil(total / limit)} ({total} kết quả)
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                >
                  Trước
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    setPage(Math.min(Math.ceil(total / limit) - 1, page + 1))
                  }
                  disabled={page >= Math.ceil(total / limit) - 1}
                >
                  Sau
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
