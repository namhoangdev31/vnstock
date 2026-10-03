import path from "node:path"

export default defineNuxtConfig({
  compatibilityDate: "2024-11-01",
  devtools: { enabled: false },
  telemetry: false,
  ssr: false,
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
        "https://vnstock.fastapicloud.dev",
    },
  },
  nitro: {
    output: {
      publicDir: path.resolve(__dirname, "../backend/app/frontend"),
    },
  },
  routeRules: {
    "/api/**": {
      proxy: `${process.env.VITE_API_URL || process.env.NUXT_PUBLIC_API_URL || "https://vnstock.fastapicloud.dev"}/api/**`,
    },
  },
  colorMode: {
    preference: "dark",
    fallback: "dark",
  },
})
