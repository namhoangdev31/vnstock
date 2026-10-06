import { TradingClient } from "@vnstock/dnse";

const client = new TradingClient({
  apiKey: "",
  apiSecret: "",
  baseUrl: "",
  autoReconnect: true,
  maxRetries: 10,
  heartbeatInterval: 25,
  timeout: 60,
})