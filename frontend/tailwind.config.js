/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
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
      // Agency OS Design Tokens - Bloomberg Terminal Dark Mode
      // Sprint 1: Theme Foundation (CEO Directive #008)
      colors: {
        // Base layers - Warm Charcoal
        'bg-void': '#080604',
        'bg-base': '#0C0A08',
        'bg-surface': 'rgba(255, 255, 255, 0.03)',
        'bg-surface-hover': 'rgba(255, 255, 255, 0.06)',
        'bg-elevated': 'rgba(255, 255, 255, 0.08)',
        
        // Borders - Glassmorphism
        'border-subtle': 'rgba(255, 255, 255, 0.06)',
        'border-default': 'rgba(255, 255, 255, 0.08)',
        'border-strong': 'rgba(255, 255, 255, 0.12)',
        
        // Text - Warm Cream
        'text-primary': '#FAF5F0',
        'text-secondary': '#A09890',
        'text-muted': '#6B6560',
        
        // Accent - Amber Primary, Violet for AI only
        'accent-primary': '#D4956A',
        'accent-primary-hover': '#E0A87D',
        'accent-ai': '#7C3AED',
        'accent-ai-hover': '#9061F9',
        'accent-teal': '#14B8A6',
        'accent-blue': '#3B82F6',
        
        // Status
        'status-success': '#10B981',
        'status-warning': '#F59E0B',
        'status-error': '#EF4444',
        
        // Tiers (ALS Lead Scoring)
        'tier-hot': '#EF4444',
        'tier-warm': '#F59E0B',
        'tier-cool': '#3B82F6',
        
        // shadcn/ui compatibility
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
        'glow-sm': '0 0 10px rgba(212, 149, 106, 0.2)',
        'glow-md': '0 0 20px rgba(212, 149, 106, 0.3)',
        'glow-lg': '0 0 30px rgba(212, 149, 106, 0.4)',
        'glow-ai-sm': '0 0 10px rgba(124, 58, 237, 0.2)',
        'glow-ai-md': '0 0 20px rgba(124, 58, 237, 0.3)',
      },
      backdropBlur: {
        'glass': '12px',
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
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(124, 58, 237, 0.4)' },
          '50%': { boxShadow: '0 0 0 8px rgba(124, 58, 237, 0)' }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite'
      }
    }
  },
  plugins: [require("tailwindcss-animate")],
}
