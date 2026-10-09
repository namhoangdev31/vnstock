import type { Config } from "tailwindcss"

export default {
  content: [
    "./components/**/*.{js,vue,ts}",
    "./layouts/**/*.vue",
    "./pages/**/*.vue",
    "./plugins/**/*.{js,ts}",
    "./app.vue",
  ],
  theme: {
    extend: {
      colors: {
        aave: {
          violet: "var(--color-aave-violet)",
          obsidian: "var(--color-obsidian)",
          inkwell: "var(--color-inkwell)",
          charcoal: "var(--color-charcoal)",
          iron: "var(--color-iron)",
          graphite: "var(--color-graphite)",
          pewter: "var(--color-pewter)",
          ash: "var(--color-ash)",
          bone: "var(--color-bone)",
          paper: "var(--color-paper)",
        },
        surface: {
          canvas: "var(--surface-page-canvas)",
          lavender: "var(--surface-lavender-wash)",
          card: "var(--surface-warm-card)",
          midnight: "var(--surface-midnight)",
          abyss: "var(--surface-abyss)",
        },
        tv: {
          canvas: "var(--color-tv-canvas)",
          surface: "var(--color-tv-surface)",
          card: "var(--color-tv-card)",
          border: "var(--color-tv-border)",
          primary: "var(--color-tv-text-primary)",
          secondary: "var(--color-tv-text-secondary)",
          bull: "var(--color-tv-bull)",
          bear: "var(--color-tv-bear)",
          gold: "var(--color-tv-gold)",
        },
        quant: {
          petrol: "var(--color-quant-petrol)",
          border: "var(--color-quant-border)",
          badge: "var(--color-quant-badge)",
          badgeText: "var(--color-quant-badge-text)",
          text: "var(--color-quant-text)",
          bull: "var(--color-quant-bull)",
          bear: "var(--color-quant-bear)",
        },
        ticker: {
          bg: "var(--ticker-bg)",
          border: "var(--ticker-border)",
          hover: "var(--ticker-hover)",
          symbol: "var(--ticker-symbol)",
          price: "var(--ticker-price)",
          muted: "var(--ticker-muted)",
        },
      },
    },
  },
} satisfies Config
