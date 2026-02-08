/**
 * ChannelIntegrations.tsx - Channel Integrations Management Component
 * Phase: Operation Modular Cockpit
 * 
 * Features:
 * - Email integration card (status)
 * - LinkedIn card (connection)
 * - SMS card (status)
 * - Voice AI card (status)
 * - Direct Mail card
 * - Each card shows: Connected/Disconnected, last sync, action button
 * - Bloomberg dark mode + glassmorphic styling
 */

"use client";

import { useState, useCallback } from "react";
import {
  Mail,
  Briefcase,
  MessageSquare,
  Phone,
  FileText,
  Check,
  Clock,
  AlertCircle,
  RefreshCw,
  Settings,
  Zap,
  Link2,
  ExternalLink,
} from "lucide-react";

// ============================================
// Types
// ============================================

type IntegrationStatus = "connected" | "pending" | "disconnected" | "error";

interface ChannelIntegration {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  status: IntegrationStatus;
  lastSync?: string;
  colorClass: string;
  bgColorClass: string;
  stats?: {
    label: string;
    value: string | number;
  };
}

// ============================================
// Status Badge Component
// ============================================

function StatusBadge({ status }: { status: IntegrationStatus }) {
  const statusConfig = {
    connected: {
      icon: <Check className="w-3 h-3" />,
      text: "Connected",
      className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    },
    pending: {
      icon: <Clock className="w-3 h-3" />,
      text: "Pending",
      className: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    },
    disconnected: {
      icon: <AlertCircle className="w-3 h-3" />,
      text: "Disconnected",
      className: "bg-[#2A2A3D] text-[#6E6E82] border-[#2A2A3D]",
    },
    error: {
      icon: <AlertCircle className="w-3 h-3" />,
      text: "Error",
      className: "bg-red-500/15 text-red-400 border-red-500/30",
    },
  };

  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full border ${config.className}`}
    >
      {config.icon}
      {config.text}
    </span>
  );
}

// ============================================
// Action Button Component
// ============================================

function ActionButton({
  status,
  onConnect,
  onManage,
  onReconnect,
}: {
  status: IntegrationStatus;
  onConnect: () => void;
  onManage: () => void;
  onReconnect: () => void;
}) {
  if (status === "connected") {
    return (
      <button
        onClick={onManage}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#B4B4C4] bg-[#1A1A28] border border-[#2A2A3D] rounded-lg hover:bg-[#222233] hover:border-[#3A3A4D] transition-all"
      >
        <Settings className="w-4 h-4" />
        Manage
      </button>
    );
  }

  if (status === "error") {
    return (
      <button
        onClick={onReconnect}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-lg hover:bg-amber-500/20 transition-all"
      >
        <RefreshCw className="w-4 h-4" />
        Reconnect
      </button>
    );
  }

  if (status === "pending") {
    return (
      <button
        onClick={onManage}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded-lg hover:bg-amber-500/20 transition-all"
      >
        <Clock className="w-4 h-4" />
        Complete Setup
      </button>
    );
  }

  return (
    <button
      onClick={onConnect}
      className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-purple-500 rounded-lg hover:bg-purple-400 transition-all"
    >
      <Zap className="w-4 h-4" />
      Connect
    </button>
  );
}

// ============================================
// Integration Card Component
// ============================================

function IntegrationCard({
  integration,
  onConnect,
  onManage,
  onReconnect,
}: {
  integration: ChannelIntegration;
  onConnect: (id: string) => void;
  onManage: (id: string) => void;
  onReconnect: (id: string) => void;
}) {
  return (
    <div className="group bg-[#12121D]/60 backdrop-blur-xl border border-[#1E1E2E] rounded-xl overflow-hidden hover:border-[#2A2A3D] transition-all duration-200">
      {/* Card Header */}
      <div className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center ${integration.bgColorClass}`}
            >
              <span className={integration.colorClass}>{integration.icon}</span>
            </div>
            <div>
              <h3 className="font-semibold text-white">{integration.name}</h3>
              <p className="text-xs text-[#6E6E82] mt-0.5">
                {integration.description}
              </p>
            </div>
          </div>
          <StatusBadge status={integration.status} />
        </div>

        {/* Stats / Last Sync */}
        <div className="flex items-center justify-between pt-4 border-t border-[#1E1E2E]">
          <div className="flex items-center gap-4">
            {integration.lastSync && (
              <div className="flex items-center gap-1.5 text-xs text-[#6E6E82]">
                <RefreshCw className="w-3 h-3" />
                Last sync: {integration.lastSync}
              </div>
            )}
            {integration.stats && (
              <div className="text-xs">
                <span className="text-[#6E6E82]">{integration.stats.label}: </span>
                <span className="text-[#B4B4C4] font-medium">
                  {integration.stats.value}
                </span>
              </div>
            )}
            {!integration.lastSync && !integration.stats && (
              <div className="text-xs text-[#6E6E82]">Not configured</div>
            )}
          </div>
          <ActionButton
            status={integration.status}
            onConnect={() => onConnect(integration.id)}
            onManage={() => onManage(integration.id)}
            onReconnect={() => onReconnect(integration.id)}
          />
        </div>
      </div>
    </div>
  );
}

// ============================================
// Initial Data
// ============================================

const initialIntegrations: ChannelIntegration[] = [
  {
    id: "email",
    name: "Email Provider",
    description: "Cold email campaigns and warm-up",
    icon: <Mail className="w-5 h-5" />,
    status: "connected",
    lastSync: "2 min ago",
    colorClass: "text-purple-400",
    bgColorClass: "bg-purple-500/15",
    stats: { label: "Active sequences", value: 12 },
  },
  {
    id: "linkedin",
    name: "LinkedIn",
    description: "Professional network outreach",
    icon: <Briefcase className="w-5 h-5" />,
    status: "connected",
    lastSync: "5 min ago",
    colorClass: "text-blue-400",
    bgColorClass: "bg-blue-500/15",
    stats: { label: "Connections pending", value: 47 },
  },
  {
    id: "sms",
    name: "SMS Provider",
    description: "Text message campaigns",
    icon: <MessageSquare className="w-5 h-5" />,
    status: "connected",
    lastSync: "15 min ago",
    colorClass: "text-teal-400",
    bgColorClass: "bg-teal-500/15",
    stats: { label: "Messages today", value: 234 },
  },
  {
    id: "voice",
    name: "Voice AI",
    description: "AI-powered voice calls",
    icon: <Phone className="w-5 h-5" />,
    status: "pending",
    colorClass: "text-amber-400",
    bgColorClass: "bg-amber-500/15",
  },
  {
    id: "direct-mail",
    name: "Direct Mail",
    description: "Physical mail automation",
    icon: <FileText className="w-5 h-5" />,
    status: "disconnected",
    colorClass: "text-pink-400",
    bgColorClass: "bg-pink-500/15",
  },
];

// ============================================
// Main Component
// ============================================

export interface ChannelIntegrationsProps {
  className?: string;
}

export function ChannelIntegrations({ className = "" }: ChannelIntegrationsProps) {
  const [integrations, setIntegrations] =
    useState<ChannelIntegration[]>(initialIntegrations);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Calculate connection stats
  const connectedCount = integrations.filter(
    (i) => i.status === "connected"
  ).length;
  const totalCount = integrations.length;

  // Handlers
  const handleConnect = useCallback((id: string) => {
    console.log(`Connecting integration: ${id}`);
    // TODO: Open connection modal or OAuth flow
  }, []);

  const handleManage = useCallback((id: string) => {
    console.log(`Managing integration: ${id}`);
    // TODO: Open settings modal for the integration
  }, []);

  const handleReconnect = useCallback((id: string) => {
    console.log(`Reconnecting integration: ${id}`);
    // TODO: Trigger reconnection flow
  }, []);

  const handleRefreshAll = useCallback(async () => {
    setIsRefreshing(true);
    // Simulate refresh
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setIsRefreshing(false);
  }, []);

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-500/15 rounded-xl flex items-center justify-center">
            <Link2 className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              Channel Integrations
            </h2>
            <p className="text-sm text-[#6E6E82]">
              {connectedCount} of {totalCount} channels connected
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefreshAll}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#B4B4C4] bg-[#1A1A28] border border-[#2A2A3D] rounded-lg hover:bg-[#222233] hover:border-[#3A3A4D] transition-all disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`}
            />
            Refresh All
          </button>
          <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-purple-500 rounded-lg hover:bg-purple-400 transition-all">
            <ExternalLink className="w-4 h-4" />
            Integration Docs
          </button>
        </div>
      </div>

      {/* Connection Status Banner */}
      {connectedCount === totalCount && (
        <div className="flex items-center gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
            <Check className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="flex-1">
            <div className="font-medium text-emerald-400">
              All Channels Connected
            </div>
            <div className="text-xs text-emerald-400/70">
              Your omnichannel outreach is fully operational
            </div>
          </div>
        </div>
      )}

      {connectedCount < totalCount && connectedCount > 0 && (
        <div className="flex items-center gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
          <div className="w-10 h-10 bg-amber-500/20 rounded-lg flex items-center justify-center">
            <AlertCircle className="w-5 h-5 text-amber-400" />
          </div>
          <div className="flex-1">
            <div className="font-medium text-amber-400">
              {totalCount - connectedCount} Channel
              {totalCount - connectedCount > 1 ? "s" : ""} Need Attention
            </div>
            <div className="text-xs text-amber-400/70">
              Complete setup to unlock full omnichannel capabilities
            </div>
          </div>
        </div>
      )}

      {/* Integration Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {integrations.map((integration) => (
          <IntegrationCard
            key={integration.id}
            integration={integration}
            onConnect={handleConnect}
            onManage={handleManage}
            onReconnect={handleReconnect}
          />
        ))}
      </div>

      {/* Help Section */}
      <div className="bg-[#12121D]/40 border border-[#1E1E2E] rounded-xl p-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-[#1A1A28] rounded-lg flex items-center justify-center flex-shrink-0">
            <Zap className="w-5 h-5 text-[#6E6E82]" />
          </div>
          <div>
            <h4 className="font-medium text-[#B4B4C4] mb-1">
              Need help connecting?
            </h4>
            <p className="text-sm text-[#6E6E82] leading-relaxed">
              Each channel integration comes with step-by-step setup guides.
              Contact support if you need assistance configuring your
              connections or troubleshooting sync issues.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChannelIntegrations;
