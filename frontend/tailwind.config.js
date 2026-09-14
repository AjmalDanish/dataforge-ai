/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        panel: "#1e293b",
        accent: "#10b981",
        warn: "#f59e0b",
      },
    },
  },
  plugins: [],
};
