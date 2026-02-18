'use client';

import { Campaign } from '@/data/mock-campaigns';
import { CampaignStatusBadge } from './CampaignStatusBadge';
import { CampaignChannels } from './CampaignChannels';
import { CampaignMetrics } from './CampaignMetrics';
import { CampaignSequence } from './CampaignSequence';
import { InsightBox } from './InsightBox';

interface Props {
  campaign: Campaign;
}

export function CampaignCard({ campaign }: Props) {
  return (
    <div className="bg-bg-surface rounded-xl p-6 border border-slate-200 mb-4">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="text-lg font-bold text-slate-800 flex items-center gap-2.5">
            {campaign.name}
            {campaign.isAI && (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-violet-100 text-amber">
                AI Campaign
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-2">
            <CampaignChannels channels={campaign.channels} />
            <CampaignStatusBadge status={campaign.status} />
            <span className="text-xs text-text-muted">Priority: {campaign.priority}%</span>
          </div>
        </div>
      </div>

      <CampaignMetrics metrics={campaign.metrics} />
      <CampaignSequence sequence={campaign.sequence} />
      
      {campaign.aiInsight && <InsightBox insight={campaign.aiInsight} />}
    </div>
  );
}
