"use client";

import { Linkedin, Check, X, AlertCircle, Shield, ExternalLink } from "lucide-react";

/**
 * LinkedIn connection status
 */
export type LinkedInStatus = "connected" | "disconnected" | "connecting" | "awaiting_2fa" | "error";

/**
 * LinkedInStatusCard props
 */
export interface LinkedInStatusCardProps {
  /** Connection status */
  status: LinkedInStatus;
  /** Profile name when connected */
  profileName?: string | null;
  /** Profile URL when connected */
  profileUrl?: string | null;
  /** When the account was connected */
  connectedAt?: string | null;
  /** Handler for connect button */
  onConnect?: () => void;
  /** Handler for disconnect button */
  onDisconnect?: () => void;
}

/**
 * Get status badge configuration
 */
function getStatusConfig(status: LinkedInStatus) {
  switch (status) {
    case "connected":
      return {
        label: "Connected",
        bgColor: "bg-[#DCFCE7]",
        textColor: "text-[#166534]",
        icon: Check,
      };
    case "disconnected":
      return {
        label: "Not Connected",
        bgColor: "bg-[#F1F5F9]",
        textColor: "text-[#64748B]",
        icon: X,
      };
    case "connecting":
      return {
        label: "Connecting...",
        bgColor: "bg-[#FEF3C7]",
        textColor: "text-[#B45309]",
        icon: AlertCircle,
      };
    case "awaiting_2fa":
      return {
        label: "Awaiting 2FA",
        bgColor: "bg-[#FEF3C7]",
        textColor: "text-[#B45309]",
        icon: AlertCircle,
      };
    case "error":
      return {
        label: "Connection Error",
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
 * LinkedInStatusCard - LinkedIn connection status display and management
 *
 * Features:
 * - Connection status badge
 * - Profile info when connected
 * - Connect/Disconnect buttons
 * - Security info section
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - LinkedIn blue: #0077B5
 * - Success: #10B981 / #DCFCE7
 * - Error: #EF4444 / #FEE2E2
 */
export function LinkedInStatusCard({
  status,
  profileName,
  profileUrl,
  connectedAt,
  onConnect,
  onDisconnect,
}: LinkedInStatusCardProps) {
  const statusConfig = getStatusConfig(status);
  const StatusIcon = statusConfig.icon;

  return (
    <div className="space-y-6">
      {/* Main Status Card */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E2E8F0] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#0077B5]/10 rounded-lg">
              <Linkedin className="h-5 w-5 text-[#0077B5]" />
            </div>
            <h3 className="text-sm font-semibold text-[#1E293B]">
              Connection Status
            </h3>
          </div>
          {/* Status Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ${statusConfig.bgColor}`}
          >
            <StatusIcon className={`h-3.5 w-3.5 ${statusConfig.textColor}`} />
            <span className={`text-xs font-medium ${statusConfig.textColor}`}>
              {statusConfig.label}
            </span>
          </div>
        </div>

        <div className="p-6">
          {status === "connected" && profileName ? (
            /* Connected State */
            <div className="space-y-4">
              {/* Profile Info */}
              <div className="flex items-center gap-4 p-4 bg-[#F8FAFC] rounded-lg">
                <div className="w-12 h-12 bg-[#0077B5] rounded-full flex items-center justify-center">
                  <Linkedin className="h-6 w-6 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[#1E293B]">{profileName}</p>
                  {profileUrl && (
                    <a
                      href={profileUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-[#0077B5] hover:underline flex items-center gap-1"
                    >
                      View Profile
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                  {connectedAt && (
                    <p className="text-[10px] text-[#94A3B8] mt-0.5">
                      Connected on {formatDate(connectedAt)}
                    </p>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={onDisconnect}
                  className="px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:bg-[#F8FAFC] hover:border-[#DC2626] hover:text-[#DC2626] transition-colors"
                >
                  Disconnect
                </button>
                <button
                  type="button"
                  onClick={onConnect}
                  className="px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:bg-[#F8FAFC] hover:border-[#0077B5] hover:text-[#0077B5] transition-colors"
                >
                  Reconnect
                </button>
              </div>
            </div>
          ) : (
            /* Disconnected State */
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-[#F8FAFC] rounded-full flex items-center justify-center mx-auto mb-4">
                <Linkedin className="h-8 w-8 text-[#94A3B8]" />
              </div>
              <p className="text-sm text-[#64748B] mb-4">
                Connect your LinkedIn account to enable automated outreach to prospects.
              </p>
              <button
                type="button"
                onClick={onConnect}
                className="inline-flex items-center gap-2 px-6 py-2.5 bg-[#0077B5] hover:bg-[#005C8F] text-white font-medium rounded-lg transition-colors"
              >
                <Linkedin className="h-5 w-5" />
                Connect LinkedIn
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Security Information */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-[#64748B]" />
            <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              Security Information
            </h3>
          </div>
        </div>
        <div className="p-6">
          <ul className="space-y-3">
            <li className="flex items-start gap-3">
              <div className="mt-0.5">
                <Shield className="h-4 w-4 text-[#10B981]" />
              </div>
              <span className="text-sm text-[#64748B]">
                Credentials encrypted using AES-256 encryption
              </span>
            </li>
            <li className="flex items-start gap-3">
              <div className="mt-0.5">
                <Shield className="h-4 w-4 text-[#10B981]" />
              </div>
              <span className="text-sm text-[#64748B]">
                Password never stored in plain text
              </span>
            </li>
            <li className="flex items-start gap-3">
              <div className="mt-0.5">
                <Shield className="h-4 w-4 text-[#10B981]" />
              </div>
              <span className="text-sm text-[#64748B]">
                Only used for automated outreach sequences
              </span>
            </li>
            <li className="flex items-start gap-3">
              <div className="mt-0.5">
                <Shield className="h-4 w-4 text-[#10B981]" />
              </div>
              <span className="text-sm text-[#64748B]">
                We never post to your LinkedIn feed
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default LinkedInStatusCard;
