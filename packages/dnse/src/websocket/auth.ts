import { createHmac } from "node:crypto";

export interface AuthMessage {
	action: "auth";
	api_key: string;
	signature: string;
	timestamp: number;
	nonce: string;
}

/**
 * Quản lý xác thực HMAC-SHA256 cho kết nối WebSocket DNSE.
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
	public createAuthMessage(): AuthMessage {
		const timestamp = Math.floor(Date.now() / 1000);
		// Microseconds tương tự int(time.time() * 1000000)
		const nonce = String(
			Math.floor(Date.now() * 1000 + (performance.now() % 1000) * 1000),
		);

		const signature = this.computeSignature(timestamp, nonce);

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
	public computeSignature(timestamp: number, nonce: string): string {
		const message = `${this.apiKey}:${timestamp}:${nonce}`;
		return createHmac("sha256", this.apiSecret).update(message).digest("hex");
	}
}
