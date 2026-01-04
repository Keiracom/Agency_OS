/**
 * FILE: frontend/components/landing/TypingDemo.tsx
 * PURPOSE: AI email typing animation showing personalization capability
 * PHASE: 21
 */

"use client";

import { useState, useEffect, useRef } from "react";
import { Sparkles } from "lucide-react";

interface TypingDemoProps {
  to?: string;
  subject?: string;
  body?: string;
  typingSpeed?: number;
  restartDelay?: number;
  className?: string;
}

const defaultEmail = {
  to: "sarah@bloomdigital.com.au",
  subject: "Quick question about your healthcare marketing expansion",
  body: `Hi Sarah,

I noticed Bloom Digital has been expanding into healthcare marketing — congrats on the recent wins with Medicare providers.

We've helped similar agencies book 40+ qualified meetings per month using our multi-channel approach. Given your focus on regulated industries, I think our compliance-first platform could be a great fit.

Would you be open to a quick 15-min call next week to explore?

Best,
Alex`,
};

export default function TypingDemo({
  to = defaultEmail.to,
  subject = defaultEmail.subject,
  body = defaultEmail.body,
  typingSpeed = 25,
  restartDelay = 5000,
  className = "",
}: TypingDemoProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(true);
  const [charIndex, setCharIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (charIndex < body.length) {
      const char = body[charIndex];

      // Variable delay based on punctuation
      let delay = typingSpeed;
      if (char === "." || char === "!" || char === "?") {
        delay = 150;
      } else if (char === ",") {
        delay = 100;
      } else if (char === "\n") {
        delay = 200;
      }

      const timer = setTimeout(() => {
        setDisplayedText((prev) => prev + char);
        setCharIndex((prev) => prev + 1);

        // Auto-scroll to keep cursor in view
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      }, delay);

      return () => clearTimeout(timer);
    } else {
      // Finished typing
      setIsTyping(false);

      // Restart after delay
      const restartTimer = setTimeout(() => {
        setDisplayedText("");
        setCharIndex(0);
        setIsTyping(true);
      }, restartDelay);

      return () => clearTimeout(restartTimer);
    }
  }, [charIndex, body, typingSpeed, restartDelay]);

  return (
    <div className={`rounded-lg bg-white/5 backdrop-blur-[20px] border border-white/10 overflow-hidden ${className}`}>
      {/* Email Header */}
      <div className="border-b border-white/10">
        {/* AI Writing Indicator */}
        <div className="px-4 py-2 border-b border-white/5 flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className={`absolute inline-flex h-full w-full rounded-full bg-purple-400 ${isTyping ? "animate-ping" : ""} opacity-75`}></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
          </span>
          <span className="text-xs text-purple-400 flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            {isTyping ? "AI is writing..." : "AI finished"}
          </span>
        </div>

        {/* To Field */}
        <div className="px-4 py-2 flex items-center gap-2 border-b border-white/5">
          <span className="text-xs text-white/40 w-12">To:</span>
          <span className="text-sm text-white/80">{to}</span>
        </div>

        {/* Subject Field */}
        <div className="px-4 py-2 flex items-center gap-2">
          <span className="text-xs text-white/40 w-12">Subject:</span>
          <span className="text-sm text-white">{subject}</span>
        </div>
      </div>

      {/* Email Body */}
      <div
        ref={containerRef}
        className="p-4 min-h-[240px] max-h-[300px] overflow-y-auto"
      >
        <pre className="text-sm text-white/80 whitespace-pre-wrap font-sans leading-relaxed">
          {displayedText}
          {isTyping && (
            <span className="inline-block w-0.5 h-4 bg-white/80 ml-0.5 animate-blink" />
          )}
        </pre>
      </div>

      <style jsx>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
        .animate-blink {
          animation: blink 1s step-end infinite;
        }
      `}</style>
    </div>
  );
}
