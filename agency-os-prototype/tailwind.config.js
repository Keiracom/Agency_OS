/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        mint: {
          50: '#f0fdf8',
          100: '#ccfce8',
          200: '#99f6d4',
          300: '#5eebb8',
          400: '#2dd498',
          500: '#0eb77a',
          600: '#059562',
          700: '#047652',
          800: '#065d43',
          900: '#054d38',
        },
      },
      keyframes: {
        'shine': {
          '0%': { backgroundPosition: '200% 50%' },
          '100%': { backgroundPosition: '-200% 50%' },
        },
        'number-tick': {
          '0%': { transform: 'translateY(100%)' },
          '100%': { transform: 'translateY(0)' },
        },
      },
      animation: {
        'shine': 'shine 4s linear infinite',
      },
    },
  },
  plugins: [],
}
