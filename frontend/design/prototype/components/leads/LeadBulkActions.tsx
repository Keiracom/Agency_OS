"use client";

import { RefreshCw, Pause, Archive, X, Loader2 } from "lucide-react";

/**
 * LeadBulkActions props
 */
export interface LeadBulkActionsProps {
  /** Number of selected leads */
  selectedCount: number;
  /** Handler for bulk enrich */
  onEnrich?: () => void;
  /** Handler for bulk pause */
  onPause?: () => void;
  /** Handler for bulk archive */
  onArchive?: () => void;
  /** Handler for clearing selection */
  onClear?: () => void;
  /** Is any bulk action processing */
  isProcessing?: boolean;
  /** Which action is processing */
  processingAction?: "enrich" | "pause" | "archive" | null;
}

/**
 * LeadBulkActions - Bulk action floating bar component
 *
 * Features:
 * - Floating bar when selection > 0
 * - Selection count display
 * - Enrich, Pause, Archive actions
 * - Clear selection button
 * - Loading states for actions
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Card background: #FFFFFF
 * - Accent blue: #3B82F6
 * - Shadow: shadow-lg
 *
 * Usage:
 * ```tsx
 * {selectedCount > 0 && (
 *   <LeadBulkActions
 *     selectedCount={selectedCount}
 *     onEnrich={() => handleBulkEnrich()}
 *     onPause={() => handleBulkPause()}
 *     onArchive={() => handleBulkArchive()}
 *     onClear={() => setSelectedIds([])}
 *     isProcessing={isProcessing}
 *   />
 * )}
 * ```
 */
export function LeadBulkActions({
  selectedCount,
  onEnrich,
  onPause,
  onArchive,
  onClear,
  isProcessing = false,
  processingAction = null,
}: LeadBulkActionsProps) {
  if (selectedCount === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-lg shadow-black/10 px-4 py-3">
        <div className="flex items-center gap-4">
          {/* Selection count */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-[#1E293B]">
              {selectedCount}
            </span>
            <span className="text-sm text-[#64748B]">
              lead{selectedCount !== 1 ? "s" : ""} selected
            </span>
          </div>

          {/* Divider */}
          <div className="w-px h-6 bg-[#E2E8F0]" />

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={onEnrich}
              disabled={isProcessing}
              className="flex items-center gap-2 px-3 py-1.5 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {processingAction === "enrich" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Enrich All
            </button>

            <button
              onClick={onPause}
              disabled={isProcessing}
              className="flex items-center gap-2 px-3 py-1.5 bg-[#FEF3C7] hover:bg-[#FDE68A] text-[#92400E] text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {processingAction === "pause" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Pause className="h-4 w-4" />
              )}
              Pause
            </button>

            <button
              onClick={onArchive}
              disabled={isProcessing}
              className="flex items-center gap-2 px-3 py-1.5 bg-[#FEE2E2] hover:bg-[#FECACA] text-[#991B1B] text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {processingAction === "archive" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Archive className="h-4 w-4" />
              )}
              Archive
            </button>
          </div>

          {/* Divider */}
          <div className="w-px h-6 bg-[#E2E8F0]" />

          {/* Clear selection */}
          <button
            onClick={onClear}
            disabled={isProcessing}
            className="flex items-center gap-1 px-2 py-1.5 text-[#64748B] hover:text-[#374151] text-sm transition-colors disabled:opacity-50"
          >
            <X className="h-4 w-4" />
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}

export default LeadBulkActions;
