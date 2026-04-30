/**
 * MeetingScheduler.tsx - Meeting Booking Modal
 * Phase: Operation Modular Cockpit
 * 
 * Bloomberg dark mode + glassmorphic styling
 * Ready to wire to calendar API (Google Calendar, Calendly, etc.)
 * 
 * Features:
 * - Calendar date picker
 * - Time slot selection
 * - Lead info display
 * - Meeting type selection (Discovery/Demo/Follow-up)
 * - Duration picker (15/30/45/60 min)
 * - Notes field
 * - Timezone display
 * - Confirm/Cancel buttons
 */

"use client";

import { useState, useMemo, useCallback } from "react";
import {
  X,
  Calendar,
  Clock,
  ChevronLeft,
  ChevronRight,
  User,
  Building2,
  Video,
  Phone,
  MessageSquare,
  Check,
  Loader2,
  Globe,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ============================================
// Bloomberg Color Reference (from LeadDetailModal)
// ============================================
// Base: bg-bg-cream
// Surface: bg-bg-surface
// Surface Hover: bg-bg-elevated
// Elevated: bg-bg-elevated
// Border Subtle: border-default
// Border Default: border-default
// Text Primary: text-ink
// Text Secondary: text-ink-2
// Text Muted: text-ink-3
// Accent Purple: text-amber / bg-amber

// ============================================
// Types
// ============================================

export type MeetingType = "discovery" | "demo" | "follow-up";

export type MeetingDuration = 15 | 30 | 45 | 60;

export interface LeadInfo {
  id: string;
  name: string;
  email: string;
  company?: string;
  title?: string;
  avatarUrl?: string;
}

export interface TimeSlot {
  time: string; // "09:00", "09:30", etc.
  available: boolean;
}

export interface MeetingSchedulerProps {
  /** Lead to schedule meeting with */
  lead: LeadInfo;
  /** Whether the modal is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Submit handler - receives meeting details */
  onSubmit?: (meeting: ScheduledMeeting) => Promise<void>;
  /** Pre-selected date (optional) */
  initialDate?: Date;
  /** Available time slots by date (optional - for API integration) */
  availableSlots?: Record<string, TimeSlot[]>;
  /** User's timezone */
  timezone?: string;
}

export interface ScheduledMeeting {
  leadId: string;
  type: MeetingType;
  date: Date;
  time: string;
  duration: MeetingDuration;
  notes: string;
  timezone: string;
}

// ============================================
// Meeting Type Config
// ============================================

const MEETING_TYPES: { value: MeetingType; label: string; icon: typeof Video; description: string }[] = [
  {
    value: "discovery",
    label: "Discovery Call",
    icon: Phone,
    description: "Initial conversation to understand needs",
  },
  {
    value: "demo",
    label: "Product Demo",
    icon: Video,
    description: "Full walkthrough of the platform",
  },
  {
    value: "follow-up",
    label: "Follow-up",
    icon: MessageSquare,
    description: "Continue previous discussion",
  },
];

const DURATIONS: { value: MeetingDuration; label: string }[] = [
  { value: 15, label: "15 min" },
  { value: 30, label: "30 min" },
  { value: 45, label: "45 min" },
  { value: 60, label: "60 min" },
];

// ============================================
// Helper Functions
// ============================================

function generateDefaultTimeSlots(): TimeSlot[] {
  const slots: TimeSlot[] = [];
  // Generate slots from 9 AM to 6 PM in 30-min increments
  for (let hour = 9; hour < 18; hour++) {
    slots.push({ time: `${hour.toString().padStart(2, "0")}:00`, available: true });
    slots.push({ time: `${hour.toString().padStart(2, "0")}:30`, available: true });
  }
  return slots;
}

function formatDateKey(date: Date): string {
  return date.toISOString().split("T")[0];
}

function getMonthDays(year: number, month: number): (number | null)[] {
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  
  const days: (number | null)[] = [];
  
  // Add empty slots for days before the first of the month
  for (let i = 0; i < firstDay; i++) {
    days.push(null);
  }
  
  // Add the days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    days.push(day);
  }
  
  return days;
}

function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  );
}

function isDateInPast(date: Date): boolean {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return date < today;
}

function isWeekend(date: Date): boolean {
  const day = date.getDay();
  return day === 0 || day === 6;
}

// ============================================
// Sub-Components
// ============================================

interface CalendarPickerProps {
  selectedDate: Date;
  onSelectDate: (date: Date) => void;
  minDate?: Date;
}

function CalendarPicker({ selectedDate, onSelectDate, minDate }: CalendarPickerProps) {
  const [viewDate, setViewDate] = useState(selectedDate);
  
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const days = getMonthDays(year, month);
  
  const monthName = viewDate.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  
  const prevMonth = () => setViewDate(new Date(year, month - 1, 1));
  const nextMonth = () => setViewDate(new Date(year, month + 1, 1));
  
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  return (
    <div className="space-y-4">
      {/* Month Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={prevMonth}
          className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-ink-2 hover:text-ink"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="text-ink font-semibold">{monthName}</span>
        <button
          onClick={nextMonth}
          className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-ink-2 hover:text-ink"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      
      {/* Day Headers */}
      <div className="grid grid-cols-7 gap-1 text-center text-xs text-ink-3 font-medium">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
          <div key={day} className="py-2">{day}</div>
        ))}
      </div>
      
      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-1">
        {days.map((day, index) => {
          if (day === null) {
            return <div key={`empty-${index}`} className="aspect-square" />;
          }
          
          const date = new Date(year, month, day);
          const isSelected = isSameDay(date, selectedDate);
          const isToday = isSameDay(date, today);
          const isPast = isDateInPast(date);
          const isDisabled = isPast || (minDate && date < minDate);
          const weekend = isWeekend(date);
          
          return (
            <button
              key={day}
              onClick={() => !isDisabled && onSelectDate(date)}
              disabled={isDisabled}
              className={cn(
                "aspect-square rounded-lg text-sm font-medium transition-all",
                "flex items-center justify-center",
                isSelected && "bg-amber text-ink ring-2 ring-amber/50",
                !isSelected && isToday && "ring-1 ring-amber/50 text-amber",
                !isSelected && !isToday && !isDisabled && "text-ink hover:bg-bg-elevated",
                isDisabled && "text-[#3A3A4D] cursor-not-allowed",
                weekend && !isSelected && !isDisabled && "text-ink-3"
              )}
            >
              {day}
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface TimeSlotPickerProps {
  slots: TimeSlot[];
  selectedTime: string | null;
  onSelectTime: (time: string) => void;
}

function TimeSlotPicker({ slots, selectedTime, onSelectTime }: TimeSlotPickerProps) {
  // Group slots by morning/afternoon
  const morningSlots = slots.filter((s) => parseInt(s.time.split(":")[0]) < 12);
  const afternoonSlots = slots.filter((s) => parseInt(s.time.split(":")[0]) >= 12);
  
  const renderSlotGroup = (groupSlots: TimeSlot[], label: string) => (
    <div className="space-y-2">
      <span className="text-xs font-medium text-ink-3 uppercase tracking-wide">{label}</span>
      <div className="grid grid-cols-3 gap-2">
        {groupSlots.map((slot) => {
          const isSelected = selectedTime === slot.time;
          const hour = parseInt(slot.time.split(":")[0]);
          const minute = slot.time.split(":")[1];
          const displayTime = `${hour > 12 ? hour - 12 : hour}:${minute} ${hour >= 12 ? "PM" : "AM"}`;
          
          return (
            <button
              key={slot.time}
              onClick={() => slot.available && onSelectTime(slot.time)}
              disabled={!slot.available}
              className={cn(
                "px-3 py-2 rounded-lg text-sm font-medium transition-all",
                "border",
                isSelected && "bg-amber border-amber text-ink",
                !isSelected && slot.available && "border-default text-ink-2 hover:border-amber/50 hover:text-ink hover:bg-bg-elevated",
                !slot.available && "border-default text-[#3A3A4D] cursor-not-allowed line-through"
              )}
            >
              {displayTime}
            </button>
          );
        })}
      </div>
    </div>
  );
  
  return (
    <div className="space-y-4">
      {morningSlots.length > 0 && renderSlotGroup(morningSlots, "Morning")}
      {afternoonSlots.length > 0 && renderSlotGroup(afternoonSlots, "Afternoon")}
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function MeetingScheduler({
  lead,
  isOpen,
  onClose,
  onSubmit,
  initialDate,
  availableSlots,
  timezone = Intl.DateTimeFormat().resolvedOptions().timeZone,
}: MeetingSchedulerProps) {
  // Form state
  const [selectedDate, setSelectedDate] = useState<Date>(initialDate || new Date());
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [meetingType, setMeetingType] = useState<MeetingType>("discovery");
  const [duration, setDuration] = useState<MeetingDuration>(30);
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Get time slots for selected date
  const timeSlots = useMemo(() => {
    const dateKey = formatDateKey(selectedDate);
    return availableSlots?.[dateKey] || generateDefaultTimeSlots();
  }, [selectedDate, availableSlots]);
  
  // Validation
  const isValid = selectedTime !== null && selectedDate !== null;
  
  // Handle submit
  const handleSubmit = useCallback(async () => {
    if (!isValid || !onSubmit) return;
    
    setIsSubmitting(true);
    try {
      await onSubmit({
        leadId: lead.id,
        type: meetingType,
        date: selectedDate,
        time: selectedTime!,
        duration,
        notes,
        timezone,
      });
      onClose();
    } catch (error) {
      console.error("Failed to schedule meeting:", error);
    } finally {
      setIsSubmitting(false);
    }
  }, [isValid, onSubmit, lead.id, meetingType, selectedDate, selectedTime, duration, notes, timezone, onClose]);
  
  // Get initials for avatar
  const initials = lead.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
  
  if (!isOpen) return null;
  
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 animate-in fade-in duration-200"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div
          className={cn(
            "pointer-events-auto w-full max-w-2xl max-h-[90vh] overflow-hidden",
            "rounded-2xl border border-default",
            // Glassmorphic effect
            "bg-bg-surface/95 backdrop-blur-xl",
            "shadow-2xl shadow-black/50",
            "animate-in zoom-in-95 slide-in-from-bottom-4 duration-300"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-default">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-xl bg-amber/10 text-amber">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-ink">Schedule Meeting</h2>
                <p className="text-sm text-ink-3">Book a time with {lead.name}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-bg-elevated transition-colors text-ink-3 hover:text-ink"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          {/* Content */}
          <div className="overflow-y-auto max-h-[calc(90vh-140px)]">
            <div className="p-6 space-y-6">
              {/* Lead Info Card */}
              <div className="p-4 rounded-xl bg-bg-cream border border-default">
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  {lead.avatarUrl ? (
                    <img
                      src={lead.avatarUrl}
                      alt={lead.name}
                      className="w-12 h-12 rounded-full object-cover ring-2 ring-amber/30"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-amber to-amber flex items-center justify-center text-ink font-semibold">
                      {initials}
                    </div>
                  )}
                  
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-ink font-semibold truncate">{lead.name}</h3>
                    {lead.title && (
                      <div className="flex items-center gap-1.5 text-sm text-ink-2">
                        <User className="w-3.5 h-3.5 text-ink-3" />
                        <span className="truncate">{lead.title}</span>
                      </div>
                    )}
                    {lead.company && (
                      <div className="flex items-center gap-1.5 text-sm text-ink-2">
                        <Building2 className="w-3.5 h-3.5 text-ink-3" />
                        <span className="truncate">{lead.company}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Meeting Type Selection */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-ink">Meeting Type</label>
                <div className="grid grid-cols-3 gap-3">
                  {MEETING_TYPES.map((type) => {
                    const Icon = type.icon;
                    const isSelected = meetingType === type.value;
                    
                    return (
                      <button
                        key={type.value}
                        onClick={() => setMeetingType(type.value)}
                        className={cn(
                          "p-4 rounded-xl border text-left transition-all",
                          isSelected 
                            ? "border-amber bg-amber/10" 
                            : "border-default hover:border-[#3A3A4D] hover:bg-bg-elevated"
                        )}
                      >
                        <Icon className={cn("w-5 h-5 mb-2", isSelected ? "text-amber" : "text-ink-3")} />
                        <div className={cn("font-medium text-sm", isSelected ? "text-ink" : "text-ink-2")}>
                          {type.label}
                        </div>
                        <div className="text-xs text-ink-3 mt-1">{type.description}</div>
                      </button>
                    );
                  })}
                </div>
              </div>
              
              {/* Duration Selection */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-ink">Duration</label>
                <div className="flex gap-2">
                  {DURATIONS.map((d) => (
                    <button
                      key={d.value}
                      onClick={() => setDuration(d.value)}
                      className={cn(
                        "px-4 py-2 rounded-lg text-sm font-medium transition-all border",
                        duration === d.value
                          ? "bg-amber border-amber text-ink"
                          : "border-default text-ink-2 hover:border-amber/50 hover:text-ink"
                      )}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Date & Time Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-6">
                {/* Calendar */}
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-ink">Select Date</label>
                  <div className="p-4 rounded-xl bg-bg-cream border border-default">
                    <CalendarPicker
                      selectedDate={selectedDate}
                      onSelectDate={(date) => {
                        setSelectedDate(date);
                        setSelectedTime(null); // Reset time when date changes
                      }}
                    />
                  </div>
                </div>
                
                {/* Time Slots */}
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-ink">Select Time</label>
                  <div className="p-4 rounded-xl bg-bg-cream border border-default max-h-[320px] overflow-y-auto">
                    <TimeSlotPicker
                      slots={timeSlots}
                      selectedTime={selectedTime}
                      onSelectTime={setSelectedTime}
                    />
                  </div>
                </div>
              </div>
              
              {/* Notes */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-ink">
                  Notes <span className="text-ink-3 font-normal">(optional)</span>
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add any notes or context for the meeting..."
                  rows={3}
                  className={cn(
                    "w-full px-4 py-3 rounded-xl resize-none",
                    "bg-bg-cream border border-default",
                    "text-ink placeholder-[#6E6E82]",
                    "focus:outline-none focus:ring-2 focus:ring-amber/50 focus:border-amber",
                    "transition-all"
                  )}
                />
              </div>
              
              {/* Timezone Display */}
              <div className="flex items-center gap-2 text-sm text-ink-3">
                <Globe className="w-4 h-4" />
                <span>Times shown in {timezone.replace(/_/g, " ")}</span>
              </div>
            </div>
          </div>
          
          {/* Footer */}
          <div className="px-6 py-4 border-t border-default bg-bg-cream/50">
            <div className="flex items-center justify-between">
              {/* Selected Summary */}
              <div className="text-sm text-ink-2">
                {selectedTime ? (
                  <span>
                    <span className="text-ink font-medium">
                      {selectedDate.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
                    </span>
                    {" at "}
                    <span className="text-ink font-medium">
                      {(() => {
                        const hour = parseInt(selectedTime.split(":")[0]);
                        const minute = selectedTime.split(":")[1];
                        return `${hour > 12 ? hour - 12 : hour}:${minute} ${hour >= 12 ? "PM" : "AM"}`;
                      })()}
                    </span>
                    {" • "}
                    <span className="text-amber">{duration} min</span>
                  </span>
                ) : (
                  <span className="text-ink-3">Select a date and time</span>
                )}
              </div>
              
              {/* Actions */}
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  onClick={onClose}
                  className="text-ink-2 hover:text-ink hover:bg-bg-elevated"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={!isValid || isSubmitting}
                  className={cn(
                    "bg-amber hover:bg-violet-700 text-ink",
                    "disabled:opacity-50 disabled:cursor-not-allowed",
                    "min-w-[140px]"
                  )}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Scheduling...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4 mr-2" />
                      Confirm Booking
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default MeetingScheduler;
