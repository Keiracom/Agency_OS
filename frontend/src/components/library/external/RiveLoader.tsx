"use client";

import { useRive, Layout, Fit, Alignment } from "@rive-app/react-canvas";

interface RiveLoaderProps {
  size?: number;
  label?: string;
  showLabel?: boolean;
}

// Animated loading indicator with Rive animation
export function RiveLoader({
  size = 120,
  label = "LOADING",
  showLabel = true
}: RiveLoaderProps) {
  const { RiveComponent, rive } = useRive({
    src: "https://cdn.rive.app/animations/off_road_car.riv",
    autoplay: true,
    layout: new Layout({
      fit: Fit.Contain,
      alignment: Alignment.Center,
    }),
  });

  return (
    <div className="w-full h-full min-h-[300px] bg-slate-950 rounded-xl flex flex-col items-center justify-center gap-4 relative">
      {/* Main loader container */}
      <div className="relative" style={{ width: size, height: size }}>
        {/* Outer glow effect */}
        <div className="absolute inset-0 bg-cyan-500/20 blur-2xl rounded-full animate-pulse" />

        {/* Secondary glow ring */}
        <div
          className="absolute inset-[-10%] border-2 border-cyan-500/30 rounded-full animate-spin"
          style={{ animationDuration: "3s" }}
        />

        {/* Inner glow ring */}
        <div
          className="absolute inset-[5%] border border-cyan-400/20 rounded-full animate-spin"
          style={{ animationDuration: "2s", animationDirection: "reverse" }}
        />

        {/* Rive canvas container */}
        <div className="relative w-full h-full rounded-full overflow-hidden bg-slate-900/50 backdrop-blur-sm">
          <RiveComponent />
        </div>

        {/* Corner accent dots */}
        <div className="absolute -top-1 left-1/2 w-2 h-2 bg-cyan-400 rounded-full transform -translate-x-1/2 animate-pulse" />
        <div className="absolute -bottom-1 left-1/2 w-2 h-2 bg-cyan-400 rounded-full transform -translate-x-1/2 animate-pulse" />
        <div className="absolute top-1/2 -left-1 w-2 h-2 bg-cyan-400 rounded-full transform -translate-y-1/2 animate-pulse" />
        <div className="absolute top-1/2 -right-1 w-2 h-2 bg-cyan-400 rounded-full transform -translate-y-1/2 animate-pulse" />
      </div>

      {/* Loading text with animated dots */}
      {showLabel && (
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 text-sm font-mono tracking-widest">
            {label}
          </span>
          <span className="flex gap-1">
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </span>
        </div>
      )}

      {/* Bottom label */}
      <p className="absolute bottom-4 text-cyan-400/60 text-xs font-mono">
        RIVE LOADER
      </p>

      {/* Subtle background grid */}
      <div
        className="absolute inset-0 pointer-events-none opacity-5"
        style={{
          backgroundImage: `
            linear-gradient(rgba(34, 211, 238, 0.5) 1px, transparent 1px),
            linear-gradient(90deg, rgba(34, 211, 238, 0.5) 1px, transparent 1px)
          `,
          backgroundSize: "20px 20px",
        }}
      />
    </div>
  );
}

export default RiveLoader;
