/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary:       "var(--color-primary)",
        accent:        "var(--color-accent)",
        surface:       "var(--color-surface)",
        card:          "var(--color-card)",
        "text-primary":"var(--color-text-primary)",
        "text-muted":  "var(--color-text-muted)",
        border:        "var(--color-border)",
      },
      fontFamily: {
        display: ["'Bebas Neue'",          "cursive"],
        heading: ["'Cormorant Garamond'",  "Georgia", "serif"],
        body:    ["'Outfit'",              "sans-serif"],
        mono:    ["'JetBrains Mono'",      "monospace"],
      },
      boxShadow: {
        premium:      "0 4px 20px -2px rgba(26,26,255,0.05), 0 0 3px rgba(26,26,255,0.02)",
        "premium-hover": "0 12px 30px -4px rgba(26,26,255,0.10), 0 0 5px rgba(26,26,255,0.05)",
      },
      backgroundImage: {
        "mesh-gradient":
          "radial-gradient(at 40% 20%, hsla(240,100%,96%,1) 0px, transparent 50%), radial-gradient(at 80% 0%, hsla(240,100%,92%,1) 0px, transparent 50%), radial-gradient(at 0% 50%, hsla(240,100%,94%,1) 0px, transparent 50%), radial-gradient(at 80% 50%, hsla(240,100%,90%,1) 0px, transparent 50%), radial-gradient(at 0% 100%, hsla(240,100%,96%,1) 0px, transparent 50%)",
      },
    },
  },
  plugins: [],
}
