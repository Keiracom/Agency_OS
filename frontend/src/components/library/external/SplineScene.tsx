"use client";

import { useState, useEffect } from "react";

interface SplineSceneProps {
  sceneUrl?: string;
}

// Animated 3D-style placeholder until Spline compatibility is resolved
export function SplineScene({ sceneUrl }: SplineSceneProps) {
  const [rotation, setRotation] = useState(0);
  const [hover, setHover] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setRotation((r) => (r + 1) % 360);
    }, 50);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="relative w-full h-full min-h-[300px] bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950 rounded-xl overflow-hidden"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* Animated background grid */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(168, 85, 247, 0.3) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(168, 85, 247, 0.3) 1px, transparent 1px)
          `,
          backgroundSize: "30px 30px",
          transform: `perspective(500px) rotateX(60deg) translateY(${rotation % 30}px)`,
          transformOrigin: "center top",
        }}
      />

      {/* Central 3D object placeholder */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div
          className="relative"
          style={{
            transform: `rotateY(${rotation}deg) rotateX(${hover ? 15 : 0}deg)`,
            transformStyle: "preserve-3d",
            transition: "transform 0.3s ease",
          }}
        >
          {/* Cube faces */}
          <div
            className="w-24 h-24 border-2 border-purple-500/60 bg-purple-500/10 backdrop-blur-sm absolute"
            style={{
              transform: "translateZ(48px)",
              boxShadow: "0 0 30px rgba(168, 85, 247, 0.3), inset 0 0 20px rgba(168, 85, 247, 0.1)",
            }}
          />
          <div
            className="w-24 h-24 border-2 border-purple-500/40 bg-purple-500/5 absolute"
            style={{ transform: "rotateY(90deg) translateZ(48px)" }}
          />
          <div
            className="w-24 h-24 border-2 border-purple-500/40 bg-purple-500/5 absolute"
            style={{ transform: "rotateY(-90deg) translateZ(48px)" }}
          />
          <div
            className="w-24 h-24 border-2 border-purple-500/30 bg-purple-500/5 absolute"
            style={{ transform: "translateZ(-48px)" }}
          />
          <div
            className="w-24 h-24 border-2 border-pink-500/40 bg-pink-500/5 absolute"
            style={{ transform: "rotateX(90deg) translateZ(48px)" }}
          />
          <div
            className="w-24 h-24 border-2 border-pink-500/30 bg-pink-500/5 absolute"
            style={{ transform: "rotateX(-90deg) translateZ(48px)" }}
          />
        </div>
      </div>

      {/* Floating particles */}
      {[...Array(8)].map((_, i) => (
        <div
          key={i}
          className="absolute w-1 h-1 bg-purple-400 rounded-full animate-pulse"
          style={{
            left: `${20 + (i * 10)}%`,
            top: `${30 + Math.sin(i) * 20}%`,
            animationDelay: `${i * 0.2}s`,
            opacity: 0.6,
          }}
        />
      ))}

      {/* Corner decorations */}
      <div className="absolute top-3 left-3 w-6 h-6 border-l-2 border-t-2 border-purple-500/50" />
      <div className="absolute top-3 right-3 w-6 h-6 border-r-2 border-t-2 border-purple-500/50" />
      <div className="absolute bottom-3 left-3 w-6 h-6 border-l-2 border-b-2 border-purple-500/50" />
      <div className="absolute bottom-3 right-3 w-6 h-6 border-r-2 border-b-2 border-purple-500/50" />

      {/* Label */}
      <div className="absolute bottom-4 left-0 right-0 text-center">
        <p className="text-purple-400/60 text-xs font-mono">SPLINE 3D PLACEHOLDER</p>
        <p className="text-purple-500/40 text-[10px] font-mono mt-1">
          Replace with your .splinecode URL
        </p>
      </div>

      {/* Glow effect */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(circle at 50% 50%, rgba(168, 85, 247, 0.15) 0%, transparent 60%)",
        }}
      />
    </div>
  );
}

export default SplineScene;
