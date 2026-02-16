/**
 * LUCIDE ICON MAPPING — Pure Bloomberg Design System
 * CEO Directive #027 — Replace ALL emoji with Lucide icons
 * 
 * Usage:
 *   import { ChannelIcon, StatusIcon, ActionIcon } from '@/lib/icons';
 *   <ChannelIcon type="email" className="icon-accent" />
 */

import {
  Mail,
  Phone,
  PhoneCall,
  Linkedin,
  Link2,
  Flame,
  TrendingUp,
  BarChart3,
  Settings,
  Target,
  MessageSquare,
  User,
  Users,
  ClipboardList,
  CheckCircle2,
  XCircle,
  Zap,
  ArrowUpRight,
  Building2,
  Globe,
  Bell,
  FileText,
  Rocket,
  ArrowRight,
  DollarSign,
  Calendar,
  Search,
  Plus,
  Trash2,
  Crown,
  Trophy,
  Star,
  AlertCircle,
  Clock,
  Send,
  Briefcase,
  type LucideIcon,
} from 'lucide-react';
import { cn } from './utils';

// ============================================
// EMOJI TO LUCIDE MAPPING
// ============================================
export const EMOJI_TO_ICON: Record<string, LucideIcon> = {
  '📧': Mail,
  '📱': Phone,
  '🔗': Linkedin,
  '🔥': Flame,
  '📊': TrendingUp,
  '⚙️': Settings,
  '🎯': Target,
  '💬': MessageSquare,
  '👤': User,
  '👥': Users,
  '📋': ClipboardList,
  '✅': CheckCircle2,
  '❌': XCircle,
  '⚡️': Zap,
  '⚡': Zap,
  '📈': ArrowUpRight,
  '🏢': Building2,
  '🌐': Globe,
  '📞': PhoneCall,
  '🔔': Bell,
  '📝': FileText,
  '🚀': Rocket,
  '💰': DollarSign,
  '📅': Calendar,
  '🔍': Search,
  '➕': Plus,
  '🗑': Trash2,
  '👑': Crown,
  '🏆': Trophy,
  '⭐': Star,
  '⚠️': AlertCircle,
  '⏰': Clock,
  '✉️': Mail,
  '💼': Briefcase,
  '✨': Zap,
};

// ============================================
// CHANNEL ICONS
// ============================================
export type ChannelType = 'email' | 'linkedin' | 'sms' | 'voice' | 'phone' | 'mail';

const CHANNEL_ICONS: Record<ChannelType, LucideIcon> = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageSquare,
  voice: PhoneCall,
  phone: Phone,
  mail: Send,
};

interface IconProps {
  className?: string;
  size?: number;
  strokeWidth?: number;
}

export function ChannelIcon({ 
  type, 
  className,
  size = 16,
  strokeWidth = 1.5,
}: IconProps & { type: ChannelType }) {
  const Icon = CHANNEL_ICONS[type] || Mail;
  return <Icon className={cn('icon-accent', className)} size={size} strokeWidth={strokeWidth} />;
}

// ============================================
// STATUS ICONS
// ============================================
export type StatusType = 'active' | 'success' | 'warning' | 'error' | 'pending' | 'paused';

const STATUS_ICONS: Record<StatusType, LucideIcon> = {
  active: CheckCircle2,
  success: CheckCircle2,
  warning: AlertCircle,
  error: XCircle,
  pending: Clock,
  paused: Clock,
};

export function StatusIcon({ 
  type, 
  className,
  size = 16,
  strokeWidth = 1.5,
}: IconProps & { type: StatusType }) {
  const Icon = STATUS_ICONS[type] || CheckCircle2;
  return <Icon className={cn('icon-accent', className)} size={size} strokeWidth={strokeWidth} />;
}

// ============================================
// ACTION ICONS
// ============================================
export type ActionType = 'add' | 'delete' | 'edit' | 'search' | 'settings' | 'send' | 'schedule' | 'call';

const ACTION_ICONS: Record<ActionType, LucideIcon> = {
  add: Plus,
  delete: Trash2,
  edit: FileText,
  search: Search,
  settings: Settings,
  send: Send,
  schedule: Calendar,
  call: PhoneCall,
};

export function ActionIcon({ 
  type, 
  className,
  size = 16,
  strokeWidth = 1.5,
}: IconProps & { type: ActionType }) {
  const Icon = ACTION_ICONS[type] || Plus;
  return <Icon className={cn('icon-secondary', className)} size={size} strokeWidth={strokeWidth} />;
}

// ============================================
// METRIC ICONS (for dashboard cards)
// ============================================
export type MetricType = 'meetings' | 'revenue' | 'leads' | 'replies' | 'calls' | 'emails' | 'growth';

const METRIC_ICONS: Record<MetricType, LucideIcon> = {
  meetings: Calendar,
  revenue: DollarSign,
  leads: Users,
  replies: MessageSquare,
  calls: PhoneCall,
  emails: Mail,
  growth: TrendingUp,
};

export function MetricIcon({ 
  type, 
  className,
  size = 20,
  strokeWidth = 1.5,
}: IconProps & { type: MetricType }) {
  const Icon = METRIC_ICONS[type] || BarChart3;
  return <Icon className={cn('icon-accent', className)} size={size} strokeWidth={strokeWidth} />;
}

// ============================================
// ICON CONTAINER (styled wrapper)
// ============================================
export function IconContainer({ 
  children, 
  className,
  variant = 'default',
}: { 
  children: React.ReactNode; 
  className?: string;
  variant?: 'default' | 'accent' | 'muted';
}) {
  const variantClasses = {
    default: 'bg-amber-glow',
    accent: 'bg-amber/20',
    muted: 'bg-bg-elevated',
  };
  
  return (
    <div className={cn(
      'flex items-center justify-center rounded-lg p-2',
      variantClasses[variant],
      className
    )}>
      {children}
    </div>
  );
}

// ============================================
// HELPER: Convert emoji string to Lucide icon
// ============================================
export function emojiToIcon(emoji: string): LucideIcon | null {
  return EMOJI_TO_ICON[emoji] || null;
}

// ============================================
// HELPER: Render icon from emoji or Lucide name
// ============================================
export function renderIcon(
  iconOrEmoji: string,
  { className, size = 16, strokeWidth = 1.5 }: IconProps = {}
) {
  const Icon = EMOJI_TO_ICON[iconOrEmoji];
  if (Icon) {
    return <Icon className={className} size={size} strokeWidth={strokeWidth} />;
  }
  // If it's not an emoji, assume it's already a component or return null
  return null;
}
