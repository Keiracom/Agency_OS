/**
 * NewCampaignModal.tsx - Campaign Creation Modal
 * Phase: Operation Modular Cockpit
 * 
 * Modal for creating new campaigns with permission mode selection.
 */

"use client";

import { useState } from "react";
import {
  XCircle,
  Plus,
  CheckCircle,
  Sparkles,
  Eye,
  MousePointer,
} from "lucide-react";
import type { PermissionMode } from "@/lib/api/types";

// ============================================
// Types
// ============================================

interface NewCampaignData {
  name: string;
  description: string;
  permissionMode: PermissionMode;
}

interface NewCampaignModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: NewCampaignData) => void;
  /** Loading state during submission */
  isSubmitting?: boolean;
}

// ============================================
// Configuration
// ============================================

const permissionModes: {
  id: PermissionMode;
  label: string;
  description: string;
  icon: typeof Sparkles;
}[] = [
  {
    id: "autopilot",
    label: "Autopilot",
    description: "AI handles everything automatically",
    icon: Sparkles,
  },
  {
    id: "co_pilot",
    label: "Co-Pilot",
    description: "Review before sending",
    icon: Eye,
  },
  {
    id: "manual",
    label: "Manual",
    description: "Full control over every action",
    icon: MousePointer,
  },
];

// ============================================
// Component
// ============================================

export function NewCampaignModal({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting = false,
}: NewCampaignModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [permissionMode, setPermissionMode] = useState<PermissionMode>("autopilot");

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (!name.trim()) return;
    onSubmit({ name, description, permissionMode });
    // Reset form
    setName("");
    setDescription("");
    setPermissionMode("autopilot");
  };

  const handleClose = () => {
    if (isSubmitting) return;
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">New Campaign</h2>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-slate-400 hover:text-slate-600 disabled:opacity-50"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {/* Campaign Name */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Campaign Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Tech Decision Makers Q1"
              disabled={isSubmitting}
              className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-slate-50"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Description <span className="text-slate-400">(optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of your target audience..."
              rows={3}
              disabled={isSubmitting}
              className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:bg-slate-50"
            />
          </div>

          {/* Permission Mode */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Permission Mode
            </label>
            <div className="space-y-2">
              {permissionModes.map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => setPermissionMode(mode.id)}
                  disabled={isSubmitting}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                    permissionMode === mode.id
                      ? "border-blue-500 bg-blue-50"
                      : "border-slate-200 hover:border-slate-300"
                  } disabled:opacity-50`}
                >
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      permissionMode === mode.id
                        ? "bg-blue-500 text-white"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    <mode.icon className="w-5 h-5" />
                  </div>
                  <div className="text-left">
                    <div className="font-medium text-slate-900">{mode.label}</div>
                    <div className="text-xs text-slate-500">{mode.description}</div>
                  </div>
                  {permissionMode === mode.id && (
                    <CheckCircle className="w-5 h-5 text-blue-500 ml-auto" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 flex items-center justify-end gap-3">
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-slate-600 text-sm font-medium hover:text-slate-800 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!name.trim() || isSubmitting}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4" />
                Create Campaign
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default NewCampaignModal;
