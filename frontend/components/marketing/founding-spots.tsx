/**
 * FILE: components/marketing/founding-spots.tsx
 * PURPOSE: Display live founding spots remaining counter with API backend
 * UPDATED: Step 8/8 - Now uses /api/v1/billing/founding-spots endpoint
 */

"use client";

import { useEffect, useState } from "react";

interface FoundingSpotsProps {
  className?: string;
  showPulse?: boolean;
  variant?: "badge" | "text" | "compact";
}

export function FoundingSpots({
  className = "",
  showPulse = true,
  variant = "badge"
}: FoundingSpotsProps) {
  const [remaining, setRemaining] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    async function fetchSpots() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const response = await fetch(`${apiUrl}/billing/founding-spots`);
        
        if (response.ok) {
          const data = await response.json();
          setRemaining(data.spots_remaining);
        } else {
          // Fallback if API not available
          setRemaining(17);
        }
      } catch {
        // Fallback to static number if fetch fails
        setRemaining(17);
        setError(true);
      }
      setLoading(false);
    }

    fetchSpots();

    // Refresh every 30 seconds for live updates
    const interval = setInterval(fetchSpots, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    // Show skeleton while loading
    return (
      <span className={`inline-block h-4 w-32 animate-pulse bg-panel rounded ${className}`} />
    );
  }

  // If sold out
  if (remaining !== null && remaining <= 0) {
    return (
      <span className={`text-amber font-semibold ${className}`}>
        Founding spots sold out
      </span>
    );
  }

  // Urgency styling based on remaining spots
  const urgencyColor = remaining !== null && remaining <= 5
    ? "text-amber"
    : remaining !== null && remaining <= 10
    ? "text-amber-500"
    : "text-amber";

  if (variant === "compact") {
    return (
      <span className={`font-semibold ${className}`}>
        <span className={urgencyColor}>{remaining}</span> of 20 left
      </span>
    );
  }

  if (variant === "text") {
    return (
      <span className={`font-semibold ${className}`}>
        <span className={urgencyColor}>{remaining} of 20</span> founding spots remaining
      </span>
    );
  }

  // Default: badge variant
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      {showPulse && (
        <span className="relative flex h-2.5 w-2.5">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
            remaining !== null && remaining <= 5 ? "bg-amber" : "bg-amber-500"
          }`} />
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
            remaining !== null && remaining <= 5 ? "bg-amber" : "bg-amber-500"
          }`} />
        </span>
      )}
      <span className="font-semibold">
        <span className={urgencyColor}>{remaining} of 20</span> founding spots remaining
      </span>
    </span>
  );
}

/**
 * Hook to get founding spots data
 * Updated: Step 8/8 - Now uses /api/v1/billing/founding-spots endpoint
 */
export function useFoundingSpots() {
  const [remaining, setRemaining] = useState<number | null>(null);
  const [totalSpots, setTotalSpots] = useState<number>(20);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSpots() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const response = await fetch(`${apiUrl}/billing/founding-spots`);
        
        if (response.ok) {
          const data = await response.json();
          setRemaining(data.spots_remaining);
          setTotalSpots(data.total_spots);
        } else {
          setRemaining(17);
        }
      } catch {
        setRemaining(17);
      }
      setLoading(false);
    }

    fetchSpots();

    // Refresh every 30 seconds for live updates
    const interval = setInterval(fetchSpots, 30000);
    return () => clearInterval(interval);
  }, []);

  return {
    remaining,
    totalSpots,
    loading,
    soldOut: remaining !== null && remaining <= 0,
    isUrgent: remaining !== null && remaining <= 5,
  };
}
