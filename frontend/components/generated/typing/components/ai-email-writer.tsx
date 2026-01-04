"use client"

import { useEffect, useState } from "react"
import { Sparkles } from "lucide-react"

interface AIEmailWriterProps {
  className?: string
}

const EMAIL_CONTENT = `Hi Sarah,

I noticed Bloom Digital has been expanding into healthcare marketing — congrats on the recent wins with Medicare providers.

We've helped similar agencies book 40+ qualified meetings per month using our multi-channel approach. Given your focus on regulated industries, I think our compliance-first platform could be a great fit.

Would you be open to a quick 15-min call next week to explore?

Best,
Alex`

export default function AIEmailWriter({ className = "" }: AIEmailWriterProps) {
  const [displayedText, setDisplayedText] = useState("")
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const [showCursor, setShowCursor] = useState(true)

  // Cursor blink effect
  useEffect(() => {
    const cursorInterval = setInterval(() => {
      setShowCursor((prev) => !prev)
    }, 530)

    return () => clearInterval(cursorInterval)
  }, [])

  // Typewriter effect
  useEffect(() => {
    if (currentIndex < EMAIL_CONTENT.length) {
      const currentChar = EMAIL_CONTENT[currentIndex]
      let delay = 25 // Default typing speed

      // Variable speed based on punctuation
      if (currentChar === ".") {
        delay = 150
      } else if (currentChar === ",") {
        delay = 100
      } else if (currentChar === "\n") {
        delay = 200
      }

      const timeout = setTimeout(() => {
        setDisplayedText(EMAIL_CONTENT.slice(0, currentIndex + 1))
        setCurrentIndex(currentIndex + 1)
      }, delay)

      return () => clearTimeout(timeout)
    } else if (!isComplete) {
      setIsComplete(true)

      // Restart after 5 seconds
      setTimeout(() => {
        setDisplayedText("")
        setCurrentIndex(0)
        setIsComplete(false)
      }, 5000)
    }
  }, [currentIndex, isComplete])

  return (
    <div className={`w-full max-w-2xl ${className}`}>
      {/* Glass morphism card */}
      <div className="bg-white/5 backdrop-blur-[20px] border border-white/10 rounded-lg overflow-hidden">
        {/* Status indicator */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10">
          <div className="relative">
            <Sparkles className="w-4 h-4 text-purple-400" />
            {!isComplete && (
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
            )}
          </div>
          <span className="text-sm text-white/70">{isComplete ? "AI finished" : "AI is writing..."}</span>
        </div>

        {/* Email compose UI */}
        <div className="p-4 space-y-3">
          {/* To field */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-white/50 min-w-[60px]">To:</span>
            <span className="text-white">sarah@bloomdigital.com.au</span>
          </div>

          {/* Subject field */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-white/50 min-w-[60px]">Subject:</span>
            <span className="text-white">Quick question about your healthcare marketing expansion</span>
          </div>

          {/* Divider */}
          <div className="border-t border-white/10" />

          {/* Email body with typewriter effect */}
          <div className="min-h-[300px] text-sm text-white/90 leading-relaxed font-mono whitespace-pre-wrap">
            {displayedText}
            <span
              className={`inline-block w-[2px] h-4 bg-gradient-to-b from-blue-500 to-purple-600 ml-0.5 ${
                showCursor ? "opacity-100" : "opacity-0"
              } transition-opacity`}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
