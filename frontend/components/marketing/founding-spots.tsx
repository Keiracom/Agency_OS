/**
 * FILE: components/marketing/founding-spots.tsx
 * PURPOSE: Display live founding spots remaining counter with realtime updates
 */

"use client";

import { useEffect, useState } from "react";
import { createAnonClient } from "@/lib/supabase";

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
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAnonClient() as any;

    async function fetchSpots() {
      try {
        const { data, error } = await supabase
          .from("founding_spots")
          .select("total_spots, spots_taken")
          .eq("id", 1)
          .single();

        if (data && !error) {
          setRemaining(data.total_spots - data.spots_taken);
        } else {
          // If table doesn't exist yet (migration not run), use default
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

    // Subscribe to realtime updates
    const channel = supabase
      .channel("founding_spots_changes")
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "founding_spots" },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (payload: any) => {
          const { total_spots, spots_taken } = payload.new as {
            total_spots: number;
            spots_taken: number;
          };
          setRemaining(total_spots - spots_taken);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  if (loading) {
    // Show skeleton while loading
    return (
      <span className={`inline-block h-4 w-32 animate-pulse bg-gray-200 rounded ${className}`} />
    );
  }

  // If sold out
  if (remaining !== null && remaining <= 0) {
    return (
      <span className={`text-red-500 font-semibold ${className}`}>
        Founding spots sold out
      </span>
    );
  }

  // Urgency styling based on remaining spots
  const urgencyColor = remaining !== null && remaining <= 5
    ? "text-red-500"
    : remaining !== null && remaining <= 10
    ? "text-amber-500"
    : "text-green-500";

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
            remaining !== null && remaining <= 5 ? "bg-red-500" : "bg-amber-500"
          }`} />
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
            remaining !== null && remaining <= 5 ? "bg-red-500" : "bg-amber-500"
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
 */
export function useFoundingSpots() {
  const [remaining, setRemaining] = useState<number | null>(null);
  const [totalSpots, setTotalSpots] = useState<number>(20);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const supabase = createAnonClient() as any;

    async function fetchSpots() {
      try {
        const { data, error } = await supabase
          .from("founding_spots")
          .select("total_spots, spots_taken")
          .eq("id", 1)
          .single();

        if (data && !error) {
          setRemaining(data.total_spots - data.spots_taken);
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

    const channel = supabase
      .channel("founding_spots_hook")
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "founding_spots" },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (payload: any) => {
          const { total_spots, spots_taken } = payload.new as {
            total_spots: number;
            spots_taken: number;
          };
          setRemaining(total_spots - spots_taken);
          setTotalSpots(total_spots);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  return {
    remaining,
    totalSpots,
    loading,
    soldOut: remaining !== null && remaining <= 0,
    isUrgent: remaining !== null && remaining <= 5,
  };
}
