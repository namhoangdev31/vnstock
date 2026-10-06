import { EncodingError } from "./exceptions";

export type WebSocketEncoding = "json" | "msgpack";

export class MessageEncoder {
	public readonly encoding: WebSocketEncoding;

	constructor(encoding: WebSocketEncoding = "json") {
		if (encoding !== "json" && encoding !== "msgpack") {
			throw new ValueError(
				`Invalid encoding: ${encoding}. Must be 'json' or 'msgpack'`,
			);
		}
		this.encoding = encoding;
	}

	public encode(data: unknown): string {
		try {
			if (this.encoding === "json") {
				return JSON.stringify(data);
			}
			// Mặc định fallback JSON nếu chưa cài msgpack binary
			return JSON.stringify(data);
		} catch (e: unknown) {
			throw new EncodingError(
				`Failed to encode message: ${e instanceof Error ? e.message : String(e)}`,
			);
		}
	}
}

export class MessageDecoder {
	public readonly encoding: WebSocketEncoding;

	constructor(encoding: WebSocketEncoding = "json") {
		if (encoding !== "json" && encoding !== "msgpack") {
			throw new ValueError(
				`Invalid encoding: ${encoding}. Must be 'json' or 'msgpack'`,
			);
		}
		this.encoding = encoding;
	}

	public decode<T = Record<string, unknown>>(
		data: string | ArrayBuffer | Buffer,
	): T {
		try {
			let text: string;
			if (typeof data === "string") {
				text = data;
			} else if (Buffer.isBuffer(data)) {
				text = data.toString("utf-8");
			} else {
				text = new TextDecoder().decode(data);
			}
			return JSON.parse(text) as T;
		} catch (e: unknown) {
			throw new EncodingError(
				`Failed to decode message: ${e instanceof Error ? e.message : String(e)}`,
			);
		}
	}
}

class ValueError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "ValueError";
	}
}
