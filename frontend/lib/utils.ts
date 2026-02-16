import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getInitials(name: string): string {
  if (!name) return "?"
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) {
    return parts[0].charAt(0).toUpperCase()
  }
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
}

const avatarColors = [
  "bg-amber",
  "bg-orange-500",
  "bg-amber-500",
  "bg-yellow-500",
  "bg-lime-500",
  "bg-amber",
  "bg-amber",
  "bg-amber",
  "bg-amber",
  "bg-amber",
  "bg-bg-elevated",
  "bg-indigo-500",
  "bg-amber",
  "bg-amber",
  "bg-fuchsia-500",
  "bg-amber-light",
  "bg-rose-500",
]

export function getAvatarColor(name: string): string {
  if (!name) return avatarColors[0]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return avatarColors[Math.abs(hash) % avatarColors.length]
}

export function getTierColor(tier: string): string {
  const tierColors: Record<string, string> = {
    hot: "text-amber",
    warm: "text-orange-500",
    cool: "text-text-secondary",
    cold: "text-amber",
    dead: "text-gray-500",
  }
  return tierColors[tier?.toLowerCase()] || "text-gray-500"
}
