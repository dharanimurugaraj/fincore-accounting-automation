import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "var(--color-primary)",
          hover: "var(--color-primary-hover)",
          light: "var(--color-primary-light)",
          subtle: "var(--color-primary-subtle)",
        },
        ai: {
          teal: "var(--color-ai-teal)",
          "teal-light": "var(--color-ai-teal-light)",
          violet: "var(--color-ai-violet)",
          "violet-light": "var(--color-ai-violet-light)",
        },
        neutral: {
          app: "var(--color-bg-app)",
          card: "var(--color-bg-card)",
          row: "var(--color-bg-row)",
          border: "var(--color-border)",
          "border-light": "var(--color-border-light)",
        },
        t: {
          heading: "var(--color-text-heading)",
          body: "var(--color-text-body)",
          muted: "var(--color-text-muted)",
          link: "var(--color-text-link)",
        },
        status: {
          critical: {
            DEFAULT: "var(--color-critical)",
            bg: "var(--color-critical-bg)",
          },
          high: {
            DEFAULT: "var(--color-high)",
            bg: "var(--color-high-bg)",
          },
          medium: {
            DEFAULT: "var(--color-medium)",
            bg: "var(--color-medium-bg)",
          },
          success: {
            DEFAULT: "var(--color-success)",
            bg: "var(--color-success-bg)",
          },
        },
        // Fallbacks
        border: "var(--color-border)",
        background: "var(--color-bg-app)",
        foreground: "var(--color-text-body)",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};

export default config;
