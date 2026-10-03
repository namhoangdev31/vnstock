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

export interface DerivativesSnapshot {
	symbol: string;
	as_of: string;
	session_phase: string;
	quote: { price: number | null; reference: number | null; change: number | null; change_percent: number | null; ceiling: number | null; floor: number | null };
	basis: { value: number; zscore: number; spot: number | null };
	technical: { vwap: number | null; bollinger: Record<string, number>; rsi: number | null; atr: number | null };
	candles: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>;
	orderflow: Array<{ time: string; buy_volume: number; sell_volume: number; delta: number; vwap: number | null }>;
	signal: { direction: string; entry: number; stop_loss: number | null; take_profit: number | null; trailing_stop: number | null; confidence: number; created_at: string } | null;
	disclaimer: string;
}

export interface FlowRadarSnapshot {
	as_of: string;
	engine: Record<string, unknown>;
	flows: Array<Record<string, unknown>>;
	breadth: Record<string, number> | null;
	macro: Array<Record<string, unknown>>;
	availability: Record<string, { available: boolean; reason: string | null }>;
}

export interface PredictionSnapshot {
	symbol: string;
	as_of: string;
	current_price: number | null;
	price_limits: { floor: number | null; ceiling: number | null };
	atc: { available: boolean; reason: string };
	monte_carlo: { available: boolean; simulations: number; p10: number | null; p50: number | null; p90: number | null; histogram: Array<{ price: number; probability: number }>; reason: string | null };
	ledger: Array<Record<string, unknown>>;
	disclaimer: string;
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

export interface PositionItem { id: string; symbol: string; side: string; quantity: number; entry_price: number; current_price: number; unrealized_pnl: number; realized_pnl: number; margin_required: number; settlement_date?: string | null; status: string }
export interface OrderItem { id: string; symbol: string; side: string; order_type: string; price: number; stop_price?: number | null; quantity: number; filled_quantity: number; filled_price?: number | null; fee: number; tax: number; status: string; reject_reason?: string | null; created_at: string; updated_at: string }

export async function getDerivativesSnapshot(options?: { query?: { symbol?: string; timeframe?: string; limit?: number } }): Promise<DerivativesSnapshot> {
	return (await client.get<DerivativesSnapshot, unknown, true>({ url: "/api/v1/quant/cockpit/derivatives", query: options?.query, security: [{ scheme: "bearer", type: "http" }] })).data;
}

export async function getFlowRadarSnapshot(): Promise<FlowRadarSnapshot> {
	return (await client.get<FlowRadarSnapshot, unknown, true>({ url: "/api/v1/quant/cockpit/flow-radar", security: [{ scheme: "bearer", type: "http" }] })).data;
}

export async function getPredictionSnapshot(options?: { query?: { symbol?: string } }): Promise<PredictionSnapshot> {
	return (await client.get<PredictionSnapshot, unknown, true>({ url: "/api/v1/quant/cockpit/prediction", query: options?.query, security: [{ scheme: "bearer", type: "http" }] })).data;
}

export async function listSymbols(options?: {
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

export async function getDailyPrice(options: {
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

export async function getRealtimePrice(options: {
	path: { symbol: string };
}): Promise<RealtimePriceResponse> {
	const res = await client.get<RealtimePriceResponse, unknown, true>({
		url: `/api/v1/stock/${options.path.symbol}/price/realtime`,
		security: [{ scheme: "bearer", type: "http" }],
	});
	return res.data;
}

export async function getCompanyOverview(options: {
	path: { symbol: string };
}): Promise<CompanyOverview> {
	const res = await client.get<CompanyOverview, unknown, true>({
		url: `/api/v1/stock/${options.path.symbol}/overview`,
		security: [{ scheme: "bearer", type: "http" }],
	});
	return res.data;
}

export async function getFinancials(options: {
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

export async function listPortfolios(): Promise<PortfoliosResponse> {
	const res = await client.get<PortfoliosResponse, unknown, true>({
		url: "/api/v1/simulation/portfolios",
		security: [{ scheme: "bearer", type: "http" }],
	});
	return res.data;
}

export async function getMarginStatus(options: {
	path: { portfolio_id: string };
}): Promise<MarginStatusResponse> {
	const res = await client.get<MarginStatusResponse, unknown, true>({
		url: `/api/v1/simulation/portfolios/${options.path.portfolio_id}/margin-status`,
		security: [{ scheme: "bearer", type: "http" }],
	});
	return res.data;
}

export async function processSettlement(): Promise<SettlementProcessResponse> {
	const res = await client.post<SettlementProcessResponse, unknown, true>({
		url: "/api/v1/simulation/settlement/process",
		security: [{ scheme: "bearer", type: "http" }],
	});
	return res.data;
}

export async function getAlphaBaskets(options?: {
	query?: { horizon?: string; record_journal?: boolean };
}): Promise<AlphaBasketsResponse> {
	const res = await client.get<AlphaBasketsResponse, unknown, true>({
		url: "/api/v1/simulation/alpha/baskets",
		security: [{ scheme: "bearer", type: "http" }],
		query: options?.query,
	});
	return res.data;
}

export async function getIBoardIndices(): Promise<IBoardIndexItem[]> {
	const res = await client.get<IBoardIndexItem[], unknown, true>({
		url: "/api/v1/stock/iboard/indices",
		security: [{ scheme: "bearer", type: "http" }],
	});
	return res.data;
}

export async function getIBoardBoard(options?: {
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

export async function getIBoardStockDetail(options: {
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

export async function getIBoardCandles(options: {
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

export async function getIBoardMarketPulse(): Promise<IBoardMarketPulse> {
	const res = await client.get<IBoardMarketPulse, unknown, true>({
		url: "/api/v1/stock/iboard/market-pulse",
		security: [{ scheme: "bearer", type: "http" }],
	});
	return res.data;
}

export async function placeSimulationOrder(payload: {
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

export async function listSimulationOrders(options?: {
	query?: { portfolio_id?: string; limit?: number };
}): Promise<SimulationOrderDTO[]> {
	const res = await client.get<SimulationOrderDTO[], unknown, true>({
		url: "/api/v1/simulation/orders",
		security: [{ scheme: "bearer", type: "http" }],
		query: options?.query,
	});
	return res.data;
}

export async function listSimulationPositions(options: { path: { portfolio_id: string } }): Promise<PositionItem[]> {
	const res = await client.get<PositionItem[], unknown, true>({ url: `/api/v1/simulation/portfolios/${options.path.portfolio_id}/positions`, security: [{ scheme: "bearer", type: "http" }] });
	return res.data;
}

export async function placePortfolioOrder(options: { path: { portfolio_id: string }; body: { symbol: string; side: string; quantity: number; price: number; order_type: string; stop_price?: number } }): Promise<OrderItem> {
	const res = await client.post<OrderItem, unknown, true>({ url: `/api/v1/simulation/portfolios/${options.path.portfolio_id}/orders`, security: [{ scheme: "bearer", type: "http" }], body: options.body });
	return res.data;
}

export async function closeSimulationPosition(options: { path: { position_id: string }; body: { quantity: number; price: number } }): Promise<unknown> {
	const res = await client.post({ url: `/api/v1/simulation/positions/${options.path.position_id}/close`, security: [{ scheme: "bearer", type: "http" }], body: options.body });
	return res.data;
}

export async function allocateAlphaBasket(options: { path: { portfolio_id: string }; body: { horizon: string } }): Promise<OrderItem[]> {
	const res = await client.post<OrderItem[], unknown, true>({ url: `/api/v1/simulation/portfolios/${options.path.portfolio_id}/alpha/allocate`, security: [{ scheme: "bearer", type: "http" }], body: options.body });
	return res.data;
}

export const StockService = {
	getDerivativesSnapshot,
	getFlowRadarSnapshot,
	getPredictionSnapshot,
	listSymbols,
	getDailyPrice,
	getRealtimePrice,
	getCompanyOverview,
	getFinancials,
	listPortfolios,
	getMarginStatus,
	processSettlement,
	getAlphaBaskets,
	getIBoardIndices,
	getIBoardBoard,
	getIBoardStockDetail,
	getIBoardCandles,
	getIBoardMarketPulse,
	placeSimulationOrder,
	listSimulationOrders,
	listSimulationPositions,
	placePortfolioOrder,
	closeSimulationPosition,
	allocateAlphaBasket,
};

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
