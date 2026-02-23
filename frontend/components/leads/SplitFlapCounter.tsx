"use client";

/**
 * FILE: frontend/components/leads/SplitFlapCounter.tsx
 * PURPOSE: Bloomberg Terminal-style animated split-flap counter bar
 * SPRINT: Dashboard Sprint 2 - Step 6/8 Animated Lead Scoreboard
 * THEME: Bloomberg Terminal dark mode (charcoal #0C0A08, amber #D4956A)
 */

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Users, Database, TrendingUp, Calendar } from "lucide-react";

interface CounterProps {
  value: number;
  label: string;
  icon: React.ReactNode;
  suffix?: string;
  decimals?: number;
}

/**
 * Single animated odometer digit
 */
function OdometerDigit({ digit }: { digit: string }) {
  return (
    <div className="relative w-6 h-10 overflow-hidden">
      {/* Split-flap card background */}
      <div 
        className="absolute inset-0 rounded-sm"
        style={{ 
          backgroundColor: "#1A1714",
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08), inset 0 -1px 0 rgba(0,0,0,0.4)"
        }}
      />
      
      {/* Center divider line (split-flap effect) */}
      <div 
        className="absolute left-0 right-0 top-1/2 h-px z-10"
        style={{ backgroundColor: "rgba(0,0,0,0.6)" }}
      />
      
      {/* Animated digit */}
      <AnimatePresence mode="popLayout">
        <motion.span
          key={digit}
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 20, opacity: 0 }}
          transition={{ 
            type: "spring", 
            stiffness: 300, 
            damping: 30,
            duration: 0.3 
          }}
          className="absolute inset-0 flex items-center justify-center text-lg font-mono font-bold"
          style={{ color: "#D4956A" }}
        >
          {digit}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

/**
 * Animated odometer counter with split-flap effect
 */
function OdometerCounter({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const [displayValue, setDisplayValue] = useState(0);
  const animationRef = useRef<number>();
  const startTimeRef = useRef<number>();
  const startValueRef = useRef(0);
  
  useEffect(() => {
    const duration = 2000; // 2 second animation
    startValueRef.current = displayValue;
    startTimeRef.current = Date.now();
    
    const animate = () => {
      const now = Date.now();
      const elapsed = now - (startTimeRef.current || now);
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function for smooth deceleration
      const easeOutExpo = 1 - Math.pow(2, -10 * progress);
      
      const currentValue = startValueRef.current + (value - startValueRef.current) * easeOutExpo;
      setDisplayValue(Math.round(currentValue * Math.pow(10, decimals)) / Math.pow(10, decimals));
      
      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };
    
    animationRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [value, decimals]);
  
  // Format the display value with proper padding
  const formattedValue = decimals > 0 
    ? displayValue.toFixed(decimals) 
    : Math.floor(displayValue).toString();
  
  const digits = formattedValue.split("");
  
  return (
    <div className="flex gap-0.5">
      {digits.map((digit, idx) => (
        <OdometerDigit key={idx} digit={digit} />
      ))}
    </div>
  );
}

/**
 * Individual counter card in the split-flap bar
 */
function CounterCard({ value, label, icon, suffix = "", decimals = 0 }: CounterProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="flex items-center gap-4 px-6 py-4 rounded-xl"
      style={{
        backgroundColor: "#0C0A08",
        border: "1px solid rgba(212, 149, 106, 0.2)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.03)"
      }}
    >
      {/* Icon */}
      <div 
        className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: "rgba(212, 149, 106, 0.1)" }}
      >
        <span style={{ color: "#D4956A" }}>{icon}</span>
      </div>
      
      {/* Counter */}
      <div>
        <div className="flex items-baseline gap-1">
          <OdometerCounter value={value} decimals={decimals} />
          {suffix && (
            <span 
              className="text-sm font-mono font-medium ml-1"
              style={{ color: "#D4956A" }}
            >
              {suffix}
            </span>
          )}
        </div>
        <p className="text-[10px] font-semibold uppercase tracking-wider mt-1" style={{ color: "#6B7280" }}>
          {label}
        </p>
      </div>
    </motion.div>
  );
}

/**
 * Split-flap counter bar - Bloomberg Terminal style
 */
export interface SplitFlapCounterBarProps {
  totalLeads: number;
  enrichedCount: number;
  averageALS: number;
  meetingsBooked: number;
}

export function SplitFlapCounterBar({ 
  totalLeads, 
  enrichedCount, 
  averageALS, 
  meetingsBooked 
}: SplitFlapCounterBarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="w-full p-4 rounded-2xl"
      style={{
        backgroundColor: "#0A0908",
        border: "1px solid rgba(212, 149, 106, 0.15)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)"
      }}
    >
      <div className="grid grid-cols-4 gap-4">
        <CounterCard
          value={totalLeads}
          label="Total Leads"
          icon={<Users className="w-5 h-5" />}
        />
        <CounterCard
          value={enrichedCount}
          label="Enriched"
          icon={<Database className="w-5 h-5" />}
        />
        <CounterCard
          value={averageALS}
          label="Avg ALS Score"
          icon={<TrendingUp className="w-5 h-5" />}
        />
        <CounterCard
          value={meetingsBooked}
          label="Meetings Booked"
          icon={<Calendar className="w-5 h-5" />}
        />
      </div>
    </motion.div>
  );
}
