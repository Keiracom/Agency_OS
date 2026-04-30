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
      // Agency Desk — Cream/Amber Light Theme (PR1 rebuild)
      colors: {
        // Cream surface palette
        'cream':     'var(--cream)',
        'surface':   'var(--surface)',
        'panel':     'var(--panel-bg)',
        'brand-bar': 'var(--brand-bar)',
        'on-amber':  'var(--on-amber)',

        // Ink scale
        'ink':   'var(--ink)',
        'ink-2': 'var(--ink-2)',
        'ink-3': 'var(--ink-3)',
        'ink-4': 'var(--ink-4)',

        // Rules (cream-friendly subtle borders)
        'rule':        'var(--rule)',
        'rule-strong': 'var(--rule-strong)',

        // Status (muted to fit cream backdrop)
        'green':  'var(--green)',
        'red':    'var(--red)',
        'blue':   'var(--blue)',
        'copper': 'var(--copper)',

        // Legacy aliases removed in A1 token codemod (2026-04-30).
        // Components now use the canonical /demo tokens directly:
        //   bg-void → bg-cream            border-border-subtle  → border-rule
        //   bg-base → bg-surface          border-border-default → border-rule-strong
        //   bg-surface → bg-panel         text-text-primary    → text-ink
        //   bg-elevated → bg-panel        text-text-secondary  → text-ink-2
        //                                  text-text-muted      → text-ink-3

        // Accent — amber unchanged between themes
        'amber':       'var(--amber)',
        'amber-light': 'var(--amber-light)',
        'amber-soft':  'var(--amber-soft)',
        'amber-glow':  'var(--amber-glow)',

        // Error state
        'error':      'var(--error)',
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
        sans:    ['DM Sans', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        serif:   ['Playfair Display', 'Georgia', 'serif'],
        display: ['Playfair Display', 'Georgia', 'serif'],
        mono:    ['JetBrains Mono', 'monospace'],
      },
      spacing: {
        // Layout dimensions exposed as Tailwind utilities
        'sidebar': 'var(--sidebar-w)',     // 232px
        'topbar':  'var(--topbar-h)',      // 56px
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
