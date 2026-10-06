import { decode as decodeMsgpack } from "@msgpack/msgpack";
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
 * Giải mã message nhận từ WebSocket Server DNSE.
 * Tự động nhận diện và giải mã cả JSON (chuỗi text) lẫn MsgPack (nhị phân ArrayBuffer/Buffer/Uint8Array).
 */
export class MessageDecoder {
	public readonly encoding: WebSocketEncoding;

	constructor(encoding: WebSocketEncoding = "json") {
		this.encoding = encoding;
	}

	public decode<T = Record<string, unknown>>(
		data: string | ArrayBuffer | Uint8Array | Buffer,
	): T {
		try {
			if (typeof data === "string") {
				return JSON.parse(data) as T;
			}

			let uint8: Uint8Array;
			if (data instanceof Uint8Array) {
				uint8 = data;
			} else if (data instanceof ArrayBuffer) {
				uint8 = new Uint8Array(data);
			} else if (typeof Buffer !== "undefined" && Buffer.isBuffer(data)) {
				const buf = data as unknown as {
					buffer: ArrayBuffer;
					byteOffset: number;
					byteLength: number;
				};
				uint8 = new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
			} else {
				uint8 = new Uint8Array(data as ArrayBuffer);
			}

			if (uint8.length > 0 && (uint8[0] === 0x7b || uint8[0] === 0x5b)) {
				try {
					const text = new TextDecoder("utf-8").decode(uint8);
					return JSON.parse(text) as T;
				} catch {
					// Fall  to msgpack decoding
				}
			}

			try {
				return decodeMsgpack(uint8) as T;
			} catch {
				const text = new TextDecoder("utf-8").decode(uint8);
				return JSON.parse(text) as T;
			}
		} catch (e: unknown) {
			throw new EncodingError(
				`Failed to decode message: ${e instanceof Error ? e.message : String(e)}`,
			);
		}
	}
}
