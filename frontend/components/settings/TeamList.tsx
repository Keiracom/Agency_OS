'use client';

import { UserPlus } from 'lucide-react';
import { TeamMember } from '@/data/mock-settings';

interface TeamListProps {
  members: TeamMember[];
}

const roleConfig = {
  owner: {
    bg: 'bg-[rgba(124,58,237,0.15)]',
    text: 'text-accent-primary',
    avatarBg: 'bg-gradient-to-br from-accent-primary to-accent-blue',
  },
  admin: {
    bg: 'bg-[rgba(59,130,246,0.15)]',
    text: 'text-accent-blue',
    avatarBg: 'bg-gradient-to-br from-accent-blue to-accent-teal',
  },
  member: {
    bg: 'bg-[rgba(20,184,166,0.15)]',
    text: 'text-accent-teal',
    avatarBg: 'bg-gradient-to-br from-accent-teal to-status-success',
  },
};

export function TeamList({ members }: TeamListProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5 text-text-primary font-semibold">
          <svg className="w-5 h-5 text-accent-primary" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Team Members
        </div>
        <span className="text-sm text-text-muted">{members.length} of 5 seats used</span>
      </div>

      {/* Body */}
      <div className="p-6">
        <div className="flex flex-col gap-3">
          {members.map((member) => {
            const config = roleConfig[member.role];
            return (
              <div
                key={member.id}
                className="flex items-center justify-between px-5 py-4 bg-bg-surface-hover rounded-[10px]"
              >
                <div className="flex items-center gap-4">
                  <div
                    className={`w-11 h-11 rounded-full flex items-center justify-center font-semibold text-sm text-white ${config.avatarBg}`}
                  >
                    {member.initials}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary">{member.name}</h4>
                    <p className="text-sm text-text-muted">{member.email}</p>
                  </div>
                </div>
                <span
                  className={`px-3 py-1 text-xs font-medium rounded-full capitalize ${config.bg} ${config.text}`}
                >
                  {member.role}
                </span>
              </div>
            );
          })}
        </div>

        {/* Invite Button */}
        <button className="flex items-center justify-center gap-2 w-full p-4 mt-4 bg-transparent border-2 border-dashed border-border-default rounded-[10px] text-text-muted text-sm font-medium cursor-pointer transition-all hover:border-accent-primary hover:text-accent-primary hover:bg-[rgba(124,58,237,0.15)]">
          <UserPlus className="w-[18px] h-[18px]" />
          Invite Team Member
        </button>
      </div>
    </div>
  );
}

export default TeamList;
