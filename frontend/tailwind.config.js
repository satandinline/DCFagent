/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          900: '#1a365d',
          700: '#2b6cb0',
          500: '#3182ce',
          300: '#63b3ed',
        },
        accent: {
          DEFAULT: '#d69e2e',
          light: '#ecc94b',
          dark: '#b7791f',
        },
        finance: {
          bg: '#f7fafc',
          card: '#ffffff',
          'dark-bg': '#0f1724',
          'dark-card': '#1a2332',
          positive: '#38a169',
          negative: '#e53e3e',
        },
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: '0 2px 8px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 8px 24px rgba(0, 0, 0, 0.1)',
      },
    },
  },
  plugins: [],
}
