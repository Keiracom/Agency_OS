/**
 * SettingsPanel.tsx - Settings Page Component
 * Phase: Operation Modular Cockpit
 * 
 * Ported from settings-v2.html
 * Features:
 * - Tabbed navigation (Profile, ICP, Integrations, Notifications)
 * - ICP configuration with tag inputs
 * - Integrations grid with connection status
 * - Bloomberg dark mode + glassmorphic styling
 */

"use client";

import { useState, useCallback, type KeyboardEvent } from "react";
import {
  User,
  Target,
  Link2,
  Bell,
  Camera,
  Key,
  AlertTriangle,
  Download,
  Trash2,
  Plus,
  X,
  Mail,
  Briefcase,
  MessageSquare,
  Phone,
  Calendar,
  Cloud,
  Check,
  Clock,
  Minus,
} from "lucide-react";

// ============================================
// Types
// ============================================

type SettingsTab = "profile" | "icp" | "integrations" | "notifications";

type IntegrationStatus = "connected" | "pending" | "disconnected";

interface Integration {
  id: string;
  name: string;
  icon: React.ReactNode;
  status: IntegrationStatus;
  colorClass: string;
}

interface NotificationSetting {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
}

interface ICPTag {
  id: string;
  value: string;
}

interface ProfileFormData {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  company: string;
  timezone: string;
}

interface ICPFormData {
  industries: ICPTag[];
  titles: ICPTag[];
  companySize: string;
  regions: ICPTag[];
  excludedDomains: ICPTag[];
}

// ============================================
// Constants
// ============================================

const TABS: { key: SettingsTab; label: string; icon: React.ReactNode }[] = [
  { key: "profile", label: "Profile", icon: <User className="w-4 h-4" /> },
  { key: "icp", label: "ICP", icon: <Target className="w-4 h-4" /> },
  { key: "integrations", label: "Integrations", icon: <Link2 className="w-4 h-4" /> },
  { key: "notifications", label: "Notifications", icon: <Bell className="w-4 h-4" /> },
];

const TIMEZONES = [
  "Australia/Sydney (AEST)",
  "Australia/Melbourne",
  "Australia/Brisbane",
  "America/New_York",
  "America/Los_Angeles",
  "Europe/London",
  "Asia/Singapore",
];

const COMPANY_SIZES = [
  "1-10 employees",
  "11-50 employees",
  "51-200 employees",
  "201-500 employees",
  "501-1000 employees",
  "1000+ employees",
];

// ============================================
// Initial Data
// ============================================

const initialIntegrations: Integration[] = [
  {
    id: "email",
    name: "Email",
    icon: <Mail className="w-5 h-5" />,
    status: "connected",
    colorClass: "bg-amber/15 text-amber",
  },
  {
    id: "linkedin",
    name: "LinkedIn",
    icon: <Briefcase className="w-5 h-5" />,
    status: "connected",
    colorClass: "bg-bg-elevated/15 text-text-secondary",
  },
  {
    id: "sms",
    name: "SMS",
    icon: <MessageSquare className="w-5 h-5" />,
    status: "connected",
    colorClass: "bg-amber-glow text-amber",
  },
  {
    id: "voice",
    name: "Voice",
    icon: <Phone className="w-5 h-5" />,
    status: "pending",
    colorClass: "bg-amber-500/15 text-amber-400",
  },
  {
    id: "calendar",
    name: "Calendar",
    icon: <Calendar className="w-5 h-5" />,
    status: "connected",
    colorClass: "bg-amber-glow text-amber-light",
  },
  {
    id: "crm",
    name: "CRM",
    icon: <Cloud className="w-5 h-5" />,
    status: "disconnected",
    colorClass: "bg-indigo-500/15 text-indigo-400",
  },
];

const initialNotifications: NotificationSetting[] = [
  { id: "email_notif", label: "Email Notifications", description: "Receive email alerts for important activity", enabled: true },
  { id: "reply_alerts", label: "New Reply Alerts", description: "Get notified when leads respond", enabled: true },
  { id: "meeting_booked", label: "Meeting Booked", description: "Get notified when a meeting is scheduled", enabled: true },
  { id: "hot_lead", label: "Hot Lead Alerts", description: "Instant notification when a lead becomes hot", enabled: true },
  { id: "weekly_digest", label: "Weekly Digest", description: "Summary of your week's performance", enabled: false },
  { id: "marketing", label: "Marketing Updates", description: "News about new features and updates", enabled: false },
];

// ============================================
// Sub-Components
// ============================================

/** Tag Input Component for ICP fields */
function TagInput({
  tags,
  onAdd,
  onRemove,
  placeholder,
}: {
  tags: ICPTag[];
  onAdd: (value: string) => void;
  onRemove: (id: string) => void;
  placeholder: string;
}) {
  const [inputValue, setInputValue] = useState("");

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && inputValue.trim()) {
      e.preventDefault();
      onAdd(inputValue.trim());
      setInputValue("");
    } else if (e.key === "Backspace" && !inputValue && tags.length > 0) {
      onRemove(tags[tags.length - 1].id);
    }
  };

  return (
    <div className="min-h-[48px] p-2 bg-bg-elevated border border-default rounded-lg flex flex-wrap gap-2 focus-within:border-amber focus-within:ring-2 focus-within:ring-amber/20 transition-all">
      {tags.map((tag) => (
        <span
          key={tag.id}
          className="inline-flex items-center gap-1 px-3 py-1 bg-amber/15 text-amber text-sm rounded-full"
        >
          {tag.value}
          <button
            onClick={() => onRemove(tag.id)}
            className="hover:text-amber-light transition-colors"
          >
            <X className="w-3 h-3" />
          </button>
        </span>
      ))}
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={tags.length === 0 ? placeholder : ""}
        className="flex-1 min-w-[120px] bg-transparent text-text-primary text-sm outline-none placeholder:text-text-muted"
      />
    </div>
  );
}

/** Toggle Switch Component */
function Toggle({
  enabled,
  onToggle,
}: {
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className={`w-12 h-6 rounded-full relative transition-all duration-200 ${
        enabled
          ? "bg-amber"
          : "bg-bg-elevated border border-default"
      }`}
    >
      <span
        className={`absolute top-0.5 w-5 h-5 rounded-full bg-bg-surface shadow-md transition-all duration-200 ${
          enabled ? "left-6" : "left-0.5"
        }`}
      />
    </button>
  );
}

/** Status Badge Component */
function StatusBadge({ status }: { status: IntegrationStatus }) {
  const config = {
    connected: { color: "text-amber", bg: "bg-amber", label: "Connected" },
    pending: { color: "text-amber-400", bg: "bg-amber-400", label: "Pending Setup" },
    disconnected: { color: "text-text-muted", bg: "bg-[#6E6E82]", label: "Not Connected" },
  };

  const { color, bg, label } = config[status];

  return (
    <div className={`flex items-center gap-1.5 text-xs ${color}`}>
      <span className={`w-2 h-2 rounded-full ${bg}`} />
      {label}
    </div>
  );
}

/** Integration Action Button */
function IntegrationButton({ status }: { status: IntegrationStatus }) {
  const config = {
    connected: {
      label: "Disconnect",
      className: "bg-amber-glow text-amber border-amber/30 hover:bg-amber/20",
    },
    pending: {
      label: "Complete Setup",
      className: "bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25",
    },
    disconnected: {
      label: "Connect",
      className: "bg-amber/15 text-amber border-amber/30 hover:bg-amber/25",
    },
  };

  const { label, className } = config[status];

  return (
    <button
      className={`px-4 py-2 text-xs font-medium rounded-md border transition-all ${className}`}
    >
      {label}
    </button>
  );
}

// ============================================
// Main Component
// ============================================

export function SettingsPanel() {
  // ----------------------------------------
  // State
  // ----------------------------------------
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  
  // Profile State
  const [profile, setProfile] = useState<ProfileFormData>({
    firstName: "Dave",
    lastName: "K.",
    email: "dave@example.com",
    phone: "+61 4XX XXX XXX",
    company: "Growth Agency",
    timezone: "Australia/Sydney (AEST)",
  });

  // ICP State
  const [icp, setIcp] = useState<ICPFormData>({
    industries: [
      { id: "1", value: "SaaS" },
      { id: "2", value: "FinTech" },
      { id: "3", value: "Healthcare" },
    ],
    titles: [
      { id: "1", value: "CEO" },
      { id: "2", value: "CTO" },
      { id: "3", value: "VP of Sales" },
    ],
    companySize: "51-200 employees",
    regions: [
      { id: "1", value: "Australia" },
      { id: "2", value: "New Zealand" },
      { id: "3", value: "Singapore" },
    ],
    excludedDomains: [
      { id: "1", value: "competitor.com" },
    ],
  });

  // Integrations State
  const [integrations, setIntegrations] = useState<Integration[]>(initialIntegrations);

  // Notifications State
  const [notifications, setNotifications] = useState<NotificationSetting[]>(initialNotifications);

  // ----------------------------------------
  // Handlers
  // ----------------------------------------
  const handleProfileChange = (field: keyof ProfileFormData, value: string) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
  };

  const addTag = useCallback((field: keyof ICPFormData, value: string) => {
    if (field === "companySize") return;
    setIcp((prev) => ({
      ...prev,
      [field]: [...(prev[field] as ICPTag[]), { id: Date.now().toString(), value }],
    }));
  }, []);

  const removeTag = useCallback((field: keyof ICPFormData, id: string) => {
    if (field === "companySize") return;
    setIcp((prev) => ({
      ...prev,
      [field]: (prev[field] as ICPTag[]).filter((tag) => tag.id !== id),
    }));
  }, []);

  const toggleNotification = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, enabled: !n.enabled } : n))
    );
  };

  // LinkedIn-specific status for requirement
  const linkedInStatus = integrations.find((i) => i.id === "linkedin")?.status ?? "disconnected";

  // ----------------------------------------
  // Render
  // ----------------------------------------
  return (
    <div className="min-h-screen bg-bg-void text-text-primary">
      {/* Header */}
      <header className="bg-bg-base/80 backdrop-blur-xl border-b border-default px-8 py-5">
        <h1 className="text-xl font-bold">Settings</h1>
        <p className="text-sm text-text-muted mt-1">
          Manage your account, ICP, and integrations
        </p>
      </header>

      <div className="max-w-4xl mx-auto px-8 py-8">
        {/* Tabs */}
        <div className="inline-flex gap-1 p-1.5 bg-bg-base/80 backdrop-blur-xl rounded-xl border border-default mb-8">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg transition-all ${
                activeTab === tab.key
                  ? "bg-amber/15 text-amber"
                  : "text-text-muted hover:text-text-secondary hover:bg-bg-elevated"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === "profile" && (
          <div className="space-y-6">
            {/* Profile Card */}
            <div className="bg-bg-base/60 backdrop-blur-xl border border-default rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-default flex items-center gap-3">
                <User className="w-5 h-5 text-amber" />
                <span className="font-semibold">Profile Information</span>
              </div>
              <div className="p-6">
                {/* Avatar Section */}
                <div className="flex items-center gap-3 md:gap-6 mb-8">
                  <div className="relative">
                    <div className="w-20 h-20 rounded-full bg-gradient-to-br from-amber to-amber flex items-center justify-center text-2xl font-bold ring-4 ring-[#12121D] ring-offset-2 ring-offset-amber/20">
                      {profile.firstName[0]}{profile.lastName[0]}
                    </div>
                    <button className="absolute -bottom-1 -right-1 w-8 h-8 bg-amber rounded-full flex items-center justify-center ring-4 ring-[#12121D] hover:bg-amber transition-colors">
                      <Camera className="w-4 h-4" />
                    </button>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold">{profile.firstName} {profile.lastName}</h3>
                    <p className="text-sm text-text-secondary">{profile.email}</p>
                    <span className="inline-flex items-center gap-1.5 mt-2 px-3 py-1 bg-amber/15 text-amber text-xs font-medium rounded-full">
                      <Check className="w-3 h-3" />
                      Growth Plan
                    </span>
                  </div>
                </div>

                {/* Form Grid */}
                <div className="grid grid-cols-2 gap-5">
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">First Name</label>
                    <input
                      type="text"
                      value={profile.firstName}
                      onChange={(e) => handleProfileChange("firstName", e.target.value)}
                      className="w-full px-4 py-3 bg-bg-elevated border border-default rounded-lg text-text-primary text-sm focus:border-amber focus:ring-2 focus:ring-amber/20 outline-none transition-all"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">Last Name</label>
                    <input
                      type="text"
                      value={profile.lastName}
                      onChange={(e) => handleProfileChange("lastName", e.target.value)}
                      className="w-full px-4 py-3 bg-bg-elevated border border-default rounded-lg text-text-primary text-sm focus:border-amber focus:ring-2 focus:ring-amber/20 outline-none transition-all"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">Email Address</label>
                    <input
                      type="email"
                      value={profile.email}
                      onChange={(e) => handleProfileChange("email", e.target.value)}
                      className="w-full px-4 py-3 bg-bg-elevated border border-default rounded-lg text-text-primary text-sm focus:border-amber focus:ring-2 focus:ring-amber/20 outline-none transition-all"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">Phone Number</label>
                    <input
                      type="tel"
                      value={profile.phone}
                      onChange={(e) => handleProfileChange("phone", e.target.value)}
                      className="w-full px-4 py-3 bg-bg-elevated border border-default rounded-lg text-text-primary text-sm focus:border-amber focus:ring-2 focus:ring-amber/20 outline-none transition-all"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">Company</label>
                    <input
                      type="text"
                      value={profile.company}
                      onChange={(e) => handleProfileChange("company", e.target.value)}
                      className="w-full px-4 py-3 bg-bg-elevated border border-default rounded-lg text-text-primary text-sm focus:border-amber focus:ring-2 focus:ring-amber/20 outline-none transition-all"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm text-text-secondary">Timezone</label>
                    <select
                      value={profile.timezone}
                      onChange={(e) => handleProfileChange("timezone", e.target.value)}
                      className="w-full px-4 py-3 bg-bg-elevated border border-default rounded-lg text-text-primary text-sm focus:border-amber focus:ring-2 focus:ring-amber/20 outline-none transition-all cursor-pointer"
                    >
                      {TIMEZONES.map((tz) => (
                        <option key={tz} value={tz}>{tz}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 mt-6 pt-6 border-t border-default">
                  <button className="px-5 py-2.5 text-sm font-medium text-text-secondary border border-default rounded-lg hover:bg-bg-elevated transition-all">
                    Cancel
                  </button>
                  <button className="px-5 py-2.5 text-sm font-medium bg-amber text-text-primary rounded-lg hover:bg-amber transition-all">
                    Save Changes
                  </button>
                </div>
              </div>
            </div>

            {/* API Keys Card */}
            <div className="bg-bg-base/60 backdrop-blur-xl border border-default rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-default flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Key className="w-5 h-5 text-amber" />
                  <span className="font-semibold">API Keys</span>
                </div>
                <button className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-text-secondary border border-default rounded-lg hover:bg-bg-elevated transition-all">
                  <Plus className="w-3 h-3" />
                  Generate New Key
                </button>
              </div>
              <div className="p-6 space-y-3">
                {[
                  { name: "Production API Key", value: "aos_live_••••••••••••••••" },
                  { name: "Test API Key", value: "aos_test_••••••••••••••••" },
                ].map((key) => (
                  <div
                    key={key.name}
                    className="flex items-center justify-between p-4 bg-bg-elevated rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-amber/15 rounded-lg flex items-center justify-center">
                        <Key className="w-5 h-5 text-amber" />
                      </div>
                      <div>
                        <div className="font-medium text-sm">{key.name}</div>
                        <div className="text-xs text-text-muted font-mono mt-0.5">{key.value}</div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button className="px-3 py-1.5 text-xs font-medium text-text-secondary bg-bg-elevated rounded-md hover:bg-[#2A2A3D] transition-all">
                        Copy
                      </button>
                      <button className="px-3 py-1.5 text-xs font-medium text-text-secondary bg-bg-elevated rounded-md hover:bg-[#2A2A3D] transition-all">
                        Regenerate
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Danger Zone */}
            <div className="bg-amber/5 border border-amber/20 rounded-xl p-6">
              <h3 className="flex items-center gap-2 text-amber font-semibold mb-4">
                <AlertTriangle className="w-5 h-5" />
                Danger Zone
              </h3>
              <div className="flex gap-3">
                <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium bg-amber-glow text-amber border border-amber/30 rounded-lg hover:bg-amber/20 transition-all">
                  <Download className="w-4 h-4" />
                  Export All Data
                </button>
                <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium bg-amber-glow text-amber border border-amber/30 rounded-lg hover:bg-amber/20 transition-all">
                  <Trash2 className="w-4 h-4" />
                  Delete Account
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ICP Tab */}
        {activeTab === "icp" && (
          <div className="space-y-6">
            <div className="bg-bg-base/60 backdrop-blur-xl border border-default rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-default flex items-center gap-3">
                <Target className="w-5 h-5 text-amber" />
                <span className="font-semibold">Ideal Customer Profile</span>
              </div>
              <div className="p-6 space-y-6">
                {/* Industries */}
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Target Industries</label>
                  <TagInput
                    tags={icp.industries}
                    onAdd={(value) => addTag("industries", value)}
                    onRemove={(id) => removeTag("industries", id)}
                    placeholder="Add industry and press Enter..."
                  />
                </div>

                {/* Job Titles */}
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Target Job Titles</label>
                  <TagInput
                    tags={icp.titles}
                    onAdd={(value) => addTag("titles", value)}
                    onRemove={(id) => removeTag("titles", id)}
                    placeholder="Add job title and press Enter..."
                  />
                </div>

                {/* Company Size */}
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Company Size</label>
                  <select
                    value={icp.companySize}
                    onChange={(e) => setIcp((prev) => ({ ...prev, companySize: e.target.value }))}
                    className="w-full px-4 py-3 bg-bg-elevated border border-default rounded-lg text-text-primary text-sm focus:border-amber focus:ring-2 focus:ring-amber/20 outline-none transition-all cursor-pointer"
                  >
                    {COMPANY_SIZES.map((size) => (
                      <option key={size} value={size}>{size}</option>
                    ))}
                  </select>
                </div>

                {/* Regions */}
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Target Regions</label>
                  <TagInput
                    tags={icp.regions}
                    onAdd={(value) => addTag("regions", value)}
                    onRemove={(id) => removeTag("regions", id)}
                    placeholder="Add region and press Enter..."
                  />
                </div>

                {/* Excluded Domains */}
                <div className="space-y-2">
                  <label className="text-sm text-text-secondary">Excluded Domains</label>
                  <TagInput
                    tags={icp.excludedDomains}
                    onAdd={(value) => addTag("excludedDomains", value)}
                    onRemove={(id) => removeTag("excludedDomains", id)}
                    placeholder="Add domain to exclude..."
                  />
                  <p className="text-xs text-text-muted">
                    Leads from these domains will be automatically excluded
                  </p>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-6 border-t border-default">
                  <button className="px-5 py-2.5 text-sm font-medium text-text-secondary border border-default rounded-lg hover:bg-bg-elevated transition-all">
                    Reset to Defaults
                  </button>
                  <button className="px-5 py-2.5 text-sm font-medium bg-amber text-text-primary rounded-lg hover:bg-amber transition-all">
                    Save ICP Settings
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Integrations Tab */}
        {activeTab === "integrations" && (
          <div className="space-y-6">
            <div className="bg-bg-base/60 backdrop-blur-xl border border-default rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-default flex items-center gap-3">
                <Link2 className="w-5 h-5 text-amber" />
                <span className="font-semibold">Connected Services</span>
              </div>
              <div className="p-6">
                {/* LinkedIn Status Highlight (per requirement) */}
                {linkedInStatus === "connected" && (
                  <div className="mb-6 p-4 bg-bg-elevated/10 border border-default/20 rounded-lg flex items-center gap-3">
                    <div className="w-10 h-10 bg-bg-elevated/20 rounded-lg flex items-center justify-center">
                      <Briefcase className="w-5 h-5 text-text-secondary" />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-text-secondary">LinkedIn Connected</div>
                      <div className="text-xs text-text-secondary/70">
                        Automation is active • Last sync 2 minutes ago
                      </div>
                    </div>
                    <Check className="w-5 h-5 text-text-secondary" />
                  </div>
                )}

                {/* Integrations Grid */}
                <div className="grid grid-cols-2 gap-4">
                  {integrations.map((integration) => (
                    <div
                      key={integration.id}
                      className="flex items-center justify-between p-5 bg-bg-elevated border border-default rounded-xl hover:border-default transition-all"
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${integration.colorClass}`}>
                          {integration.icon}
                        </div>
                        <div>
                          <div className="font-semibold text-sm">{integration.name}</div>
                          <StatusBadge status={integration.status} />
                        </div>
                      </div>
                      <IntegrationButton status={integration.status} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === "notifications" && (
          <div className="space-y-6">
            <div className="bg-bg-base/60 backdrop-blur-xl border border-default rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-default flex items-center gap-3">
                <Bell className="w-5 h-5 text-amber" />
                <span className="font-semibold">Notification Preferences</span>
              </div>
              <div className="p-6 space-y-4">
                {notifications.map((notif) => (
                  <div
                    key={notif.id}
                    className="flex items-center justify-between p-4 bg-bg-elevated rounded-xl"
                  >
                    <div>
                      <div className="font-medium text-sm">{notif.label}</div>
                      <div className="text-xs text-text-muted mt-1">{notif.description}</div>
                    </div>
                    <Toggle
                      enabled={notif.enabled}
                      onToggle={() => toggleNotification(notif.id)}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SettingsPanel;
