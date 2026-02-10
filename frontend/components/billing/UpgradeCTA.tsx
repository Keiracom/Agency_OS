'use client';

import { Star, Zap } from 'lucide-react';

export function UpgradeCTA() {
  return (
    <div className="bg-gradient-to-br from-[rgba(245,158,11,0.12)] to-[rgba(251,191,36,0.08)] border border-[rgba(245,158,11,0.25)] rounded-2xl p-8 flex items-center justify-between mt-6">
      <div>
        <h3 className="text-xl font-bold text-text-primary mb-2 flex items-center gap-2.5">
          <Star className="w-6 h-6 text-status-warning" />
          Ready to dominate your market?
        </h3>
        <p className="text-sm text-text-secondary max-w-[500px]">
          Upgrade to Dominance and get 2x the meetings, dedicated Slack support, and custom
          integrations built for your workflow.
        </p>
      </div>
      <button className="inline-flex items-center gap-2 px-7 py-3.5 text-[15px] font-semibold rounded-lg bg-gradient-to-r from-status-warning to-[#FBBF24] text-bg-base hover:shadow-[0_0_24px_rgba(245,158,11,0.4)] transition-all">
        <Zap className="w-5 h-5" />
        Talk to Sales
      </button>
    </div>
  );
}

export default UpgradeCTA;
