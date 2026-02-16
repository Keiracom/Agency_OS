/**
 * MayaCompanion.tsx - Maya AI Companion Component
 * Bloomberg Terminal Dark Mode Design
 * 
 * Features:
 * - Floating avatar button (bottom-right corner)
 * - Expandable chat panel with glassmorphic design
 * - Tour guide functionality with step-by-step hints
 * - Contextual suggestions based on current page
 * - "Ask Maya" input for questions
 * - Smooth animations (slide up, fade in)
 */

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  X,
  Send,
  Sparkles,
  ChevronRight,
  HelpCircle,
  Lightbulb,
  ArrowRight,
  MessageCircle,
  BookOpen,
} from "lucide-react";

// ============================================
// Types
// ============================================

export interface MayaStep {
  content: string;
  action: string;
  highlight?: string;
}

export interface MayaMessage {
  id: string;
  role: "maya" | "user";
  content: string;
  timestamp: Date;
}

export interface ContextualSuggestion {
  icon: React.ReactNode;
  label: string;
  action: string;
  path?: string;
}

export interface PageContext {
  title: string;
  description: string;
  suggestions: ContextualSuggestion[];
}

export interface MayaCompanionProps {
  /** Custom tour steps (optional) */
  steps?: MayaStep[];
  /** Initial open state */
  defaultOpen?: boolean;
  /** Show pulsing animation */
  showPulse?: boolean;
  /** Mode: "tour" | "chat" | "auto" */
  mode?: "tour" | "chat" | "auto";
  /** Callback when tour step changes */
  onStepChange?: (step: number) => void;
  /** Callback when tour completes */
  onComplete?: () => void;
  /** Callback when user asks a question */
  onAsk?: (question: string) => Promise<string>;
  /** Additional className */
  className?: string;
}

// ============================================
// Default Tour Steps
// ============================================

const defaultSteps: MayaStep[] = [
  {
    content:
      "Welcome to Agency OS! 👋 I'm Maya, your digital employee. I'm currently analyzing your website to understand your agency and find your ideal clients. This usually takes 2-3 minutes.",
    action: "Got it",
  },
  {
    content:
      "While I analyze your website, I'm also setting up your email domains and phone numbers. These are pre-warmed and ready to use! 🚀",
    action: "Continue",
  },
  {
    content:
      "Once the analysis is complete, I'll suggest campaigns based on your ideal client profile. You'll see them on the Campaigns page.",
    action: "Show me",
    highlight: "campaigns-nav",
  },
  {
    content:
      "That's the basics! I'll be here in the corner whenever you need help. Click my avatar anytime to chat. 💬",
    action: "Finish tour",
  },
];

// ============================================
// Contextual Page Suggestions
// ============================================

const pageContexts: Record<string, PageContext> = {
  "/dashboard": {
    title: "Command Center",
    description: "Your agency's mission control",
    suggestions: [
      {
        icon: <Sparkles className="w-4 h-4" />,
        label: "Create your first campaign",
        action: "Let me help you set up a high-converting campaign",
        path: "/campaigns",
      },
      {
        icon: <Lightbulb className="w-4 h-4" />,
        label: "Understand your metrics",
        action: "I'll explain what each stat means",
      },
      {
        icon: <HelpCircle className="w-4 h-4" />,
        label: "What can Maya do?",
        action: "Discover all the ways I can help you",
      },
    ],
  },
  "/leads": {
    title: "Lead Management",
    description: "Your prospect pipeline",
    suggestions: [
      {
        icon: <Sparkles className="w-4 h-4" />,
        label: "Enrich lead data",
        action: "I can help you enrich leads with Apollo and Prospeo",
      },
      {
        icon: <Lightbulb className="w-4 h-4" />,
        label: "Score leads automatically",
        action: "Let me set up AI lead scoring for you",
      },
      {
        icon: <BookOpen className="w-4 h-4" />,
        label: "Import leads",
        action: "Guide me through importing a CSV",
      },
    ],
  },
  "/campaigns": {
    title: "Campaigns",
    description: "Your outreach sequences",
    suggestions: [
      {
        icon: <Sparkles className="w-4 h-4" />,
        label: "Create campaign from ICP",
        action: "I'll generate a campaign based on your ideal client profile",
      },
      {
        icon: <Lightbulb className="w-4 h-4" />,
        label: "Optimize send times",
        action: "Let me analyze the best times to reach your prospects",
      },
      {
        icon: <MessageCircle className="w-4 h-4" />,
        label: "A/B test copy",
        action: "Set up split testing for your sequences",
      },
    ],
  },
  "/replies": {
    title: "Inbox",
    description: "Manage conversations",
    suggestions: [
      {
        icon: <Sparkles className="w-4 h-4" />,
        label: "Suggest replies",
        action: "I'll draft personalized responses for you",
      },
      {
        icon: <Lightbulb className="w-4 h-4" />,
        label: "Detect intent",
        action: "I'll classify replies by buyer intent",
      },
      {
        icon: <HelpCircle className="w-4 h-4" />,
        label: "Escalation rules",
        action: "Set up alerts for hot leads",
      },
    ],
  },
};

const defaultContext: PageContext = {
  title: "Agency OS",
  description: "Your AI-powered growth engine",
  suggestions: [
    {
      icon: <HelpCircle className="w-4 h-4" />,
      label: "What can Maya do?",
      action: "Discover all the ways I can help you",
    },
    {
      icon: <Sparkles className="w-4 h-4" />,
      label: "Quick tour",
      action: "Take me through the platform",
    },
    {
      icon: <Lightbulb className="w-4 h-4" />,
      label: "Tips & tricks",
      action: "Share some power-user tips",
    },
  ],
};

// ============================================
// Component
// ============================================

export function MayaCompanion({
  steps = defaultSteps,
  defaultOpen = false,
  showPulse = true,
  mode = "auto",
  onStepChange,
  onComplete,
  onAsk,
  className,
}: MayaCompanionProps) {
  const pathname = usePathname();
  const inputRef = useRef<HTMLInputElement>(null);
  
  // State
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [isPulsing, setIsPulsing] = useState(showPulse);
  const [currentView, setCurrentView] = useState<"tour" | "chat">(
    mode === "tour" ? "tour" : mode === "chat" ? "chat" : "tour"
  );
  const [currentStep, setCurrentStep] = useState(0);
  const [tourCompleted, setTourCompleted] = useState(false);
  const [messages, setMessages] = useState<MayaMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  // Get page context
  const pageContext = pageContexts[pathname] || defaultContext;

  // Handle tour navigation
  const handleNextStep = useCallback(() => {
    const nextStep = currentStep + 1;

    if (nextStep >= steps.length) {
      setTourCompleted(true);
      setCurrentView("chat");
      setIsPulsing(false);
      onComplete?.();
      
      // Add completion message
      setMessages((prev) => [
        ...prev,
        {
          id: `maya-${Date.now()}`,
          role: "maya",
          content: "Tour complete! 🎉 I'm always here to help. Ask me anything or check out the suggestions below.",
          timestamp: new Date(),
        },
      ]);
      return;
    }

    setCurrentStep(nextStep);
    onStepChange?.(nextStep);
  }, [currentStep, steps.length, onComplete, onStepChange]);

  const handleDismissTour = useCallback(() => {
    setTourCompleted(true);
    setCurrentView("chat");
    setIsPulsing(false);
  }, []);

  // Handle chat
  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim()) return;

    const userMessage: MayaMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsTyping(true);

    // Get response
    let responseContent: string;
    if (onAsk) {
      try {
        responseContent = await onAsk(userMessage.content);
      } catch {
        responseContent = "Sorry, I couldn't process that request. Please try again.";
      }
    } else {
      // Default response
      responseContent = `I understand you're asking about "${userMessage.content}". In a fully connected system, I'd help you with that! For now, check out the suggestions below or explore the dashboard.`;
    }

    setIsTyping(false);
    setMessages((prev) => [
      ...prev,
      {
        id: `maya-${Date.now()}`,
        role: "maya",
        content: responseContent,
        timestamp: new Date(),
      },
    ]);
  }, [inputValue, onAsk]);

  const handleSuggestionClick = useCallback((suggestion: ContextualSuggestion) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: "user",
        content: suggestion.label,
        timestamp: new Date(),
      },
      {
        id: `maya-${Date.now()}`,
        role: "maya",
        content: suggestion.action,
        timestamp: new Date(),
      },
    ]);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Auto-focus input when opened
  useEffect(() => {
    if (isOpen && currentView === "chat" && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen, currentView]);

  // Current tour step
  const currentTourStep = steps[currentStep];

  return (
    <div className={cn("fixed bottom-6 right-6 z-50", className)}>
      {/* Panel */}
      {isOpen && (
        <div
          className={cn(
            "absolute bottom-full right-0 mb-4 w-[360px] rounded-2xl overflow-hidden",
            "bg-bg-void/60 backdrop-blur-xl border border-slate-700/50",
            "shadow-2xl shadow-black/40",
            "animate-in slide-in-from-bottom-4 fade-in duration-300"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/50 bg-bg-base/30">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber to-amber flex items-center justify-center text-text-primary font-bold shadow-lg shadow-amber/30">
                M
              </div>
              <div>
                <p className="font-semibold text-text-primary text-sm">Maya</p>
                <p className="text-xs text-text-secondary">Your Digital Employee</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 rounded-lg hover:bg-slate-700/50 text-text-secondary hover:text-text-primary transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Tour View */}
          {currentView === "tour" && !tourCompleted && currentTourStep && (
            <div className="p-5">
              {/* Tour Content */}
              <p className="text-sm text-text-secondary leading-relaxed mb-4">
                {currentTourStep.content}
              </p>

              {/* Progress dots */}
              <div className="flex items-center gap-1.5 mb-4">
                {steps.map((_, i) => (
                  <div
                    key={i}
                    className={cn(
                      "h-1.5 rounded-full transition-all duration-300",
                      i === currentStep
                        ? "bg-amber w-6"
                        : i < currentStep
                        ? "bg-amber/50 w-1.5"
                        : "bg-bg-elevated w-1.5"
                    )}
                  />
                ))}
              </div>

              {/* Tour Actions */}
              <div className="flex gap-2">
                <button
                  onClick={handleNextStep}
                  className="flex-1 px-4 py-2.5 bg-amber hover:bg-amber text-text-primary text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  {currentTourStep.action}
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  onClick={handleDismissTour}
                  className="px-4 py-2.5 bg-slate-700/50 hover:bg-slate-700 text-text-secondary text-sm font-medium rounded-lg border border-slate-600/50 transition-colors"
                >
                  Skip
                </button>
              </div>
            </div>
          )}

          {/* Chat View */}
          {(currentView === "chat" || tourCompleted) && (
            <>
              {/* Messages Area */}
              <div className="h-[280px] overflow-y-auto p-4 space-y-3">
                {messages.length === 0 && (
                  <div className="text-center py-6">
                    <Sparkles className="w-8 h-8 text-amber mx-auto mb-3" />
                    <p className="text-text-secondary text-sm">
                      Hi! I'm Maya. How can I help you today?
                    </p>
                  </div>
                )}

                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      "flex",
                      message.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    <div
                      className={cn(
                        "max-w-[85%] px-4 py-2.5 rounded-2xl text-sm",
                        message.role === "user"
                          ? "bg-amber text-text-primary rounded-br-md"
                          : "bg-slate-700/60 text-text-secondary rounded-bl-md"
                      )}
                    >
                      {message.content}
                    </div>
                  </div>
                ))}

                {isTyping && (
                  <div className="flex justify-start">
                    <div className="bg-slate-700/60 px-4 py-3 rounded-2xl rounded-bl-md">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Contextual Suggestions */}
              <div className="px-4 pb-3">
                <p className="text-xs text-text-muted mb-2 flex items-center gap-1.5">
                  <Lightbulb className="w-3 h-3" />
                  Suggestions for {pageContext.title}
                </p>
                <div className="flex flex-wrap gap-2">
                  {pageContext.suggestions.slice(0, 3).map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-bg-base/60 hover:bg-slate-700/60 border border-slate-600/30 rounded-full text-xs text-text-secondary hover:text-text-primary transition-colors"
                    >
                      {suggestion.icon}
                      {suggestion.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Input Area */}
              <div className="p-4 pt-0">
                <div className="relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask Maya anything..."
                    className="w-full px-4 py-3 pr-12 bg-bg-base/60 border border-slate-600/50 rounded-xl text-sm text-text-primary placeholder-slate-500 focus:outline-none focus:border-amber/50 focus:ring-1 focus:ring-amber/20 transition-colors"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputValue.trim()}
                    className={cn(
                      "absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg transition-colors",
                      inputValue.trim()
                        ? "bg-amber hover:bg-amber text-text-primary"
                        : "bg-slate-700/50 text-text-muted cursor-not-allowed"
                    )}
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Floating Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "w-14 h-14 rounded-full",
          "bg-gradient-to-br from-amber to-amber",
          "border-[3px] border-slate-900",
          "shadow-lg shadow-amber/40",
          "flex items-center justify-center",
          "text-text-primary text-xl font-bold",
          "transition-all duration-200",
          "hover:scale-110 hover:shadow-amber/50",
          isOpen && "scale-95"
        )}
        style={{
          animation: isPulsing && !isOpen ? "maya-pulse 2s infinite" : undefined,
        }}
      >
        {isOpen ? (
          <MessageCircle className="w-6 h-6" />
        ) : (
          "M"
        )}
      </button>

      {/* Notification Badge */}
      {!isOpen && !tourCompleted && (
        <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber rounded-full flex items-center justify-center text-[10px] text-text-primary font-bold animate-bounce">
          !
        </span>
      )}

      {/* Pulse Animation */}
      <style jsx>{`
        @keyframes maya-pulse {
          0%, 100% {
            box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4);
          }
          50% {
            box-shadow: 0 8px 32px rgba(139, 92, 246, 0.6), 0 0 0 12px rgba(139, 92, 246, 0.1);
          }
        }
      `}</style>
    </div>
  );
}

export default MayaCompanion;
