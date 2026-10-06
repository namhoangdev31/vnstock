import { ConnectionClosed, ConnectionError } from "./exceptions";

export interface WebSocketConnectionOptions {
	url: string;
	timeout?: number;
	heartbeatInterval?: number;
	autoReconnect?: boolean;
	maxRetries?: number;
}

interface PendingReceiver {
	resolve: (data: string | ArrayBuffer) => void;
	reject: (err: Error) => void;
	timer?: ReturnType<typeof setTimeout> | null;
}

/**
 * Quản lý kết nối WebSocket bằng Native WebSocket API chuẩn toàn cầu.
 * Chạy đồng nhất trên Node.js 22+, Bun, Deno, Next.js và Vue (trình duyệt).
 */
export class WebSocketConnection {
	public readonly url: string;
	public readonly timeout: number;
	public readonly heartbeatInterval: number;
	public readonly autoReconnect: boolean;
	public readonly maxRetries: number;

	private _ws: WebSocket | null = null;
	private _retryCount = 0;
	private _isConnected = false;
	private _isClosing = false;

	private _messageQueue: (string | ArrayBuffer)[] = [];
	private _pendingReceivers: PendingReceiver[] = [];

	constructor(options: WebSocketConnectionOptions) {
		this.url = options.url;
		this.timeout = options.timeout ?? 60.0;
		this.heartbeatInterval = options.heartbeatInterval ?? 25.0;
		this.autoReconnect = options.autoReconnect ?? true;
		this.maxRetries = options.maxRetries ?? 10;
	}

	public get isConnected(): boolean {
		return (
			this._isConnected &&
			this._ws !== null &&
			this._ws.readyState ===
				(typeof WebSocket !== "undefined" ? WebSocket.OPEN : 1)
		);
	}

	public get rawSocket(): WebSocket | null {
		return this._ws;
	}

	/**
	 * Thiết lập kết nối WebSocket với retry và exponential backoff.
	 */
	public async connect(): Promise<void> {
		this._isClosing = false;

		while (this._retryCount < this.maxRetries) {
			try {
				await this._createSocket();
				this._isConnected = true;
				this._retryCount = 0;
				return;
			} catch (e: unknown) {
				this._retryCount++;
				if (this._retryCount >= this.maxRetries) {
					throw new ConnectionError(
						`Failed to connect after ${this.maxRetries} attempts: ${e instanceof Error ? e.message : String(e)}`,
					);
				}

				// Exponential backoff: 1s, 2s, 4s, ... tối đa 60s
				const delay = Math.min(2 ** (this._retryCount - 1), 60);
				await new Promise((resolve) => setTimeout(resolve, delay * 1000));
			}
		}
	}

	private async _createSocket(): Promise<WebSocket> {
		const WS = this._getWebSocketConstructor();

		return new Promise((resolve, reject) => {
			let isSettled = false;
			let timeoutTimer: ReturnType<typeof setTimeout> | null = null;

			try {
				const ws = new WS(this.url);

				if (this.timeout > 0) {
					timeoutTimer = setTimeout(() => {
						if (!isSettled) {
							isSettled = true;
							try {
								ws.close();
							} catch {}
							reject(
								new ConnectionError(
									`Connection timeout after ${this.timeout}s`,
								),
							);
						}
					}, this.timeout * 1000);
				}

				ws.onopen = () => {
					if (!isSettled) {
						isSettled = true;
						if (timeoutTimer) clearTimeout(timeoutTimer);
						this._ws = ws;
						this._setupSocketListeners(ws);
						resolve(ws);
					}
				};

				ws.onerror = (event: Event) => {
					if (!isSettled) {
						isSettled = true;
						if (timeoutTimer) clearTimeout(timeoutTimer);
						const errMsg =
							(event as { message?: string }).message ||
							"WebSocket handshake failed";
						reject(new ConnectionError(errMsg));
					}
				};
			} catch (err: unknown) {
				if (timeoutTimer) clearTimeout(timeoutTimer);
				reject(
					new ConnectionError(
						`Failed to instantiate WebSocket: ${err instanceof Error ? err.message : String(err)}`,
					),
				);
			}
		});
	}

	private _setupSocketListeners(ws: WebSocket): void {
		ws.onmessage = (event: MessageEvent) => {
			const data = event.data;
			const receiver = this._pendingReceivers.shift();
			if (receiver) {
				if (receiver.timer) clearTimeout(receiver.timer);
				receiver.resolve(data);
			} else {
				this._messageQueue.push(data);
			}
		};

		ws.onclose = (event: CloseEvent) => {
			this._isConnected = false;
			if (this._isClosing) return;

			const code = event.code;
			let recoverable = false;

			if (code === 1000 || code === 1001) {
				recoverable = false;
			} else if (code === 1006 || code === 1011 || code === 1012) {
				recoverable = this.autoReconnect;
			} else {
				recoverable = this.autoReconnect;
			}

			const err = new ConnectionClosed(
				`Connection closed: ${code}${event.reason ? ` (${event.reason})` : ""}`,
				recoverable,
			);

			while (this._pendingReceivers.length > 0) {
				const receiver = this._pendingReceivers.shift();
				if (receiver) {
					if (receiver.timer) clearTimeout(receiver.timer);
					receiver.reject(err);
				}
			}
		};

		ws.onerror = (event: Event) => {
			if (this._isConnected) {
				const errMsg =
					(event as { message?: string }).message || "WebSocket error";
				const err = new ConnectionError(errMsg);
				while (this._pendingReceivers.length > 0) {
					const receiver = this._pendingReceivers.shift();
					if (receiver) {
						if (receiver.timer) clearTimeout(receiver.timer);
						receiver.reject(err);
					}
				}
			}
		};
	}

	/**
	 * Gửi dữ liệu qua WebSocket
	 */
	public async send(message: string | ArrayBuffer | Uint8Array): Promise<void> {
		if (!this._ws || !this.isConnected) {
			throw new ConnectionError("Not connected");
		}
		this._ws.send(message);
	}

	/**
	 * Đợi nhận thông điệp tiếp theo từ hàng đợi
	 */
	public async receive(timeoutMs?: number): Promise<string | ArrayBuffer> {
		if (!this.isConnected && this._messageQueue.length === 0) {
			throw new ConnectionError("Not connected");
		}

		const queuedMsg = this._messageQueue.shift();
		if (queuedMsg !== undefined) {
			return queuedMsg;
		}

		return new Promise((resolve, reject) => {
			const receiver: PendingReceiver = {
				resolve,
				reject,
				timer: null,
			};

			if (timeoutMs && timeoutMs > 0) {
				receiver.timer = setTimeout(() => {
					const idx = this._pendingReceivers.indexOf(receiver);
					if (idx !== -1) {
						this._pendingReceivers.splice(idx, 1);
					}
					reject(new ConnectionError(`Receive timed out after ${timeoutMs}ms`));
				}, timeoutMs);
			}

			this._pendingReceivers.push(receiver);
		});
	}

	/**
	 * Đóng kết nối an toàn
	 */
	public async close(): Promise<void> {
		this._isClosing = true;
		this._isConnected = false;

		if (this._ws) {
			try {
				this._ws.close(1000, "Normal closure");
			} catch {}
			this._ws = null;
		}

		const err = new ConnectionClosed("Connection closed normally: 1000", false);
		while (this._pendingReceivers.length > 0) {
			const receiver = this._pendingReceivers.shift();
			if (receiver) {
				if (receiver.timer) clearTimeout(receiver.timer);
				receiver.reject(err);
			}
		}
		this._messageQueue = [];
	}

	/**
	 * Hỗ trợ async iterator: for await (const msg of connection)
	 */
	public async *[Symbol.asyncIterator](): AsyncGenerator<
		string | ArrayBuffer,
		void,
		unknown
	> {
		while (this._isConnected) {
			try {
				const msg = await this.receive();
				yield msg;
			} catch (e: unknown) {
				if (e instanceof ConnectionClosed && e.recoverable) {
					throw e;
				}
				break;
			}
		}
	}

	private _getWebSocketConstructor(): typeof WebSocket {
		if (typeof WebSocket !== "undefined") {
			return WebSocket;
		}
		if (
			typeof globalThis !== "undefined" &&
			(globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket
		) {
			return (globalThis as unknown as { WebSocket: typeof WebSocket })
				.WebSocket;
		}
		throw new ConnectionError(
			"WebSocket is not available in the current runtime environment. Please provide a global WebSocket polyfill.",
		);
	}
}
