import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format relative time
export function timeAgo(date: string | Date): string {
  const now = new Date();
  const then = new Date(date);
  const seconds = Math.floor((now.getTime() - then.getTime()) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return then.toLocaleDateString();
}

// Format currency
export function formatCost(cost: number): string {
  if (cost < 0.01) return `$${(cost * 100).toFixed(2)}¢`;
  return `$${cost.toFixed(4)}`;
}

// Format large numbers
export function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}

// Status color mapping
export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    completed: 'bg-green-500',
    success: 'bg-green-500',
    active: 'bg-green-500',
    running: 'bg-blue-500',
    pending: 'bg-yellow-500',
    failed: 'bg-red-500',
    error: 'bg-red-500',
    crashed: 'bg-red-500',
    ended: 'bg-gray-500',
  };
  return colors[status.toLowerCase()] || 'bg-gray-500';
}

// Action type icons
export function getActionTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    task: '📋',
    tool_call: '🔧',
    message: '💬',
    heartbeat: '💓',
    sync: '🔄',
    decision: '🧠',
    learning: '📚',
    error: '❌',
  };
  return icons[type.toLowerCase()] || '📌';
}

// Category colors
export function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    general: 'bg-gray-100 text-gray-800',
    operational: 'bg-blue-100 text-blue-800',
    behavioral: 'bg-purple-100 text-purple-800',
    technical: 'bg-green-100 text-green-800',
    communication: 'bg-yellow-100 text-yellow-800',
    safety: 'bg-red-100 text-red-800',
    memory: 'bg-indigo-100 text-indigo-800',
  };
  return colors[category.toLowerCase()] || 'bg-gray-100 text-gray-800';
}

// Truncate text
export function truncate(text: string, length: number): string {
  if (text.length <= length) return text;
  return text.slice(0, length) + '...';
}

// Parse markdown-ish text to simple HTML (basic)
export function parseSimpleMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 rounded">$1</code>')
    .replace(/\n/g, '<br />');
}
