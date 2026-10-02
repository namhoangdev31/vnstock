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
      },
    },
  },
} satisfies Config
