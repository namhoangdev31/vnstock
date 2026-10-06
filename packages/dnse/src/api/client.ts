import axios, { type AxiosInstance, type AxiosRequestConfig } from "axios";
import {
	buildSignature,
	formatDnseDate,
	generateNonce,
	getApiVersion,
	getDateHeaderName,
	type SupportedAlgorithm,
} from "./common";

export interface DNSEClientOptions {
	apiKey: string;
	apiSecret: string;
	baseUrl?: string;
	algorithm?: SupportedAlgorithm;
	hmacNonceEnabled?: boolean;
	apiVersion?: string;
	timeout?: number;
}

export type DNSEClientResponse<T = unknown> = [status: number, body: string] & {
	status: number;
	data: T;
	text: string;
};

export interface LoanQueryOptions {
	disbursementFrom?: string;
	disbursementTo?: string;
	dueDateFrom?: string;
	dueDateTo?: string;
	positionId?: string | number;
	pageIndex?: number;
	pageSize?: number;
}

export interface OrderQueryOptions {
	orderCategory?: string;
	pageIndex?: number;
	pageSize?: number;
}

export interface OrderHistoryOptions {
	from?: string;
	to?: string;
	pageSize?: number;
	pageIndex?: number;
}

export interface CorporateActionOptions {
	symbol?: string;
	caType?: string;
	caStatus?: string;
	pageIndex?: number;
	pageSize?: number;
}

export interface PriceFeedOptions {
	boardId?: string;
	from?: string;
	to?: string;
	limit?: number;
	order?: "ASC" | "DESC" | string;
	nextPageToken?: string;
}

export interface MarketIndexOptions {
	from?: string;
	to?: string;
	limit?: number;
	order?: "ASC" | "DESC" | string;
	nextPageToken?: string;
}

export interface InstrumentOptions {
	symbol?: string;
	marketId?: string;
	securityGroupId?: string;
	indexName?: string;
	limit?: number;
	page?: number;
}

export class DNSEClient {
	private readonly _apiKey: string;
	private readonly _apiSecret: string;
	private readonly _baseUrl: string;
	private readonly _algorithm: SupportedAlgorithm;
	private readonly _hmacNonceEnabled: boolean;
	private readonly _apiVersion: string;
	private readonly _http: AxiosInstance;

	constructor(options: DNSEClientOptions) {
		this._apiKey = options.apiKey;
		this._apiSecret = options.apiSecret;
		this._baseUrl = (options.baseUrl || "https://openapi.dnse.com.vn").replace(
			/\/+$/,
			"",
		);
		this._algorithm = options.algorithm || "hmac-sha256";
		this._hmacNonceEnabled = options.hmacNonceEnabled ?? true;
		this._apiVersion = options.apiVersion || getApiVersion();

		this._http = axios.create({
			baseURL: this._baseUrl,
			timeout: options.timeout ?? 60000,
			headers: {
				Accept: "application/json",
			},
			// Giữ kết nối (connection pooling tương đương urllib3 PoolManager)
			maxRedirects: 5,
			validateStatus: () => true, // Không throw lỗi HTTP để trả về status code như Python
		});
	}

	// ==================== TÀI KHOẢN & SỐ DƯ ====================

	public async getAccounts<T = unknown>(
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			"/accounts",
			undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getBalances<T = unknown>(
		accountNo: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/balances`,
			undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getLoanPackages<T = unknown>(
		accountNo: string,
		marketType: string,
		symbol?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType };
		if (symbol) query.symbol = symbol;
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/loan-packages`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getLoans<T = unknown>(
		accountNo: string,
		marketType: string,
		options?: LoanQueryOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType, ...(options || {}) };
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/loans`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	// ==================== VỊ THẾ & PNL ====================

	public async getPositions<T = unknown>(
		accountNo: string,
		marketType: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/positions`,
			{ marketType },
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getPositionById<T = unknown>(
		marketType: string,
		positionId: string | number,
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/positions/${positionId}`,
			{ marketType },
			undefined,
			undefined,
			version,
			dryRun,
		);
	}

	public async getPositionPnlConfigs<T = unknown>(
		marketType: string,
		positionId: string | number,
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/positions/${positionId}/pnl-configs`,
			{ marketType },
			undefined,
			undefined,
			version,
			dryRun,
		);
	}

	public async getAccountPnlConfigs<T = unknown>(
		accountNo: string,
		marketType: string,
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/pnl-configs`,
			{ marketType },
			undefined,
			undefined,
			version,
			dryRun,
		);
	}

	public async patchAccountPnlConfigs<T = unknown>(
		accountNo: string,
		marketType: string,
		payload: unknown,
		tradingToken: string,
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"PATCH",
			`/accounts/${accountNo}/pnl-configs`,
			{ marketType },
			payload,
			{ "trading-token": tradingToken },
			version,
			dryRun,
		);
	}

	public async postPositionPnlConfigs<T = unknown>(
		marketType: string,
		positionId: string | number,
		payload: unknown,
		tradingToken: string,
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"POST",
			`/positions/${positionId}/pnl-configs`,
			{ marketType },
			payload,
			{ "trading-token": tradingToken },
			version,
			dryRun,
		);
	}

	// ==================== LỆNH & SỔ LỆNH ====================

	public async getOrders<T = unknown>(
		accountNo: string,
		marketType: string,
		options?: OrderQueryOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType, ...(options || {}) };
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/orders`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getOrderDetail<T = unknown>(
		accountNo: string,
		orderId: string | number,
		marketType: string,
		orderCategory?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType };
		if (orderCategory) query.orderCategory = orderCategory;
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/orders/${orderId}`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getExecutionDetail<T = unknown>(
		accountNo: string,
		orderId: string | number,
		marketType: string,
		orderCategory = "NORMAL",
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType };
		if (orderCategory) query.orderCategory = orderCategory;
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/executions/${orderId}`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getOrderHistory<T = unknown>(
		accountNo: string,
		marketType: string,
		options?: OrderHistoryOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType, ...(options || {}) };
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/orders/history`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getCorporateActionHistory<T = unknown>(
		accountNo: string,
		options?: CorporateActionOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/corporate-action-history`,
			options ? (options as Record<string, unknown>) : undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getPpse<T = unknown>(
		accountNo: string,
		marketType: string,
		symbol: string,
		price: number | string,
		loanPackageId: number | string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/accounts/${accountNo}/ppse`,
			{
				marketType,
				symbol,
				price: String(price),
				loanPackageId: String(loanPackageId),
			},
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	// ==================== GIÁ & THỊ TRƯỜNG ====================

	public async getSecurityDefinition<T = unknown>(
		symbol: string,
		boardId?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = {};
		if (boardId) query.boardId = boardId;
		return this._request<T>(
			"GET",
			`/price/${symbol}/secdef`,
			Object.keys(query).length ? query : undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getOhlc<T = unknown>(
		barType: string,
		query?: Record<string, unknown>,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const requestQuery: Record<string, unknown> = {
			...(query || {}),
			type: barType,
		};
		return this._request<T>(
			"GET",
			"/price/ohlc",
			requestQuery,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getTrades<T = unknown>(
		symbol: string,
		options?: PriceFeedOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/price/${symbol}/trades`,
			options ? (options as Record<string, unknown>) : undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getTradesVolumeProfile<T = unknown>(
		symbol: string,
		time: string,
		boardId?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { time };
		if (boardId) query.boardId = boardId;
		return this._request<T>(
			"GET",
			`/price/${symbol}/trades/volume-profile`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getExpectedPrice<T = unknown>(
		symbol: string,
		options?: PriceFeedOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/price/${symbol}/expected-price`,
			options ? (options as Record<string, unknown>) : undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getQuotes<T = unknown>(
		symbol: string,
		options?: PriceFeedOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/price/${symbol}/quotes`,
			options ? (options as Record<string, unknown>) : undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getForeignTrading<T = unknown>(
		symbol: string,
		options?: PriceFeedOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/price/${symbol}/foreign-trading`,
			options ? (options as Record<string, unknown>) : undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getMarketIndex<T = unknown>(
		indexName: string,
		options?: MarketIndexOptions,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			`/price/${indexName}/market-index`,
			options ? (options as Record<string, unknown>) : undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getInstruments<T = unknown>(
		options?: InstrumentOptions,
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			"/market/instruments",
			options ? (options as Record<string, unknown>) : undefined,
			undefined,
			undefined,
			version,
			dryRun,
		);
	}

	public async getLatestTrade<T = unknown>(
		symbol: string,
		boardId?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query = boardId ? { boardId } : undefined;
		return this._request<T>(
			"GET",
			`/price/${symbol}/trades/latest`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getLatestQuote<T = unknown>(
		symbol: string,
		boardId?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query = boardId ? { boardId } : undefined;
		return this._request<T>(
			"GET",
			`/price/${symbol}/quotes/latest`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getClosePrice<T = unknown>(
		symbol: string,
		boardId?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query = boardId ? { boardId } : undefined;
		return this._request<T>(
			"GET",
			`/price/${symbol}/close`,
			query,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getWorkingDates<T = unknown>(
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			"/market/working-dates",
			undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getListCareBy<T = unknown>(
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"GET",
			"/brokers/accounts/care-by",
			undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async getLastestSession<T = unknown>(
		tscProdGrpId?: string,
		boardId?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = {};
		if (tscProdGrpId) query.tscProdGrpId = tscProdGrpId;
		if (boardId) query.boardId = boardId;
		return this._request<T>(
			"GET",
			"/market/trading-session",
			Object.keys(query).length ? query : undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	// ==================== ĐẶT LỆNH & GIAO DỊCH ====================

	public async postOrder<T = unknown>(
		accountNo: string,
		marketType: string,
		payload: unknown,
		tradingToken: string,
		orderCategory = "NORMAL",
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType };
		if (orderCategory) query.orderCategory = orderCategory;
		return this._request<T>(
			"POST",
			`/accounts/${accountNo}/orders`,
			query,
			payload,
			{ "trading-token": tradingToken },
			version,
			dryRun,
		);
	}

	public async putOrder<T = unknown>(
		accountNo: string,
		orderId: string | number,
		marketType: string,
		payload: unknown,
		tradingToken: string,
		orderCategory?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType };
		if (orderCategory) query.orderCategory = orderCategory;
		return this._request<T>(
			"PUT",
			`/accounts/${accountNo}/orders/${orderId}`,
			query,
			payload,
			{ "trading-token": tradingToken },
			undefined,
			dryRun,
		);
	}

	public async cancelOrder<T = unknown>(
		accountNo: string,
		orderId: string | number,
		marketType: string,
		tradingToken: string,
		orderCategory?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const query: Record<string, unknown> = { marketType };
		if (orderCategory) query.orderCategory = orderCategory;
		return this._request<T>(
			"DELETE",
			`/accounts/${accountNo}/orders/${orderId}`,
			query,
			undefined,
			{ "trading-token": tradingToken },
			undefined,
			dryRun,
		);
	}

	public async createTradingToken<T = unknown>(
		otpType: string,
		passcode: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"POST",
			"/registration/trading-token",
			undefined,
			{ otpType, passcode },
			undefined,
			undefined,
			dryRun,
		);
	}

	public async createSmartOtpHandoff<T = unknown>(
		version = "2026-01-01",
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"POST",
			"/registration/smart-otp/handoff",
			undefined,
			undefined,
			undefined,
			version,
			dryRun,
		);
	}

	public async sendEmailOtp<T = unknown>(
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"POST",
			"/registration/send-email-otp",
			undefined,
			undefined,
			undefined,
			undefined,
			dryRun,
		);
	}

	public async closePosition<T = unknown>(
		positionId: string | number,
		marketType: string,
		tradingToken: string,
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"POST",
			`/positions/${positionId}/close`,
			{ marketType },
			undefined,
			{ "trading-token": tradingToken },
			version,
			dryRun,
		);
	}

	public async reversePosition<T = unknown>(
		positionId: string | number,
		tradingToken: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		return this._request<T>(
			"POST",
			`/positions/${positionId}/reverse`,
			{ marketType: "DERIVATIVE" },
			undefined,
			{ "trading-token": tradingToken },
			"2026-01-01",
			dryRun,
		);
	}

	// ==================== CORE REQUEST HANDLER ====================

	private async _request<T = unknown>(
		method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
		path: string,
		query?: Record<string, unknown>,
		body?: unknown,
		headers?: Record<string, string>,
		version?: string,
		dryRun = false,
	): Promise<DNSEClientResponse<T> | null> {
		const debug =
			typeof process !== "undefined" &&
			process.env?.DEBUG?.toLowerCase() === "true";

		const { dateValue, signatureHeaderValue } = await this._signatureHeaders(
			method,
			path,
		);
		const dateHeaderName = getDateHeaderName();

		const reqHeaders: Record<string, string> = {
			[dateHeaderName]: dateValue,
			"X-Signature": signatureHeaderValue,
			"x-api-key": this._apiKey,
			version: version || this._apiVersion,
			...(headers || {}),
		};

		if (body !== undefined && body !== null) {
			reqHeaders["Content-Type"] = "application/json";
		}

		if (debug || dryRun) {
			const prefix = dryRun ? "DRY RUN" : "DEBUG";
			console.log(`${prefix} url:`, `${this._baseUrl}${path}`);
			console.log(`${prefix} method:`, method);
			console.log(`${prefix} query_params:`, query || {});
			console.log(`${prefix} headers:`, reqHeaders);
			console.log(`${prefix} body:`, body);
		}

		if (dryRun) {
			return null;
		}

		const config: AxiosRequestConfig = {
			method,
			url: path,
			params: query,
			data: body,
			headers: reqHeaders,
			transformResponse: [(d) => d], // Giữ raw text để parse chủ động
		};

		try {
			const resp = await this._http.request(config);
			const rawText =
				typeof resp.data === "string" ? resp.data : JSON.stringify(resp.data);

			let parsedData: T;
			try {
				parsedData = JSON.parse(rawText) as T;
			} catch {
				parsedData = rawText as unknown as T;
			}

			const res = [resp.status, rawText] as unknown as DNSEClientResponse<T>;
			res.status = resp.status;
			res.data = parsedData;
			res.text = rawText;

			return res;
		} catch (err: unknown) {
			if (axios.isAxiosError(err) && err.response) {
				const rawText =
					typeof err.response.data === "string"
						? err.response.data
						: JSON.stringify(err.response.data);

				let parsedData: T;
				try {
					parsedData = JSON.parse(rawText) as T;
				} catch {
					parsedData = rawText as unknown as T;
				}

				const res = [
					err.response.status,
					rawText,
				] as unknown as DNSEClientResponse<T>;
				res.status = err.response.status;
				res.data = parsedData;
				res.text = rawText;
				return res;
			}
			throw err;
		}
	}

	private async _signatureHeaders(
		method: string,
		path: string,
	): Promise<{ dateValue: string; signatureHeaderValue: string }> {
		const dateValue = this._dateHeader();
		const nonce = this._hmacNonceEnabled ? generateNonce() : null;

		const { headers: headersList, signature } = await buildSignature(
			this._apiSecret,
			method,
			path,
			dateValue,
			this._algorithm,
			nonce,
			getDateHeaderName(),
		);

		let signatureHeaderValue = `Signature keyId="${this._apiKey}",algorithm="${this._algorithm}",headers="${headersList}",signature="${signature}"`;
		if (nonce) {
			signatureHeaderValue += `,nonce="${nonce}"`;
		}

		return { dateValue, signatureHeaderValue };
	}

	private _dateHeader(): string {
		return formatDnseDate();
	}
}
