"use client";

import { useState } from "react";
import {
  Mail,
  Linkedin,
  MessageSquare,
  Phone,
  Search,
  Calendar,
  Filter,
} from "lucide-react";
import { ReplyChannel, ReplyIntent } from "./ReplyCard";

/**
 * ReplyFilters props
 */
export interface ReplyFiltersProps {
  /** Currently selected channel filter */
  selectedChannel?: ReplyChannel | "all";
  /** Currently selected intent filter */
  selectedIntent?: ReplyIntent | "all";
  /** Search query */
  searchQuery?: string;
  /** Handler for channel filter change */
  onChannelChange?: (channel: ReplyChannel | "all") => void;
  /** Handler for intent filter change */
  onIntentChange?: (intent: ReplyIntent | "all") => void;
  /** Handler for search query change */
  onSearchChange?: (query: string) => void;
  /** Handler for date range change (placeholder) */
  onDateRangeChange?: (start: Date | null, end: Date | null) => void;
}

/**
 * Channel filter button configuration
 */
interface ChannelFilterButton {
  value: ReplyChannel | "all";
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  color?: string;
}

const channelFilters: ChannelFilterButton[] = [
  { value: "all", label: "All" },
  { value: "email", label: "Email", icon: Mail, color: "#3B82F6" },
  { value: "linkedin", label: "LinkedIn", icon: Linkedin, color: "#0077B5" },
  { value: "sms", label: "SMS", icon: MessageSquare, color: "#10B981" },
  { value: "voice", label: "Voice", icon: Phone, color: "#8B5CF6" },
];

/**
 * Intent filter button configuration
 */
interface IntentFilterButton {
  value: ReplyIntent | "all";
  label: string;
  color?: string;
}

const intentFilters: IntentFilterButton[] = [
  { value: "all", label: "All Intents" },
  { value: "positive", label: "Positive", color: "#059669" },
  { value: "negative", label: "Negative", color: "#DC2626" },
  { value: "question", label: "Question", color: "#7C3AED" },
  { value: "neutral", label: "Neutral", color: "#64748B" },
];

/**
 * ReplyFilters - Filter controls for the reply inbox
 *
 * Features:
 * - Channel filter buttons (All, Email, LinkedIn, SMS, Voice)
 * - Intent filter dropdown (All, Positive, Negative, Question, Neutral)
 * - Date range picker placeholder
 * - Search input for filtering by content/lead
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Background: #FFFFFF (card-bg)
 * - Border: #E2E8F0 (card-border)
 * - Active state: #3B82F6 (accent-blue)
 * - Text primary: #1E293B (text-primary)
 * - Text secondary: #64748B (text-secondary)
 */
export function ReplyFilters({
  selectedChannel = "all",
  selectedIntent = "all",
  searchQuery = "",
  onChannelChange,
  onIntentChange,
  onSearchChange,
  onDateRangeChange,
}: ReplyFiltersProps) {
  const [isIntentOpen, setIsIntentOpen] = useState(false);

  const handleChannelClick = (channel: ReplyChannel | "all") => {
    if (onChannelChange) {
      onChannelChange(channel);
    }
  };

  const handleIntentClick = (intent: ReplyIntent | "all") => {
    if (onIntentChange) {
      onIntentChange(intent);
    }
    setIsIntentOpen(false);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onSearchChange) {
      onSearchChange(e.target.value);
    }
  };

  const selectedIntentLabel =
    intentFilters.find((f) => f.value === selectedIntent)?.label || "All Intents";

  return (
    <div className="bg-white border-b border-[#E2E8F0] px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        {/* Left: Channel filters */}
        <div className="flex items-center gap-2">
          {channelFilters.map((filter) => {
            const isActive = selectedChannel === filter.value;
            const Icon = filter.icon;

            return (
              <button
                key={filter.value}
                onClick={() => handleChannelClick(filter.value)}
                className={`
                  flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                  ${
                    isActive
                      ? "bg-[#3B82F6] text-white shadow-sm"
                      : "bg-[#F1F5F9] text-[#64748B] hover:bg-[#E2E8F0]"
                  }
                `}
              >
                {Icon && (
                  <span style={{ color: isActive ? "white" : filter.color }}>
                    <Icon className="h-4 w-4" />
                  </span>
                )}
                <span>{filter.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right: Intent filter, date range, search */}
        <div className="flex items-center gap-3">
          {/* Intent Filter Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsIntentOpen(!isIntentOpen)}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:border-[#94A3B8] transition-colors"
            >
              <Filter className="h-4 w-4" />
              <span>{selectedIntentLabel}</span>
              <svg
                className={`h-4 w-4 transition-transform ${isIntentOpen ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {isIntentOpen && (
              <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-[#E2E8F0] rounded-lg shadow-lg z-10">
                {intentFilters.map((filter) => {
                  const isActive = selectedIntent === filter.value;

                  return (
                    <button
                      key={filter.value}
                      onClick={() => handleIntentClick(filter.value)}
                      className={`
                        w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition-colors
                        ${isActive ? "bg-[#EFF6FF] text-[#3B82F6]" : "text-[#64748B] hover:bg-[#F8FAFC]"}
                        first:rounded-t-lg last:rounded-b-lg
                      `}
                    >
                      {filter.color && (
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: filter.color }}
                        />
                      )}
                      <span>{filter.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Date Range Picker (placeholder) */}
          <button className="flex items-center gap-2 px-3 py-1.5 bg-white border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:border-[#94A3B8] transition-colors">
            <Calendar className="h-4 w-4" />
            <span>Date Range</span>
          </button>

          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#94A3B8]" />
            <input
              type="text"
              placeholder="Search replies..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="w-64 pl-9 pr-4 py-1.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent transition-colors"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default ReplyFilters;
