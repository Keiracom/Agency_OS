'use client';

import { Users, UserPlus } from 'lucide-react';
import { TeamMember } from '@/lib/mock/settings-data';

interface TeamSectionProps {
  members: TeamMember[];
  maxSeats?: number;
}

const roleStyles = {
  owner: {
    bg: 'bg-[rgba(212,149,106,0.15)]',
    text: 'text-[#D4956A]',
    avatarBg: 'bg-gradient-to-br from-[#D4956A] to-[#C4854A]',
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

export function TeamSection({ members, maxSeats = 5 }: TeamSectionProps) {
  return (
    <div className="glass-surface border border-border-subtle rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Users className="w-5 h-5 text-[#D4956A]" />
          <span className="font-serif font-semibold text-text-primary">Team Members</span>
        </div>
        <span className="text-sm text-text-muted">{members.length} of {maxSeats} seats used</span>
      </div>

      <div className="p-6">
        <div className="flex flex-col gap-3">
          {members.map((member) => {
            const style = roleStyles[member.role];
            return (
              <div key={member.id} className="flex items-center justify-between px-5 py-4 bg-bg-surface-hover rounded-xl">
                <div className="flex items-center gap-4">
                  <div className={`w-11 h-11 rounded-full flex items-center justify-center font-semibold text-sm text-white ${style.avatarBg}`}>
                    {member.initials}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary">{member.name}</h4>
                    <p className="text-sm text-text-muted">{member.email}</p>
                  </div>
                </div>
                <span className={`px-3 py-1 text-xs font-medium rounded-full capitalize ${style.bg} ${style.text}`}>
                  {member.role}
                </span>
              </div>
            );
          })}
        </div>

        <button className="flex items-center justify-center gap-2 w-full p-4 mt-4 bg-transparent border-2 border-dashed border-border-default rounded-xl text-text-muted text-sm font-medium cursor-pointer transition-all hover:border-[#D4956A] hover:text-[#D4956A] hover:bg-[rgba(212,149,106,0.1)]">
          <UserPlus className="w-[18px] h-[18px]" />
          Invite Team Member
        </button>
      </div>
    </div>
  );
}

export default TeamSection;
