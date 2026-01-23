"use client";

import { useState, useMemo } from "react";
import { ChevronDown, Clock, Search } from "lucide-react";

/**
 * Timezone option
 */
interface TimezoneOption {
  value: string;
  label: string;
  offset: string;
  region: string;
}

/**
 * TimezoneSelector props
 */
export interface TimezoneSelectorProps {
  /** Currently selected timezone */
  value: string;
  /** Change handler */
  onChange: (timezone: string) => void;
}

/**
 * Australian and common timezones with their UTC offsets
 * Australian timezones are prioritized at the top
 */
const TIMEZONES: TimezoneOption[] = [
  // Australian timezones (prioritized)
  { value: "Australia/Sydney", label: "Sydney", offset: "+11:00", region: "Australia" },
  { value: "Australia/Melbourne", label: "Melbourne", offset: "+11:00", region: "Australia" },
  { value: "Australia/Brisbane", label: "Brisbane", offset: "+10:00", region: "Australia" },
  { value: "Australia/Perth", label: "Perth", offset: "+08:00", region: "Australia" },
  { value: "Australia/Adelaide", label: "Adelaide", offset: "+10:30", region: "Australia" },
  { value: "Australia/Darwin", label: "Darwin", offset: "+09:30", region: "Australia" },
  { value: "Australia/Hobart", label: "Hobart", offset: "+11:00", region: "Australia" },
  // New Zealand
  { value: "Pacific/Auckland", label: "Auckland", offset: "+13:00", region: "Pacific" },
  // Asia
  { value: "Asia/Singapore", label: "Singapore", offset: "+08:00", region: "Asia" },
  { value: "Asia/Hong_Kong", label: "Hong Kong", offset: "+08:00", region: "Asia" },
  { value: "Asia/Tokyo", label: "Tokyo", offset: "+09:00", region: "Asia" },
  { value: "Asia/Shanghai", label: "Shanghai", offset: "+08:00", region: "Asia" },
  { value: "Asia/Dubai", label: "Dubai", offset: "+04:00", region: "Asia" },
  // Europe
  { value: "Europe/London", label: "London", offset: "+00:00", region: "Europe" },
  { value: "Europe/Paris", label: "Paris", offset: "+01:00", region: "Europe" },
  { value: "Europe/Berlin", label: "Berlin", offset: "+01:00", region: "Europe" },
  // Americas
  { value: "America/New_York", label: "New York", offset: "-05:00", region: "Americas" },
  { value: "America/Los_Angeles", label: "Los Angeles", offset: "-08:00", region: "Americas" },
  { value: "America/Chicago", label: "Chicago", offset: "-06:00", region: "Americas" },
  // UTC
  { value: "UTC", label: "UTC", offset: "+00:00", region: "Other" },
];

/**
 * Get current time in a timezone
 */
function getCurrentTime(timezone: string): string {
  try {
    const now = new Date();
    return now.toLocaleTimeString("en-AU", {
      timeZone: timezone,
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return "--:--";
  }
}

/**
 * TimezoneSelector - Searchable timezone dropdown
 *
 * Features:
 * - Searchable dropdown of timezones
 * - Shows current time in selected timezone
 * - Prioritizes Australian timezones
 * - Grouped by region
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Input background: #F8FAFC
 * - Border: #E2E8F0
 * - Focus ring: #3B82F6
 */
export function TimezoneSelector({ value, onChange }: TimezoneSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Get the selected timezone option
  const selectedTimezone = TIMEZONES.find((tz) => tz.value === value) || TIMEZONES[0];

  // Current time in selected timezone
  const currentTime = useMemo(() => getCurrentTime(value), [value]);

  // Filter timezones based on search query
  const filteredTimezones = useMemo(() => {
    if (!searchQuery) return TIMEZONES;
    const query = searchQuery.toLowerCase();
    return TIMEZONES.filter(
      (tz) =>
        tz.label.toLowerCase().includes(query) ||
        tz.value.toLowerCase().includes(query) ||
        tz.region.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  // Group timezones by region
  const groupedTimezones = useMemo(() => {
    const groups: Record<string, TimezoneOption[]> = {};
    filteredTimezones.forEach((tz) => {
      if (!groups[tz.region]) {
        groups[tz.region] = [];
      }
      groups[tz.region].push(tz);
    });
    return groups;
  }, [filteredTimezones]);

  return (
    <div className="relative">
      {/* Selected Value Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] hover:border-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent transition-all"
      >
        <div className="flex items-center gap-3">
          <Clock className="h-4 w-4 text-[#64748B]" />
          <span>{selectedTimezone.label}</span>
          <span className="text-xs text-[#94A3B8]">(UTC{selectedTimezone.offset})</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#64748B]">{currentTime}</span>
          <ChevronDown
            className={`h-4 w-4 text-[#64748B] transition-transform ${
              isOpen ? "rotate-180" : ""
            }`}
          />
        </div>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => {
              setIsOpen(false);
              setSearchQuery("");
            }}
          />

          {/* Dropdown Content */}
          <div className="absolute z-20 mt-1 w-full bg-white border border-[#E2E8F0] rounded-lg shadow-lg overflow-hidden">
            {/* Search Input */}
            <div className="p-2 border-b border-[#E2E8F0]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#94A3B8]" />
                <input
                  type="text"
                  placeholder="Search timezone..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-[#F8FAFC] border border-[#E2E8F0] rounded-md text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                  autoFocus
                />
              </div>
            </div>

            {/* Timezone List */}
            <div className="max-h-64 overflow-y-auto">
              {Object.entries(groupedTimezones).map(([region, timezones]) => (
                <div key={region}>
                  {/* Region Header */}
                  <div className="px-3 py-1.5 bg-[#F8FAFC] border-b border-[#E2E8F0]">
                    <span className="text-[10px] font-semibold text-[#64748B] uppercase tracking-wider">
                      {region}
                    </span>
                  </div>
                  {/* Timezone Options */}
                  {timezones.map((tz) => (
                    <button
                      key={tz.value}
                      type="button"
                      onClick={() => {
                        onChange(tz.value);
                        setIsOpen(false);
                        setSearchQuery("");
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-[#F8FAFC] transition-colors ${
                        tz.value === value ? "bg-[#EFF6FF]" : ""
                      }`}
                    >
                      <span
                        className={`${
                          tz.value === value ? "text-[#3B82F6] font-medium" : "text-[#1E293B]"
                        }`}
                      >
                        {tz.label}
                      </span>
                      <span className="text-xs text-[#94A3B8]">UTC{tz.offset}</span>
                    </button>
                  ))}
                </div>
              ))}

              {filteredTimezones.length === 0 && (
                <div className="px-4 py-6 text-center text-sm text-[#64748B]">
                  No timezones found
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default TimezoneSelector;
