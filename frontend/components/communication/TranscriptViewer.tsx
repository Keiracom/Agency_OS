"use client";

/**
 * TranscriptViewer.tsx - Voice AI Transcript Viewer
 * Phase 21: Deep Research & UI
 *
 * Text-only chat bubble interface for Voice AI logs.
 * No audio player - text transcripts only.
 */

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Phone, User, Bot, Clock, CheckCircle2, XCircle, AlertCircle } from "lucide-react";

interface TranscriptMessage {
  id: string;
  role: "agent" | "user";
  content: string;
  timestamp: Date;
}

interface TranscriptData {
  id: string;
  leadName: string;
  leadCompany: string;
  phoneNumber: string;
  startTime: Date;
  endTime?: Date;
  duration?: number; // seconds
  status: "completed" | "voicemail" | "no_answer" | "failed";
  outcome?: "meeting_booked" | "callback_requested" | "not_interested" | "no_decision";
  messages: TranscriptMessage[];
}

interface TranscriptViewerProps {
  transcript?: TranscriptData;
}

// Mock transcript for demonstration
const mockTranscript: TranscriptData = {
  id: "call-001",
  leadName: "Sarah Williams",
  leadCompany: "Bloom Digital",
  phoneNumber: "+61 412 345 678",
  startTime: new Date(Date.now() - 1000 * 60 * 15),
  endTime: new Date(Date.now() - 1000 * 60 * 12),
  duration: 183, // 3 minutes 3 seconds
  status: "completed",
  outcome: "meeting_booked",
  messages: [
    {
      id: "1",
      role: "agent",
      content: "Hi Sarah, this is Alex from Agency OS. I noticed Bloom Digital has been expanding into healthcare marketing - congratulations on the recent wins!",
      timestamp: new Date(Date.now() - 1000 * 60 * 15),
    },
    {
      id: "2",
      role: "user",
      content: "Oh, thank you! Yes, it's been a busy quarter. How can I help you?",
      timestamp: new Date(Date.now() - 1000 * 60 * 14.5),
    },
    {
      id: "3",
      role: "agent",
      content: "I help marketing agencies like yours book more qualified meetings using AI-powered outreach. We've helped similar agencies book 40+ meetings per month. Given your focus on regulated industries, I thought our compliance-first approach might be a good fit.",
      timestamp: new Date(Date.now() - 1000 * 60 * 14),
    },
    {
      id: "4",
      role: "user",
      content: "Interesting. We've been looking at automating some of our prospecting. What makes your platform different?",
      timestamp: new Date(Date.now() - 1000 * 60 * 13.5),
    },
    {
      id: "5",
      role: "agent",
      content: "Great question! Unlike generic AI tools, we use five channels - email, LinkedIn, SMS, voice, and even direct mail - all coordinated by AI. Plus, our ALS Score ranks leads by actual buying signals, not just demographics.",
      timestamp: new Date(Date.now() - 1000 * 60 * 13),
    },
    {
      id: "6",
      role: "user",
      content: "That sounds comprehensive. I'd be interested in learning more about the healthcare compliance features.",
      timestamp: new Date(Date.now() - 1000 * 60 * 12.5),
    },
    {
      id: "7",
      role: "agent",
      content: "Perfect! Would you have 15 minutes Thursday afternoon for a quick demo? I can show you exactly how we handle AHPRA and TGA compliance in outreach.",
      timestamp: new Date(Date.now() - 1000 * 60 * 12),
    },
    {
      id: "8",
      role: "user",
      content: "Thursday at 2pm works. Send me a calendar invite.",
      timestamp: new Date(Date.now() - 1000 * 60 * 11.5),
    },
    {
      id: "9",
      role: "agent",
      content: "Excellent! I'll send that right over. Looking forward to speaking with you Thursday, Sarah. Have a great day!",
      timestamp: new Date(Date.now() - 1000 * 60 * 11),
    },
  ],
};

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const formatTime = (date: Date): string => {
  return date.toLocaleTimeString("en-AU", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getStatusConfig = (status: TranscriptData["status"]) => {
  switch (status) {
    case "completed":
      return {
        color: "bg-green-500/20 text-green-400 border-green-500/30",
        icon: CheckCircle2,
        label: "Completed",
      };
    case "voicemail":
      return {
        color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
        icon: AlertCircle,
        label: "Voicemail",
      };
    case "no_answer":
      return {
        color: "bg-gray-500/20 text-gray-400 border-gray-500/30",
        icon: AlertCircle,
        label: "No Answer",
      };
    case "failed":
      return {
        color: "bg-red-500/20 text-red-400 border-red-500/30",
        icon: XCircle,
        label: "Failed",
      };
  }
};

const getOutcomeConfig = (outcome: TranscriptData["outcome"]) => {
  switch (outcome) {
    case "meeting_booked":
      return {
        color: "bg-green-500/20 text-green-400 border-green-500/30",
        label: "Meeting Booked",
      };
    case "callback_requested":
      return {
        color: "bg-blue-500/20 text-blue-400 border-blue-500/30",
        label: "Callback Requested",
      };
    case "not_interested":
      return {
        color: "bg-gray-500/20 text-gray-400 border-gray-500/30",
        label: "Not Interested",
      };
    case "no_decision":
      return {
        color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
        label: "No Decision",
      };
    default:
      return null;
  }
};

export function TranscriptViewer({ transcript = mockTranscript }: TranscriptViewerProps) {
  const statusConfig = useMemo(() => getStatusConfig(transcript.status), [transcript.status]);
  const outcomeConfig = useMemo(
    () => (transcript.outcome ? getOutcomeConfig(transcript.outcome) : null),
    [transcript.outcome]
  );

  const StatusIcon = statusConfig.icon;

  return (
    <Card className="bg-[#1a1a1f] border-white/10">
      {/* Header */}
      <CardHeader className="border-b border-white/10 pb-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-white flex items-center gap-2">
              <Phone className="h-5 w-5 text-green-400" />
              Voice AI Transcript
            </CardTitle>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span className="font-medium text-white">{transcript.leadName}</span>
              <span>-</span>
              <span>{transcript.leadCompany}</span>
            </div>
            <p className="text-xs text-gray-500">{transcript.phoneNumber}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge className={statusConfig.color}>
              <StatusIcon className="h-3 w-3 mr-1" />
              {statusConfig.label}
            </Badge>
            {outcomeConfig && (
              <Badge className={outcomeConfig.color}>{outcomeConfig.label}</Badge>
            )}
          </div>
        </div>

        {/* Call metadata */}
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatTime(transcript.startTime)}
          </div>
          {transcript.duration && (
            <div className="flex items-center gap-1">
              Duration: {formatDuration(transcript.duration)}
            </div>
          )}
        </div>
      </CardHeader>

      {/* Messages */}
      <CardContent className="pt-4 space-y-4 max-h-[500px] overflow-y-auto">
        {transcript.messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === "agent" ? "" : "flex-row-reverse"
            }`}
          >
            {/* Avatar */}
            <div
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                message.role === "agent"
                  ? "bg-purple-500/20"
                  : "bg-blue-500/20"
              }`}
            >
              {message.role === "agent" ? (
                <Bot className="h-4 w-4 text-purple-400" />
              ) : (
                <User className="h-4 w-4 text-blue-400" />
              )}
            </div>

            {/* Message bubble */}
            <div
              className={`flex-1 max-w-[80%] ${
                message.role === "agent" ? "" : "text-right"
              }`}
            >
              <div
                className={`inline-block px-4 py-2.5 rounded-2xl ${
                  message.role === "agent"
                    ? "bg-[#2a2a2f] rounded-tl-none"
                    : "bg-blue-600/20 rounded-tr-none"
                }`}
              >
                <p className="text-sm text-gray-200 leading-relaxed">
                  {message.content}
                </p>
              </div>
              <p className="text-[10px] text-gray-600 mt-1 px-2">
                {formatTime(message.timestamp)}
              </p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default TranscriptViewer;
