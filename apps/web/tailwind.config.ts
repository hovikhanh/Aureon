// Tailwind v4 reads design tokens from `src/app/globals.css` (@theme). This file documents
// the semantic token names (06 §7.2) and is kept for tooling that expects a config.
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
};

export default config;
