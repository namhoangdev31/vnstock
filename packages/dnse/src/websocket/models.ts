/**
 * Data models for DNSE market data and private channel updates.
 */

export function parseTimestamp(v: unknown, dateOnly = false): string | null {
	if (v === null || v === undefined) return null;

	try {
		if (typeof v === "string") {
			const dt = new Date(v);
			if (Number.isNaN(dt.getTime())) return v;
			if (dateOnly) {
				return dt.toISOString().slice(0, 10);
			}
			return dt.toISOString().replace("T", " ").replace("Z", "");
		}

		if (typeof v === "object" && v !== null) {
			const rec = v as Record<string, number>;
			const seconds = rec.Seconds ?? rec.seconds ?? 0;
			const nanos = rec.Nanos ?? rec.nanos ?? 0;
			const dt = new Date(seconds * 1000 + nanos / 1e6);
			if (dateOnly) {
				return dt.toISOString().slice(0, 10);
			}
			return dt.toISOString().replace("T", " ").replace("Z", "");
		}

		if (typeof v === "number") {
			const dt = new Date(v > 1e12 ? v : v * 1000);
			if (dateOnly) {
				return dt.toISOString().slice(0, 10);
			}
			return dt.toISOString().replace("T", " ").replace("Z", "");
		}
	} catch {
		return null;
	}

	return null;
}

export interface PriceLevel {
	price: number;
	quantity: number;
}

export function parsePriceLevel(data: Record<string, unknown>): PriceLevel {
	return {
		price: Number(data.price ?? 0),
		quantity: Number(data.qtty ?? data.quantity ?? 0),
	};
}

export interface Trade {
	marketId: string;
	boardId: string;
	isin: string;
	symbol: string;
	/** Giá khớp gần nhất */
	price: number;
	/** Khối lượng khớp gần nhất */
	quantity: number;
	totalVolumeTraded: number;
	grossTradeAmount: number;
	highestPrice: number;
	lowestPrice: number;
	openPrice: number;
	/** Mã phiên giao dịch hiện tại (string, VD: "40") */
	tradingSessionId: string;
	time?: string | null;
	receivedAt?: number | null;
}

export function parseTrade(data: Record<string, unknown>): Trade {
	return {
		marketId: String(data.marketId ?? ""),
		boardId: String(data.boardId ?? ""),
		isin: String(data.isin ?? ""),
		symbol: String(data.symbol ?? ""),
		price: Number(data.matchPrice ?? data.price ?? 0),
		quantity: Number(data.matchQtty ?? data.quantity ?? 0),
		totalVolumeTraded: Number(data.totalVolumeTraded ?? 0),
		grossTradeAmount: Number(data.grossTradeAmount ?? 0),
		highestPrice: Number(data.highestPrice ?? 0),
		lowestPrice: Number(data.lowestPrice ?? 0),
		openPrice: Number(data.openPrice ?? 0),
		tradingSessionId: String(data.tradingSessionId ?? ""),
		time: parseTimestamp(data.time),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface TradeExtra {
	marketId: string;
	boardId: string;
	isin: string;
	symbol: string;
	/** Giá khớp gần nhất */
	price: number;
	/** Khối lượng khớp gần nhất */
	quantity: number;
	/** Chiều mua/bán chủ động: "BUY" hoặc "SELL" */
	side: string;
	/** Giá khớp trung bình */
	avgPrice: number;
	totalVolumeTraded: number;
	grossTradeAmount: number;
	highestPrice: number;
	lowestPrice: number;
	openPrice: number;
	tradingSessionId: string;
	time?: string | null;
	receivedAt?: number | null;
}

export function parseTradeExtra(data: Record<string, unknown>): TradeExtra {
	return {
		marketId: String(data.marketId ?? ""),
		boardId: String(data.boardId ?? ""),
		isin: String(data.isin ?? ""),
		symbol: String(data.symbol ?? ""),
		price: Number(data.matchPrice ?? data.price ?? 0),
		quantity: Number(data.matchQtty ?? data.quantity ?? 0),
		side: String(data.side ?? ""),
		avgPrice: Number(data.avgPrice ?? 0),
		totalVolumeTraded: Number(data.totalVolumeTraded ?? 0),
		grossTradeAmount: Number(data.grossTradeAmount ?? 0),
		highestPrice: Number(data.highestPrice ?? 0),
		lowestPrice: Number(data.lowestPrice ?? 0),
		openPrice: Number(data.openPrice ?? 0),
		tradingSessionId: String(data.tradingSessionId ?? ""),
		time: parseTimestamp(data.time),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface ForeignInvestor {
	marketId: string;
	boardId: string;
	tradingSessionId: string;
	symbol: string;
	transactTime: string;
	foreignInvestorTypeCode: string;
	sellVolume: number;
	sellTradedAmount: number;
	buyVolume: number;
	buyTradedAmount: number;
	totalSellVolume: number;
	totalSellTradedAmount: number;
	totalBuyVolume: number;
	totalBuyTradedAmount: number;
	foreignerOrderLimitQuantity: number;
	foreignerBuyPossibleQuantity: number;
	receivedAt?: number | null;
}

export function parseForeignInvestor(
	data: Record<string, unknown>,
): ForeignInvestor {
	return {
		marketId: String(data.marketId ?? ""),
		boardId: String(data.boardId ?? ""),
		tradingSessionId: String(data.tradingSessionId ?? ""),
		symbol: String(data.symbol ?? ""),
		transactTime: String(data.transactTime ?? ""),
		foreignInvestorTypeCode: String(data.foreignInvestorTypeCode ?? ""),
		sellVolume: Number(data.sellVolume ?? 0),
		sellTradedAmount: Number(data.sellTradedAmount ?? 0),
		buyVolume: Number(data.buyVolume ?? 0),
		buyTradedAmount: Number(data.buyTradedAmount ?? 0),
		totalSellVolume: Number(data.totalSellVolume ?? 0),
		totalSellTradedAmount: Number(data.totalSellTradedAmount ?? 0),
		totalBuyVolume: Number(data.totalBuyVolume ?? 0),
		totalBuyTradedAmount: Number(data.totalBuyTradedAmount ?? 0),
		foreignerOrderLimitQuantity: Number(data.foreignerOrderLimitQuantity ?? 0),
		foreignerBuyPossibleQuantity: Number(
			data.foreignerBuyPossibleQuantity ?? 0,
		),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface MarketIndex {
	indexName: string;
	changedRatio: number;
	changedValue: number;
	fluctuationSteadinessIssueCount: number;
	fluctuationDownIssueCount: number;
	fluctuationUpIssueCount: number;
	/** Số lượng mã giảm sàn (có thể null) */
	fluctuationLowerLimitIssueCount: number | null;
	fluctuationUpperLimitIssueCount: number;
	fluctuationDownIssueVolume: number;
	fluctuationUpIssueVolume: number;
	fluctuationSteadinessIssueVolume: number;
	currencyCode: string;
	indexTypeCode: string;
	lowestValueIndexes: number;
	highestValueIndexes: number;
	priorValueIndexes: number;
	valueIndexes: number;
	contauctAccTrdVal: number;
	contauctAccTrdVol: number;
	blkTrdAccTrdVal: number;
	blkTrdAccTrdVol: number;
	grossTradeAmount: number;
	totalVolumeTraded: number;
	/** Phân loại chỉ số (string, VD: "HSX") */
	marketIndexClass: string;
	/** Mã thị trường (string, VD: "STO") */
	marketId: string;
	/** Mã phiên giao dịch hiện tại (string, VD: "40") */
	tradingSessionId: string;
	transactTime?: string | null;
	receivedAt?: number | null;
}

export function parseMarketIndex(data: Record<string, unknown>): MarketIndex {
	return {
		indexName: String(data.indexName ?? ""),
		changedRatio: Number(data.changedRatio ?? 0),
		changedValue: Number(data.changedValue ?? 0),
		fluctuationSteadinessIssueCount: Number(
			data.fluctuationSteadinessIssueCount ?? 0,
		),
		fluctuationDownIssueCount: Number(data.fluctuationDownIssueCount ?? 0),
		fluctuationUpIssueCount: Number(data.fluctuationUpIssueCount ?? 0),
		fluctuationLowerLimitIssueCount:
			data.fluctuationLowerLimitIssueCount != null
				? Number(data.fluctuationLowerLimitIssueCount)
				: null,
		fluctuationUpperLimitIssueCount: Number(
			data.fluctuationUpperLimitIssueCount ?? 0,
		),
		fluctuationDownIssueVolume: Number(data.fluctuationDownIssueVolume ?? 0),
		fluctuationUpIssueVolume: Number(data.fluctuationUpIssueVolume ?? 0),
		fluctuationSteadinessIssueVolume: Number(
			data.fluctuationSteadinessIssueVolume ?? 0,
		),
		currencyCode: String(data.currencyCode ?? ""),
		indexTypeCode: String(data.indexTypeCode ?? ""),
		lowestValueIndexes: Number(data.lowestValueIndexes ?? 0),
		highestValueIndexes: Number(data.highestValueIndexes ?? 0),
		priorValueIndexes: Number(data.priorValueIndexes ?? 0),
		valueIndexes: Number(data.valueIndexes ?? 0),
		contauctAccTrdVal: Number(data.contauctAccTrdVal ?? 0),
		contauctAccTrdVol: Number(data.contauctAccTrdVol ?? 0),
		blkTrdAccTrdVal: Number(data.blkTrdAccTrdVal ?? 0),
		blkTrdAccTrdVol: Number(data.blkTrdAccTrdVol ?? 0),
		grossTradeAmount: Number(data.grossTradeAmount ?? 0),
		totalVolumeTraded: Number(data.totalVolumeTraded ?? 0),
		marketIndexClass: String(data.marketIndexClass ?? ""),
		marketId: String(data.marketId ?? ""),
		tradingSessionId: String(data.tradingSessionId ?? ""),
		transactTime: parseTimestamp(data.transactTime),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface EstimatedMarketIndex {
	indexName: string;
	changedRatio: number;
	changedValue: number;
	fluctuationSteadinessIssueCount: number;
	fluctuationDownIssueCount: number;
	fluctuationUpIssueCount: number;
	valueIndexes: number;
	grossTradeAmount: number;
	totalVolumeTraded: number;
	time?: string | null;
	receivedAt?: number | null;
}

export function parseEstimatedMarketIndex(
	data: Record<string, unknown>,
): EstimatedMarketIndex {
	return {
		indexName: String(data.indexName ?? ""),
		changedRatio: Number(data.changedRatio ?? 0),
		changedValue: Number(data.changedValue ?? 0),
		fluctuationSteadinessIssueCount: Number(
			data.fluctuationSteadinessIssueCount ?? 0,
		),
		fluctuationDownIssueCount: Number(data.fluctuationDownIssueCount ?? 0),
		fluctuationUpIssueCount: Number(data.fluctuationUpIssueCount ?? 0),
		valueIndexes: Number(data.valueIndexes ?? 0),
		grossTradeAmount: Number(data.grossTradeAmount ?? 0),
		totalVolumeTraded: Number(data.totalVolumeTraded ?? 0),
		time: data.time ? String(data.time) : null,
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface IndexInfluenceItem {
	/** Thời gian cập nhật dữ liệu của cổ phiếu từ sàn */
	time?: string | null;
	/** Mã cổ phiếu */
	symbol: string;
	/** Số điểm đóng góp vào chỉ số (dương: kéo tăng, âm: kéo giảm) */
	influence: number;
	/** Tỷ lệ (%) đóng góp vào biến động của chỉ số */
	influenceRatio: number;
	/** Tỷ trọng vốn hóa của mã trong rổ chỉ số (%) */
	proportion: number;
	/** Tỷ lệ (%) thay đổi giá so với giá tham chiếu */
	changeRatio: number;
	/** Mức thay đổi giá tuyệt đối so với giá tham chiếu */
	changeValue: number;
	/** Giá khớp hiện tại (hoặc giá đóng cửa gần nhất) */
	price: number;
	/** Tổng giá trị giao dịch tích lũy trong khung thời gian (VND) */
	grossTradeAmount: number;
	/** Tổng khối lượng giao dịch tích lũy trong khung thời gian */
	totalVolumeTraded: number;
}

export interface IndexInfluence {
	index_name?: string | null;
	data: IndexInfluenceItem[];
	receivedAt?: number | null;
}

export function parseIndexInfluence(
	data: Record<string, unknown>,
): IndexInfluence {
	const rawList = (data.Data ?? data.data ?? []) as Record<string, unknown>[];
	const items: IndexInfluenceItem[] = rawList.map((item) => ({
		// time là object {Seconds, Nanos} theo docs
		time: parseTimestamp(item.time),
		symbol: String(item.symbol ?? ""),
		influence: Number(item.influence ?? 0),
		influenceRatio: Number(item.influenceRatio ?? 0),
		proportion: Number(item.proportion ?? 0),
		changeRatio: Number(item.changeRatio ?? 0),
		changeValue: Number(item.changeValue ?? 0),
		price: Number(item.price ?? 0),
		grossTradeAmount: Number(item.grossTradeAmount ?? 0),
		totalVolumeTraded: Number(item.totalVolumeTraded ?? 0),
	}));

	return {
		index_name: data.index_name ? String(data.index_name) : null,
		data: items,
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface ExpectedPrice {
	marketId: string;
	boardId: string;
	isin: string;
	symbol: string;
	closePrice: number;
	expectedTradePrice: number;
	expectedTradeQuantity: number;
	time?: string | null;
	receivedAt?: number | null;
}

export function parseExpectedPrice(
	data: Record<string, unknown>,
): ExpectedPrice {
	return {
		marketId: String(data.marketId ?? ""),
		boardId: String(data.boardId ?? ""),
		isin: String(data.isin ?? ""),
		symbol: String(data.symbol ?? ""),
		closePrice: Number(data.closePrice ?? 0),
		expectedTradePrice: Number(data.expectedTradePrice ?? 0),
		expectedTradeQuantity: Number(data.expectedTradeQuantity ?? 0),
		time: parseTimestamp(data.time),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface SecurityDefinition {
	marketId: string;
	boardId: string;
	symbol: string;
	isin: string;
	productGrpId: string;
	securityGroupId: string;
	basicPrice: number;
	ceilingPrice: number;
	floorPrice: number;
	openInterestQuantity: number;
	securityStatus: string;
	symbolAdminStatusCode: string;
	symbolTradingMethodStatusCode: string;
	symbolTradingSanctionStatusCode: string;
	finalTradeDate?: string | null;
	listingDate?: string | null;
	time?: string | null;
	receivedAt?: number | null;
}

export function parseSecurityDefinition(
	data: Record<string, unknown>,
): SecurityDefinition {
	return {
		marketId: String(data.marketId ?? ""),
		boardId: String(data.boardId ?? ""),
		symbol: String(data.symbol ?? ""),
		isin: String(data.isin ?? ""),
		productGrpId: String(data.productGrpId ?? ""),
		securityGroupId: String(data.securityGroupId ?? ""),
		basicPrice: Number(data.basicPrice ?? 0),
		ceilingPrice: Number(data.ceilingPrice ?? 0),
		floorPrice: Number(data.floorPrice ?? 0),
		openInterestQuantity: Number(data.openInterestQuantity ?? 0),
		securityStatus: String(data.securityStatus ?? ""),
		symbolAdminStatusCode: String(data.symbolAdminStatusCode ?? ""),
		symbolTradingMethodStatusCode: String(
			data.symbolTradingMethodStatusCode ?? "",
		),
		symbolTradingSanctionStatusCode: String(
			data.symbolTradingSanctionStatusCode ?? "",
		),
		finalTradeDate: parseTimestamp(data.finalTradeDate, true),
		listingDate: parseTimestamp(data.listingDate, true),
		time: parseTimestamp(data.time),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface Order {
	id: string;
	side: string;
	accountNo: string;
	symbol: string;
	price: number;
	priceSecure: number;
	averagePrice: number;
	quantity: number;
	fillQuantity: number;
	canceledQuantity: number;
	leaveQuantity: number;
	orderType: string;
	orderStatus: string;
	loanPackageId: number;
	marketType: string;
	transDate: string;
	createdDate: string;
	modifiedDate: string;
	receivedAt?: number | null;
}

export function parseOrder(data: Record<string, unknown>): Order {
	return {
		id: String(data.id ?? ""),
		side: String(data.side ?? ""),
		accountNo: String(data.accountNo ?? ""),
		symbol: String(data.symbol ?? ""),
		price: Number(data.price ?? 0),
		priceSecure: Number(data.priceSecure ?? 0),
		averagePrice: Number(data.averagePrice ?? 0),
		quantity: Number(data.quantity ?? 0),
		fillQuantity: Number(data.fillQuantity ?? 0),
		canceledQuantity: Number(data.canceledQuantity ?? 0),
		leaveQuantity: Number(data.leaveQuantity ?? 0),
		orderType: String(data.orderType ?? ""),
		orderStatus: String(data.orderStatus ?? ""),
		loanPackageId: Number(data.loanPackageId ?? 0),
		marketType: String(data.marketType ?? ""),
		transDate: String(data.transDate ?? ""),
		createdDate: String(data.createdDate ?? ""),
		modifiedDate: String(data.modifiedDate ?? ""),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface Position {
	id: number;
	accountNo: string;
	symbol: string;
	status: string;
	loanPackageId: number;
	side: string;
	accumulateQuantity: number;
	tradeQuantity: number;
	closedQuantity: number;
	costPrice: number;
	marketPrice: number;
	breakEvenPrice: number;
	openQuantity: number;
	overNightQuantity: number;
	averageClosePrice: number;
	marketType: string;
	createdDate: string;
	modifiedDate: string;
	receivedAt?: number | null;
}

export function parsePosition(data: Record<string, unknown>): Position {
	return {
		id: Number(data.id ?? 0),
		accountNo: String(data.accountNo ?? ""),
		symbol: String(data.symbol ?? ""),
		status: String(data.status ?? ""),
		loanPackageId: Number(data.loanPackageId ?? 0),
		side: String(data.side ?? ""),
		accumulateQuantity: Number(data.accumulateQuantity ?? 0),
		tradeQuantity: Number(data.tradeQuantity ?? 0),
		closedQuantity: Number(data.closedQuantity ?? 0),
		costPrice: Number(data.costPrice ?? 0),
		marketPrice: Number(data.marketPrice ?? 0),
		breakEvenPrice: Number(data.breakEvenPrice ?? 0),
		openQuantity: Number(data.openQuantity ?? 0),
		overNightQuantity: Number(data.overNightQuantity ?? 0),
		averageClosePrice: Number(data.averageClosePrice ?? 0),
		marketType: String(data.marketType ?? ""),
		createdDate: String(data.createdDate ?? ""),
		modifiedDate: String(data.modifiedDate ?? ""),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface Quote {
	marketId: string;
	boardId: string;
	symbol: string;
	isin: string;
	bid: PriceLevel[];
	offer: PriceLevel[];
	totalOfferQtty: number;
	totalBidQtty: number;
	time?: string | null;
	receivedAt?: number | null;
	bestBid?: [number, number] | null;
	bestAsk?: [number, number] | null;
	spread?: number | null;
}

export function parseQuote(data: Record<string, unknown>): Quote {
	const rawBids = (data.bid ?? []) as Record<string, unknown>[];
	const bids = rawBids.map(parsePriceLevel);

	const rawOffers = (data.offer ?? []) as Record<string, unknown>[];
	const offers = rawOffers.map(parsePriceLevel);

	const bestBid: [number, number] | null =
		bids.length > 0 ? [bids[0].price, bids[0].quantity] : null;
	const bestAsk: [number, number] | null =
		offers.length > 0 ? [offers[0].price, offers[0].quantity] : null;
	const spread: number | null =
		bestBid && bestAsk ? bestAsk[0] - bestBid[0] : null;

	return {
		symbol: String(data.symbol ?? ""),
		marketId: String(data.marketId ?? ""),
		boardId: String(data.boardId ?? ""),
		isin: String(data.isin ?? ""),
		bid: bids,
		offer: offers,
		totalOfferQtty: Number(data.totalOfferQtty ?? 0),
		totalBidQtty: Number(data.totalBidQtty ?? 0),
		time: parseTimestamp(data.time),
		receivedAt: (data._receivedAt as number) ?? null,
		bestBid,
		bestAsk,
		spread,
	};
}

export interface Ohlc {
	symbol: string;
	resolution: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
	time: number;
	lastUpdated: number;
	type: string;
	receivedAt?: number | null;
}

export function parseOhlc(data: Record<string, unknown>): Ohlc {
	const roundVal = (v: unknown): number => {
		if (v === null || v === undefined) return 0.0;
		return Math.round(Number(v) * 100) / 100;
	};

	return {
		symbol: String(data.symbol ?? ""),
		resolution: String(data.resolution ?? ""),
		open: roundVal(data.open),
		high: roundVal(data.high),
		low: roundVal(data.low),
		close: roundVal(data.close),
		volume: Number(data.volume ?? 0),
		time: Number(data.time ?? 0),
		lastUpdated: Number(data.lastUpdated ?? 0),
		type: String(data.type ?? ""),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface Session {
	marketId: string;
	boardId: string;
	/** Mã sự kiện chuyển trạng thái phiên giao dịch (VD: "AB2") */
	eventId: string;
	/** Mã phiên giao dịch hiện tại (string, VD: "40") */
	tradingSessionId: string;
	/** Mã nhóm sản phẩm thị trường (VD: "STO", "FIO") */
	tscProdGrpId: string;
	time?: string | null;
	receivedAt?: number | null;
}

export function parseSession(data: Record<string, unknown>): Session {
	return {
		marketId: String(data.marketId ?? ""),
		boardId: String(data.boardId ?? ""),
		eventId: String(data.eventId ?? ""),
		tradingSessionId: String(data.tradingSessionId ?? ""),
		tscProdGrpId: String(data.tscProdGrpId ?? ""),
		// docs dùng "time", không phải "sendingTime"
		time: parseTimestamp(data.time),
		receivedAt: (data._receivedAt as number) ?? null,
	};
}

export interface AccountUpdate {
	cash: number;
	buyingPower: number;
	portfolioValue: number;
	equity: number;
	timestamp: string;
}

export function parseAccountUpdate(
	data: Record<string, unknown>,
): AccountUpdate {
	const ts = Number(data.timestamp ?? Date.now());
	return {
		cash: Number(data.cash ?? 0),
		buyingPower: Number(data.buyingPower ?? 0),
		portfolioValue: Number(data.portfolioValue ?? 0),
		equity: Number(data.equity ?? 0),
		timestamp: new Date(ts).toISOString(),
	};
}
