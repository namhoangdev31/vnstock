import type {
	AxiosError,
	AxiosInstance,
	AxiosRequestHeaders,
	AxiosResponse,
	AxiosStatic,
	CreateAxiosDefaults,
} from "axios";

import type { Auth } from "../core/auth.gen";
import type {
	ServerSentEventsOptions,
	ServerSentEventsResult,
} from "../core/serverSentEvents.gen";
import type {
	Client as CoreClient,
	Config as CoreConfig,
} from "../core/types.gen";

export interface Config<T extends ClientOptions = ClientOptions>
	extends Omit<CreateAxiosDefaults, "auth" | "baseURL" | "headers" | "method">,
		CoreConfig {
	axios?: AxiosStatic | AxiosInstance;

	baseURL?: T["baseURL"];

	headers?:
		| AxiosRequestHeaders
		| Record<
				string,
				| string
				| number
				| boolean
				| (string | number | boolean)[]
				| null
				| undefined
				| unknown
		  >;

	throwOnError?: T["throwOnError"];
}

export interface RequestOptions<
	TData = unknown,
	ThrowOnError extends boolean = boolean,
	Url extends string = string,
> extends Config<{
			throwOnError: ThrowOnError;
		}>,
		Pick<
			ServerSentEventsOptions<TData>,
			| "onRequest"
			| "onSseError"
			| "onSseEvent"
			| "sseDefaultRetryDelay"
			| "sseMaxRetryAttempts"
			| "sseMaxRetryDelay"
		> {
	body?: unknown;
	path?: Record<string, unknown>;
	query?: Record<string, unknown>;

	security?: ReadonlyArray<Auth>;
	url: Url;
}

export interface ClientOptions {
	baseURL?: string;
	throwOnError?: boolean;
}

export type RequestResult<
	TData = unknown,
	TError = unknown,
	ThrowOnError extends boolean = boolean,
> = ThrowOnError extends true
	? Promise<
			AxiosResponse<
				TData extends Record<string, unknown> ? TData[keyof TData] : TData
			>
		>
	: Promise<
			| (AxiosResponse<
					TData extends Record<string, unknown> ? TData[keyof TData] : TData
			  > & {
					error: undefined;
			  })
			| (AxiosError<
					TError extends Record<string, unknown> ? TError[keyof TError] : TError
			  > & {
					data: undefined;
					error: TError extends Record<string, unknown>
						? TError[keyof TError]
						: TError;
			  })
		>;

type MethodFn = <
	TData = unknown,
	TError = unknown,
	ThrowOnError extends boolean = false,
>(
	options: Omit<RequestOptions<TData, ThrowOnError>, "method">,
) => RequestResult<TData, TError, ThrowOnError>;

type SseFn = <
	TData = unknown,
	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	_TError = unknown,
	ThrowOnError extends boolean = false,
>(
	options: Omit<RequestOptions<never, ThrowOnError>, "method">,
) => Promise<ServerSentEventsResult<TData>>;

type RequestFn = <
	TData = unknown,
	TError = unknown,
	ThrowOnError extends boolean = false,
>(
	options: Omit<RequestOptions<TData, ThrowOnError>, "method"> &
		Pick<Required<RequestOptions<TData, ThrowOnError>>, "method">,
) => RequestResult<TData, TError, ThrowOnError>;

type BuildUrlFn = <
	TData extends {
		path?: Record<string, unknown>;
		query?: Record<string, unknown>;
		url: string;
	},
>(
	options: TData &
		Pick<
			RequestOptions<unknown, boolean>,
			"axios" | "baseURL" | "paramsSerializer" | "querySerializer"
		>,
) => string;

export type Client = CoreClient<
	RequestFn,
	Config,
	MethodFn,
	BuildUrlFn,
	SseFn
> & {
	instance: AxiosInstance;
};

export type CreateClientConfig<T extends ClientOptions = ClientOptions> = (
	override?: Config<ClientOptions & T>,
) => Config<Required<ClientOptions> & T>;

export interface TDataShape {
	body?: unknown;
	headers?: unknown;
	path?: unknown;
	query?: unknown;
	url: string;
}

type OmitKeys<T, K> = Pick<T, Exclude<keyof T, K>>;

export type Options<
	TData extends TDataShape = TDataShape,
	ThrowOnError extends boolean = boolean,
	TResponse = unknown,
> = OmitKeys<
	RequestOptions<TResponse, ThrowOnError>,
	"body" | "path" | "query" | "url"
> &
	([TData] extends [never] ? unknown : Omit<TData, "url">);
