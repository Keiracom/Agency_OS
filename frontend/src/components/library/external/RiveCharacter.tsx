"use client";

import { useState, useCallback } from "react";
import {
  useRive,
  useStateMachineInput,
  Layout,
  Fit,
  Alignment,
} from "@rive-app/react-canvas";

interface RiveCharacterProps {
  size?: number;
  onStateChange?: (state: string) => void;
}

type AnimationState = "idle" | "waving" | "jumping";

// Interactive character animation with state machine interactions
export function RiveCharacter({
  size = 200,
  onStateChange
}: RiveCharacterProps) {
  const [currentState, setCurrentState] = useState<AnimationState>("idle");
  const [interactionCount, setInteractionCount] = useState(0);

  const { RiveComponent, rive } = useRive({
    src: "https://cdn.rive.app/animations/vehicles.riv",
    stateMachines: "bumpy",
    autoplay: true,
    layout: new Layout({
      fit: Fit.Contain,
      alignment: Alignment.Center,
    }),
  });

  // Get state machine input for interactions
  const bumpInput = useStateMachineInput(rive, "bumpy", "bump");

  const handleHover = useCallback(() => {
    setCurrentState("waving");
    onStateChange?.("waving");

    // Trigger state machine input if available
    if (bumpInput) {
      bumpInput.fire();
    }
  }, [bumpInput, onStateChange]);

  const handleHoverEnd = useCallback(() => {
    setCurrentState("idle");
    onStateChange?.("idle");
  }, [onStateChange]);

  const handleClick = useCallback(() => {
    setCurrentState("jumping");
    setInteractionCount((prev) => prev + 1);
    onStateChange?.("jumping");

    // Trigger bump animation on click
    if (bumpInput) {
      bumpInput.fire();
    }

    // Reset to idle after animation
    setTimeout(() => {
      setCurrentState("idle");
      onStateChange?.("idle");
    }, 800);
  }, [bumpInput, onStateChange]);

  // State color mapping (green color scheme)
  const stateColors: Record<AnimationState, { bg: string; text: string; glow: string }> = {
    idle: {
      bg: "bg-emerald-500/10",
      text: "text-emerald-400",
      glow: "rgba(52, 211, 153, 0.2)",
    },
    waving: {
      bg: "bg-green-500/20",
      text: "text-green-400",
      glow: "rgba(74, 222, 128, 0.4)",
    },
    jumping: {
      bg: "bg-lime-500/30",
      text: "text-lime-300",
      glow: "rgba(163, 230, 53, 0.5)",
    },
  };

  const currentColors = stateColors[currentState];

  return (
    <div className="w-full h-full min-h-[400px] bg-slate-950 rounded-xl flex flex-col items-center justify-center gap-6 p-6 relative">
      {/* Character container */}
      <div
        className="relative cursor-pointer transition-transform duration-300 hover:scale-105"
        style={{ width: size, height: size }}
        onMouseEnter={handleHover}
        onMouseLeave={handleHoverEnd}
        onClick={handleClick}
      >
        {/* Dynamic glow effect based on state */}
        <div
          className="absolute inset-[-20%] blur-3xl rounded-full transition-all duration-300"
          style={{ backgroundColor: currentColors.glow }}
        />

        {/* Animated border ring */}
        <div
          className={`
            absolute inset-[-5%] border-2 rounded-xl transition-all duration-300
            ${currentState === "idle" ? "border-emerald-500/30" : ""}
            ${currentState === "waving" ? "border-green-400/50 animate-pulse" : ""}
            ${currentState === "jumping" ? "border-lime-400/70" : ""}
          `}
          style={{
            transform: currentState === "jumping" ? "scale(1.1)" : "scale(1)",
          }}
        />

        {/* Rive canvas container */}
        <div
          className={`
            relative w-full h-full rounded-xl overflow-hidden transition-all duration-300
            ${currentColors.bg} backdrop-blur-sm
          `}
        >
          <RiveComponent />
        </div>

        {/* Corner accents (green theme) */}
        <div className="absolute -top-1 -left-1 w-4 h-4 border-l-2 border-t-2 border-emerald-500 transition-all duration-300" />
        <div className="absolute -top-1 -right-1 w-4 h-4 border-r-2 border-t-2 border-emerald-500 transition-all duration-300" />
        <div className="absolute -bottom-1 -left-1 w-4 h-4 border-l-2 border-b-2 border-emerald-500 transition-all duration-300" />
        <div className="absolute -bottom-1 -right-1 w-4 h-4 border-r-2 border-b-2 border-emerald-500 transition-all duration-300" />

        {/* Interaction hint */}
        <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 text-xs font-mono text-emerald-400/60 whitespace-nowrap">
          Hover or Click
        </div>
      </div>

      {/* State indicator panel */}
      <div className="flex flex-col items-center gap-4 mt-8">
        {/* Current state display */}
        <div className={`
          px-6 py-2 rounded-lg border-2 transition-all duration-300 font-mono text-sm tracking-widest
          ${currentState === "idle" ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-400" : ""}
          ${currentState === "waving" ? "border-green-400/50 bg-green-500/20 text-green-400" : ""}
          ${currentState === "jumping" ? "border-lime-400/50 bg-lime-500/20 text-lime-300" : ""}
        `}>
          STATE: {currentState.toUpperCase()}
        </div>

        {/* State indicators */}
        <div className="flex gap-6 text-xs font-mono">
          <span className={`flex items-center gap-2 transition-colors ${currentState === "idle" ? "text-emerald-400" : "text-slate-500"}`}>
            <span className={`w-2 h-2 rounded-full transition-colors ${currentState === "idle" ? "bg-emerald-400" : "bg-slate-600"}`} />
            IDLE
          </span>
          <span className={`flex items-center gap-2 transition-colors ${currentState === "waving" ? "text-green-400" : "text-slate-500"}`}>
            <span className={`w-2 h-2 rounded-full transition-colors ${currentState === "waving" ? "bg-green-400" : "bg-slate-600"}`} />
            WAVE
          </span>
          <span className={`flex items-center gap-2 transition-colors ${currentState === "jumping" ? "text-lime-300" : "text-slate-500"}`}>
            <span className={`w-2 h-2 rounded-full transition-colors ${currentState === "jumping" ? "bg-lime-400" : "bg-slate-600"}`} />
            JUMP
          </span>
        </div>

        {/* Interaction counter */}
        <div className="text-xs font-mono text-slate-500">
          Interactions: <span className="text-emerald-400">{interactionCount}</span>
        </div>
      </div>

      {/* Bottom label */}
      <p className="absolute bottom-4 text-emerald-400/60 text-xs font-mono">
        RIVE CHARACTER
      </p>

      {/* Background decorative elements */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-xl">
        {/* Subtle grid */}
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: `
              linear-gradient(rgba(52, 211, 153, 0.5) 1px, transparent 1px),
              linear-gradient(90deg, rgba(52, 211, 153, 0.5) 1px, transparent 1px)
            `,
            backgroundSize: "30px 30px",
          }}
        />

        {/* Floating particles */}
        <div className="absolute top-1/4 left-1/4 w-1 h-1 bg-emerald-400/30 rounded-full animate-ping" />
        <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-green-400/30 rounded-full animate-ping" style={{ animationDelay: "500ms" }} />
        <div className="absolute bottom-1/3 left-1/3 w-1 h-1 bg-lime-400/30 rounded-full animate-ping" style={{ animationDelay: "1000ms" }} />
      </div>
    </div>
  );
}

export default RiveCharacter;
