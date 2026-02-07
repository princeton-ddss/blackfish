/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        'orca-blue': '#1BB3F6',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        // logo: ['Galada', 'cursive'],
        logo: ['Bangers', 'system-ui'],
      }
    }
  },
  plugins: [
    require("@tailwindcss/forms"),
  ],
};
