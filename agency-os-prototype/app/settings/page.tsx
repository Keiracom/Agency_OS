"use client"

import { User, Link2, CreditCard, Bell, Shield, HelpCircle, Check, X, Clock } from "lucide-react"
import { settingsData } from "@/data/demo"

const statusIcons = {
  connected: { icon: Check, color: "text-green-500 bg-green-100" },
  pending: { icon: Clock, color: "text-yellow-500 bg-yellow-100" },
  disconnected: { icon: X, color: "text-red-500 bg-red-100" },
}

export default function SettingsPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-6">
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Manage your account and integrations</p>
      </header>

      <div className="p-8 max-w-4xl">
        {/* Profile Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center gap-3 mb-6">
            <User className="w-5 h-5 text-mint-600" />
            <h2 className="text-lg font-semibold">Profile</h2>
          </div>
          
          <div className="flex items-center gap-6 mb-6">
            <div className="w-20 h-20 bg-gradient-to-br from-mint-500 to-mint-600 rounded-full flex items-center justify-center text-white font-bold text-2xl">
              DK
            </div>
            <div>
              <h3 className="text-xl font-semibold">{settingsData.user.name}</h3>
              <p className="text-gray-500">{settingsData.user.email}</p>
              <p className="text-sm text-mint-600 font-medium mt-1">{settingsData.user.plan} Plan</p>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input
                type="text"
                defaultValue={settingsData.user.name}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mint-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                defaultValue={settingsData.user.email}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mint-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
              <input
                type="text"
                defaultValue={settingsData.user.company}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mint-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
              <select className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mint-500 focus:border-transparent">
                <option>Australia/Sydney (AEST)</option>
                <option>Australia/Melbourne</option>
                <option>Australia/Brisbane</option>
              </select>
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <button className="px-4 py-2 text-sm font-medium text-white bg-mint-500 rounded-lg hover:bg-mint-600 transition-colors">
              Save Changes
            </button>
          </div>
        </div>

        {/* Integrations Section */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center gap-3 mb-6">
            <Link2 className="w-5 h-5 text-mint-600" />
            <h2 className="text-lg font-semibold">Integrations</h2>
          </div>

          <div className="space-y-4">
            {settingsData.integrations.map((integration) => {
              const status = statusIcons[integration.status as keyof typeof statusIcons]
              const StatusIcon = status.icon
              return (
                <div
                  key={integration.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center text-2xl">
                      {integration.icon}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{integration.name}</p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className={`w-5 h-5 rounded-full flex items-center justify-center ${status.color}`}>
                          <StatusIcon className="w-3 h-3" />
                        </span>
                        <span className="text-sm text-gray-500 capitalize">{integration.status}</span>
                      </div>
                    </div>
                  </div>
                  <button
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      integration.status === "connected"
                        ? "text-red-600 bg-red-50 hover:bg-red-100"
                        : integration.status === "pending"
                        ? "text-yellow-600 bg-yellow-50 hover:bg-yellow-100"
                        : "text-mint-600 bg-mint-50 hover:bg-mint-100"
                    }`}
                  >
                    {integration.status === "connected"
                      ? "Disconnect"
                      : integration.status === "pending"
                      ? "Complete Setup"
                      : "Connect"}
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        {/* Quick Settings */}
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <Bell className="w-5 h-5 text-mint-600" />
              <h2 className="text-lg font-semibold">Notifications</h2>
            </div>
            <div className="space-y-3">
              <label className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Email notifications</span>
                <input type="checkbox" defaultChecked className="rounded text-mint-500 focus:ring-mint-500" />
              </label>
              <label className="flex items-center justify-between">
                <span className="text-sm text-gray-700">New reply alerts</span>
                <input type="checkbox" defaultChecked className="rounded text-mint-500 focus:ring-mint-500" />
              </label>
              <label className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Weekly digest</span>
                <input type="checkbox" className="rounded text-mint-500 focus:ring-mint-500" />
              </label>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <CreditCard className="w-5 h-5 text-mint-600" />
              <h2 className="text-lg font-semibold">Billing</h2>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              You're on the <strong className="text-mint-600">Velocity</strong> plan. 
              Next billing date: <strong>Feb 15, 2026</strong>
            </p>
            <button className="text-sm text-mint-600 font-medium hover:underline">
              Manage subscription →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
