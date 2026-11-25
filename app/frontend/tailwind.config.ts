import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'Inter Variable'", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono Variable'", "ui-monospace", "monospace"],
      },
      colors: {
        // Light theme. "ink" = surfaces (950 page, 900 cards ... 600 borders); accents darkened for contrast on white.
        ink: { 950: "#f4f7fb", 900: "#ffffff", 850: "#f8fafc", 800: "#eef2f7", 700: "#e2e8f0", 600: "#cbd5e1" },
        brand: { 300: "#0e7490", 400: "#0891b2", 500: "#0e7490", 600: "#155e75" },
        violet: { 400: "#7c3aed", 500: "#6d28d9" },
        ok: { 400: "#059669", 500: "#047857" },
        bad: { 400: "#e11d48", 500: "#be123c" },
        warn: { 400: "#b45309" },
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(8,145,178,.20), 0 8px 24px -10px rgba(8,145,178,.45)",
        card: "0 1px 2px rgba(15,23,42,.06), 0 12px 32px -16px rgba(15,23,42,.18)",
      },
      backgroundImage: {
        grid: "linear-gradient(rgba(15,23,42,.04) 1px, transparent 1px), linear-gradient(90deg, rgba(15,23,42,.04) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};
export default config;
