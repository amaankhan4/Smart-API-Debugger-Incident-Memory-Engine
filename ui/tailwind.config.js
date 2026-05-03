/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        panel: '#0f172a',
        panelSoft: '#111827'
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(148, 163, 184, 0.2), 0 10px 35px rgba(15,23,42,0.45)'
      }
    }
  },
  darkMode: 'class',
  plugins: []
};
