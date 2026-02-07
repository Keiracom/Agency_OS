/**
 * Bloomberg Terminal Theme Constants
 * Matching HTML prototypes: dashboard-v3.html, campaigns-v4.html, leads-v2.html
 */

export const theme = {
  colors: {
    // Base layers
    bgPrimary: '#0A0A12',
    bgSecondary: '#12121A',
    bgTertiary: '#1A1A24',
    bgVoid: '#05050A',
    
    // Borders
    borderColor: '#2A2A3A',
    borderSubtle: '#1E1E2E',
    borderStrong: '#3A3A50',
    
    // Text
    textPrimary: '#FFFFFF',
    textSecondary: '#A0A0B0',
    textMuted: '#6B6B7B',
    
    // Accents - Purple primary (matching HTML prototype)
    accentPurple: '#7C3AED',
    accentPurpleLight: '#9D5CFF',
    accentGreen: '#10B981',
    accentBlue: '#3B82F6',
    accentOrange: '#F59E0B',
    accentRed: '#EF4444',
    accentTeal: '#14B8A6',
    
    // Status/Tier colors
    tierHot: '#EF4444',
    tierWarm: '#F59E0B',
    tierCool: '#3B82F6',
    tierCold: '#6B7280',
    tierDead: '#374151',
    
    // Channel colors
    channelEmail: '#3B82F6',
    channelLinkedin: '#7C3AED',
    channelSms: '#14B8A6',
    channelVoice: '#F59E0B',
    channelMail: '#EC4899',
  },
  
  fonts: {
    sans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    mono: "'JetBrains Mono', monospace",
  },
  
  // CSS class helpers
  classes: {
    card: 'bg-[#12121A] border border-[#2A2A3A] rounded-2xl',
    cardHover: 'hover:border-[#7C3AED]/50 transition-colors',
    textPrimary: 'text-white',
    textSecondary: 'text-[#A0A0B0]',
    textMuted: 'text-[#6B6B7B]',
    accentPurple: 'text-[#9D5CFF]',
    borderDefault: 'border-[#2A2A3A]',
  }
} as const;

export type ThemeColors = typeof theme.colors;
export type ThemeFonts = typeof theme.fonts;
