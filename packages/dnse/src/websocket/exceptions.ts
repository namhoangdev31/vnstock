export class TradingWebSocketError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "TradingWebSocketError";
	}
}

export class ConnectionError extends TradingWebSocketError {
	constructor(message: string) {
		super(message);
		this.name = "ConnectionError";
	}
}

export class ConnectionClosed extends TradingWebSocketError {
	public readonly recoverable: boolean;

	constructor(message: string, recoverable = false) {
		super(message);
		this.name = "ConnectionClosed";
		this.recoverable = recoverable;
	}
}

export class AuthenticationError extends TradingWebSocketError {
	constructor(message: string) {
		super(message);
		this.name = "AuthenticationError";
	}
}

export class SubscriptionError extends TradingWebSocketError {
	constructor(message: string) {
		super(message);
		this.name = "SubscriptionError";
	}
}

export class EncodingError extends TradingWebSocketError {
	constructor(message: string) {
		super(message);
		this.name = "EncodingError";
	}
}
