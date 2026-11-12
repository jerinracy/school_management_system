import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', '"Noto Sans Bengali"', "system-ui", "sans-serif"],
        bangla: ['"Noto Sans Bengali"', '"Inter"', "system-ui", "sans-serif"],
      },
      colors: {
        canvas: "rgb(var(--bg-canvas) / <alpha-value>)",
        surface: "rgb(var(--bg-surface) / <alpha-value>)",
        elevated: "rgb(var(--bg-elevated) / <alpha-value>)",
        ink: {
          DEFAULT: "rgb(var(--text-ink) / <alpha-value>)",
          muted: "rgb(var(--text-muted) / <alpha-value>)",
          subtle: "rgb(var(--text-subtle) / <alpha-value>)",
        },
        border: {
          DEFAULT: "rgb(var(--border-default) / <alpha-value>)",
          strong: "rgb(var(--border-strong) / <alpha-value>)",
        },
        primary: {
          DEFAULT: "rgb(var(--color-primary) / <alpha-value>)",
          hover: "rgb(var(--color-primary-hover) / <alpha-value>)",
          soft: "rgb(var(--color-primary-soft) / <alpha-value>)",
          border: "rgb(var(--color-primary-border) / <alpha-value>)",
        },
        academic: {
          amber: "rgb(var(--color-amber) / <alpha-value>)",
          amberSoft: "rgb(var(--color-amber-soft) / <alpha-value>)",
          navy: "rgb(var(--color-navy) / <alpha-value>)",
          navySoft: "rgb(var(--color-navy-soft) / <alpha-value>)",
        },
      },
      keyframes: {
        "page-enter": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "data-fade": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
      animation: {
        "page-enter": "page-enter 180ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "data-fade": "data-fade 220ms ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
