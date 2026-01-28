"use client";

import { useState, useRef } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";

// ============================================================================
// DYNAMIC IMPORTS - Avoid SSR issues with 3D/canvas libraries
// ============================================================================

// R3F + Drei Components
const FloatingCrystal = dynamic(
  () => import("@/src/components/library/3d/FloatingCrystal"),
  { ssr: false, loading: () => <ComponentLoader name="Floating Crystal" color="#00d4ff" /> }
);
const GlassOrb = dynamic(
  () => import("@/src/components/library/3d/GlassOrb").catch(() => ({ default: () => <PlaceholderCard name="GlassOrb" color="#00d4ff" /> })),
  { ssr: false, loading: () => <ComponentLoader name="Glass Orb" color="#00d4ff" /> }
);
const ParticleField = dynamic(
  () => import("@/src/components/library/3d/ParticleField").catch(() => ({ default: () => <PlaceholderCard name="ParticleField" color="#00d4ff" /> })),
  { ssr: false, loading: () => <ComponentLoader name="Particle Field" color="#00d4ff" /> }
);
const FloatingText3D = dynamic(
  () => import("@/src/components/library/3d/FloatingText3D").catch(() => ({ default: () => <PlaceholderCard name="FloatingText3D" color="#00d4ff" /> })),
  { ssr: false, loading: () => <ComponentLoader name="3D Text" color="#00d4ff" /> }
);
const WaveGrid = dynamic(
  () => import("@/src/components/library/3d/WaveGrid").catch(() => ({ default: () => <PlaceholderCard name="WaveGrid" color="#00d4ff" /> })),
  { ssr: false, loading: () => <ComponentLoader name="Wave Grid" color="#00d4ff" /> }
);
const NeonTunnel = dynamic(
  () => import("@/src/components/library/3d/NeonTunnel").catch(() => ({ default: () => <PlaceholderCard name="NeonTunnel" color="#00d4ff" /> })),
  { ssr: false, loading: () => <ComponentLoader name="Neon Tunnel" color="#00d4ff" /> }
);

// Sci-Fi Components
const HoloCard = dynamic(
  () => import("@/src/components/library/scifi/HoloCard"),
  { ssr: false, loading: () => <ComponentLoader name="Holo Card" color="#00ffff" /> }
);

// Spline Components
const SplineScene = dynamic(
  () => import("@/src/components/library/external/SplineScene"),
  { ssr: false, loading: () => <ComponentLoader name="Spline Scene" color="#a855f7" /> }
);
const SplineRobot = dynamic(
  () => import("@/src/components/library/external/SplineRobot").catch(() => ({ default: () => <PlaceholderCard name="SplineRobot" color="#a855f7" /> })),
  { ssr: false, loading: () => <ComponentLoader name="Spline Robot" color="#a855f7" /> }
);
const SplineAbstract = dynamic(
  () => import("@/src/components/library/external/SplineAbstract").catch(() => ({ default: () => <PlaceholderCard name="SplineAbstract" color="#a855f7" /> })),
  { ssr: false, loading: () => <ComponentLoader name="Spline Abstract" color="#a855f7" /> }
);

// Rive Components
const RiveButton = dynamic(
  () => import("@/src/components/library/external/RiveButton"),
  { ssr: false, loading: () => <ComponentLoader name="Rive Button" color="#f97316" /> }
);
const RiveLoader = dynamic(
  () => import("@/src/components/library/external/RiveLoader").catch(() => ({ default: () => <PlaceholderCard name="RiveLoader" color="#f97316" /> })),
  { ssr: false, loading: () => <ComponentLoader name="Rive Loader" color="#f97316" /> }
);
const RiveCharacter = dynamic(
  () => import("@/src/components/library/external/RiveCharacter").catch(() => ({ default: () => <PlaceholderCard name="RiveCharacter" color="#f97316" /> })),
  { ssr: false, loading: () => <ComponentLoader name="Rive Character" color="#f97316" /> }
);

// UI Effect Components
const SparklesCore = dynamic(
  () => import("@/src/components/ui/sparkles").then(mod => ({ default: mod.SparklesCore })),
  { ssr: false }
);

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

function ComponentLoader({ name, color = "#00d4ff" }: { name: string; color?: string }) {
  return (
    <div className="w-full h-full min-h-[350px] bg-slate-900/50 rounded-xl border border-slate-700/50 flex items-center justify-center">
      <div className="text-center">
        <div
          className="w-12 h-12 border-3 rounded-full animate-spin mx-auto mb-4"
          style={{
            borderColor: `${color}30`,
            borderTopColor: color,
          }}
        />
        <p className="text-slate-400 text-sm font-mono">Loading {name}...</p>
        <div className="flex justify-center gap-1 mt-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="w-1.5 h-1.5 rounded-full animate-bounce"
              style={{ backgroundColor: color, animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function PlaceholderCard({ name, color = "#666" }: { name: string; color?: string }) {
  return (
    <div className="w-full h-full min-h-[350px] bg-slate-900/50 rounded-xl border border-dashed border-slate-600/50 flex items-center justify-center">
      <div className="text-center">
        <div
          className="w-16 h-16 rounded-xl flex items-center justify-center mx-auto mb-4"
          style={{ backgroundColor: `${color}20`, border: `1px solid ${color}40` }}
        >
          <span style={{ color }} className="text-2xl">+</span>
        </div>
        <p className="text-slate-400 text-sm font-mono">{name}</p>
        <p className="text-slate-600 text-xs mt-1">Coming soon</p>
      </div>
    </div>
  );
}

interface ShowcaseCardProps {
  title: string;
  engine: string;
  description: string;
  accentColor: string;
  children: React.ReactNode;
  codeSnippet?: string;
  tags?: string[];
}

function ShowcaseCard({ title, engine, description, accentColor, children, codeSnippet, tags = [] }: ShowcaseCardProps) {
  const [showCode, setShowCode] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  return (
    <>
      {/* Fullscreen Modal */}
      <AnimatePresence>
        {isFullscreen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-slate-950/95 backdrop-blur-md flex items-center justify-center p-8"
            onClick={() => setIsFullscreen(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="w-full max-w-6xl h-[80vh] bg-slate-900 rounded-2xl border border-slate-700/50 overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="h-full flex flex-col">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50">
                  <div>
                    <h2 className="text-xl font-bold text-white">{title}</h2>
                    <p className="text-slate-500 text-sm font-mono">{engine}</p>
                  </div>
                  <button
                    onClick={() => setIsFullscreen(false)}
                    className="w-10 h-10 rounded-lg bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white transition-colors"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <div className="flex-1 p-6">
                  {children}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Card */}
      <div className="group relative">
        {/* Glow effect on hover */}
        <div
          className="absolute -inset-1 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl"
          style={{ background: `linear-gradient(135deg, ${accentColor}40, transparent)` }}
        />

        {/* Card */}
        <div className="relative bg-slate-900/80 backdrop-blur-sm rounded-xl border border-slate-700/50 overflow-hidden h-full flex flex-col">
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between flex-shrink-0">
            <div>
              <h3 className="text-white font-semibold">{title}</h3>
              <p className="text-slate-500 text-xs font-mono">{engine}</p>
            </div>
            <div className="flex items-center gap-2">
              {/* Fullscreen button */}
              <button
                onClick={() => setIsFullscreen(true)}
                className="w-7 h-7 rounded-md bg-slate-800/50 hover:bg-slate-700 flex items-center justify-center text-slate-500 hover:text-white transition-colors"
                title="Fullscreen"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
              {codeSnippet && (
                <button
                  onClick={() => setShowCode(!showCode)}
                  className={`w-7 h-7 rounded-md flex items-center justify-center transition-colors ${
                    showCode
                      ? 'bg-slate-700 text-white'
                      : 'bg-slate-800/50 hover:bg-slate-700 text-slate-500 hover:text-white'
                  }`}
                  title="Show code"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                </button>
              )}
              <span
                className="px-2 py-1 rounded text-xs font-mono"
                style={{
                  backgroundColor: `${accentColor}20`,
                  color: accentColor,
                  border: `1px solid ${accentColor}40`,
                }}
              >
                LIVE
              </span>
            </div>
          </div>

          {/* Tags */}
          {tags.length > 0 && (
            <div className="px-4 py-2 border-b border-slate-700/30 flex gap-2 flex-wrap flex-shrink-0">
              {tags.map((tag) => (
                <span key={tag} className="px-2 py-0.5 bg-slate-800/50 rounded text-xs text-slate-400 font-mono">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Component container */}
          <div className="h-[380px] flex-shrink-0 overflow-hidden">
            <AnimatePresence mode="wait">
              {showCode ? (
                <motion.div
                  key="code"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="h-full p-4 overflow-auto"
                >
                  <pre className="text-xs font-mono text-slate-300 bg-slate-950/50 p-4 rounded-lg overflow-x-auto">
                    <code>{codeSnippet}</code>
                  </pre>
                </motion.div>
              ) : (
                <motion.div
                  key="preview"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="h-full"
                >
                  {children}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-slate-700/50 bg-slate-950/50 mt-auto">
            <p className="text-slate-500 text-xs leading-relaxed">{description}</p>
          </div>
        </div>
      </div>
    </>
  );
}

// ============================================================================
// CATEGORY DATA
// ============================================================================

type CategoryKey = "all" | "r3f" | "spline" | "rive" | "scifi" | "ui";

const categories: { key: CategoryKey; label: string; color: string; icon: string; count: number }[] = [
  { key: "all", label: "All", color: "#ffffff", icon: "⬡", count: 14 },
  { key: "r3f", label: "React Three Fiber", color: "#00d4ff", icon: "◇", count: 6 },
  { key: "spline", label: "Spline", color: "#a855f7", icon: "◈", count: 3 },
  { key: "rive", label: "Rive", color: "#f97316", icon: "◉", count: 3 },
  { key: "scifi", label: "Sci-Fi UI", color: "#00ffff", icon: "◎", count: 1 },
  { key: "ui", label: "Effects", color: "#22c55e", icon: "✦", count: 1 },
];

// ============================================================================
// MAIN SHOWROOM PAGE
// ============================================================================

export default function ShowroomPage() {
  const [activeCategory, setActiveCategory] = useState<CategoryKey>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const isDark = theme === "dark";

  const shouldShow = (category: CategoryKey, title: string) => {
    const categoryMatch = activeCategory === "all" || activeCategory === category;
    const searchMatch = !searchQuery || title.toLowerCase().includes(searchQuery.toLowerCase());
    return categoryMatch && searchMatch;
  };

  return (
    <div className={`min-h-screen transition-colors duration-300 ${isDark ? "bg-slate-950" : "bg-gray-50"}`}>
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden">
        <div className={`absolute inset-0 transition-colors duration-300 ${isDark ? "bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950" : "bg-gradient-to-br from-gray-50 via-white to-gray-100"}`} />
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `radial-gradient(circle at 20% 20%, rgba(0, 200, 255, 0.15) 0%, transparent 40%),
                             radial-gradient(circle at 80% 80%, rgba(168, 85, 247, 0.1) 0%, transparent 40%),
                             radial-gradient(circle at 50% 50%, rgba(249, 115, 22, 0.05) 0%, transparent 60%)`,
          }}
        />
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgba(100, 100, 100, 0.2) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(100, 100, 100, 0.2) 1px, transparent 1px)
            `,
            backgroundSize: "60px 60px",
          }}
        />
        {/* Floating orbs */}
        <div className="absolute top-20 left-[10%] w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDuration: '8s' }} />
        <div className="absolute bottom-20 right-[10%] w-96 h-96 bg-purple-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDuration: '10s' }} />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className={`border-b backdrop-blur-md sticky top-0 z-20 transition-colors duration-300 ${isDark ? "border-slate-800/50 bg-slate-950/80" : "border-gray-200 bg-white/80"}`}>
          <div className="max-w-[1800px] mx-auto px-6 py-4">
            <div className="flex items-center justify-between gap-8">
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-purple-500 flex items-center justify-center">
                    <span className="text-white font-bold text-lg">S</span>
                  </div>
                  <div className={`absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 ${isDark ? "border-slate-950" : "border-white"}`} />
                </div>
                <div>
                  <h1 className={`text-xl font-bold ${isDark ? "text-white" : "text-gray-900"}`}>Component Showroom</h1>
                  <p className={`text-xs font-mono ${isDark ? "text-slate-500" : "text-gray-500"}`}>R3F • SPLINE • RIVE • UI EFFECTS</p>
                </div>
              </div>

              {/* Search */}
              <div className="flex-1 max-w-md">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search components..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className={`w-full border rounded-lg px-4 py-2 pl-10 text-sm focus:outline-none transition-colors ${
                      isDark
                        ? "bg-slate-800/50 border-slate-700/50 text-white placeholder-slate-500 focus:border-cyan-500/50"
                        : "bg-white border-gray-300 text-gray-900 placeholder-gray-400 focus:border-cyan-500"
                    }`}
                  />
                  <svg className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? "text-slate-500" : "text-gray-400"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>

              <div className="flex items-center gap-4">
                {/* Theme Toggle */}
                <button
                  onClick={() => setTheme(isDark ? "light" : "dark")}
                  className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                    isDark
                      ? "bg-slate-800 hover:bg-slate-700 text-yellow-400"
                      : "bg-gray-100 hover:bg-gray-200 text-slate-700"
                  }`}
                  title={`Switch to ${isDark ? "light" : "dark"} mode`}
                >
                  {isDark ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                    </svg>
                  )}
                </button>
                <span className={`flex items-center gap-2 text-xs font-mono ${isDark ? "text-slate-500" : "text-gray-500"}`}>
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  {categories[0].count} COMPONENTS
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Category Tabs */}
        <div className="max-w-[1800px] mx-auto px-6 py-6">
          <div className="flex flex-wrap gap-2">
            {categories.map((cat) => (
              <button
                key={cat.key}
                onClick={() => setActiveCategory(cat.key)}
                className={`group px-4 py-2.5 rounded-xl text-sm font-medium border backdrop-blur-sm transition-all duration-300 flex items-center gap-2 ${
                  activeCategory === cat.key
                    ? "scale-105 shadow-lg"
                    : "hover:scale-102"
                }`}
                style={{
                  backgroundColor: activeCategory === cat.key ? `${cat.color}15` : `${cat.color}05`,
                  borderColor: activeCategory === cat.key ? `${cat.color}60` : `${cat.color}20`,
                  color: activeCategory === cat.key ? cat.color : `${cat.color}99`,
                  boxShadow: activeCategory === cat.key ? `0 4px 20px ${cat.color}20` : 'none',
                }}
              >
                <span className="text-lg opacity-70">{cat.icon}</span>
                <span>{cat.label}</span>
                <span
                  className="ml-1 px-1.5 py-0.5 rounded text-xs"
                  style={{ backgroundColor: `${cat.color}20` }}
                >
                  {cat.count}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Component Grid */}
        <main className="max-w-[1800px] mx-auto px-6 pb-12">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">

            {/* ============================================ */}
            {/* REACT THREE FIBER COMPONENTS */}
            {/* ============================================ */}

            {shouldShow("r3f", "Liquid Crystal") && (
              <ShowcaseCard
                title="Liquid Crystal"
                engine="@react-three/fiber + drei"
                description="Interactive floating octahedron with distort material, environment mapping, and dynamic lighting. Perfect for hero sections and premium UI accents."
                accentColor="#00d4ff"
                tags={["3D", "Interactive", "Materials"]}
                codeSnippet={`import { FloatingCrystal } from "@/src/components/library";

<FloatingCrystal />

// Uses MeshDistortMaterial for liquid effect
// Includes environment lighting
// Auto-rotates with subtle float animation`}
              >
                <FloatingCrystal />
              </ShowcaseCard>
            )}

            {shouldShow("r3f", "Glass Orb") && (
              <ShowcaseCard
                title="Glass Orb"
                engine="@react-three/fiber + drei"
                description="Transparent glass sphere with transmission material, chromatic aberration, and inner glow core. Creates stunning light refraction effects."
                accentColor="#00d4ff"
                tags={["3D", "Glass", "Refraction"]}
                codeSnippet={`import { GlassOrb } from "@/src/components/library";

<GlassOrb />

// MeshTransmissionMaterial for glass
// Chromatic aberration effect
// Pulsing inner glow core`}
              >
                <GlassOrb />
              </ShowcaseCard>
            )}

            {shouldShow("r3f", "Particle Field") && (
              <ShowcaseCard
                title="Particle Field"
                engine="@react-three/fiber + drei"
                description="500+ animated particles in a spherical formation with color gradients. Creates an ethereal, cosmic atmosphere."
                accentColor="#00d4ff"
                tags={["3D", "Particles", "Animation"]}
                codeSnippet={`import { ParticleField } from "@/src/components/library";

<ParticleField />

// 500+ particles
// Spherical distribution
// Color gradient animation`}
              >
                <ParticleField />
              </ShowcaseCard>
            )}

            {shouldShow("r3f", "3D Text") && (
              <ShowcaseCard
                title="3D Typography"
                engine="@react-three/fiber + drei"
                description="Extruded 3D text with metallic materials and dramatic lighting. Great for hero headlines and brand displays."
                accentColor="#00d4ff"
                tags={["3D", "Typography", "Branding"]}
                codeSnippet={`import { FloatingText3D } from "@/src/components/library";

<FloatingText3D />

// Extruded geometry
// Metallic materials
// Float animation`}
              >
                <FloatingText3D />
              </ShowcaseCard>
            )}

            {shouldShow("r3f", "Wave Grid") && (
              <ShowcaseCard
                title="Wave Grid"
                engine="@react-three/fiber"
                description="Animated plane geometry with real-time vertex displacement creating ocean-like waves. Hypnotic background effect."
                accentColor="#00d4ff"
                tags={["3D", "Generative", "Background"]}
                codeSnippet={`import { WaveGrid } from "@/src/components/library";

<WaveGrid />

// Real-time vertex shader
// Sine wave displacement
// Gradient coloring`}
              >
                <WaveGrid />
              </ShowcaseCard>
            )}

            {shouldShow("r3f", "Neon Tunnel") && (
              <ShowcaseCard
                title="Neon Tunnel"
                engine="@react-three/fiber"
                description="Infinite neon tunnel with rotating torus rings and particle streaks. Creates an immersive warp-speed effect."
                accentColor="#00d4ff"
                tags={["3D", "Animation", "Immersive"]}
                codeSnippet={`import { NeonTunnel } from "@/src/components/library";

<NeonTunnel />

// Infinite scrolling rings
// Particle streak effects
// Fog depth effect`}
              >
                <NeonTunnel />
              </ShowcaseCard>
            )}

            {/* ============================================ */}
            {/* SPLINE COMPONENTS */}
            {/* ============================================ */}

            {shouldShow("spline", "Spline Placeholder") && (
              <ShowcaseCard
                title="3D Hero Scene"
                engine="@splinetool/react-spline"
                description="Placeholder for Spline 3D scenes. Replace the URL with your own .splinecode export for custom 3D experiences."
                accentColor="#a855f7"
                tags={["Spline", "No-Code", "3D"]}
                codeSnippet={`import { SplineScene } from "@/src/components/library";

<SplineScene
  sceneUrl="https://prod.spline.design/xxx/scene.splinecode"
/>

// Export from Spline app
// Supports interactions
// No code required`}
              >
                <SplineScene />
              </ShowcaseCard>
            )}

            {shouldShow("spline", "Spline Robot") && (
              <ShowcaseCard
                title="Spline Robot"
                engine="@splinetool/react-spline"
                description="Interactive 3D robot character. Demonstrates Spline's ability to create complex, animated 3D scenes with real-time interactions."
                accentColor="#a855f7"
                tags={["Spline", "Character", "Interactive"]}
                codeSnippet={`import { SplineRobot } from "@/src/components/library";

<SplineRobot />

// Pre-configured scene URL
// Loading state handling
// Error fallback included`}
              >
                <SplineRobot />
              </ShowcaseCard>
            )}

            {shouldShow("spline", "Abstract Scene") && (
              <ShowcaseCard
                title="Abstract Scene"
                engine="@splinetool/react-spline"
                description="Abstract 3D composition with dynamic elements. Shows how Spline can create artistic, non-representational 3D art."
                accentColor="#a855f7"
                tags={["Spline", "Abstract", "Art"]}
                codeSnippet={`import { SplineAbstract } from "@/src/components/library";

<SplineAbstract />

// Abstract composition
// Dynamic animations
// Ambient effects`}
              >
                <SplineAbstract />
              </ShowcaseCard>
            )}

            {/* ============================================ */}
            {/* RIVE COMPONENTS */}
            {/* ============================================ */}

            {shouldShow("rive", "Animated Button") && (
              <ShowcaseCard
                title="Animated Button"
                engine="@rive-app/react-canvas"
                description="State machine-driven animation with interactive hover and click states. Demonstrates Rive's powerful state machine capabilities."
                accentColor="#f97316"
                tags={["Rive", "Interactive", "State Machine"]}
                codeSnippet={`import { RiveButton } from "@/src/components/library";

<RiveButton
  label="ACTIVATE"
  onClick={() => console.log('clicked')}
/>

// State machine driven
// Hover/click states
// Ripple effects`}
              >
                <RiveButton />
              </ShowcaseCard>
            )}

            {shouldShow("rive", "Rive Loader") && (
              <ShowcaseCard
                title="Rive Loader"
                engine="@rive-app/react-canvas"
                description="Smooth animated loading indicator. Perfect for async operations and page transitions."
                accentColor="#f97316"
                tags={["Rive", "Loading", "Animation"]}
                codeSnippet={`import { RiveLoader } from "@/src/components/library";

<RiveLoader
  size={120}
  label="LOADING"
/>

// Configurable size
// Custom label
// Smooth loop`}
              >
                <RiveLoader />
              </ShowcaseCard>
            )}

            {shouldShow("rive", "Interactive Character") && (
              <ShowcaseCard
                title="Interactive Character"
                engine="@rive-app/react-canvas"
                description="Character with hover and click interactions driven by Rive state machine. Hover to wave, click to jump!"
                accentColor="#f97316"
                tags={["Rive", "Character", "States"]}
                codeSnippet={`import { RiveCharacter } from "@/src/components/library";

<RiveCharacter />

// Hover: wave animation
// Click: jump animation
// State indicators`}
              >
                <RiveCharacter />
              </ShowcaseCard>
            )}

            {/* ============================================ */}
            {/* SCI-FI UI COMPONENTS */}
            {/* ============================================ */}

            {shouldShow("scifi", "Holo Interface") && (
              <ShowcaseCard
                title="Holo Interface"
                engine="Arwes-inspired"
                description="Cyberpunk-style holographic card with scan lines, periodic glitch effects, and animated corner accents. Perfect for sci-fi dashboards."
                accentColor="#00ffff"
                tags={["Sci-Fi", "Cyberpunk", "Effects"]}
                codeSnippet={`import { HoloCard } from "@/src/components/library";

<HoloCard />

// Scan line animation
// Random glitch effects
// SVG corner accents
// Noise overlay`}
              >
                <HoloCard />
              </ShowcaseCard>
            )}

            {/* ============================================ */}
            {/* UI EFFECT COMPONENTS */}
            {/* ============================================ */}

            {shouldShow("ui", "Sparkles Effect") && (
              <ShowcaseCard
                title="Sparkles Effect"
                engine="@tsparticles/react"
                description="Interactive particle sparkles with configurable density, size, and colors. Add magic to any element."
                accentColor="#22c55e"
                tags={["Particles", "Interactive", "Effect"]}
                codeSnippet={`import { SparklesCore } from "@/src/components/ui/sparkles";

<SparklesCore
  background="transparent"
  minSize={0.4}
  maxSize={1}
  particleDensity={100}
  particleColor="#22c55e"
/>

// Click to add particles
// Configurable density
// Any color`}
              >
                <div className="w-full h-full relative bg-slate-950">
                  <SparklesCore
                    background="transparent"
                    minSize={0.6}
                    maxSize={1.4}
                    particleDensity={120}
                    particleColor="#22c55e"
                  />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <span className="text-3xl mb-2 block">✨</span>
                      <span className="text-white/90 font-bold text-lg">Click for more!</span>
                    </div>
                  </div>
                </div>
              </ShowcaseCard>
            )}

          </div>
        </main>

        {/* Import Reference */}
        <section className="max-w-[1800px] mx-auto px-6 pb-12">
          <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6">
            <h2 className="text-white font-semibold text-lg mb-6 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/20 to-purple-500/20 flex items-center justify-center">
                <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
              </div>
              Quick Import Reference
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { title: "R3F + Drei", color: "#00d4ff", imports: ["FloatingCrystal", "GlassOrb", "ParticleField", "FloatingText3D", "WaveGrid", "NeonTunnel"] },
                { title: "Spline", color: "#a855f7", imports: ["SplineScene", "SplineRobot", "SplineAbstract"] },
                { title: "Rive", color: "#f97316", imports: ["RiveButton", "RiveLoader", "RiveCharacter"] },
                { title: "UI Effects", color: "#22c55e", imports: ["HoloCard", "SparklesCore"] },
              ].map((group) => (
                <div key={group.title} className="p-4 bg-slate-800/30 rounded-xl border border-slate-700/30">
                  <h3 className="font-mono text-sm mb-3" style={{ color: group.color }}>{group.title}</h3>
                  <code className="text-slate-400 text-xs block space-y-1">
                    <span className="text-slate-500">import {"{"}</span>
                    {group.imports.map((imp, i) => (
                      <span key={imp} className="block pl-2">
                        <span className="text-cyan-300">{imp}</span>
                        {i < group.imports.length - 1 && <span className="text-slate-500">,</span>}
                      </span>
                    ))}
                    <span className="text-slate-500">{"}"} from <span className="text-green-400">&quot;@/src/components/library&quot;</span></span>
                  </code>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-slate-800/50 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-[1800px] mx-auto px-6 py-4">
            <div className="flex items-center justify-between text-xs text-slate-600 font-mono">
              <span>AGENCY_OS.SHOWROOM.V2</span>
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full" /> R3F
                </span>
                <span className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-purple-500 rounded-full" /> SPLINE
                </span>
                <span className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-orange-500 rounded-full" /> RIVE
                </span>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
