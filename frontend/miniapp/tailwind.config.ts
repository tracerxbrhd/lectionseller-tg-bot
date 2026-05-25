import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app: {
          bg: "var(--app-bg)",
          panel: "var(--app-panel)",
          text: "var(--app-text)",
          muted: "var(--app-muted)",
          border: "var(--app-border)",
          accent: "var(--app-accent)",
          "accent-strong": "var(--app-accent-strong)",
        },
      },
      boxShadow: {
        soft: "0 8px 30px rgba(18, 38, 36, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
