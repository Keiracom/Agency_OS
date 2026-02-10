'use client';

import { useState } from 'react';
import { Camera, Check } from 'lucide-react';
import { UserProfile, mockTimezones } from '@/data/mock-settings';

interface ProfileCardProps {
  profile: UserProfile;
}

export function ProfileCard({ profile }: ProfileCardProps) {
  const [formData, setFormData] = useState({
    firstName: profile.name.split(' ')[0],
    lastName: profile.name.split(' ')[1] || '',
    email: profile.email,
    phone: profile.phone,
    company: profile.company,
    timezone: profile.timezone,
  });

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden mb-6">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-text-primary font-semibold">
          <svg className="w-5 h-5 text-accent-primary" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Profile Information
        </div>
      </div>

      {/* Body */}
      <div className="p-6">
        {/* Profile Header */}
        <div className="flex items-center gap-6 mb-8">
          <div className="relative">
            <div className="w-[88px] h-[88px] bg-gradient-to-br from-accent-primary to-accent-blue rounded-full flex items-center justify-center text-white font-bold text-3xl border-[3px] border-bg-surface shadow-[0_0_0_3px_rgba(124,58,237,0.15)]">
              {profile.initials}
            </div>
            <button className="absolute bottom-0 right-0 w-8 h-8 bg-accent-primary rounded-full flex items-center justify-center cursor-pointer border-[3px] border-bg-surface hover:bg-accent-primary-hover hover:scale-110 transition-all">
              <Camera className="w-3.5 h-3.5 text-white" />
            </button>
          </div>
          <div>
            <h3 className="text-xl font-semibold text-text-primary">{profile.name}</h3>
            <p className="text-sm text-text-secondary mt-1">{profile.email}</p>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[rgba(124,58,237,0.15)] text-accent-primary text-xs font-semibold rounded-full mt-2">
              <Check className="w-3 h-3" />
              {profile.plan}
            </div>
          </div>
        </div>

        {/* Form Grid */}
        <div className="grid grid-cols-2 gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">First Name</label>
            <input
              type="text"
              value={formData.firstName}
              onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
              className="px-4 py-3 text-sm border border-border-default rounded-lg bg-bg-surface-hover text-text-primary outline-none transition-all focus:border-accent-primary focus:ring-[3px] focus:ring-[rgba(124,58,237,0.15)]"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Last Name</label>
            <input
              type="text"
              value={formData.lastName}
              onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
              className="px-4 py-3 text-sm border border-border-default rounded-lg bg-bg-surface-hover text-text-primary outline-none transition-all focus:border-accent-primary focus:ring-[3px] focus:ring-[rgba(124,58,237,0.15)]"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Email Address</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="px-4 py-3 text-sm border border-border-default rounded-lg bg-bg-surface-hover text-text-primary outline-none transition-all focus:border-accent-primary focus:ring-[3px] focus:ring-[rgba(124,58,237,0.15)]"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Phone Number</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              className="px-4 py-3 text-sm border border-border-default rounded-lg bg-bg-surface-hover text-text-primary outline-none transition-all focus:border-accent-primary focus:ring-[3px] focus:ring-[rgba(124,58,237,0.15)]"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Company</label>
            <input
              type="text"
              value={formData.company}
              onChange={(e) => setFormData({ ...formData, company: e.target.value })}
              className="px-4 py-3 text-sm border border-border-default rounded-lg bg-bg-surface-hover text-text-primary outline-none transition-all focus:border-accent-primary focus:ring-[3px] focus:ring-[rgba(124,58,237,0.15)]"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Timezone</label>
            <select
              value={formData.timezone}
              onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
              className="px-4 py-3 text-sm border border-border-default rounded-lg bg-bg-surface-hover text-text-primary outline-none transition-all cursor-pointer focus:border-accent-primary focus:ring-[3px] focus:ring-[rgba(124,58,237,0.15)]"
            >
              {mockTimezones.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 mt-6 pt-6 border-t border-border-subtle">
          <button className="px-5 py-2.5 text-sm font-medium rounded-lg bg-transparent text-text-secondary border border-border-default hover:bg-bg-surface-hover hover:text-text-primary transition-all">
            Cancel
          </button>
          <button className="px-5 py-2.5 text-sm font-medium rounded-lg bg-accent-primary text-white hover:bg-accent-primary-hover hover:-translate-y-px transition-all">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

export default ProfileCard;
