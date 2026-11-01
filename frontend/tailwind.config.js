/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#141414',
          900: '#191919',
          850: '#202020',
          800: '#262626',
          750: '#303030',
          700: '#3a3a3a',
          600: '#525252',
          500: '#737373',
          400: '#a3a3a3',
          300: '#c4c4c4',
          200: '#e2e2e2',
          100: '#f5f5f4',
        },
        studio: {
          violet: '#bdbdbd',
          purple: '#f0f0f0',
          orchid: '#ffffff',
          glow: 'rgba(255, 255, 255, 0.12)',
          border: 'rgba(255, 255, 255, 0.08)',
          card: '#202020',
        },
        purple: {
          50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8',
          400: '#a1a1aa', 500: '#71717a', 600: '#52525b', 700: '#3f3f46',
          800: '#27272a', 900: '#18181b', 950: '#09090b',
        },
        emerald: {
          50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8', 400: '#a1a1aa',
          500: '#71717a', 600: '#52525b', 700: '#3f3f46', 800: '#27272a', 900: '#18181b',
        },
        green: {
          50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8', 400: '#a1a1aa',
          500: '#71717a', 600: '#52525b', 700: '#3f3f46', 800: '#27272a', 900: '#18181b',
        },
        rose: {
          50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8', 400: '#a1a1aa',
          500: '#71717a', 600: '#52525b', 700: '#3f3f46', 800: '#27272a', 900: '#18181b',
        },
        red: {
          50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8', 400: '#a1a1aa',
          500: '#71717a', 600: '#52525b', 700: '#3f3f46', 800: '#27272a', 900: '#18181b',
        },
        amber: {
          50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8', 400: '#a1a1aa',
          500: '#71717a', 600: '#52525b', 700: '#3f3f46', 800: '#27272a', 900: '#18181b',
        },
        orange: {
          50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8', 400: '#a1a1aa',
          500: '#71717a', 600: '#52525b', 700: '#3f3f46', 800: '#27272a', 900: '#18181b',
        },
        sky: {
          50: '#fafafa', 100: '#f4f4f5', 200: '#e4e4e7', 300: '#d4d4d8', 400: '#a1a1aa',
          500: '#71717a', 600: '#52525b', 700: '#3f3f46', 800: '#27272a', 900: '#18181b',
        },
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'card': '0 4px 20px 0 rgba(0, 0, 0, 0.25)',
        'subtle': '0 1px 3px 0 rgba(0, 0, 0, 0.2)',
        'elevated': '0 10px 25px -5px rgba(0, 0, 0, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
