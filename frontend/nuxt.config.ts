import path from "node:path"

export default defineNuxtConfig({
  compatibilityDate: "2024-11-01",
  devtools: { enabled: false },
  telemetry: false,
  ssr: false,
  experimental: {
    appManifest: false,
  },
  vite: {
    server: {
      watch: {
        ignored: ["**/dist/**", "**/../backend/app/frontend/**"],
      },
    },
    optimizeDeps: {
      exclude: ["@vnstock/dnse"],
    },
  },
  modules: ["@nuxt/ui", "@vueuse/nuxt"],
  css: ["~/assets/css/main.css"],
  app: {
    head: {
      title: "Vnstock Quants & Predictive Analytics Engine",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        {
          name: "description",
          content:
            "24/7 Continuous Quantitative Research, Predictive Analytics, and Simulation Engine for VN30F1M Derivatives & Equities",
        },
      ],
      link: [
        { rel: "icon", type: "image/png", href: "/assets/images/favicon.png" },
        { rel: "preconnect", href: "https://fonts.googleapis.com" },
        {
          rel: "preconnect",
          href: "https://fonts.gstatic.com",
          crossorigin: "",
        },
      ],
    },
  },
  runtimeConfig: {
    public: {
      apiUrl:
        process.env.VITE_API_URL ||
        process.env.NUXT_PUBLIC_API_URL ||
        "http://127.0.0.1:8000",
      dnseApiKey:
        process.env.DNSE_API_KEY ||
        process.env.NUXT_PUBLIC_DNSE_API_KEY,
      dnseApiSecret:
        process.env.DNSE_API_SECRET ||
        process.env.NUXT_PUBLIC_DNSE_API_SECRET,
      dnseWsUrl: process.env.DNSE_WS_URL || "wss://ws-openapi.dnse.com.vn",
    },
  },
  nitro: {
    output: {
      publicDir: path.resolve(__dirname, "../backend/app/frontend"),
    },
  },
  routeRules: {
    "/dnse-api/**": {
      proxy: "https://openapi.dnse.com.vn/**",
    },
    "/api/**": {
      proxy: `${process.env.VITE_API_URL || process.env.NUXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/**`,
    },
  },
  colorMode: {
    preference: "dark",
    fallback: "dark",
  },
})
