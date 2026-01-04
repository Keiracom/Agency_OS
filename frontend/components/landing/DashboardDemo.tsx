/**
 * FILE: frontend/components/landing/DashboardDemo.tsx
 * PURPOSE: Animated dashboard demo matching landing-page-v2.html
 * FEATURES: Counting stats, live activity feed, AI typing, ALS distribution
 */

"use client";

import { useState, useEffect, useRef } from "react";
import { Mail, Linkedin, MessageSquare, Phone, Calendar, Lock, Sparkles } from "lucide-react";

// Animated counter hook
function useAnimatedCounter(target: number, duration: number = 2000, startOnView: boolean = true) {
  const [count, setCount] = useState(0);
  const [hasStarted, setHasStarted] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!startOnView) {
      setHasStarted(true);
    }
  }, [startOnView]);

  useEffect(() => {
    if (startOnView && ref.current) {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting && !hasStarted) {
            setHasStarted(true);
          }
        },
        { threshold: 0.5 }
      );
      observer.observe(ref.current);
      return () => observer.disconnect();
    }
  }, [hasStarted, startOnView]);

  useEffect(() => {
    if (!hasStarted) return;

    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(target * easeOut));

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [hasStarted, target, duration]);

  return { count, ref };
}

// Activity feed data
const activities = [
  { name: "Sarah Chen", company: "Bloom Digital", action: "Opened email", channel: "email" as const, color: "blue" },
  { name: "Michael Jones", company: "Growth Labs", action: "Clicked link", channel: "email" as const, color: "blue" },
  { name: "Lisa Wong", company: "Pixel Perfect", action: "Accepted connection", channel: "linkedin" as const, color: "sky" },
  { name: "David Park", company: "Momentum Media", action: "Replied to SMS", channel: "sms" as const, color: "green" },
  { name: "Emma Wilson", company: "Digital First", action: "Answered call", channel: "phone" as const, color: "purple" },
  { name: "James Liu", company: "Scale Agency", action: "Booked meeting", channel: "calendar" as const, color: "emerald" },
  { name: "Anna Smith", company: "Brand Forward", action: "Opened email", channel: "email" as const, color: "blue" },
  { name: "Tom Brown", company: "Creative Co", action: "Viewed profile", channel: "linkedin" as const, color: "sky" },
];

const channelIcons = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageSquare,
  phone: Phone,
  calendar: Calendar,
};

const channelColors = {
  email: "text-blue-400 bg-blue-500/20",
  linkedin: "text-sky-400 bg-sky-500/20",
  sms: "text-green-400 bg-green-500/20",
  phone: "text-purple-400 bg-purple-500/20",
  calendar: "text-emerald-400 bg-emerald-500/20",
};

// Email content for typing animation
const emailText = `Hi Sarah,

I noticed Bloom Digital has been expanding into healthcare marketing — congrats on the recent wins with Medicare providers.

We've helped similar agencies book 40+ qualified meetings per month using our multi-channel approach. Given your focus on regulated industries, I think our compliance-first platform could be a great fit.

Would you be open to a quick 15-min call next week to explore?`;

interface DashboardDemoProps {
  className?: string;
}

export default function DashboardDemo({ className = "" }: DashboardDemoProps) {
  const [visibleActivities, setVisibleActivities] = useState<typeof activities>([]);
  const [activityIndex, setActivityIndex] = useState(0);
  const [typedText, setTypedText] = useState("");
  const [isTyping, setIsTyping] = useState(true);
  const [charIndex, setCharIndex] = useState(0);

  // Animated counters
  const pipeline = useAnimatedCounter(284);
  const meetings = useAnimatedCounter(47);
  const replyRate = useAnimatedCounter(12);
  const leads = useAnimatedCounter(2847);

  // Initialize activity feed
  useEffect(() => {
    const initial = activities.slice(0, 5);
    setVisibleActivities(initial);
    setActivityIndex(5);
  }, []);

  // Rotate activity feed
  useEffect(() => {
    const interval = setInterval(() => {
      setActivityIndex((prev) => {
        const nextIdx = prev % activities.length;
        const newActivity = activities[nextIdx];

        setVisibleActivities((current) => {
          const updated = [newActivity, ...current.slice(0, 4)];
          return updated;
        });

        return prev + 1;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  // Typing animation
  useEffect(() => {
    if (charIndex < emailText.length) {
      const char = emailText[charIndex];
      let delay = Math.random() * 30 + 20;

      if (char === "\n") delay = 200;
      else if (char === ".") delay = 150;
      else if (char === ",") delay = 100;

      const timer = setTimeout(() => {
        setTypedText(emailText.slice(0, charIndex + 1));
        setCharIndex((prev) => prev + 1);
      }, delay);

      return () => clearTimeout(timer);
    } else {
      setIsTyping(false);
      // Restart after 5 seconds
      const restartTimer = setTimeout(() => {
        setTypedText("");
        setCharIndex(0);
        setIsTyping(true);
      }, 5000);
      return () => clearTimeout(restartTimer);
    }
  }, [charIndex]);

  return (
    <div className={`rounded-2xl overflow-hidden border border-white/10 bg-[#12121a] shadow-2xl ${className}`}>
      {/* Browser Chrome */}
      <div className="flex items-center gap-2 px-4 py-3 bg-[#1a1a24] border-b border-white/10">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
          <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
          <div className="w-3 h-3 rounded-full bg-[#28c840]" />
        </div>
        <div className="flex-1 flex justify-center">
          <div className="px-4 py-1.5 rounded-lg bg-[#0a0a0f] text-white/40 text-xs flex items-center gap-2">
            <Lock className="w-3 h-3 text-green-500" />
            app.agencyos.com.au
          </div>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="p-6 md:p-8 bg-gradient-to-br from-[#12121a] to-[#0a0a0f]">
        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/40 text-xs uppercase tracking-wider">Pipeline</span>
              <span className="text-xs text-emerald-400 flex items-center gap-1">↑ 12%</span>
            </div>
            <p className="text-2xl md:text-3xl font-bold">
              $<span ref={pipeline.ref}>{pipeline.count.toLocaleString()}</span>K
            </p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/40 text-xs uppercase tracking-wider">Meetings</span>
              <span className="text-xs text-emerald-400">↑ 8 this week</span>
            </div>
            <p className="text-2xl md:text-3xl font-bold">
              <span ref={meetings.ref}>{meetings.count}</span>
            </p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/40 text-xs uppercase tracking-wider">Reply Rate</span>
              <span className="text-xs text-emerald-400">↑ 2.1%</span>
            </div>
            <p className="text-2xl md:text-3xl font-bold">
              <span ref={replyRate.ref}>{replyRate.count}</span>%
            </p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/40 text-xs uppercase tracking-wider">Leads</span>
              <span className="text-xs text-blue-400">Active</span>
            </div>
            <p className="text-2xl md:text-3xl font-bold">
              <span ref={leads.ref}>{leads.count.toLocaleString()}</span>
            </p>
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Live Activity Feed */}
          <div className="rounded-xl bg-white/5 border border-white/10 overflow-hidden">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                Live Activity
              </h3>
              <span className="text-xs text-white/40">Auto-updating</span>
            </div>
            <div className="divide-y divide-white/5 h-[220px] overflow-hidden">
              {visibleActivities.map((activity, idx) => {
                const Icon = channelIcons[activity.channel];
                const colorClass = channelColors[activity.channel];
                return (
                  <div
                    key={`${activity.name}-${idx}`}
                    className="px-4 py-3 flex items-center gap-3 transition-all duration-300"
                    style={{
                      animation: idx === 0 ? "slideIn 0.4s ease-out" : undefined,
                    }}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${colorClass}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{activity.name}</p>
                      <p className="text-xs text-white/50">{activity.action}</p>
                    </div>
                    <span className="text-xs text-white/30">{Math.floor(Math.random() * 5) + 1}s ago</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* AI Email Composer */}
          <div className="rounded-xl bg-white/5 border border-white/10 overflow-hidden">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <h3 className="font-semibold text-sm flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                AI Writing Email
              </h3>
              <span className={`text-xs px-2 py-1 rounded-full ${isTyping ? "bg-purple-500/20 text-purple-300" : "bg-emerald-500/20 text-emerald-300"}`}>
                {isTyping ? "Generating" : "Complete"}
              </span>
            </div>
            <div className="p-4">
              <div className="mb-3 space-y-1.5">
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-white/40">To:</span>
                  <span className="text-white">Sarah Chen, Marketing Director</span>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-white/40">Company:</span>
                  <span className="text-white">Bloom Digital</span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-[#0a0a0f] border border-white/10 min-h-[140px] max-h-[140px] overflow-hidden">
                <p className="text-xs text-white/80 leading-relaxed whitespace-pre-wrap font-mono">
                  {typedText}
                  {isTyping && <span className="inline-block w-0.5 h-3 bg-purple-400 ml-0.5 animate-pulse" />}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* ALS Score Distribution */}
        <div className="mt-6 rounded-xl bg-white/5 border border-white/10 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-sm">Lead Quality Distribution</h3>
            <span className="text-xs text-white/40">Agency Lead Score (ALS)</span>
          </div>
          <div className="grid grid-cols-5 gap-3">
            {[
              { label: "Hot", value: 24, color: "bg-red-500", textColor: "text-red-400" },
              { label: "Warm", value: 31, color: "bg-orange-500", textColor: "text-orange-400" },
              { label: "Cool", value: 28, color: "bg-blue-500", textColor: "text-blue-400" },
              { label: "Cold", value: 12, color: "bg-gray-500", textColor: "text-gray-400" },
              { label: "Dead", value: 5, color: "bg-gray-700", textColor: "text-gray-600" },
            ].map((tier, idx) => (
              <div key={tier.label}>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className={`font-medium ${tier.textColor}`}>{tier.label}</span>
                  <span className="text-white/60">{tier.value}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className={`h-full ${tier.color} rounded-full transition-all duration-1000`}
                    style={{
                      width: `${tier.value}%`,
                      animation: `progressBar 1.5s ease-out forwards`,
                      animationDelay: `${idx * 0.2}s`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        @keyframes progressBar {
          from {
            width: 0;
          }
        }
      `}</style>
    </div>
  );
}
