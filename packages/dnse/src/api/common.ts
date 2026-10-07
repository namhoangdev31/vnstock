export const DEFAULT_API_VERSION = "2026-07-23";

/**
 * Tạo chuỗi UUID/Nonce ngẫu nhiên an toàn trên mọi runtime (Browser, Node, Bun).
 */
export function generateNonce(): string {
	if (typeof globalThis.crypto?.randomUUID === "function") {
		return globalThis.crypto.randomUUID().replace(/-/g, "");
	}
	const bytes = new Uint8Array(16);
	if (globalThis.crypto?.getRandomValues) {
		globalThis.crypto.getRandomValues(bytes);
	} else {
		for (let i = 0; i < 16; i++) {
			bytes[i] = Math.floor(Math.random() * 256);
		}
	}
	return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Lấy tên header ngày tháng (mặc định 'X-Aux-Date' trên Browser, 'Date' trên Server hoặc qua env DATE_HEADER)
 */
export function getDateHeaderName(): string {
	if (typeof window !== "undefined") {
		return "X-Aux-Date";
	}
	if (typeof process !== "undefined" && process.env?.DATE_HEADER) {
		return process.env.DATE_HEADER;
	}
	return "Date";
}

/**
 * Lấy phiên bản API mặc định hoặc từ biến môi trường
 */
export function getApiVersion(): string {
	if (typeof process !== "undefined" && process.env?.DNSE_API_VERSION) {
		return process.env.DNSE_API_VERSION;
	}
	return DEFAULT_API_VERSION;
}

/**
 * Format ngày tháng theo chuẩn RFC 2822 / RFC 1123 múi giờ Việt Nam UTC+7 (GMT+7)
 */
export function formatDnseDate(date: Date = new Date()): string {
	const vnTime = new Date(date.getTime() + 7 * 60 * 60 * 1000);
	const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
	const months = [
		"Jan",
		"Feb",
		"Mar",
		"Apr",
		"May",
		"Jun",
		"Jul",
		"Aug",
		"Sep",
		"Oct",
		"Nov",
		"Dec",
	];

	const dayName = days[vnTime.getUTCDay()];
	const day = String(vnTime.getUTCDate()).padStart(2, "0");
	const monthName = months[vnTime.getUTCMonth()];
	const year = vnTime.getUTCFullYear();
	const hours = String(vnTime.getUTCHours()).padStart(2, "0");
	const minutes = String(vnTime.getUTCMinutes()).padStart(2, "0");
	const seconds = String(vnTime.getUTCSeconds()).padStart(2, "0");

	return `${dayName}, ${day} ${monthName} ${year} ${hours}:${minutes}:${seconds} GMT+7`;
}

export type SupportedAlgorithm =
	| "hmac-sha256"
	| "hmac-sha384"
	| "hmac-sha512"
	| "hmac-sha1";

/**
 * Xây dựng chữ ký HMAC xác thực yêu cầu gửi lên DNSE API.
 * Hoạt động 100% Isomorphic/Universal trên Web Crypto API chuẩn.
 */
export async function buildSignature(
	secret: string,
	method: string,
	path: string,
	dateValue: string,
	algorithm: SupportedAlgorithm = "hmac-sha256",
	nonce?: string | null,
	headerName?: string,
): Promise<{ headers: string; signature: string }> {
	const actualHeaderName = headerName || getDateHeaderName();
	const headerKey = actualHeaderName.toLowerCase();
	const headers = `(request-target) ${headerKey}`;

	let signatureString = `(request-target): ${method.toLowerCase()} ${path}\n${headerKey}: ${dateValue}`;
	if (nonce) {
		signatureString += `\nnonce: ${nonce}`;
	}

	let hashAlgo = "SHA-256";
	if (algorithm === "hmac-sha384") {
		hashAlgo = "SHA-384";
	} else if (algorithm === "hmac-sha512") {
		hashAlgo = "SHA-512";
	} else if (algorithm === "hmac-sha1") {
		hashAlgo = "SHA-1";
	}

	const enc = new TextEncoder();
	const key = await globalThis.crypto.subtle.importKey(
		"raw",
		enc.encode(secret),
		{ name: "HMAC", hash: hashAlgo },
		false,
		["sign"],
	);
	const sig = await globalThis.crypto.subtle.sign(
		"HMAC",
		key,
		enc.encode(signatureString),
	);
	const bytes = new Uint8Array(sig);
	let binary = "";
	const len = bytes.byteLength;
	for (let i = 0; i < len; i++) {
		binary += String.fromCharCode(bytes[i]);
	}
	const base64 =
		typeof btoa !== "undefined"
			? btoa(binary)
			: Buffer.from(binary, "binary").toString("base64");
	const escaped = base64
		.replace(/\+/g, "%2B")
		.replace(/\//g, "%2F")
		.replace(/=/g, "%3D");

	return { headers, signature: escaped };
}

export interface SendSignedRequestOptions {
	url: string;
	method: string;
	headers?: Record<string, string>;
	body?: unknown;
	apiKey: string;
	apiSecret: string;
	algorithm?: SupportedAlgorithm;
	hmacNonceEnabled?: boolean;
}

/**
 * Gửi HTTP request đã ký chữ ký bảo mật tới DNSE
 */
export async function sendSignedRequest(
	options: SendSignedRequestOptions,
): Promise<{ status: number; data: string }> {
	const {
		url,
		method,
		headers: inputHeaders = {},
		body,
		apiKey,
		apiSecret,
		algorithm = "hmac-sha256",
		hmacNonceEnabled = true,
	} = options;

	const debug =
		typeof process !== "undefined" &&
		process.env?.DEBUG?.toLowerCase() === "true";

	const reqHeaders: Record<string, string> = {
		...inputHeaders,
		version: inputHeaders.version || getApiVersion(),
	};

	const parsedUrl = new URL(url);
	const path = parsedUrl.pathname;
	const dateValue = formatDnseDate();
	const dateHeaderName = getDateHeaderName();

	const nonce = hmacNonceEnabled ? generateNonce() : null;
	const { headers: headersList, signature } = await buildSignature(
		apiSecret,
		method,
		path,
		dateValue,
		algorithm,
		nonce,
		dateHeaderName,
	);

	let signatureHeaderValue = `Signature keyId="${apiKey}",algorithm="${algorithm}",headers="${headersList}",signature="${signature}"`;
	if (nonce) {
		signatureHeaderValue += `,nonce="${nonce}"`;
	}

	reqHeaders[dateHeaderName] = dateValue;
	reqHeaders["X-Signature"] = signatureHeaderValue;
	reqHeaders["x-api-key"] = apiKey;

	let bodyData: string | undefined;
	if (body !== undefined && body !== null) {
		bodyData = JSON.stringify(body);
		reqHeaders["Content-Type"] = "application/json";
	}

	if (debug) {
		console.log("DEBUG url:", url);
		console.log("DEBUG method:", method);
		console.log("DEBUG headers:", reqHeaders);
		console.log("DEBUG body:", body);
	}

	const response = await fetch(url, {
		method,
		headers: reqHeaders,
		body: bodyData,
	});

	const bodyText = await response.text();
	if (debug) {
		console.log("DEBUG status:", response.status);
		console.log("DEBUG response:", bodyText);
	}

	return {
		status: response.status,
		data: bodyText,
	};
}
