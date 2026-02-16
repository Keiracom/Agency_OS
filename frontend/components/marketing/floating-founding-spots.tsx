/**
 * FILE: components/marketing/floating-founding-spots.tsx
 * PURPOSE: Fixed bottom-right floating counter showing remaining founding spots
 * FEATURES: Realtime updates, urgency styling, click to scroll to pricing
 */

"use client";

import { useFoundingSpots } from "./founding-spots";

export function FloatingFoundingSpots() {
  const { remaining, loading, soldOut, isUrgent } = useFoundingSpots();

  // Don't show while loading
  if (loading) return null;

  // Sold out state
  if (soldOut) {
    return (
      <div className="fixed bottom-4 right-4 z-50 bg-amber text-text-primary px-4 py-3 rounded-lg shadow-lg">
        <span className="font-semibold">Founding spots sold out</span>
      </div>
    );
  }

  // Urgency-based styling
  const urgencyClass = isUrgent
    ? "bg-amber animate-pulse"
    : remaining !== null && remaining <= 10
    ? "bg-orange-500"
    : "bg-gradient-to-r from-amber to-amber";

  return (
    <a
      href="#pricing"
      className={`fixed bottom-4 right-4 z-50 ${urgencyClass} text-text-primary px-4 py-3 rounded-lg shadow-lg cursor-pointer hover:scale-105 transition-transform flex items-center gap-3`}
    >
      {/* Pulsing dot for urgency */}
      {isUrgent && (
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-bg-surface opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-bg-surface"></span>
        </span>
      )}

      <div className="flex flex-col leading-tight">
        <span className="text-2xl font-bold">{remaining}/20</span>
        <span className="text-xs opacity-90">founding spots left</span>
      </div>

      <div className="text-xs border-l border-white/30 pl-3 ml-1">
        <span className="font-semibold">50% off</span>
        <br />
        <span className="opacity-90">for life</span>
      </div>
    </a>
  );
}
