import { client } from "./client.gen";

export interface StockSymbolItem {
	symbol: string;
	organ_name: string | null;
	exchange: string | null;
	industry: string | null;
	asset_type: string;
	is_active: boolean;
	updated_at: string;
}

export interface StockSymbolsResponse {
	data: StockSymbolItem[];
	count: number;
}

export interface OHLCVRecord {
	trading_date: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
	value?: number | null;
}

export interface PriceHistoryResponse {
	symbol: string;
	interval: string;
	count: number;
	data: OHLCVRecord[];
}

export interface RealtimePriceResponse {
	symbol: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
	time: string;
}

export interface CompanyOverview {
	symbol: string;
	company_name?: string | null;
	short_name?: string | null;
	industry_name?: string | null;
	established_date?: string | null;
	listed_date?: string | null;
	charter_capital?: number | null;
	outstanding_shares?: number | null;
	market_cap?: number | null;
	website?: string | null;
	description?: string | null;
}

export interface FinancialReportItem {
	id: string;
	symbol: string;
	report_type: string;
	period: string;
	year: number;
	quarter?: number | null;
	data: Record<string, unknown>;
}

export interface FinancialReportsResponse {
	symbol: string;
	report_type: string;
	period: string;
	count: number;
	data: FinancialReportItem[];
}

export interface MarginStatusResponse {
	equity: number;
	margin_used: number;
	margin_ratio: number | null;
	status: string;
}

export interface SettlementProcessResponse {
	settled: number;
}

export interface AlphaCriteria {
	key: string;
	label: string;
	passed: boolean;
	value?: number | null;
	threshold?: number | null;
}

export interface AlphaTicker {
	symbol: string;
	horizon: string;
	alpha_score: number;
	criteria: AlphaCriteria[];
}

export interface AlphaBasketsResponse {
	horizon: string;
	baskets: Record<string, AlphaTicker[]>;
}

export interface PortfolioItem {
	id: string;
	name: string;
	initial_balance: number;
	cash_balance: number;
	equity: number;
	margin_used: number;
	created_at: string;
	updated_at: string;
}

export interface PortfoliosResponse {
	data: PortfolioItem[];
	count: number;
}

export class StockService {
	public static async listSymbols(options?: {
		query?: {
			skip?: number;
			limit?: number;
			exchange?: string;
			asset_type?: string;
			search?: string;
		};
	}): Promise<StockSymbolsResponse> {
		const res = await client.get<StockSymbolsResponse, unknown, true>({
			url: "/api/v1/stock/symbols",
			security: [{ scheme: "bearer", type: "http" }],
			query: options?.query,
		});
		return res.data;
	}

	public static async getDailyPrice(options: {
		path: { symbol: string };
		query: { start: string; end?: string };
	}): Promise<PriceHistoryResponse> {
		const res = await client.get<PriceHistoryResponse, unknown, true>({
			url: `/api/v1/stock/${options.path.symbol}/price/daily`,
			security: [{ scheme: "bearer", type: "http" }],
			query: options.query,
		});
		return res.data;
	}

	public static async getRealtimePrice(options: {
		path: { symbol: string };
	}): Promise<RealtimePriceResponse> {
		const res = await client.get<RealtimePriceResponse, unknown, true>({
			url: `/api/v1/stock/${options.path.symbol}/price/realtime`,
			security: [{ scheme: "bearer", type: "http" }],
		});
		return res.data;
	}

	public static async getCompanyOverview(options: {
		path: { symbol: string };
	}): Promise<CompanyOverview> {
		const res = await client.get<CompanyOverview, unknown, true>({
			url: `/api/v1/stock/${options.path.symbol}/overview`,
			security: [{ scheme: "bearer", type: "http" }],
		});
		return res.data;
	}

	public static async getFinancials(options: {
		path: { symbol: string };
		query?: { report_type?: string; period?: string };
	}): Promise<FinancialReportsResponse> {
		const res = await client.get<FinancialReportsResponse, unknown, true>({
			url: `/api/v1/stock/${options.path.symbol}/financials`,
			security: [{ scheme: "bearer", type: "http" }],
			query: options.query,
		});
		return res.data;
	}

	public static async listPortfolios(): Promise<PortfoliosResponse> {
		const res = await client.get<PortfoliosResponse, unknown, true>({
			url: "/api/v1/simulation/portfolios",
			security: [{ scheme: "bearer", type: "http" }],
		});
		return res.data;
	}

	public static async getMarginStatus(options: {
		path: { portfolio_id: string };
	}): Promise<MarginStatusResponse> {
		const res = await client.get<MarginStatusResponse, unknown, true>({
			url: `/api/v1/simulation/portfolios/${options.path.portfolio_id}/margin-status`,
			security: [{ scheme: "bearer", type: "http" }],
		});
		return res.data;
	}

	public static async processSettlement(): Promise<SettlementProcessResponse> {
		const res = await client.post<SettlementProcessResponse, unknown, true>({
			url: "/api/v1/simulation/settlement/process",
			security: [{ scheme: "bearer", type: "http" }],
		});
		return res.data;
	}

	public static async getAlphaBaskets(options?: {
		query?: { horizon?: string; record_journal?: boolean };
	}): Promise<AlphaBasketsResponse> {
		const res = await client.get<AlphaBasketsResponse, unknown, true>({
			url: "/api/v1/simulation/alpha/baskets",
			security: [{ scheme: "bearer", type: "http" }],
			query: options?.query,
		});
		return res.data;
	}

	public static async getIBoardIndices(): Promise<IBoardIndexItem[]> {
		const res = await client.get<IBoardIndexItem[], unknown, true>({
			url: "/api/v1/stock/iboard/indices",
			security: [{ scheme: "bearer", type: "http" }],
		});
		return res.data;
	}

	public static async getIBoardBoard(options?: {
		query?: {
			category?: string;
			group?: string;
			sector?: string;
			search?: string;
			limit?: number;
		};
	}): Promise<IBoardStockRow[]> {
		const res = await client.get<IBoardStockRow[], unknown, true>({
			url: "/api/v1/stock/iboard/board",
			security: [{ scheme: "bearer", type: "http" }],
			query: options?.query,
		});
		return res.data;
	}

	public static async getIBoardStockDetail(options: {
		path: { symbol: string };
		query?: { timeframe?: string };
	}): Promise<IBoardStockDetail> {
		const res = await client.get<IBoardStockDetail, unknown, true>({
			url: `/api/v1/stock/iboard/stock-detail/${options.path.symbol}`,
			security: [{ scheme: "bearer", type: "http" }],
			query: options.query,
		});
		return res.data;
	}

	public static async getIBoardCandles(options: {
		path: { symbol: string };
		query?: {
			timeframe?: string;
			limit?: number;
		};
	}): Promise<IBoardCandleBar[]> {
		const res = await client.get<IBoardCandleBar[], unknown, true>({
			url: `/api/v1/stock/iboard/candles/${options.path.symbol}`,
			security: [{ scheme: "bearer", type: "http" }],
			query: options.query,
		});
		return res.data;
	}

	public static async getIBoardMarketPulse(): Promise<IBoardMarketPulse> {
		const res = await client.get<IBoardMarketPulse, unknown, true>({
			url: "/api/v1/stock/iboard/market-pulse",
			security: [{ scheme: "bearer", type: "http" }],
		});
		return res.data;
	}

	public static async placeSimulationOrder(payload: {
		portfolio_id: string;
		symbol: string;
		side: "BUY" | "SELL";
		order_type?: string;
		quantity: number;
		price?: number;
	}): Promise<unknown> {
		const res = await client.post({
			url: "/api/v1/simulation/orders",
			security: [{ scheme: "bearer", type: "http" }],
			body: payload,
		});
		return res.data;
	}

	public static async listSimulationOrders(options?: {
		query?: { portfolio_id?: string; limit?: number };
	}): Promise<SimulationOrderDTO[]> {
		const res = await client.get<SimulationOrderDTO[], unknown, true>({
			url: "/api/v1/simulation/orders",
			security: [{ scheme: "bearer", type: "http" }],
			query: options?.query,
		});
		return res.data;
	}
}

export interface IBoardIndexBreadth {
	advance: number;
	ceiling: number;
	unchanged: number;
	decline: number;
	floor: number;
}

export interface IBoardIndexItem {
	id: string;
	name: string;
	price: string;
	change: string;
	change_percent: string;
	is_positive: boolean;
	is_unchanged?: boolean;
	volume: string;
	value: string;
	breadth: IBoardIndexBreadth;
	sparkline: number[];
}

export interface OrderBookLevel {
	price: number;
	volume: number;
}

export interface IBoardStockRow {
	symbol: string;
	name: string;
	exchange: string;
	margin_rate?: string | null;
	last_price: number;
	ref_price: number;
	ceiling_price: number;
	floor_price: number;
	high_price: number;
	low_price: number;
	avg_price: number;
	change: number;
	change_percent: number;
	volume: number;
	value_billion: number;
	buy_ratio: number;
	sell_ratio: number;
	foreign_buy: number;
	foreign_sell: number;
	foreign_room: number;
	status: "up" | "down" | "ref" | "ceiling" | "floor";
	sparkline: number[];
	bid_book: OrderBookLevel[];
	ask_book: OrderBookLevel[];
	category: string;
	sector?: string | null;
	expiry_date?: string | null;
}

export interface MatchedTickDTO {
	time: string;
	price: number;
	volume: number;
	side: string;
}

export interface CompanyOverviewDTO {
	market_cap_billion: number;
	pe: number;
	pb: number;
	roe: number;
}

export interface CorporateEventDTO {
	date: string;
	title: string;
}

export interface IBoardCandleBar {
	time: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
}

export interface IBoardStockDetail {
	stock: IBoardStockRow;
	matched_ticks: MatchedTickDTO[];
	overview: CompanyOverviewDTO;
	company_overview?: CompanyOverviewDTO;
	events: CorporateEventDTO[];
	candles: IBoardCandleBar[];
}

export interface TopMoverItem {
	symbol: string;
	name: string;
	price: string;
	change: string;
}

export interface IBoardMarketPulse {
	ai_insight: string;
	top_gainers: TopMoverItem[];
	top_losers: TopMoverItem[];
	sector_performance?: Record<string, number>;
}

export interface SimulationOrderDTO {
	id: string;
	symbol: string;
	side: string;
	order_type: string;
	price: number;
	stop_price?: number | null;
	quantity: number;
	filled_quantity: number;
	filled_price?: number | null;
	fee: number;
	tax: number;
	status: string;
	reject_reason?: string | null;
	created_at: string;
	updated_at: string;
}

