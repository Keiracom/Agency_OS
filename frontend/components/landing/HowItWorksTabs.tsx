/**
 * FILE: frontend/components/landing/HowItWorksTabs.tsx
 * PURPOSE: Interactive tabs showing the 5-step process with auto-rotation
 * PHASE: 21
 */

"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Eye, BarChart3, Rocket, Calendar } from "lucide-react";

interface TabItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}

interface HowItWorksTabsProps {
  autoRotate?: boolean;
  rotateInterval?: number;
  className?: string;
}

const tabs: TabItem[] = [
  {
    id: "discover",
    label: "Discover",
    icon: <Search className="w-5 h-5" />,
    title: "ICP extracted from your website in 5 minutes",
    description:
      "Just enter your website URL. Our AI analyzes your existing clients, case studies, and messaging to understand exactly who you serve best. No forms, no interviews—just instant ICP extraction.",
  },
  {
    id: "find",
    label: "Find",
    icon: <Eye className="w-5 h-5" />,
    title: "AI scouts Australian businesses showing buying signals",
    description:
      "Our AI continuously monitors the Australian market for businesses matching your ICP. We look for hiring patterns, tech stack changes, funding announcements, and other buying signals that indicate they're ready to buy.",
  },
  {
    id: "score",
    label: "Score",
    icon: <BarChart3 className="w-5 h-5" />,
    title: "ALS Score™ ranks by budget, timeline, and fit",
    description:
      "Every lead gets an Agency Lead Score (ALS) from 0-100. We analyze authority level, company fit, timing signals, and risk factors. Focus only on Hot leads (85+) that are ready to close.",
  },
  {
    id: "reach",
    label: "Reach",
    icon: <Rocket className="w-5 h-5" />,
    title: "5-channel outreach: Email, SMS, LinkedIn, Voice, Mail",
    description:
      "True multi-channel engagement—not just email with extras. Each channel works together with intelligent sequencing. LinkedIn warms them up, email provides value, voice AI books the meeting.",
  },
  {
    id: "convert",
    label: "Convert",
    icon: <Calendar className="w-5 h-5" />,
    title: "Meetings booked on your calendar. Automatically.",
    description:
      "When a lead is ready, our AI handles the booking conversation. You wake up to qualified meetings on your calendar. Just show up, close the deal, and grow your agency.",
  },
];

export default function HowItWorksTabs({
  autoRotate = true,
  rotateInterval = 6000,
  className = "",
}: HowItWorksTabsProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const pauseTimeoutRef = useRef<NodeJS.Timeout>();

  // Intersection Observer for visibility
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.3 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, []);

  // Auto-rotate logic
  useEffect(() => {
    if (!autoRotate || isPaused || !isVisible) return;

    const timer = setInterval(() => {
      setActiveTab((prev) => (prev + 1) % tabs.length);
    }, rotateInterval);

    return () => clearInterval(timer);
  }, [autoRotate, rotateInterval, isPaused, isVisible]);

  const handleTabClick = (index: number) => {
    setActiveTab(index);
    setIsPaused(true);

    // Resume auto-rotate after 10 seconds of inactivity
    if (pauseTimeoutRef.current) {
      clearTimeout(pauseTimeoutRef.current);
    }
    pauseTimeoutRef.current = setTimeout(() => {
      setIsPaused(false);
    }, 10000);
  };

  const currentTab = tabs[activeTab];

  return (
    <div
      ref={containerRef}
      className={`w-full max-w-4xl mx-auto ${className}`}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* Tab Bar */}
      <div className="flex justify-center mb-8">
        <div className="inline-flex rounded-lg bg-white/5 backdrop-blur-[20px] border border-white/10 p-1">
          {tabs.map((tab, index) => (
            <button
              key={tab.id}
              onClick={() => handleTabClick(index)}
              className={`relative px-4 py-2.5 text-sm font-medium rounded-md transition-all duration-300 flex items-center gap-2 ${
                activeTab === index
                  ? "text-white"
                  : "text-white/50 hover:text-white/70"
              }`}
            >
              {/* Active indicator */}
              {activeTab === index && (
                <span className="absolute inset-0 rounded-md bg-gradient-to-r from-blue-500 to-purple-600 opacity-20" />
              )}
              <span className="relative">{tab.icon}</span>
              <span className="relative hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Progress indicator */}
      <div className="flex justify-center gap-2 mb-8">
        {tabs.map((_, index) => (
          <div
            key={index}
            className={`h-1 rounded-full transition-all duration-300 ${
              index === activeTab
                ? "w-8 bg-gradient-to-r from-blue-500 to-purple-600"
                : index < activeTab
                ? "w-2 bg-white/30"
                : "w-2 bg-white/10"
            }`}
          />
        ))}
      </div>

      {/* Content */}
      <div className="relative min-h-[200px]">
        <div
          key={currentTab.id}
          className="text-center animate-fadeIn"
        >
          {/* Step Badge */}
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-r from-blue-500 to-purple-600 text-white font-bold text-sm mb-6">
            0{activeTab + 1}
          </div>

          {/* Title */}
          <h3 className="text-2xl md:text-3xl font-bold text-white mb-4">
            {currentTab.title}
          </h3>

          {/* Description */}
          <p className="text-white/60 text-lg max-w-2xl mx-auto leading-relaxed">
            {currentTab.description}
          </p>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.4s ease-out;
        }
      `}</style>
    </div>
  );
}
