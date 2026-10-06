import { TradingClient } from "@vnstock/dnse";

let _wsClient: TradingClient | null = null;

/**
 * DNSE WebSocket Composable
 */
export const useDnseWs = (): TradingClient => {
  if (!_wsClient) {
    let apiKey = "";
    let apiSecret = "";
    let baseUrl = "wss://ws-openapi.dnse.com.vn";

    try {
      const config = useRuntimeConfig();
      apiKey = (config.public?.dnseApiKey as string) || "";
      apiSecret = (config.public?.dnseApiSecret as string) || "";
      baseUrl = (config.public?.dnseWsUrl as string) || baseUrl;
    } catch {
      if (typeof process !== "undefined" && process.env) {
        apiKey = process.env.DNSE_API_KEY || "";
        apiSecret = process.env.DNSE_API_SECRET || "";
        baseUrl = process.env.DNSE_WS_URL || baseUrl;
      }
    }

    _wsClient = new TradingClient({
      apiKey,
      apiSecret,
      baseUrl,
      autoReconnect: true,
      maxRetries: 10,
      heartbeatInterval: 25,
      timeout: 60,
    });
  }
  return _wsClient;
};

export const dnseWsClient = new Proxy({} as TradingClient, {
  get(_target, prop, receiver) {
    const client = useDnseWs();
    const value = Reflect.get(client, prop, receiver);
    if (typeof value === "function") {
      return value.bind(client);
    }
    return value;
  },
});
