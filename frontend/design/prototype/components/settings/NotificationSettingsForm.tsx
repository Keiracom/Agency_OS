"use client";

import { useState } from "react";
import { Mail, Bell, Activity, Clock } from "lucide-react";

/**
 * Notification preferences interface
 */
export interface NotificationPreferences {
  dailyDigestEnabled: boolean;
  dailyDigestTime: string;
  meetingAlertsEnabled: boolean;
  replyAlertsEnabled: boolean;
  replyAlertTiers: {
    hot: boolean;
    warm: boolean;
    cool: boolean;
    cold: boolean;
  };
  activityFeedEnabled: boolean;
}

/**
 * NotificationSettingsForm props
 */
export interface NotificationSettingsFormProps {
  /** Initial values (optional, uses defaults if not provided) */
  initialValues?: Partial<NotificationPreferences>;
  /** Called when form is saved */
  onSave?: (values: NotificationPreferences) => void;
}

/**
 * Toggle switch component
 */
function Toggle({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!enabled)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        enabled ? "bg-[#3B82F6]" : "bg-[#E2E8F0]"
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
          enabled ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}

/**
 * Checkbox component
 */
function Checkbox({
  checked,
  onChange,
  label,
  color,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  color: string;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <div
        className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
          checked ? `${color} border-transparent` : "bg-white border-[#D1D5DB]"
        }`}
      >
        {checked && (
          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 12 12">
            <path d="M10.28 2.28a.75.75 0 0 1 0 1.06l-5.5 5.5a.75.75 0 0 1-1.06 0l-2.5-2.5a.75.75 0 1 1 1.06-1.06L4.5 7.22l4.97-4.94a.75.75 0 0 1 1.06 0z" />
          </svg>
        )}
      </div>
      <span className="text-sm text-[#1E293B]">{label}</span>
    </label>
  );
}

/**
 * Time options for daily digest
 */
const TIME_OPTIONS = [
  "06:00",
  "07:00",
  "08:00",
  "09:00",
  "10:00",
  "11:00",
  "12:00",
];

/**
 * NotificationSettingsForm - Form for managing notification preferences
 *
 * Features:
 * - Toggle switches for each setting
 * - Daily digest with time picker
 * - Meeting alerts toggle
 * - Reply alerts with tier checkboxes
 * - Activity feed toggle
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Primary: #3B82F6
 * - Hot tier: #EF4444
 * - Warm tier: #F97316
 * - Cool tier: #3B82F6
 * - Cold tier: #6B7280
 */
export function NotificationSettingsForm({
  initialValues,
  onSave,
}: NotificationSettingsFormProps) {
  const [values, setValues] = useState<NotificationPreferences>({
    dailyDigestEnabled: initialValues?.dailyDigestEnabled ?? true,
    dailyDigestTime: initialValues?.dailyDigestTime ?? "09:00",
    meetingAlertsEnabled: initialValues?.meetingAlertsEnabled ?? true,
    replyAlertsEnabled: initialValues?.replyAlertsEnabled ?? true,
    replyAlertTiers: {
      hot: initialValues?.replyAlertTiers?.hot ?? true,
      warm: initialValues?.replyAlertTiers?.warm ?? true,
      cool: initialValues?.replyAlertTiers?.cool ?? false,
      cold: initialValues?.replyAlertTiers?.cold ?? false,
    },
    activityFeedEnabled: initialValues?.activityFeedEnabled ?? true,
  });

  const handleSave = () => {
    if (onSave) {
      onSave(values);
    }
  };

  return (
    <div className="space-y-6">
      {/* Daily Digest Section */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-[#64748B]" />
            <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              Daily Digest
            </h3>
          </div>
        </div>
        <div className="p-6 space-y-4">
          {/* Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[#1E293B]">
                Send daily summary email
              </p>
              <p className="text-xs text-[#64748B] mt-0.5">
                Receive a daily overview of your outreach performance
              </p>
            </div>
            <Toggle
              enabled={values.dailyDigestEnabled}
              onChange={(v) => setValues({ ...values, dailyDigestEnabled: v })}
            />
          </div>

          {/* Time Picker - only show when enabled */}
          {values.dailyDigestEnabled && (
            <div className="pt-4 border-t border-[#E2E8F0]">
              <label className="block text-sm font-medium text-[#1E293B] mb-2">
                Delivery Time
              </label>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-[#64748B]" />
                <select
                  value={values.dailyDigestTime}
                  onChange={(e) =>
                    setValues({ ...values, dailyDigestTime: e.target.value })
                  }
                  className="px-3 py-2 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent"
                >
                  {TIME_OPTIONS.map((time) => (
                    <option key={time} value={time}>
                      {time.replace(":00", ":00 AM")}
                    </option>
                  ))}
                </select>
                <span className="text-xs text-[#94A3B8]">(Your timezone)</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Real-time Alerts Section */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-[#64748B]" />
            <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              Real-time Alerts
            </h3>
          </div>
        </div>
        <div className="p-6 space-y-6">
          {/* Meeting Alerts */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[#1E293B]">
                New meeting booked
              </p>
              <p className="text-xs text-[#64748B] mt-0.5">
                Get notified when a prospect books a meeting
              </p>
            </div>
            <Toggle
              enabled={values.meetingAlertsEnabled}
              onChange={(v) => setValues({ ...values, meetingAlertsEnabled: v })}
            />
          </div>

          {/* Reply Alerts */}
          <div className="pt-4 border-t border-[#E2E8F0]">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-medium text-[#1E293B]">
                  Lead replied
                </p>
                <p className="text-xs text-[#64748B] mt-0.5">
                  Get notified when leads respond to outreach
                </p>
              </div>
              <Toggle
                enabled={values.replyAlertsEnabled}
                onChange={(v) => setValues({ ...values, replyAlertsEnabled: v })}
              />
            </div>

            {/* Tier Selection - only show when enabled */}
            {values.replyAlertsEnabled && (
              <div className="ml-6 pl-4 border-l-2 border-[#E2E8F0] space-y-2">
                <p className="text-xs font-medium text-[#64748B] mb-3">
                  Notify me for:
                </p>
                <Checkbox
                  checked={values.replyAlertTiers.hot}
                  onChange={(v) =>
                    setValues({
                      ...values,
                      replyAlertTiers: { ...values.replyAlertTiers, hot: v },
                    })
                  }
                  label="Hot leads (85+)"
                  color="bg-[#EF4444]"
                />
                <Checkbox
                  checked={values.replyAlertTiers.warm}
                  onChange={(v) =>
                    setValues({
                      ...values,
                      replyAlertTiers: { ...values.replyAlertTiers, warm: v },
                    })
                  }
                  label="Warm leads (60-84)"
                  color="bg-[#F97316]"
                />
                <Checkbox
                  checked={values.replyAlertTiers.cool}
                  onChange={(v) =>
                    setValues({
                      ...values,
                      replyAlertTiers: { ...values.replyAlertTiers, cool: v },
                    })
                  }
                  label="Cool leads (35-59)"
                  color="bg-[#3B82F6]"
                />
                <Checkbox
                  checked={values.replyAlertTiers.cold}
                  onChange={(v) =>
                    setValues({
                      ...values,
                      replyAlertTiers: { ...values.replyAlertTiers, cold: v },
                    })
                  }
                  label="Cold leads (20-34)"
                  color="bg-[#6B7280]"
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Dashboard Section */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E2E8F0]">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-[#64748B]" />
            <h3 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
              Dashboard
            </h3>
          </div>
        </div>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[#1E293B]">
                Show live activity feed
              </p>
              <p className="text-xs text-[#64748B] mt-0.5">
                See real-time outreach activity on your dashboard home page
              </p>
            </div>
            <Toggle
              enabled={values.activityFeedEnabled}
              onChange={(v) => setValues({ ...values, activityFeedEnabled: v })}
            />
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

export default NotificationSettingsForm;
