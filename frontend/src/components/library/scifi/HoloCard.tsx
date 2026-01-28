"use client";

import { useState, useEffect } from "react";

interface HoloCardProps {
  title?: string;
  subtitle?: string;
  children?: React.ReactNode;
}

export function HoloCard({
  title = "SYSTEM STATUS",
  subtitle = "ONLINE",
  children
}: HoloCardProps) {
  const [glitchActive, setGlitchActive] = useState(false);
  const [scanLine, setScanLine] = useState(0);

  // Periodic glitch effect
  useEffect(() => {
    const glitchInterval = setInterval(() => {
      setGlitchActive(true);
      setTimeout(() => setGlitchActive(false), 100);
    }, 3000 + Math.random() * 2000);

    return () => clearInterval(glitchInterval);
  }, []);

  // Scanning line animation
  useEffect(() => {
    const scanInterval = setInterval(() => {
      setScanLine((prev) => (prev + 1) % 100);
    }, 30);

    return () => clearInterval(scanInterval);
  }, []);

  return (
    <div className="relative w-full h-full min-h-[300px] p-1">
      {/* Outer glow */}
      <div className="absolute inset-0 bg-cyan-500/20 blur-xl rounded-lg" />

      {/* Main card container */}
      <div
        className={`relative w-full h-full bg-slate-950/90 backdrop-blur-sm border border-cyan-500/50 rounded-lg overflow-hidden ${
          glitchActive ? "translate-x-[2px]" : ""
        }`}
        style={{
          boxShadow: `
            0 0 20px rgba(0, 255, 255, 0.3),
            inset 0 0 20px rgba(0, 255, 255, 0.1),
            0 0 40px rgba(0, 255, 255, 0.1)
          `,
        }}
      >
        {/* Animated corner accents */}
        <svg className="absolute top-0 left-0 w-16 h-16" viewBox="0 0 64 64">
          <path
            d="M 0 20 L 0 0 L 20 0"
            fill="none"
            stroke="cyan"
            strokeWidth="2"
            className="animate-pulse"
          />
          <circle cx="0" cy="0" r="3" fill="cyan" className="animate-ping" />
        </svg>
        <svg className="absolute top-0 right-0 w-16 h-16" viewBox="0 0 64 64">
          <path
            d="M 44 0 L 64 0 L 64 20"
            fill="none"
            stroke="cyan"
            strokeWidth="2"
            className="animate-pulse"
          />
        </svg>
        <svg className="absolute bottom-0 left-0 w-16 h-16" viewBox="0 0 64 64">
          <path
            d="M 0 44 L 0 64 L 20 64"
            fill="none"
            stroke="cyan"
            strokeWidth="2"
            className="animate-pulse"
          />
        </svg>
        <svg className="absolute bottom-0 right-0 w-16 h-16" viewBox="0 0 64 64">
          <path
            d="M 44 64 L 64 64 L 64 44"
            fill="none"
            stroke="cyan"
            strokeWidth="2"
            className="animate-pulse"
          />
        </svg>

        {/* Scan line effect */}
        <div
          className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent pointer-events-none"
          style={{ top: `${scanLine}%` }}
        />

        {/* Header */}
        <div className="relative border-b border-cyan-500/30 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3
                className={`text-cyan-400 font-mono text-lg tracking-widest ${
                  glitchActive ? "text-red-400" : ""
                }`}
                style={{
                  textShadow: "0 0 10px cyan, 0 0 20px cyan",
                }}
              >
                {title}
              </h3>
              <p className="text-cyan-600 font-mono text-xs tracking-wider mt-1">
                {subtitle}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
              <span className="text-cyan-400 font-mono text-xs">ACTIVE</span>
            </div>
          </div>
        </div>

        {/* Content area */}
        <div className="relative p-4">
          {children || (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 border border-cyan-500/50 rounded flex items-center justify-center">
                  <span className="text-2xl text-cyan-400">◇</span>
                </div>
                <div>
                  <p className="text-cyan-300 font-mono text-sm">QUANTUM CORE</p>
                  <p className="text-cyan-600 font-mono text-xs">Stability: 99.7%</p>
                </div>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-teal-400 rounded-full animate-pulse"
                  style={{ width: "87%" }}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                {["SYNC", "LOAD", "TEMP"].map((label, i) => (
                  <div key={label} className="bg-slate-900/50 border border-cyan-500/20 rounded p-2">
                    <p className="text-cyan-400 font-mono text-lg">
                      {[98, 42, 37][i]}%
                    </p>
                    <p className="text-cyan-600 font-mono text-[10px]">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer status bar */}
        <div className="absolute bottom-0 left-0 right-0 h-6 bg-slate-900/80 border-t border-cyan-500/20 flex items-center px-3 justify-between">
          <span className="text-cyan-600 font-mono text-[10px]">
            SYS://HOLO.CARD.v2.1
          </span>
          <span className="text-cyan-600 font-mono text-[10px] animate-pulse">
            ▸▸▸ CONNECTED ◂◂◂
          </span>
        </div>

        {/* Noise overlay */}
        <div
          className="absolute inset-0 opacity-[0.03] pointer-events-none"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          }}
        />
      </div>
    </div>
  );
}

export default HoloCard;
