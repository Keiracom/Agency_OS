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
      // Bloomberg Dark Theme Tokens (v2 - Warmed up)
      colors: {
        // Base layers (warmed up for glassmorphism)
        'bg-void': '#08070D',
        'bg-base': '#0D0C14',
        'bg-surface': '#171622',
        'bg-surface-hover': '#1E1C2D',
        'bg-elevated': '#262438',
        
        // Borders (warmed up)
        'border-subtle': '#221F30',
        'border-default': '#2E2B40',
        'border-strong': '#3D3955',
        
        // Glass (new tokens for glassmorphism)
        glass: {
          surface: 'rgba(23, 22, 34, 0.55)',
          border: 'rgba(255, 255, 255, 0.06)',
          'border-hover': 'rgba(255, 255, 255, 0.1)',
        },
        
        // Text
        'text-primary': '#F8F8FC',
        'text-secondary': '#B4B4C4',
        'text-muted': '#6E6E82',
        
        // Accent
        'accent-primary': '#7C3AED',
        'accent-primary-hover': '#9061F9',
        'accent-teal': '#14B8A6',
        'accent-blue': '#3B82F6',
        
        // Status
        'status-success': '#22C55E',
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
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      boxShadow: {
        'glow-sm': '0 0 10px rgba(124, 58, 237, 0.2)',
        'glow-md': '0 0 20px rgba(124, 58, 237, 0.3)',
        'glow-lg': '0 0 30px rgba(124, 58, 237, 0.4)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.04)',
        'glass-glow': '0 0 20px rgba(124, 58, 237, 0.15)',
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
