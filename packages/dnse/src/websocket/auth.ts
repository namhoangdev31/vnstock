export interface AuthMessage {
	action: "auth";
	api_key: string;
	signature: string;
	timestamp: number;
	nonce: string;
}

async function hmacSha256Hex(secret: string, message: string): Promise<string> {
	const enc = new TextEncoder();
	const key = await globalThis.crypto.subtle.importKey(
		"raw",
		enc.encode(secret),
		{ name: "HMAC", hash: "SHA-256" },
		false,
		["sign"],
	);
	const sig = await globalThis.crypto.subtle.sign(
		"HMAC",
		key,
		enc.encode(message),
	);
	const bytes = new Uint8Array(sig);
	let hex = "";
	for (let i = 0; i < bytes.length; i++) {
		hex += bytes[i].toString(16).padStart(2, "0");
	}
	return hex;
}

/**
 * Quản lý xác thực HMAC-SHA256 cho kết nối WebSocket DNSE.
 * Hoạt động 100% Isomorphic/Universal trên Web Crypto API chuẩn (Node.js, Bun, Browser).
 */
export class AuthManager {
	public readonly apiKey: string;
	public readonly apiSecret: string;

	constructor(apiKey: string, apiSecret: string) {
		this.apiKey = apiKey;
		this.apiSecret = apiSecret;
	}

	/**
	 * Tạo payload thông điệp xác thực gửi lên máy chủ WebSocket
	 */
	public async createAuthMessage(): Promise<AuthMessage> {
		const timestamp = Math.floor(Date.now() / 1000);
		// Microseconds tương tự int(time.time() * 1000000)
		const nonce = String(
			Math.floor(Date.now() * 1000 + (performance.now() % 1000) * 1000),
		);

		const signature = await this.computeSignature(timestamp, nonce);

		return {
			action: "auth",
			api_key: this.apiKey,
			signature,
			timestamp,
			nonce,
		};
	}

	/**
	 * Tính chữ ký HMAC-SHA256 dạng hex: {api_key}:{timestamp}:{nonce}
	 */
	public async computeSignature(
		timestamp: number,
		nonce: string,
	): Promise<string> {
		const message = `${this.apiKey}:${timestamp}:${nonce}`;
		return hmacSha256Hex(this.apiSecret, message);
	}
}
