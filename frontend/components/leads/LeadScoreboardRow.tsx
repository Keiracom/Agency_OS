"use client";

/**
 * FILE: frontend/components/leads/LeadScoreboardRow.tsx
 * PURPOSE: Animated leaderboard row with ALS colour coding
 * SPRINT: Dashboard Sprint 2 - Step 6/8 Animated Lead Scoreboard
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

// Tier type based on ALS score
export type ALSTier = "hot" | "warm" | "cool" | "cold";

export interface LeadScoreboardRowProps {
  id: string;
  rank: number;
  alsScore: number;
  companyName: string;
  decisionMaker: string;
  title: string;
  enrichmentDepth: number; // 0-100 percentage
  isNew?: boolean;
  index: number;
}

/**
 * Get ALS tier from score
 * Hot: 85-100, Warm: 60-84, Cool: 30-59, Cold: 0-29
 */
export function getALSTier(score: number): ALSTier {
  if (score >= 85) return "hot";
  if (score >= 60) return "warm";
  if (score >= 30) return "cool";
  return "cold";
}

/**
 * Get colour styling for ALS tier
 * Hot = amber glow (#D4956A)
 * Warm = yellow (#EAB308)
 * Cool = grey (#6B7280)
 * Cold = dark grey (#374151)
 */
export function getALSColour(tier: ALSTier): { text: string; bg: string; glow: string; border: string } {
  switch (tier) {
    case "hot":
      return {
        text: "#D4956A",
        bg: "rgba(212, 149, 106, 0.15)",
        glow: "0 0 20px rgba(212, 149, 106, 0.4)",
        border: "rgba(212, 149, 106, 0.3)"
      };
    case "warm":
      return {
        text: "#EAB308",
        bg: "rgba(234, 179, 8, 0.15)",
        glow: "0 0 15px rgba(234, 179, 8, 0.3)",
        border: "rgba(234, 179, 8, 0.3)"
      };
    case "cool":
      return {
        text: "#6B7280",
        bg: "rgba(107, 114, 128, 0.15)",
        glow: "none",
        border: "rgba(107, 114, 128, 0.3)"
      };
    case "cold":
      return {
        text: "#374151",
        bg: "rgba(55, 65, 81, 0.15)",
        glow: "none",
        border: "rgba(55, 65, 81, 0.3)"
      };
  }
}

/**
 * Enrichment depth indicator bar
 */
function EnrichmentDepthBar({ depth }: { depth: number }) {
  // Determine colour based on depth
  let barColour = "#374151"; // Cold
  if (depth >= 80) barColour = "#D4956A"; // Hot amber
  else if (depth >= 50) barColour = "#EAB308"; // Warm yellow  
  else if (depth >= 20) barColour = "#6B7280"; // Cool grey

  return (
    <div className="w-24 flex items-center gap-2">
      <div 
        className="flex-1 h-2 rounded-full overflow-hidden"
        style={{ backgroundColor: "rgba(255,255,255,0.05)" }}
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${depth}%` }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
          className="h-full rounded-full"
          style={{ backgroundColor: barColour }}
        />
      </div>
      <span className="text-xs font-mono" style={{ color: barColour }}>
        {depth}%
      </span>
    </div>
  );
}

/**
 * Animated leaderboard row
 */
export function LeadScoreboardRow({
  id,
  rank,
  alsScore,
  companyName,
  decisionMaker,
  title,
  enrichmentDepth,
  isNew = false,
  index
}: LeadScoreboardRowProps) {
  const router = useRouter();
  const tier = getALSTier(alsScore);
  const colours = getALSColour(tier);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -20, y: isNew ? 50 : 0 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{
        layout: { type: "spring", stiffness: 300, damping: 30 },
        opacity: { duration: 0.3 },
        x: { duration: 0.4, delay: index * 0.05 }
      }}
      onClick={() => router.push(`/dashboard/leads/${id}`)}
      className="group flex items-center gap-4 px-5 py-4 rounded-xl cursor-pointer transition-all"
      style={{
        backgroundColor: "rgba(255,255,255,0.02)",
        border: `1px solid rgba(255,255,255,0.05)`,
      }}
      whileHover={{
        backgroundColor: "rgba(255,255,255,0.05)",
        borderColor: colours.border,
        transition: { duration: 0.2 }
      }}
    >
      {/* Rank Badge */}
      <div 
        className="w-8 h-8 rounded-lg flex items-center justify-center font-mono font-bold text-sm flex-shrink-0"
        style={{
          backgroundColor: rank <= 3 ? colours.bg : "rgba(255,255,255,0.03)",
          color: rank <= 3 ? colours.text : "#6B7280"
        }}
      >
        {rank}
      </div>

      {/* ALS Score with glow effect */}
      <motion.div
        className="w-16 flex-shrink-0 text-center"
        animate={{
          textShadow: tier === "hot" ? [colours.glow, "none", colours.glow] : "none"
        }}
        transition={{
          repeat: tier === "hot" ? Infinity : 0,
          duration: 2
        }}
      >
        <span 
          className="text-2xl font-bold font-mono"
          style={{ color: colours.text }}
        >
          {alsScore}
        </span>
        <p 
          className="text-[9px] font-semibold uppercase tracking-wider"
          style={{ color: colours.text, opacity: 0.7 }}
        >
          {tier}
        </p>
      </motion.div>

      {/* Company & Decision Maker */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm text-text-primary truncate group-hover:text-accent-primary transition-colors">
          {companyName}
        </p>
        <p className="text-xs text-text-muted truncate">
          {decisionMaker} · {title}
        </p>
      </div>

      {/* Enrichment Depth */}
      <EnrichmentDepthBar depth={enrichmentDepth} />

      {/* New badge */}
      {isNew && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="px-2 py-1 rounded text-[10px] font-semibold uppercase"
          style={{
            backgroundColor: "rgba(16, 185, 129, 0.15)",
            color: "#10B981",
            border: "1px solid rgba(16, 185, 129, 0.3)"
          }}
        >
          New
        </motion.span>
      )}

      {/* Arrow */}
      <motion.span
        className="text-text-muted opacity-0 group-hover:opacity-100 transition-opacity"
        animate={{ x: [0, 4, 0] }}
        transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
      >
        →
      </motion.span>
    </motion.div>
  );
}
