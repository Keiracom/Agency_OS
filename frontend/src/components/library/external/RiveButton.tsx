"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { useRive, Layout, Fit, Alignment } from "@rive-app/react-canvas";

interface RiveButtonProps {
  label?: string;
  onClick?: () => void;
}

// Interactive button with Rive animation
export function RiveButton({ label = "ACTIVATE", onClick }: RiveButtonProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isPressed, setIsPressed] = useState(false);
  const [ripples, setRipples] = useState<{ id: number; x: number; y: number }[]>([]);

  const handleClick = useCallback((e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const newRipple = { id: Date.now(), x, y };
    setRipples((prev) => [...prev, newRipple]);

    setTimeout(() => {
      setRipples((prev) => prev.filter((r) => r.id !== newRipple.id));
    }, 600);

    onClick?.();
  }, [onClick]);

  return (
    <div className="w-full h-full min-h-[300px] bg-slate-950 rounded-xl flex flex-col items-center justify-center gap-6 p-6">
      {/* Rive Animation Display */}
      <div className="relative w-48 h-48">
        <RiveAnimation />
      </div>

      {/* Interactive Button */}
      <button
        className={`
          relative px-8 py-3 rounded-lg font-mono text-sm tracking-widest
          border-2 transition-all duration-300 overflow-hidden
          ${isHovered
            ? "border-orange-400 bg-orange-500/20 text-orange-300 scale-105"
            : "border-orange-500/50 bg-orange-500/10 text-orange-400"
          }
          ${isPressed ? "scale-95" : ""}
        `}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onMouseDown={() => setIsPressed(true)}
        onMouseUp={() => setIsPressed(false)}
        onClick={handleClick}
        style={{
          boxShadow: isHovered
            ? "0 0 30px rgba(251, 146, 60, 0.4), inset 0 0 20px rgba(251, 146, 60, 0.1)"
            : "0 0 15px rgba(251, 146, 60, 0.2)",
        }}
      >
        {/* Ripple effects */}
        {ripples.map((ripple) => (
          <span
            key={ripple.id}
            className="absolute w-1 h-1 bg-orange-400 rounded-full animate-ping"
            style={{
              left: ripple.x,
              top: ripple.y,
              transform: "translate(-50%, -50%)",
            }}
          />
        ))}

        {/* Button content */}
        <span className="relative z-10">{label}</span>

        {/* Animated border glow */}
        <div className="absolute inset-0 rounded-lg opacity-50">
          <div
            className="absolute inset-0 rounded-lg animate-pulse"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(251, 146, 60, 0.3), transparent)",
              backgroundSize: "200% 100%",
              animation: "shimmer 2s infinite",
            }}
          />
        </div>
      </button>

      {/* Status indicators */}
      <div className="flex gap-4 text-xs font-mono">
        <span className={`flex items-center gap-1 ${isHovered ? "text-orange-400" : "text-slate-500"}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isHovered ? "bg-orange-400" : "bg-slate-600"}`} />
          HOVER
        </span>
        <span className={`flex items-center gap-1 ${isPressed ? "text-orange-400" : "text-slate-500"}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${isPressed ? "bg-orange-400" : "bg-slate-600"}`} />
          PRESS
        </span>
      </div>

      <style jsx>{`
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
    </div>
  );
}

// Separate Rive animation component
function RiveAnimation() {
  const { RiveComponent, rive } = useRive({
    src: "https://cdn.rive.app/animations/vehicles.riv",
    stateMachines: "bumpy",
    layout: new Layout({
      fit: Fit.Contain,
      alignment: Alignment.Center,
    }),
    autoplay: true,
  });

  return (
    <div className="relative w-full h-full">
      {/* Glow effect behind animation */}
      <div className="absolute inset-0 bg-orange-500/10 blur-2xl rounded-full" />

      {/* Border frame */}
      <div className="absolute inset-0 border-2 border-orange-500/30 rounded-xl" />

      {/* Rive canvas */}
      <div className="relative w-full h-full rounded-xl overflow-hidden bg-slate-900/50">
        <RiveComponent />
      </div>

      {/* Corner accents */}
      <div className="absolute -top-1 -left-1 w-3 h-3 border-l-2 border-t-2 border-orange-500" />
      <div className="absolute -top-1 -right-1 w-3 h-3 border-r-2 border-t-2 border-orange-500" />
      <div className="absolute -bottom-1 -left-1 w-3 h-3 border-l-2 border-b-2 border-orange-500" />
      <div className="absolute -bottom-1 -right-1 w-3 h-3 border-r-2 border-b-2 border-orange-500" />
    </div>
  );
}

export default RiveButton;
