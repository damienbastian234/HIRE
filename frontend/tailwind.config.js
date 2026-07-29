/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#12172B",
          800: "#1B2140",
          700: "#242C55",
        },
        paper: "#F7F5F0",
        signal: {
          DEFAULT: "#F2A93B",
          light: "#FBD9A0",
          dark: "#C9861F",
        },
        slate: {
          DEFAULT: "#5B6178",
          light: "#9297AB",
        },
        success: "#3FAE7A",
        alert: "#E15C4E",
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        card: "0.875rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(18,23,43,0.06), 0 8px 24px rgba(18,23,43,0.06)",
        pop: "0 12px 32px rgba(18,23,43,0.16)",
      },
      keyframes: {
        dash: {
          "0%": { strokeDashoffset: "283" },
          "100%": { strokeDashoffset: "var(--offset)" },
        },
      },
      animation: {
        dash: "dash 1.1s ease-out forwards",
      },
    },
  },
  plugins: [],
};
