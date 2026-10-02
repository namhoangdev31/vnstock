import {
	type ClientOptions,
	type Config,
	createClient,
	createConfig,
} from "./client";
import type { ClientOptions as ClientOptions2 } from "./types.gen";

export type CreateClientConfig<T extends ClientOptions = ClientOptions2> = (
	override?: Config<ClientOptions & T>,
) => Config<Required<ClientOptions> & T>;

export const client = createClient(
	createConfig<ClientOptions2>({ throwOnError: true }),
);
