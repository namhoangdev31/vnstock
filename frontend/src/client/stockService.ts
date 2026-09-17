import { client } from "./client.gen"

export interface StockSymbolItem {
  symbol: string
  organ_name: string | null
  exchange: string | null
  industry: string | null
  asset_type: string
  is_active: boolean
  updated_at: string
}

export interface StockSymbolsResponse {
  data: StockSymbolItem[]
  count: number
}

export interface OHLCVRecord {
  trading_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  value?: number | null
}

export interface PriceHistoryResponse {
  symbol: string
  interval: string
  count: number
  data: OHLCVRecord[]
}

export interface RealtimePriceResponse {
  symbol: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  time: string
}

export interface CompanyOverview {
  symbol: string
  company_name?: string | null
  short_name?: string | null
  industry_name?: string | null
  established_date?: string | null
  listed_date?: string | null
  charter_capital?: number | null
  outstanding_shares?: number | null
  market_cap?: number | null
  website?: string | null
  description?: string | null
}

export interface FinancialReportItem {
  id: string
  symbol: string
  report_type: string
  period: string
  year: number
  quarter?: number | null
  data: Record<string, unknown>
}

export interface FinancialReportsResponse {
  symbol: string
  report_type: string
  period: string
  count: number
  data: FinancialReportItem[]
}

export class StockService {
  public static async listSymbols(options?: {
    query?: {
      skip?: number
      limit?: number
      exchange?: string
      asset_type?: string
      search?: string
    }
  }): Promise<StockSymbolsResponse> {
    const res = await client.get<StockSymbolsResponse, unknown, true>({
      url: "/api/v1/stock/symbols",
      security: [{ scheme: "bearer", type: "http" }],
      query: options?.query,
    })
    return res.data
  }

  public static async getDailyPrice(options: {
    path: { symbol: string }
    query: { start: string; end?: string }
  }): Promise<PriceHistoryResponse> {
    const res = await client.get<PriceHistoryResponse, unknown, true>({
      url: `/api/v1/stock/${options.path.symbol}/price/daily`,
      security: [{ scheme: "bearer", type: "http" }],
      query: options.query,
    })
    return res.data
  }

  public static async getRealtimePrice(options: {
    path: { symbol: string }
  }): Promise<RealtimePriceResponse> {
    const res = await client.get<RealtimePriceResponse, unknown, true>({
      url: `/api/v1/stock/${options.path.symbol}/price/realtime`,
      security: [{ scheme: "bearer", type: "http" }],
    })
    return res.data
  }

  public static async getCompanyOverview(options: {
    path: { symbol: string }
  }): Promise<CompanyOverview> {
    const res = await client.get<CompanyOverview, unknown, true>({
      url: `/api/v1/stock/${options.path.symbol}/overview`,
      security: [{ scheme: "bearer", type: "http" }],
    })
    return res.data
  }

  public static async getFinancials(options: {
    path: { symbol: string }
    query?: { report_type?: string; period?: string }
  }): Promise<FinancialReportsResponse> {
    const res = await client.get<FinancialReportsResponse, unknown, true>({
      url: `/api/v1/stock/${options.path.symbol}/financials`,
      security: [{ scheme: "bearer", type: "http" }],
      query: options.query,
    })
    return res.data
  }
}
