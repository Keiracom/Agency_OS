"use client";

import { Check, X, AlertCircle, Shield } from "lucide-react";

/**
 * Integration status type
 */
export type IntegrationStatus = "connected" | "not_connected" | "error";

/**
 * IntegrationStatusCard props
 */
export interface IntegrationStatusCardProps {
  /** Integration name */
  name: string;
  /** Integration description */
  description: string;
  /** Connection status */
  status: IntegrationStatus;
  /** When the integration was connected */
  connectedAt?: string | null;
  /** Whether this integration is managed by the platform (no user action needed) */
  isManaged?: boolean;
}

/**
 * Get status badge configuration
 */
function getStatusConfig(status: IntegrationStatus) {
  switch (status) {
    case "connected":
      return {
        label: "Connected",
        bgColor: "bg-[#DCFCE7]",
        textColor: "text-[#166534]",
        icon: Check,
      };
    case "not_connected":
      return {
        label: "Not Connected",
        bgColor: "bg-[#F1F5F9]",
        textColor: "text-[#64748B]",
        icon: X,
      };
    case "error":
      return {
        label: "Error",
        bgColor: "bg-[#FEE2E2]",
        textColor: "text-[#DC2626]",
        icon: AlertCircle,
      };
  }
}

/**
 * Format connection date
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-AU", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * IntegrationStatusCard - Display card for integration connection status
 *
 * Features:
 * - Integration name and description
 * - Connection status badge (Connected/Not Connected/Error)
 * - "Managed by Agency OS" label for platform integrations
 * - Connected date when available
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Success: #10B981 / #DCFCE7
 * - Error: #EF4444 / #FEE2E2
 * - Text secondary: #64748B
 */
export function IntegrationStatusCard({
  name,
  description,
  status,
  connectedAt,
  isManaged = false,
}: IntegrationStatusCardProps) {
  const statusConfig = getStatusConfig(status);
  const StatusIcon = statusConfig.icon;

  return (
    <div className="flex items-center justify-between py-4 border-b border-[#E2E8F0] last:border-0">
      {/* Left: Name and description */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[#1E293B]">{name}</span>
          {isManaged && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#F1F5F9] rounded-full">
              <Shield className="h-3 w-3 text-[#64748B]" />
              <span className="text-[10px] font-medium text-[#64748B]">
                Managed by Agency OS
              </span>
            </span>
          )}
        </div>
        <p className="text-xs text-[#64748B] mt-0.5">{description}</p>
        {status === "connected" && connectedAt && (
          <p className="text-[10px] text-[#94A3B8] mt-1">
            Connected on {formatDate(connectedAt)}
          </p>
        )}
      </div>

      {/* Right: Status badge */}
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${statusConfig.bgColor}`}
      >
        <StatusIcon className={`h-3.5 w-3.5 ${statusConfig.textColor}`} />
        <span className={`text-xs font-medium ${statusConfig.textColor}`}>
          {statusConfig.label}
        </span>
      </div>
    </div>
  );
}

export default IntegrationStatusCard;
