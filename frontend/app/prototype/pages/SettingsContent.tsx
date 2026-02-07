/**
 * SettingsContent.tsx - Settings Page Content
 * Phase: Operation Modular Cockpit
 */

"use client";

import { useState } from "react";
import {
  Target,
  Linkedin,
  Building,
  Bell,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

const tabs = [
  { id: "icp", label: "ICP Settings", icon: Target },
  { id: "linkedin", label: "LinkedIn", icon: Linkedin },
  { id: "profile", label: "Company Profile", icon: Building },
  { id: "notifications", label: "Notifications", icon: Bell },
];

export function SettingsContent() {
  const [activeTab, setActiveTab] = useState("icp");

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-slate-900">Settings</h2>
        <p className="text-sm text-slate-500">Configure your account and targeting preferences</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Tabs */}
        <div className="w-56 space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === "icp" && <ICPSettingsTab />}
          {activeTab === "linkedin" && <LinkedInSettingsTab />}
          {activeTab === "profile" && <ProfileSettingsTab />}
          {activeTab === "notifications" && <NotificationsSettingsTab />}
        </div>
      </div>
    </div>
  );
}

function ICPSettingsTab() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-1">Ideal Customer Profile</h3>
      <p className="text-sm text-slate-500 mb-6">Define who you want to target</p>

      <div className="space-y-6">
        {/* Industries */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Target Industries</label>
          <div className="flex flex-wrap gap-2">
            {["SaaS", "FinTech", "HealthTech", "E-commerce", "MarTech"].map((ind) => (
              <span key={ind} className="px-3 py-1.5 bg-blue-50 text-blue-700 text-sm rounded-lg flex items-center gap-2">
                {ind}
                <button className="text-blue-400 hover:text-blue-600">×</button>
              </span>
            ))}
            <button className="px-3 py-1.5 border border-dashed border-slate-300 text-slate-500 text-sm rounded-lg hover:border-blue-400 hover:text-blue-600">
              + Add Industry
            </button>
          </div>
        </div>

        {/* Company Size */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Company Size</label>
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: "1-10", selected: false },
              { label: "11-50", selected: true },
              { label: "51-200", selected: true },
              { label: "201-500", selected: true },
            ].map((size) => (
              <button
                key={size.label}
                className={`px-4 py-2 rounded-lg text-sm font-medium border ${
                  size.selected
                    ? "bg-blue-50 border-blue-200 text-blue-700"
                    : "border-slate-200 text-slate-600 hover:border-blue-200"
                }`}
              >
                {size.label}
              </button>
            ))}
          </div>
        </div>

        {/* Job Titles */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">Target Job Titles</label>
          <div className="flex flex-wrap gap-2">
            {["CEO", "CTO", "VP Engineering", "Head of Product", "Founder"].map((title) => (
              <span key={title} className="px-3 py-1.5 bg-emerald-50 text-emerald-700 text-sm rounded-lg flex items-center gap-2">
                {title}
                <button className="text-emerald-400 hover:text-emerald-600">×</button>
              </span>
            ))}
            <button className="px-3 py-1.5 border border-dashed border-slate-300 text-slate-500 text-sm rounded-lg hover:border-emerald-400 hover:text-emerald-600">
              + Add Title
            </button>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-100">
          <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
            Save ICP Settings
          </button>
        </div>
      </div>
    </div>
  );
}

function LinkedInSettingsTab() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-1">LinkedIn Connection</h3>
      <p className="text-sm text-slate-500 mb-6">Manage your LinkedIn account integration</p>

      <div className="space-y-6">
        {/* Connected Account */}
        <div className="flex items-center justify-between p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500 rounded-full flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="font-medium text-emerald-900">Connected</p>
              <p className="text-sm text-emerald-700">john.smith@company.com</p>
            </div>
          </div>
          <button className="px-3 py-1.5 text-emerald-700 text-sm font-medium hover:bg-emerald-100 rounded-lg">
            Disconnect
          </button>
        </div>

        {/* Daily Limits */}
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-3">Daily Activity Limits</h4>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 border border-slate-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-600">Connection Requests</span>
                <span className="font-medium text-slate-900">25/day</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: "60%" }} />
              </div>
              <p className="text-xs text-slate-500 mt-1">15 sent today</p>
            </div>
            <div className="p-4 border border-slate-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-600">Messages</span>
                <span className="font-medium text-slate-900">50/day</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: "40%" }} />
              </div>
              <p className="text-xs text-slate-500 mt-1">20 sent today</p>
            </div>
          </div>
        </div>

        {/* Health Score */}
        <div className="p-4 border border-slate-200 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-slate-700">Account Health</h4>
            <span className="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs font-medium rounded">Excellent</span>
          </div>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-slate-900">98%</div>
              <div className="text-xs text-slate-500">Acceptance Rate</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">0</div>
              <div className="text-xs text-slate-500">Warnings</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-900">45d</div>
              <div className="text-xs text-slate-500">Account Age</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileSettingsTab() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-1">Company Profile</h3>
      <p className="text-sm text-slate-500 mb-6">Your company information for outreach</p>

      {/* Coming Soon Banner */}
      <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
        <div>
          <p className="font-medium text-amber-800">Coming Soon</p>
          <p className="text-sm text-amber-700">Company profile settings are being implemented.</p>
        </div>
      </div>

      <div className="space-y-5 opacity-60">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Company Name</label>
          <input
            type="text"
            defaultValue="Acme Agency"
            disabled
            className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm bg-slate-50"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Website</label>
          <input
            type="text"
            defaultValue="https://acmeagency.com"
            disabled
            className="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm bg-slate-50"
          />
        </div>
        <div className="pt-4 border-t border-slate-100">
          <button disabled className="px-4 py-2 bg-slate-300 text-slate-500 text-sm font-medium rounded-lg cursor-not-allowed">
            Save Profile
          </button>
        </div>
      </div>
    </div>
  );
}

function NotificationsSettingsTab() {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-lg p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-1">Notification Preferences</h3>
      <p className="text-sm text-slate-500 mb-6">Choose how you want to be notified</p>

      {/* Coming Soon Banner */}
      <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
        <div>
          <p className="font-medium text-amber-800">Coming Soon</p>
          <p className="text-sm text-amber-700">Notification preferences are being implemented.</p>
        </div>
      </div>

      <div className="space-y-4 opacity-60">
        {[
          { id: "replies", label: "New Replies", desc: "Get notified when leads reply", enabled: true },
          { id: "meetings", label: "Meeting Booked", desc: "Get notified when a meeting is scheduled", enabled: true },
          { id: "priority", label: "High Priority Alert", desc: "Get notified for strong interest signals", enabled: true },
          { id: "daily", label: "Daily Digest", desc: "Daily summary of all activity", enabled: false },
        ].map((notif) => (
          <div key={notif.id} className="flex items-center justify-between p-4 border border-slate-200 rounded-lg">
            <div>
              <p className="font-medium text-slate-900">{notif.label}</p>
              <p className="text-sm text-slate-500">{notif.desc}</p>
            </div>
            <div
              className={`w-12 h-6 rounded-full ${notif.enabled ? "bg-blue-400" : "bg-slate-200"}`}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full shadow ${notif.enabled ? "translate-x-6" : "translate-x-0.5"}`}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default SettingsContent;
