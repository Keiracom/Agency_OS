/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
    './design/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px'
      }
    },
    extend: {
      // Pure Bloomberg Dark Theme — Warm Charcoal + Amber ONLY
      colors: {
        // Background layers — reference CSS vars so data-theme switches them
        'bg-void': 'var(--bg-void)',
        'bg-base': 'var(--bg-base)',
        'bg-surface': 'var(--bg-surface)',
        'bg-elevated': 'var(--bg-elevated)',

        // Borders — reference CSS vars
        'border-subtle': 'var(--border-subtle)',
        'border-default': 'var(--border-default)',
        'border-focus': 'var(--border-focus)',

        // Text — reference CSS vars
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',

        // Accent — reference CSS vars (amber unchanged between themes)
        'amber': 'var(--amber)',
        'amber-light': 'var(--amber-light)',
        'amber-glow': 'var(--amber-glow)',

        // Error state — reference CSS vars
        'error': 'var(--error)',
        'error-glow': 'var(--error-glow)',
        
        // Glass
        glass: {
          surface: 'rgba(255,255,255,0.04)',
          border: 'rgba(255,255,255,0.10)',
          'border-hover': 'rgba(255,255,255,0.15)',
        },
        
        // shadcn/ui compatibility layer
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))'
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))'
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))'
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))'
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))'
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))'
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))'
        },
        chart: {
          '1': 'hsl(var(--chart-1))',
          '2': 'hsl(var(--chart-2))',
          '3': 'hsl(var(--chart-3))',
          '4': 'hsl(var(--chart-4))',
          '5': 'hsl(var(--chart-5))'
        }
      },
      fontFamily: {
        sans: ['DM Sans', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        serif: ['Instrument Serif', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(212,149,106,0.15)',
        'glow-md': '0 0 20px rgba(212,149,106,0.20)',
        'glow-lg': '0 0 30px rgba(212,149,106,0.25)',
        'glass': '0 4px 24px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06)',
        'glass-lg': '0 12px 40px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.08)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' }
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' }
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(212,149,106,0.4)' },
          '50%': { boxShadow: '0 0 0 8px rgba(212,149,106,0)' }
        },
        'shimmer': {
          '100%': { transform: 'translateX(100%)' }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'shimmer': 'shimmer 2s infinite'
      }
    }
  },
  plugins: [require("tailwindcss-animate")],
}
