"use client";

import { Mail, MessageSquare, Linkedin, Phone, ArrowRight, Clock } from "lucide-react";

/**
 * Sequence step data
 */
export interface SequenceStep {
  id: string;
  step_number: number;
  channel: "email" | "sms" | "linkedin" | "voice";
  name: string;
  delay_days: number;
  content_preview?: string;
  subject?: string;
  is_active: boolean;
}

/**
 * SequenceBuilder props
 */
export interface SequenceBuilderProps {
  /** List of sequence steps */
  sequences: SequenceStep[];
  /** Whether the builder is read-only (view mode) */
  isReadOnly?: boolean;
}

/**
 * Channel icon mapping
 */
const channelIcons = {
  email: Mail,
  sms: MessageSquare,
  linkedin: Linkedin,
  voice: Phone,
};

/**
 * Channel colors (from DESIGN_SYSTEM.md)
 */
const channelColors = {
  email: {
    bg: "bg-[#DBEAFE]",
    text: "text-[#1D4ED8]",
    border: "border-[#3B82F6]",
  },
  sms: {
    bg: "bg-[#D1FAE5]",
    text: "text-[#059669]",
    border: "border-[#10B981]",
  },
  linkedin: {
    bg: "bg-[#E0F2FE]",
    text: "text-[#0369A1]",
    border: "border-[#0077B5]",
  },
  voice: {
    bg: "bg-[#EDE9FE]",
    text: "text-[#7C3AED]",
    border: "border-[#8B5CF6]",
  },
};

/**
 * Channel labels
 */
const channelLabels = {
  email: "Email",
  sms: "SMS",
  linkedin: "LinkedIn",
  voice: "Voice",
};

/**
 * SequenceBuilder - Visual sequence editor with timeline view
 *
 * Features:
 * - Timeline view with connected steps
 * - Channel icon per step
 * - Delay indicator between steps
 * - Content preview
 * - Step status (active/inactive)
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Card background: #FFFFFF
 * - Card border: #E2E8F0
 * - Channel colors as defined
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 */
export function SequenceBuilder({
  sequences,
  isReadOnly = true,
}: SequenceBuilderProps) {
  // Sort sequences by step number
  const sortedSequences = [...sequences].sort(
    (a, b) => a.step_number - b.step_number
  );

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
          Sequence Timeline
        </h3>
      </div>

      {/* Timeline */}
      <div className="p-6">
        {sortedSequences.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-[#64748B]">No sequence steps configured</p>
          </div>
        ) : (
          <div className="space-y-4">
            {sortedSequences.map((step, index) => {
              const Icon = channelIcons[step.channel];
              const colors = channelColors[step.channel];
              const isLast = index === sortedSequences.length - 1;

              return (
                <div key={step.id}>
                  {/* Step Card */}
                  <div
                    className={`flex items-start gap-4 ${
                      !step.is_active ? "opacity-50" : ""
                    }`}
                  >
                    {/* Step Number & Icon */}
                    <div className="flex-shrink-0">
                      <div
                        className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center border-2 ${colors.border}`}
                      >
                        <Icon className={`h-5 w-5 ${colors.text}`} />
                      </div>
                    </div>

                    {/* Step Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-xs font-semibold text-[#94A3B8] uppercase">
                          Step {step.step_number}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}
                        >
                          {channelLabels[step.channel]}
                        </span>
                        {!step.is_active && (
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-[#F1F5F9] text-[#64748B]">
                            Disabled
                          </span>
                        )}
                      </div>

                      <h4 className="font-medium text-[#1E293B] mb-1">{step.name}</h4>

                      {/* Subject (for email) */}
                      {step.subject && (
                        <p className="text-sm text-[#64748B] mb-1">
                          <span className="font-medium">Subject:</span> {step.subject}
                        </p>
                      )}

                      {/* Content Preview */}
                      {step.content_preview && (
                        <p className="text-sm text-[#94A3B8] line-clamp-2">
                          {step.content_preview}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Delay Connector (if not last) */}
                  {!isLast && (
                    <div className="flex items-center gap-4 ml-6 py-3">
                      <div className="flex-shrink-0 w-0.5 h-8 bg-[#E2E8F0] ml-[23px]" />
                      <div className="flex items-center gap-2 text-xs text-[#94A3B8]">
                        <Clock className="h-3.5 w-3.5" />
                        <span>
                          Wait{" "}
                          {sortedSequences[index + 1]?.delay_days || 0}{" "}
                          {(sortedSequences[index + 1]?.delay_days || 0) === 1
                            ? "day"
                            : "days"}
                        </span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default SequenceBuilder;
