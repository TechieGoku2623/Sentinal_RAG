import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#0A1628", mid: "#142842", dark: "#060D18" },
        brand: { DEFAULT: "#0369A1", light: "#0EA5E9", pale: "#EFF6FF" },
        slate: { muted: "#64748B", line: "#DDE3EA" },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-ibm-plex-mono)", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(10,22,40,0.04), 0 8px 24px rgba(10,22,40,0.06)",
        glow: "0 0 40px rgba(3,105,161,0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
