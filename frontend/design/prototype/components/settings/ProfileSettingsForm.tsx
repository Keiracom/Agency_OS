"use client";

import { useState } from "react";
import { Building2, User, Upload, ExternalLink, CreditCard } from "lucide-react";
import { TimezoneSelector } from "./TimezoneSelector";

/**
 * Client profile data
 */
export interface ClientProfile {
  companyName: string;
  companyLogoUrl: string | null;
  contactEmail: string;
  timezone: string;
  tier: "ignition" | "velocity" | "dominance";
  subscriptionStatus: "active" | "trialing" | "past_due" | "cancelled";
  nextBillingDate: string | null;
}

/**
 * ProfileSettingsForm props
 */
export interface ProfileSettingsFormProps {
  /** Initial profile data */
  initialValues?: Partial<ClientProfile>;
  /** Called when form is saved */
  onSave?: (values: Partial<ClientProfile>) => void;
}

/**
 * Get tier badge styling
 */
function getTierBadge(tier: string) {
  const styles: Record<string, { bg: string; text: string }> = {
    ignition: { bg: "bg-[#DBEAFE]", text: "text-[#1D4ED8]" },
    velocity: { bg: "bg-[#FEF3C7]", text: "text-[#B45309]" },
    dominance: { bg: "bg-[#F3E8FF]", text: "text-[#7C3AED]" },
  };
  return styles[tier] || styles.ignition;
}

/**
 * Get subscription status badge
 */
function getStatusBadge(status: string) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    active: { bg: "bg-[#DCFCE7]", text: "text-[#166534]", label: "Active" },
    trialing: { bg: "bg-[#DBEAFE]", text: "text-[#1D4ED8]", label: "Trialing" },
    past_due: { bg: "bg-[#FEE2E2]", text: "text-[#DC2626]", label: "Past Due" },
    cancelled: { bg: "bg-[#F1F5F9]", text: "text-[#64748B]", label: "Cancelled" },
  };
  return styles[status] || styles.active;
}

/**
 * Format date for display
 */
function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-AU", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * ProfileSettingsForm - Form for editing client profile settings
 *
 * Features:
 * - Company name input
 * - Logo upload placeholder
 * - Contact email input
 * - Timezone selector
 * - Billing info display (read-only)
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Primary: #3B82F6
 * - Input background: #F8FAFC
 * - Border: #E2E8F0
 */
export function ProfileSettingsForm({
  initialValues,
  onSave,
}: ProfileSettingsFormProps) {
  const [values, setValues] = useState<ClientProfile>({
    companyName: initialValues?.companyName ?? "Acme Agency",
    companyLogoUrl: initialValues?.companyLogoUrl ?? null,
    contactEmail: initialValues?.contactEmail ?? "john@acmeagency.com",
    timezone: initialValues?.timezone ?? "Australia/Sydney",
    tier: initialValues?.tier ?? "velocity",
    subscriptionStatus: initialValues?.subscriptionStatus ?? "active",
    nextBillingDate: initialValues?.nextBillingDate ?? "2026-02-01",
  });

  const handleSave = () => {
    if (onSave) {
      onSave(values);
    }
  };

  const tierBadge = getTierBadge(values.tier);
  const statusBadge = getStatusBadge(values.subscriptionStatus);

  return (
    <div className="space-y-6">
      {/* Company Information */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-[#64748B]" />
            <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              Company Information
            </h3>
          </div>
        </div>
        <div className="p-6 space-y-6">
          {/* Company Name */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Company Name
            </label>
            <input
              type="text"
              value={values.companyName}
              onChange={(e) => setValues({ ...values, companyName: e.target.value })}
              className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
              placeholder="Your company name"
            />
          </div>

          {/* Logo Upload */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Company Logo
            </label>
            <div className="flex items-center gap-4">
              {/* Logo Preview */}
              <div className="w-16 h-16 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg flex items-center justify-center overflow-hidden">
                {values.companyLogoUrl ? (
                  <img
                    src={values.companyLogoUrl}
                    alt="Company logo"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <Building2 className="h-6 w-6 text-[#94A3B8]" />
                )}
              </div>
              {/* Upload Button */}
              <button
                type="button"
                className="flex items-center gap-2 px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:bg-[#F8FAFC] transition-colors"
              >
                <Upload className="h-4 w-4" />
                Upload New
              </button>
            </div>
            <p className="text-xs text-[#94A3B8] mt-2">
              PNG, JPG up to 2MB. Recommended size: 200x200px
            </p>
          </div>
        </div>
      </div>

      {/* Contact Information */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-2">
            <User className="h-5 w-5 text-[#64748B]" />
            <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              Contact Information
            </h3>
          </div>
        </div>
        <div className="p-6 space-y-6">
          {/* Contact Email */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Contact Email
            </label>
            <input
              type="email"
              value={values.contactEmail}
              onChange={(e) => setValues({ ...values, contactEmail: e.target.value })}
              className="w-full px-4 py-2.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
              placeholder="contact@company.com"
            />
          </div>

          {/* Timezone */}
          <div>
            <label className="block text-sm font-medium text-[#1E293B] mb-2">
              Timezone
            </label>
            <TimezoneSelector
              value={values.timezone}
              onChange={(tz) => setValues({ ...values, timezone: tz })}
            />
            <p className="text-xs text-[#94A3B8] mt-2">
              Used for scheduling outreach and daily digest delivery
            </p>
          </div>
        </div>
      </div>

      {/* Billing Information (Read-only) */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-[#64748B]" />
            <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              Billing
            </h3>
          </div>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-2 gap-6">
            {/* Current Plan */}
            <div>
              <p className="text-xs text-[#64748B] mb-1">Current Plan</p>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${tierBadge.bg} ${tierBadge.text}`}
                >
                  {values.tier}
                </span>
              </div>
            </div>

            {/* Status */}
            <div>
              <p className="text-xs text-[#64748B] mb-1">Status</p>
              <span
                className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${statusBadge.bg} ${statusBadge.text}`}
              >
                {statusBadge.label}
              </span>
            </div>

            {/* Next Billing */}
            {values.nextBillingDate && (
              <div className="col-span-2">
                <p className="text-xs text-[#64748B] mb-1">Next Billing Date</p>
                <p className="text-sm font-medium text-[#1E293B]">
                  {formatDate(values.nextBillingDate)}
                </p>
              </div>
            )}
          </div>

          {/* Manage Billing Button */}
          <div className="mt-6 pt-4 border-t border-[#E2E8F0]">
            <button
              type="button"
              className="flex items-center gap-2 px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm font-medium text-[#64748B] hover:bg-[#F8FAFC] transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
              Manage Billing
            </button>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="px-6 py-2.5 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25"
        >
          Save Changes
        </button>
      </div>
    </div>
  );
}

export default ProfileSettingsForm;
