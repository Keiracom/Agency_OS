"use client";

/**
 * FILE: hooks/use-pipeline-stream.ts
 * PURPOSE: SSE hook for live pipeline ProspectCard stream
 * Connects to /api/pipeline/stream and maintains a deduplicated card list
 */

import { useEffect, useRef, useState, useCallback } from "react";
import type { ProspectCard } from "@/lib/types/prospect-card";

const MAX_CARDS = 200;

export interface UsePipelineStreamResult {
  cards: ProspectCard[];
  isConnected: boolean;
  cardCount: number;
  latestCard: ProspectCard | null;
}

export function usePipelineStream(): UsePipelineStreamResult {
  const [cards, setCards] = useState<ProspectCard[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const seenRef = useRef<Set<string>>(new Set());

  const addCard = useCallback((card: ProspectCard) => {
    if (seenRef.current.has(card.domain)) {
      // Update existing card in-place (deduplicate by domain)
      setCards((prev) =>
        prev.map((c) => (c.domain === card.domain ? card : c))
      );
      return;
    }
    seenRef.current.add(card.domain);
    setCards((prev) => {
      const next = [card, ...prev];
      return next.length > MAX_CARDS ? next.slice(0, MAX_CARDS) : next;
    });
  }, []);

  useEffect(() => {
    const es = new EventSource("/api/pipeline/stream");
    esRef.current = es;

    es.onopen = () => setIsConnected(true);

    es.addEventListener("prospect_card", (event: MessageEvent) => {
      try {
        const card: ProspectCard = JSON.parse(event.data);
        addCard(card);
      } catch {
        // malformed event — ignore
      }
    });

    es.onerror = () => {
      setIsConnected(false);
      // EventSource auto-reconnects; we just update connected state
    };

    return () => {
      es.close();
      esRef.current = null;
      setIsConnected(false);
    };
  }, [addCard]);

  return {
    cards,
    isConnected,
    cardCount: cards.length,
    latestCard: cards[0] ?? null,
  };
}
