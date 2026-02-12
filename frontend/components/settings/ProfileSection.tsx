'use client';

import { useState } from 'react';
import { Camera, Check, User } from 'lucide-react';
import { UserProfile, mockTimezones } from '@/lib/mock/settings-data';

interface ProfileSectionProps {
  profile: UserProfile;
}

export function ProfileSection({ profile }: ProfileSectionProps) {
  const [formData, setFormData] = useState({
    firstName: profile.name.split(' ')[0],
    lastName: profile.name.split(' ')[1] || '',
    email: profile.email,
    phone: profile.phone,
    company: profile.company,
    timezone: profile.timezone,
  });

  const inputClass = `px-4 py-3 text-sm border border-border-subtle rounded-lg 
    bg-bg-base text-text-primary outline-none transition-all
    focus:border-[#D4956A] focus:ring-[3px] focus:ring-[rgba(212,149,106,0.15)]`;

  return (
    <div className="glass-surface border border-border-subtle rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border-subtle flex items-center gap-2.5">
        <User className="w-5 h-5 text-[#D4956A]" />
        <span className="font-serif font-semibold text-text-primary">Profile Information</span>
      </div>

      <div className="p-6">
        {/* Avatar Section */}
        <div className="flex items-center gap-6 mb-8">
          <div className="relative">
            <div className="w-[88px] h-[88px] bg-gradient-to-br from-[#D4956A] to-[#C4854A] rounded-full flex items-center justify-center text-white font-bold text-3xl border-[3px] border-bg-surface shadow-[0_0_0_3px_rgba(212,149,106,0.15)]">
              {profile.initials}
            </div>
            <button className="absolute bottom-0 right-0 w-8 h-8 bg-[#D4956A] rounded-full flex items-center justify-center cursor-pointer border-[3px] border-bg-surface hover:bg-[#E4A57A] hover:scale-110 transition-all">
              <Camera className="w-3.5 h-3.5 text-white" />
            </button>
          </div>
          <div>
            <h3 className="text-xl font-semibold text-text-primary">{profile.name}</h3>
            <p className="text-sm text-text-secondary mt-1">{profile.email}</p>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[rgba(212,149,106,0.15)] text-[#D4956A] text-xs font-semibold rounded-full mt-2">
              <Check className="w-3 h-3" />
              {profile.plan}
            </div>
          </div>
        </div>

        {/* Form Grid */}
        <div className="grid grid-cols-2 gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">First Name</label>
            <input type="text" value={formData.firstName} onChange={(e) => setFormData({ ...formData, firstName: e.target.value })} className={inputClass} />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Last Name</label>
            <input type="text" value={formData.lastName} onChange={(e) => setFormData({ ...formData, lastName: e.target.value })} className={inputClass} />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Email Address</label>
            <input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} className={inputClass} />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Phone Number</label>
            <input type="tel" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} className={inputClass} />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Company</label>
            <input type="text" value={formData.company} onChange={(e) => setFormData({ ...formData, company: e.target.value })} className={inputClass} />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-text-secondary">Timezone</label>
            <select value={formData.timezone} onChange={(e) => setFormData({ ...formData, timezone: e.target.value })} className={`${inputClass} cursor-pointer`}>
              {mockTimezones.map((tz) => (<option key={tz} value={tz}>{tz}</option>))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfileSection;
