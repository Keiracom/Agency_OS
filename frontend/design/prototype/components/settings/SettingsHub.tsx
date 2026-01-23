"use client";

import { useState } from "react";
import {
  Target,
  Building2,
  Shield,
  Trash2,
  ChevronRight,
  Zap,
  Plane,
  Users,
} from "lucide-react";
import { DashboardShell } from "../layout/DashboardShell";
import { EmergencyPauseButton } from "./EmergencyPauseButton";
import { IntegrationStatusCard, IntegrationStatus } from "./IntegrationStatusCard";

/**
 * Permission mode type
 */
type PermissionMode = "autopilot" | "co_pilot" | "manual";

/**
 * Integration data
 */
interface Integration {
  name: string;
  description: string;
  status: IntegrationStatus;
  connectedAt: string | null;
  isManaged: boolean;
}

/**
 * Demo data for integrations
 */
const DEMO_INTEGRATIONS: Integration[] = [
  {
    name: "Apollo",
    description: "Lead enrichment and contact data",
    status: "connected",
    connectedAt: "2026-01-10T09:00:00Z",
    isManaged: true,
  },
  {
    name: "LinkedIn",
    description: "Automated connection requests and messaging",
    status: "connected",
    connectedAt: "2026-01-15T14:30:00Z",
    isManaged: false,
  },
  {
    name: "Salesforge",
    description: "Email sending and deliverability",
    status: "connected",
    connectedAt: "2026-01-10T09:00:00Z",
    isManaged: true,
  },
  {
    name: "Twilio",
    description: "SMS and voice calling",
    status: "not_connected",
    connectedAt: null,
    isManaged: true,
  },
];

/**
 * Permission mode card
 */
function PermissionModeCard({
  mode,
  title,
  description,
  icon: Icon,
  isSelected,
  onClick,
}: {
  mode: PermissionMode;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 p-4 rounded-lg border-2 text-left transition-all ${
        isSelected
          ? "border-[#3B82F6] bg-[#EFF6FF]"
          : "border-[#E2E8F0] bg-white hover:border-[#94A3B8]"
      }`}
    >
      <div className="flex items-center gap-3 mb-2">
        <div
          className={`p-2 rounded-lg ${
            isSelected ? "bg-[#3B82F6]" : "bg-[#F1F5F9]"
          }`}
        >
          <Icon
            className={`h-4 w-4 ${isSelected ? "text-white" : "text-[#64748B]"}`}
          />
        </div>
        <span
          className={`text-sm font-semibold ${
            isSelected ? "text-[#1D4ED8]" : "text-[#1E293B]"
          }`}
        >
          {title}
        </span>
      </div>
      <p className="text-xs text-[#64748B]">{description}</p>
    </button>
  );
}

/**
 * SettingsHub - Main settings page with navigation to subsections
 *
 * Features:
 * - ICP link card
 * - Organization name and tier display
 * - Permission mode selector
 * - Emergency pause controls
 * - Integrations list
 * - Danger zone (delete organization)
 *
 * Design tokens from DESIGN_SYSTEM.md applied throughout
 */
export function SettingsHub() {
  const [isPaused, setIsPaused] = useState(false);
  const [pausedAt, setPausedAt] = useState<string | null>(null);
  const [permissionMode, setPermissionMode] = useState<PermissionMode>("co_pilot");
  const [orgName, setOrgName] = useState("Acme Agency");

  const handlePause = () => {
    setIsPaused(true);
    setPausedAt(new Date().toISOString());
  };

  const handleResume = () => {
    setIsPaused(false);
    setPausedAt(null);
  };

  return (
    <DashboardShell title="Settings" activePath="/settings">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* ICP Link Card */}
        <button
          type="button"
          className="w-full bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-6 text-left hover:border-[#3B82F6] hover:shadow-md transition-all group"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-[#EFF6FF] rounded-lg group-hover:bg-[#3B82F6] transition-colors">
                <Target className="h-6 w-6 text-[#3B82F6] group-hover:text-white transition-colors" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-[#1E293B]">
                  Ideal Customer Profile
                </h2>
                <p className="text-sm text-[#64748B]">
                  Define your target audience for all campaigns
                </p>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-[#94A3B8] group-hover:text-[#3B82F6] transition-colors" />
          </div>
        </button>

        {/* Organization Card */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E2E8F0]">
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-[#64748B]" />
              <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
                Organization
              </h2>
            </div>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-2 gap-6">
              {/* Organization Name */}
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Organization Name
                </label>
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                />
              </div>
              {/* Subscription Tier */}
              <div>
                <label className="block text-sm font-medium text-[#1E293B] mb-2">
                  Subscription Tier
                </label>
                <div className="flex items-center gap-3">
                  <span className="px-3 py-2 bg-[#FEF3C7] text-[#B45309] text-sm font-semibold rounded-lg">
                    Velocity
                  </span>
                  <button
                    type="button"
                    className="text-sm font-medium text-[#3B82F6] hover:text-[#2563EB]"
                  >
                    Upgrade
                  </button>
                </div>
              </div>
            </div>
            <div className="mt-6">
              <button className="px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors">
                Save Changes
              </button>
            </div>
          </div>
        </div>

        {/* Permission Mode Card */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E2E8F0]">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-[#64748B]" />
              <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
                Default Permission Mode
              </h2>
            </div>
          </div>
          <div className="p-6">
            <p className="text-sm text-[#64748B] mb-4">
              Choose how much control you want over outreach activities
            </p>
            <div className="flex gap-4">
              <PermissionModeCard
                mode="autopilot"
                title="Autopilot"
                description="Fully automated outreach. We handle everything."
                icon={Zap}
                isSelected={permissionMode === "autopilot"}
                onClick={() => setPermissionMode("autopilot")}
              />
              <PermissionModeCard
                mode="co_pilot"
                title="Co-Pilot"
                description="Review hot leads and meetings before action."
                icon={Plane}
                isSelected={permissionMode === "co_pilot"}
                onClick={() => setPermissionMode("co_pilot")}
              />
              <PermissionModeCard
                mode="manual"
                title="Manual"
                description="Approve all outreach before it's sent."
                icon={Users}
                isSelected={permissionMode === "manual"}
                onClick={() => setPermissionMode("manual")}
              />
            </div>
          </div>
        </div>

        {/* Emergency Pause */}
        <EmergencyPauseButton
          isPaused={isPaused}
          pausedAt={pausedAt}
          onPause={handlePause}
          onResume={handleResume}
        />

        {/* Integrations Card */}
        <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E2E8F0]">
            <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              Integrations
            </h2>
          </div>
          <div className="px-6">
            {DEMO_INTEGRATIONS.map((integration) => (
              <IntegrationStatusCard
                key={integration.name}
                name={integration.name}
                description={integration.description}
                status={integration.status}
                connectedAt={integration.connectedAt}
                isManaged={integration.isManaged}
              />
            ))}
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-xl border border-[#EF4444] shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-[#FEE2E2] bg-[#FEF2F2]">
            <h2 className="text-sm font-semibold text-[#DC2626] uppercase tracking-wider">
              Danger Zone
            </h2>
          </div>
          <div className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-[#1E293B]">
                  Delete Organization
                </h3>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Permanently delete your organization and all associated data.
                  This action cannot be undone.
                </p>
              </div>
              <button
                type="button"
                className="flex items-center gap-2 px-4 py-2 bg-[#EF4444] hover:bg-[#DC2626] text-white text-sm font-medium rounded-lg transition-colors"
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}

export default SettingsHub;
