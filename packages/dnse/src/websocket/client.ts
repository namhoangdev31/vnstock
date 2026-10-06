import { EventEmitter } from "node:events";
import { AuthManager } from "./auth";
import { WebSocketConnection } from "./connection";
import {
	MessageDecoder,
	MessageEncoder,
	type WebSocketEncoding,
} from "./encoding";
import {
	AuthenticationError,
	ConnectionClosed,
	ConnectionError,
	SubscriptionError,
} from "./exceptions";
import {
	type AccountUpdate,
	type EstimatedMarketIndex,
	type ExpectedPrice,
	type ForeignInvestor,
	type IndexInfluence,
	type MarketIndex,
	type Ohlc,
	type Order,
	type Position,
	parseAccountUpdate,
	parseEstimatedMarketIndex,
	parseExpectedPrice,
	parseForeignInvestor,
	parseIndexInfluence,
	parseMarketIndex,
	parseOhlc,
	parseOrder,
	parsePosition,
	parseQuote,
	parseSecurityDefinition,
	parseSession,
	parseTrade,
	parseTradeExtra,
	type Quote,
	type SecurityDefinition,
	type Session,
	type Trade,
	type TradeExtra,
} from "./models";

export const DEFAULT_BOARDS = [
	"G1",
	"G3",
	"G4",
	"G7",
	"T1",
	"T2",
	"T3",
	"T4",
	"T6",
];

interface MsgTypeMapping {
	event: string;
	parser: (data: Record<string, unknown>) => unknown;
	field?: string;
}

const MSG_TYPE_MAP: Record<string, MsgTypeMapping> = {
	t: { event: "trade", parser: parseTrade },
	te: { event: "trade_extra", parser: parseTradeExtra },
	e: { event: "expected_price", parser: parseExpectedPrice },
	sd: { event: "security_definition", parser: parseSecurityDefinition },
	q: { event: "quote", parser: parseQuote },
	b: { event: "ohlc", parser: parseOhlc },
	bc: { event: "ohlc_closed", parser: parseOhlc },
	do: { event: "order_event", parser: parseOrder, field: "order" },
	eo: { event: "order_event", parser: parseOrder, field: "order" },
	dp: { event: "position_event", parser: parsePosition, field: "position" },
	ep: { event: "position_event", parser: parsePosition, field: "position" },
	mi: { event: "market_index", parser: parseMarketIndex },
	emi: {
		event: "estimated_market_index",
		parser: parseEstimatedMarketIndex,
		field: "marketIndex",
	},
	ii: { event: "market_index_influence", parser: parseIndexInfluence },
	a: { event: "account", parser: parseAccountUpdate },
	f: { event: "foreign", parser: parseForeignInvestor },
	s: { event: "session", parser: parseSession },
};

export class AsyncQueue<T> {
	private _items: T[] = [];
	private _waitingResolvers: ((item: T) => void)[] = [];

	public push(item: T): void {
		const resolver = this._waitingResolvers.shift();
		if (resolver) {
			resolver(item);
		} else {
			this._items.push(item);
		}
	}

	public async shift(timeoutMs?: number): Promise<T | null> {
		const queuedItem = this._items.shift();
		if (queuedItem !== undefined) {
			return queuedItem;
		}

		return new Promise((resolve) => {
			let timer: ReturnType<typeof setTimeout> | null = null;
			const resolver = (item: T) => {
				if (timer) clearTimeout(timer);
				resolve(item);
			};

			if (timeoutMs && timeoutMs > 0) {
				timer = setTimeout(() => {
					const idx = this._waitingResolvers.indexOf(resolver);
					if (idx !== -1) {
						this._waitingResolvers.splice(idx, 1);
					}
					resolve(null);
				}, timeoutMs);
			}

			this._waitingResolvers.push(resolver);
		});
	}

	public clear(): void {
		this._items = [];
		this._waitingResolvers = [];
	}
}

function hashSymbol(s: string): number {
	let hash = 0;
	for (let i = 0; i < s.length; i++) {
		hash = ((hash << 5) - hash + s.charCodeAt(i)) | 0;
	}
	return Math.abs(hash);
}

export interface TradingClientOptions {
	apiKey: string;
	apiSecret: string;
	baseUrl?: string;
	encoding?: WebSocketEncoding;
	autoReconnect?: boolean;
	maxRetries?: number;
	heartbeatInterval?: number;
	timeout?: number;
}

export interface SubscriptionData {
	symbols: string[];
	kwargs?: Record<string, unknown>;
}

export interface ReconnectingEventData {
	attempt: number;
	maxRetries: number;
	delay: number;
	error: string;
}

/**
 * Async WebSocket client for DNSE real-time trading & market data.
 */
export class TradingClient extends EventEmitter {
	public readonly apiKey: string;
	public readonly apiSecret: string;
	public readonly baseUrl: string;
	public readonly encoding: WebSocketEncoding;
	public readonly autoReconnect: boolean;
	public readonly maxRetries: number;
	public readonly heartbeatInterval: number;
	public readonly timeout: number;

	private _connection: WebSocketConnection | null = null;
	private _authManager: AuthManager;
	private _encoder: MessageEncoder;
	private _decoder: MessageDecoder;
	private _subscriptions: Map<string, SubscriptionData> = new Map();
	private _isAuthenticated = false;
	private _sessionId: string | null = null;

	private _queues: Map<string, AsyncQueue<unknown>> = new Map();
	private _dispatchQueues: AsyncQueue<Record<string, unknown>>[] = [];
	private _isDispatcherRunning = false;
	private _numWorkers = 6;

	private _lastPongTime = 0;
	private _heartbeatTimer: ReturnType<typeof setInterval> | null = null;
	private _reconnectLoopActive = false;

	constructor(options: TradingClientOptions) {
		super();
		this.apiKey = options.apiKey;
		this.apiSecret = options.apiSecret;
		this.baseUrl = options.baseUrl ?? "wss://ws-openapi.dnse.com.vn";
		this.encoding = options.encoding ?? "json";
		this.autoReconnect = options.autoReconnect ?? true;
		this.maxRetries = options.maxRetries ?? 10;
		this.heartbeatInterval = options.heartbeatInterval ?? 25.0;
		this.timeout = options.timeout ?? 60.0;

		this._authManager = new AuthManager(this.apiKey, this.apiSecret);
		this._encoder = new MessageEncoder(this.encoding);
		this._decoder = new MessageDecoder(this.encoding);
	}

	public get isAuthenticated(): boolean {
		return this._isAuthenticated;
	}

	public get sessionId(): string | null {
		return this._sessionId;
	}

	public get isHealthy(): boolean {
		if (!this._connection?.isConnected) {
			return false;
		}
		if (!this._isAuthenticated) {
			return false;
		}
		if (this.heartbeatInterval > 0) {
			const timeSincePong = (Date.now() - this._lastPongTime) / 1000;
			const maxPongDelay = this.heartbeatInterval * 2;
			if (timeSincePong > maxPongDelay) {
				return false;
			}
		}
		return true;
	}

	/**
	 * Khởi tạo kết nối WebSocket và xác thực người dùng.
	 */
	public async connect(): Promise<void> {
		const url = `${this.baseUrl}/v1/stream?encoding=${this.encoding}`;

		this._connection = new WebSocketConnection({
			url,
			timeout: this.timeout,
			heartbeatInterval: this.heartbeatInterval,
			autoReconnect: this.autoReconnect,
			maxRetries: this.maxRetries,
		});

		await this._connection.connect();

		const welcome = await this._connection.receive(this.timeout * 1000);
		const welcomeData = this._decoder.decode<Record<string, unknown>>(welcome);
		this._sessionId =
			(welcomeData.session_id as string) || (welcomeData.sid as string) || null;

		await this._authenticate();

		this._isDispatcherRunning = true;
		this._lastPongTime = Date.now();

		this._dispatchQueues = Array.from(
			{ length: this._numWorkers },
			() => new AsyncQueue<Record<string, unknown>>(),
		);

		for (let i = 0; i < this._numWorkers; i++) {
			this._startDispatchWorker(i);
		}

		this._startMessageLoop();
		this._startHeartbeatLoop();
	}

	private async _authenticate(): Promise<void> {
		if (!this._connection) {
			throw new ConnectionError("Connection not initialized");
		}

		const authMsg = this._authManager.createAuthMessage();
		const encoded = this._encoder.encode(authMsg);
		await this._connection.send(encoded);

		const response = await this._connection.receive(this.timeout * 1000);
		const data = this._decoder.decode<Record<string, unknown>>(response);
		const action = data.action || data.a;

		if (action === "auth_success") {
			this._isAuthenticated = true;
		} else if (action === "auth_error" || action === "error") {
			const errMsg = data.message || data.msg || "Unknown error";
			throw new AuthenticationError(`Authentication failed: ${errMsg}`);
		} else {
			throw new AuthenticationError(`Unexpected response: ${String(action)}`);
		}
	}

	private _startMessageLoop(): void {
		const runLoop = async () => {
			let reconnectAttempt = 0;
			const maxReconnectDelay = 60;

			while (this._isDispatcherRunning && this._connection) {
				try {
					for await (const message of this._connection) {
						const data = this._decoder.decode<Record<string, unknown>>(message);
						data._receivedAt = Date.now() / 1000;

						const symbol = String(data.Symbol || data.symbol || "");
						const workerIdx = hashSymbol(symbol) % this._numWorkers;
						this._dispatchQueues[workerIdx].push(data);

						reconnectAttempt = 0;
					}
				} catch (e: unknown) {
					if (e instanceof ConnectionClosed) {
						if (this.autoReconnect && e.recoverable) {
							reconnectAttempt++;
							this.emit("reconnecting", {
								attempt: reconnectAttempt,
								maxRetries: this.maxRetries,
								delay: 0,
								error: e.message,
							} satisfies ReconnectingEventData);

							try {
								await this._handleReconnection();
								reconnectAttempt = 0;
							} catch (reconnectErr) {
								this.emit("error", reconnectErr);
								break;
							}
						} else {
							this.emit("error", e);
							break;
						}
					} else {
						this.emit("error", e);
						if (!this.autoReconnect) {
							break;
						}

						if (this._isConnectionError(e)) {
							reconnectAttempt++;
							if (reconnectAttempt > this.maxRetries) {
								this.emit("max_reconnect_exceeded", reconnectAttempt);
								break;
							}

							const delay = Math.min(
								2 ** (reconnectAttempt - 1),
								maxReconnectDelay,
							);
							this.emit("reconnecting", {
								attempt: reconnectAttempt,
								maxRetries: this.maxRetries,
								delay,
								error: e instanceof Error ? e.message : String(e),
							} satisfies ReconnectingEventData);

							await new Promise((resolve) => setTimeout(resolve, delay * 1000));

							try {
								await this._handleReconnection();
								reconnectAttempt = 0;
							} catch {}
						} else {
							break;
						}
					}
				}
			}
		};

		runLoop().catch((err) => {
			this.emit("error", err);
		});
	}

	private _startDispatchWorker(workerIdx: number): void {
		const queue = this._dispatchQueues[workerIdx];
		const workerLoop = async () => {
			while (this._isDispatcherRunning) {
				try {
					const data = await queue.shift(1000);
					if (data && this._isDispatcherRunning) {
						await this._dispatchMessage(data);
					}
				} catch (err: unknown) {
					this.emit("error", err);
				}
			}
		};

		workerLoop().catch((err) => {
			this.emit("error", err);
		});
	}

	private async _dispatchMessage(data: Record<string, unknown>): Promise<void> {
		const action = data.action || data.a;
		const msgType = data.T as string | undefined;

		if (action === "subscribed") {
			this.emit("subscribed", data);
		} else if (action === "ping") {
			if (this._connection) {
				await this._connection.send(this._encoder.encode({ action: "pong" }));
			}
		} else if (action === "pong") {
			this._lastPongTime = Date.now();
		} else if (action === "error") {
			const errorMsg = String(data.message || data.msg || "Server error");
			this.emit("error", new Error(errorMsg));
		} else if (msgType && msgType in MSG_TYPE_MAP) {
			const { event, parser, field } = MSG_TYPE_MAP[msgType];
			let targetPayload = data;

			if (field && typeof data[field] === "object" && data[field] !== null) {
				targetPayload = {
					...(data[field] as Record<string, unknown>),
					_receivedAt: data._receivedAt,
				};
			}

			const obj = parser(targetPayload);
			this.emit(event, obj);

			// Phản hồi thêm alias cho đơn hàng và vị thế
			if (event === "order_event") {
				this.emit("order", obj);
			}
			if (event === "position_event") {
				this.emit("position", obj);
			}

			// Đẩy vào async queue nếu không có listener callback
			if (this.listenerCount(event) === 0) {
				const q = this._queues.get(event);
				if (q) {
					q.push(obj);
				}
				const generalQ = this._queues.get("*");
				if (generalQ) {
					generalQ.push(obj);
				}
			}
		}
	}

	private _startHeartbeatLoop(): void {
		if (this.heartbeatInterval <= 0) return;

		if (this._heartbeatTimer) {
			clearInterval(this._heartbeatTimer);
		}

		this._heartbeatTimer = setInterval(async () => {
			if (this._isDispatcherRunning && this._connection?.isConnected) {
				try {
					const pingMsg = this._encoder.encode({ action: "ping" });
					await this._connection.send(pingMsg);
				} catch {
					// Message loop sẽ bắt lỗi đóng kết nối
				}
			}
		}, this.heartbeatInterval * 1000);
	}

	private async _handleReconnection(): Promise<void> {
		if (this._reconnectLoopActive) return;
		this._reconnectLoopActive = true;

		try {
			const previousSubscriptions = new Map(this._subscriptions);
			this._isAuthenticated = false;

			if (!this._connection) return;

			await this._connection.connect();
			const welcome = await this._connection.receive(this.timeout * 1000);
			const welcomeData =
				this._decoder.decode<Record<string, unknown>>(welcome);
			this._sessionId =
				(welcomeData.session_id as string) ||
				(welcomeData.sid as string) ||
				null;

			await this._authenticate();

			// Đăng ký lại toàn bộ kênh
			for (const [channel, sub] of previousSubscriptions.entries()) {
				await this._subscribeChannel(channel, sub.symbols, sub.kwargs);
			}

			this._lastPongTime = Date.now();
			this.emit("reconnected", { sessionId: this._sessionId });
		} finally {
			this._reconnectLoopActive = false;
		}
	}

	private _isConnectionError(error: unknown): boolean {
		if (error instanceof ConnectionError || error instanceof ConnectionClosed) {
			return true;
		}
		const msg = String(error).toLowerCase();
		const keywords = [
			"connection",
			"network",
			"socket",
			"timeout",
			"reset",
			"refused",
			"closed",
			"broken pipe",
			"eof",
			"disconnect",
		];
		return keywords.some((kw) => msg.includes(kw));
	}

	private _makeFilteredHandler<T>(
		boardId: string | null | undefined,
		attr: string,
		handler: (obj: T) => void,
	): (obj: T) => void {
		if (!boardId) return handler;
		return (obj: T) => {
			if ((obj as Record<string, unknown>)[attr] === boardId) {
				handler(obj);
			}
		};
	}

	/**
	 * Đăng ký kênh WebSocket tổng quát
	 */
	public async _subscribeChannel(
		channel: string,
		symbols: string[],
		kwargs?: Record<string, unknown>,
	): Promise<void> {
		if (!this._isAuthenticated || !this._connection) {
			throw new SubscriptionError("Must authenticate before subscribing");
		}

		const subscribeMsg = {
			action: "subscribe",
			channels: [{ name: channel, symbols, ...(kwargs ?? {}) }],
		};

		const encoded = this._encoder.encode(subscribeMsg);
		await this._connection.send(encoded);

		this._subscriptions.set(channel, { symbols, kwargs });
	}

	/**
	 * Hủy đăng ký kênh WebSocket
	 */
	public async unsubscribe(channel: string, symbols: string[]): Promise<void> {
		if (!this._connection) return;

		const unsubscribeMsg = {
			action: "unsubscribe",
			channels: [{ name: channel, symbols }],
		};

		const encoded = this._encoder.encode(unsubscribeMsg);
		await this._connection.send(encoded);

		const stored = this._subscriptions.get(channel);
		if (stored) {
			stored.symbols = stored.symbols.filter((s) => !symbols.includes(s));
			if (stored.symbols.length === 0) {
				this._subscriptions.delete(channel);
			}
		}
	}

	/**
	 * Đăng ký luồng khớp lệnh (Trade)
	 */
	public async subscribeTrades(
		symbols: string[],
		onTrade?: (trade: Trade) => void,
		encoding: WebSocketEncoding = "json",
		boardId?: string | null,
	): Promise<void> {
		const boards = boardId ? [boardId] : DEFAULT_BOARDS;

		for (const board of boards) {
			const channel = `tick.${board}.${encoding}`;
			await this._subscribeChannel(channel, symbols);
		}

		if (onTrade) {
			const handler = this._makeFilteredHandler(boardId, "boardId", onTrade);
			this.on("trade", handler as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký luồng thông tin khớp lệnh mở rộng (TradeExtra)
	 */
	public async subscribeTradeExtra(
		symbols: string[],
		onTradeExtra?: (tradeExtra: TradeExtra) => void,
		encoding: WebSocketEncoding = "json",
		boardId?: string | null,
	): Promise<void> {
		const boards = boardId ? [boardId] : DEFAULT_BOARDS;

		for (const board of boards) {
			const channel = `tick_extra.${board}.${encoding}`;
			await this._subscribeChannel(channel, symbols);
		}

		if (onTradeExtra) {
			const handler = this._makeFilteredHandler(
				boardId,
				"boardId",
				onTradeExtra,
			);
			this.on("trade_extra", handler as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký luồng giá dự kiến (Expected Price)
	 */
	public async subscribeExpectedPrice(
		symbols: string[],
		onExpectedPrice?: (expectedPrice: ExpectedPrice) => void,
		encoding: WebSocketEncoding = "json",
		boardId?: string | null,
	): Promise<void> {
		const boards = boardId ? [boardId] : DEFAULT_BOARDS;

		for (const board of boards) {
			const channel = `expected_price.${board}.${encoding}`;
			await this._subscribeChannel(channel, symbols);
		}

		if (onExpectedPrice) {
			const handler = this._makeFilteredHandler(
				boardId,
				"boardId",
				onExpectedPrice,
			);
			this.on("expected_price", handler as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký sự kiện lệnh tài khoản cá nhân
	 */
	public async subscribeOrderEvent(
		marketType = "STOCK",
		onOrderEvent?: (order: Order) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `order.${marketType}.${encoding}`;
		await this._subscribeChannel(channel, []);

		if (onOrderEvent) {
			this.on("order_event", onOrderEvent as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký sự kiện lệnh tài khoản môi giới
	 */
	public async subscribeBrokerOrderEvent(
		investorId: string,
		marketType = "STOCK",
		onOrderEvent?: (order: Order) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `order.broker.${marketType}.${investorId}.${encoding}`;
		await this._subscribeChannel(channel, []);

		if (onOrderEvent) {
			this.on("order_event", onOrderEvent as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký sự kiện vị thế phái sinh/cổ phiếu
	 */
	public async subscribePositionEvent(
		marketType = "STOCK",
		onPositionEvent?: (position: Position) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `position.${marketType}.${encoding}`;
		await this._subscribeChannel(channel, []);

		if (onPositionEvent) {
			this.on(
				"position_event",
				onPositionEvent as (...args: unknown[]) => void,
			);
		}
	}

	/**
	 * Đăng ký sự kiện vị thế tài khoản môi giới
	 */
	public async subscribeBrokerPositionEvent(
		investorId: string,
		marketType = "STOCK",
		onPositionEvent?: (position: Position) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `position.broker.${marketType}.${investorId}.${encoding}`;
		await this._subscribeChannel(channel, []);

		if (onPositionEvent) {
			this.on(
				"position_event",
				onPositionEvent as (...args: unknown[]) => void,
			);
		}
	}

	/**
	 * Đăng ký định nghĩa chứng khoán (Security Definition)
	 */
	public async subscribeSecDef(
		symbols: string[],
		onSecDef?: (secDef: SecurityDefinition) => void,
		encoding: WebSocketEncoding = "json",
		boardId?: string | null,
	): Promise<void> {
		const boards = boardId ? [boardId] : DEFAULT_BOARDS;

		for (const board of boards) {
			const channel = `security_definition.${board}.${encoding}`;
			await this._subscribeChannel(channel, symbols);
		}

		if (onSecDef) {
			const handler = this._makeFilteredHandler(boardId, "boardId", onSecDef);
			this.on("security_definition", handler as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký biến động chỉ số thị trường (Market Index)
	 */
	public async subscribeMarketIndex(
		marketIndex: string,
		onMarketIndex?: (marketIndex: MarketIndex) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `market_index.${marketIndex}.${encoding}`;
		await this._subscribeChannel(channel, []);

		if (onMarketIndex) {
			this.on("market_index", onMarketIndex as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký chỉ số thị trường ước tính (Estimated Market Index)
	 */
	public async subscribeEstimatedMarketIndex(
		estimatedMarketIndex: string,
		onEstimatedMarketIndex?: (
			estimatedMarketIndex: EstimatedMarketIndex,
		) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `estimated_market_index.${estimatedMarketIndex}.${encoding}`;
		await this._subscribeChannel(channel, []);

		if (onEstimatedMarketIndex) {
			this.on(
				"estimated_market_index",
				onEstimatedMarketIndex as (...args: unknown[]) => void,
			);
		}
	}

	/**
	 * Đăng ký ảnh hưởng của cổ phiếu tới chỉ số (Market Index Influence)
	 */
	public async subscribeMarketIndexInfluence(
		indexName: string,
		resolution = 1,
		onMarketIndexInfluence?: (influence: IndexInfluence) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `market_index_influence.${indexName}.${resolution}.${encoding}`;
		await this._subscribeChannel(channel, []);

		if (onMarketIndexInfluence) {
			this.on(
				"market_index_influence",
				onMarketIndexInfluence as (...args: unknown[]) => void,
			);
		}
	}

	/**
	 * Đăng ký sổ lệnh giá tốt nhất (Quote - Top price)
	 */
	public async subscribeQuotes(
		symbols: string[],
		onQuote?: (quote: Quote) => void,
		encoding: WebSocketEncoding = "json",
		boardId?: string | null,
	): Promise<void> {
		const boards = boardId
			? [boardId]
			: ["G1", "G2", "G3", "G4", "G5", "G6", "G7"];

		for (const board of boards) {
			const channel = `top_price.${board}.${encoding}`;
			await this._subscribeChannel(channel, symbols);
		}

		if (onQuote) {
			const handler = this._makeFilteredHandler(boardId, "boardId", onQuote);
			this.on("quote", handler as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký dữ liệu giao dịch nhà đầu tư nước ngoài (Khối ngoại)
	 */
	public async subscribeForeignTrading(
		symbols: string[],
		boardId = "*",
		onTrade?: (foreign: ForeignInvestor) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `foreign.${boardId}.${encoding}`;
		await this._subscribeChannel(channel, symbols);

		if (onTrade) {
			this.on("foreign", onTrade as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký nến OHLC trực tiếp
	 */
	public async subscribeOhlc(
		symbols: string[],
		resolution?: string | null,
		onOhlc?: (ohlc: Ohlc) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const resolutions = resolution
			? [resolution]
			: ["1", "3", "5", "15", "30", "1H", "1D", "1W"];

		for (const res of resolutions) {
			const channel = `ohlc.${res}.${encoding}`;
			await this._subscribeChannel(channel, symbols);
		}

		if (onOhlc) {
			this.on("ohlc", onOhlc as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký nến OHLC khi đóng nến
	 */
	public async subscribeOhlcClosed(
		symbols: string[],
		resolution?: string | null,
		onOhlc?: (ohlc: Ohlc) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const resolutions = resolution
			? [resolution]
			: ["1", "3", "5", "15", "30", "1H", "1D", "1W"];

		for (const res of resolutions) {
			const channel = `ohlc_closed.${res}.${encoding}`;
			await this._subscribeChannel(channel, symbols);
		}

		if (onOhlc) {
			this.on("ohlc_closed", onOhlc as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký sự kiện phiên giao dịch (Session state)
	 */
	public async subscribeSession(
		productGroupId: string,
		boardId = "*",
		onSession?: (session: Session) => void,
		encoding: WebSocketEncoding = "json",
	): Promise<void> {
		const channel = `session.${productGroupId}.${boardId}.${encoding}`;
		await this._subscribeChannel(channel, []);

		if (onSession) {
			this.on("session", onSession as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký sự kiện cập nhật lệnh
	 */
	public async subscribeOrders(
		onOrder?: (order: Order) => void,
	): Promise<void> {
		await this._subscribeChannel("orders", []);
		if (onOrder) {
			this.on("order", onOrder as (...args: unknown[]) => void);
			this.on("order_event", onOrder as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký sự kiện cập nhật vị thế
	 */
	public async subscribePositions(
		onPosition?: (position: Position) => void,
	): Promise<void> {
		await this._subscribeChannel("positions", []);
		if (onPosition) {
			this.on("position", onPosition as (...args: unknown[]) => void);
			this.on("position_event", onPosition as (...args: unknown[]) => void);
		}
	}

	/**
	 * Đăng ký sự kiện cập nhật tài khoản
	 */
	public async subscribeAccount(
		onAccount?: (account: AccountUpdate) => void,
	): Promise<void> {
		await this._subscribeChannel("account", []);
		if (onAccount) {
			this.on("account", onAccount as (...args: unknown[]) => void);
		}
	}

	/**
	 * Lấy hàng đợi AsyncQueue dành cho event tương ứng (dùng khi consume qua async loop)
	 */
	public queue(event: string): AsyncQueue<unknown> {
		let q = this._queues.get(event);
		if (!q) {
			q = new AsyncQueue<unknown>();
			this._queues.set(event, q);
		}
		return q;
	}

	/**
	 * Đóng kết nối an toàn
	 */
	public async disconnect(): Promise<void> {
		this._isDispatcherRunning = false;

		if (this._heartbeatTimer) {
			clearInterval(this._heartbeatTimer);
			this._heartbeatTimer = null;
		}

		for (const q of this._dispatchQueues) {
			q.clear();
		}
		this._dispatchQueues = [];

		for (const q of this._queues.values()) {
			q.clear();
		}
		this._queues.clear();

		if (this._connection) {
			await this._connection.close();
			this._connection = null;
		}

		this._isAuthenticated = false;
	}
}
