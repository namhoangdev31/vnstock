import { EncodingError } from "./exceptions";

/** Định dạng encoding được hỗ trợ bởi DNSE WebSocket. */
export type WebSocketEncoding = "json" | "msgpack";

/**
 * Mã hoá message gửi lên WebSocket Server DNSE (JSON).
 */
export class MessageEncoder {
	public readonly encoding: WebSocketEncoding = "json";

	public encode(data: unknown): string {
		try {
			return JSON.stringify(data);
		} catch (e: unknown) {
			throw new EncodingError(
				`Failed to encode message: ${e instanceof Error ? e.message : String(e)}`,
			);
		}
	}
}

/**
 * Giải mã message nhận từ WebSocket Server DNSE (JSON).
 * Hỗ trợ: string, ArrayBuffer, Buffer (Node.js/Bun).
 */
export class MessageDecoder {
	public readonly encoding: WebSocketEncoding = "json";

	public decode<T = Record<string, unknown>>(
		data: string | ArrayBuffer | Buffer,
	): T {
		try {
			let text: string;
			if (typeof data === "string") {
				text = data;
			} else if (typeof Buffer !== "undefined" && Buffer.isBuffer(data)) {
				text = data.toString("utf-8");
			} else {
				text = new TextDecoder("utf-8").decode(data as ArrayBuffer);
			}
			return JSON.parse(text) as T;
		} catch (e: unknown) {
			throw new EncodingError(
				`Failed to decode message: ${e instanceof Error ? e.message : String(e)}`,
			);
		}
	}
}
