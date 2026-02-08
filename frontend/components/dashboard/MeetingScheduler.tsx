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
// Base: bg-[#0A0A12]
// Surface: bg-[#12121D]
// Surface Hover: bg-[#1A1A28]
// Elevated: bg-[#222233]
// Border Subtle: border-[#1E1E2E]
// Border Default: border-[#2A2A3D]
// Text Primary: text-[#F8F8FC]
// Text Secondary: text-[#B4B4C4]
// Text Muted: text-[#6E6E82]
// Accent Purple: text-violet-500 / bg-violet-500

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
          className="p-2 rounded-lg hover:bg-[#1A1A28] transition-colors text-[#B4B4C4] hover:text-[#F8F8FC]"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <span className="text-[#F8F8FC] font-semibold">{monthName}</span>
        <button
          onClick={nextMonth}
          className="p-2 rounded-lg hover:bg-[#1A1A28] transition-colors text-[#B4B4C4] hover:text-[#F8F8FC]"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      
      {/* Day Headers */}
      <div className="grid grid-cols-7 gap-1 text-center text-xs text-[#6E6E82] font-medium">
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
                isSelected && "bg-violet-600 text-white ring-2 ring-violet-500/50",
                !isSelected && isToday && "ring-1 ring-violet-500/50 text-violet-400",
                !isSelected && !isToday && !isDisabled && "text-[#F8F8FC] hover:bg-[#1A1A28]",
                isDisabled && "text-[#3A3A4D] cursor-not-allowed",
                weekend && !isSelected && !isDisabled && "text-[#6E6E82]"
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
      <span className="text-xs font-medium text-[#6E6E82] uppercase tracking-wide">{label}</span>
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
                isSelected && "bg-violet-600 border-violet-500 text-white",
                !isSelected && slot.available && "border-[#2A2A3D] text-[#B4B4C4] hover:border-violet-500/50 hover:text-[#F8F8FC] hover:bg-[#1A1A28]",
                !slot.available && "border-[#1E1E2E] text-[#3A3A4D] cursor-not-allowed line-through"
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
            "rounded-2xl border border-[#2A2A3D]",
            // Glassmorphic effect
            "bg-[#12121D]/95 backdrop-blur-xl",
            "shadow-2xl shadow-black/50",
            "animate-in zoom-in-95 slide-in-from-bottom-4 duration-300"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#2A2A3D]">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-xl bg-violet-500/10 text-violet-400">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-[#F8F8FC]">Schedule Meeting</h2>
                <p className="text-sm text-[#6E6E82]">Book a time with {lead.name}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[#1A1A28] transition-colors text-[#6E6E82] hover:text-[#F8F8FC]"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          {/* Content */}
          <div className="overflow-y-auto max-h-[calc(90vh-140px)]">
            <div className="p-6 space-y-6">
              {/* Lead Info Card */}
              <div className="p-4 rounded-xl bg-[#0A0A12] border border-[#1E1E2E]">
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  {lead.avatarUrl ? (
                    <img
                      src={lead.avatarUrl}
                      alt={lead.name}
                      className="w-12 h-12 rounded-full object-cover ring-2 ring-violet-500/30"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-semibold">
                      {initials}
                    </div>
                  )}
                  
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-[#F8F8FC] font-semibold truncate">{lead.name}</h3>
                    {lead.title && (
                      <div className="flex items-center gap-1.5 text-sm text-[#B4B4C4]">
                        <User className="w-3.5 h-3.5 text-[#6E6E82]" />
                        <span className="truncate">{lead.title}</span>
                      </div>
                    )}
                    {lead.company && (
                      <div className="flex items-center gap-1.5 text-sm text-[#B4B4C4]">
                        <Building2 className="w-3.5 h-3.5 text-[#6E6E82]" />
                        <span className="truncate">{lead.company}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Meeting Type Selection */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-[#F8F8FC]">Meeting Type</label>
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
                            ? "border-violet-500 bg-violet-500/10" 
                            : "border-[#2A2A3D] hover:border-[#3A3A4D] hover:bg-[#1A1A28]"
                        )}
                      >
                        <Icon className={cn("w-5 h-5 mb-2", isSelected ? "text-violet-400" : "text-[#6E6E82]")} />
                        <div className={cn("font-medium text-sm", isSelected ? "text-[#F8F8FC]" : "text-[#B4B4C4]")}>
                          {type.label}
                        </div>
                        <div className="text-xs text-[#6E6E82] mt-1">{type.description}</div>
                      </button>
                    );
                  })}
                </div>
              </div>
              
              {/* Duration Selection */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-[#F8F8FC]">Duration</label>
                <div className="flex gap-2">
                  {DURATIONS.map((d) => (
                    <button
                      key={d.value}
                      onClick={() => setDuration(d.value)}
                      className={cn(
                        "px-4 py-2 rounded-lg text-sm font-medium transition-all border",
                        duration === d.value
                          ? "bg-violet-600 border-violet-500 text-white"
                          : "border-[#2A2A3D] text-[#B4B4C4] hover:border-violet-500/50 hover:text-[#F8F8FC]"
                      )}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Date & Time Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Calendar */}
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-[#F8F8FC]">Select Date</label>
                  <div className="p-4 rounded-xl bg-[#0A0A12] border border-[#1E1E2E]">
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
                  <label className="block text-sm font-medium text-[#F8F8FC]">Select Time</label>
                  <div className="p-4 rounded-xl bg-[#0A0A12] border border-[#1E1E2E] max-h-[320px] overflow-y-auto">
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
                <label className="block text-sm font-medium text-[#F8F8FC]">
                  Notes <span className="text-[#6E6E82] font-normal">(optional)</span>
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add any notes or context for the meeting..."
                  rows={3}
                  className={cn(
                    "w-full px-4 py-3 rounded-xl resize-none",
                    "bg-[#0A0A12] border border-[#2A2A3D]",
                    "text-[#F8F8FC] placeholder-[#6E6E82]",
                    "focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500",
                    "transition-all"
                  )}
                />
              </div>
              
              {/* Timezone Display */}
              <div className="flex items-center gap-2 text-sm text-[#6E6E82]">
                <Globe className="w-4 h-4" />
                <span>Times shown in {timezone.replace(/_/g, " ")}</span>
              </div>
            </div>
          </div>
          
          {/* Footer */}
          <div className="px-6 py-4 border-t border-[#2A2A3D] bg-[#0A0A12]/50">
            <div className="flex items-center justify-between">
              {/* Selected Summary */}
              <div className="text-sm text-[#B4B4C4]">
                {selectedTime ? (
                  <span>
                    <span className="text-[#F8F8FC] font-medium">
                      {selectedDate.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}
                    </span>
                    {" at "}
                    <span className="text-[#F8F8FC] font-medium">
                      {(() => {
                        const hour = parseInt(selectedTime.split(":")[0]);
                        const minute = selectedTime.split(":")[1];
                        return `${hour > 12 ? hour - 12 : hour}:${minute} ${hour >= 12 ? "PM" : "AM"}`;
                      })()}
                    </span>
                    {" • "}
                    <span className="text-violet-400">{duration} min</span>
                  </span>
                ) : (
                  <span className="text-[#6E6E82]">Select a date and time</span>
                )}
              </div>
              
              {/* Actions */}
              <div className="flex items-center gap-3">
                <Button
                  variant="ghost"
                  onClick={onClose}
                  className="text-[#B4B4C4] hover:text-[#F8F8FC] hover:bg-[#1A1A28]"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={!isValid || isSubmitting}
                  className={cn(
                    "bg-violet-600 hover:bg-violet-700 text-white",
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
