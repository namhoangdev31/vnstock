import { createHmac, randomUUID } from "node:crypto";

export const DEFAULT_API_VERSION = "2026-07-23";

/**
 * Lấy tên header ngày tháng (mặc định 'Date' hoặc cấu hình qua env DATE_HEADER)
 */
export function getDateHeaderName(): string {
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
 * Format ngày tháng theo chuẩn RFC 2822 UTC (+0000) giống hệt Python datetime.strftime('%a, %d %b %Y %H:%M:%S %z')
 */
export function formatDnseDate(date: Date = new Date()): string {
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

	const dayName = days[date.getUTCDay()];
	const day = String(date.getUTCDate()).padStart(2, "0");
	const monthName = months[date.getUTCMonth()];
	const year = date.getUTCFullYear();
	const hours = String(date.getUTCHours()).padStart(2, "0");
	const minutes = String(date.getUTCMinutes()).padStart(2, "0");
	const seconds = String(date.getUTCSeconds()).padStart(2, "0");

	return `${dayName}, ${day} ${monthName} ${year} ${hours}:${minutes}:${seconds} +0000`;
}

export type SupportedAlgorithm =
	| "hmac-sha256"
	| "hmac-sha384"
	| "hmac-sha512"
	| "hmac-sha1";

/**
 * Xây dựng chữ ký HMAC xác thực yêu cầu gửi lên DNSE API
 */
export function buildSignature(
	secret: string,
	method: string,
	path: string,
	dateValue: string,
	algorithm: SupportedAlgorithm = "hmac-sha256",
	nonce?: string | null,
	headerName?: string,
): { headers: string; signature: string } {
	const actualHeaderName = headerName || getDateHeaderName();
	const headerKey = actualHeaderName.toLowerCase();
	const headers = `(request-target) ${headerKey}`;

	let signatureString = `(request-target): ${method.toLowerCase()} ${path}\n${headerKey}: ${dateValue}`;
	if (nonce) {
		signatureString += `\nnonce: ${nonce}`;
	}

	let hashAlgo = "sha256";
	if (algorithm === "hmac-sha384") {
		hashAlgo = "sha384";
	} else if (algorithm === "hmac-sha512") {
		hashAlgo = "sha512";
	} else if (algorithm === "hmac-sha1") {
		hashAlgo = "sha1";
	}

	const mac = createHmac(hashAlgo, Buffer.from(secret, "utf-8"));
	mac.update(Buffer.from(signatureString, "utf-8"));
	const encoded = mac.digest("base64");
	const escaped = encodeURIComponent(encoded);

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

	const nonce = hmacNonceEnabled ? randomUUID().replace(/-/g, "") : null;
	const { headers: headersList, signature } = buildSignature(
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
