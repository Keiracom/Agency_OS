'use client';

import { useState } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { CampaignCard, BestContentCard, RecommendationsCard } from '@/components/campaigns';
import { mockCampaigns, mockBestContent, mockRecommendations, statusStyles, channelEmoji, Campaign } from '@/data/mock-campaigns';

export default function CampaignsPage() {
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>(mockCampaigns[0]?.id || '');
  
  const selectedCampaign = mockCampaigns.find((c) => c.id === selectedCampaignId) || mockCampaigns[0];

  return (
    <AppShell>
      {/* Page Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Campaigns</h1>
        <button className="px-5 py-2.5 bg-bg-elevated text-text-primary rounded-lg font-semibold text-sm hover:bg-bg-elevated transition-colors">
          + New Campaign
        </button>
      </div>

      {/* Campaign List - Selectable Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {mockCampaigns.map((campaign) => {
          const isSelected = campaign.id === selectedCampaignId;
          const statusStyle = statusStyles[campaign.status];
          
          return (
            <button
              key={campaign.id}
              onClick={() => setSelectedCampaignId(campaign.id)}
              className={`p-4 rounded-xl border text-left transition-all ${
                isSelected
                  ? 'border-default bg-bg-surface ring-2 ring-blue-200'
                  : 'border-slate-200 bg-bg-surface hover:border-slate-300 hover:shadow-sm'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800 text-sm">{campaign.name}</span>
                    {campaign.isAI && (
                      <span className="text-xs px-2 py-0.5 bg-violet-100 text-amber rounded-full font-medium">
                        ✨ AI
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm">
                      {campaign.channels.map((ch) => channelEmoji[ch]).join(' ')}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusStyle.bg} ${statusStyle.text}`}>
                      {statusStyle.dot} {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Quick Metrics */}
              <div className="flex items-center gap-4 mt-3 pt-3 border-t border-slate-100">
                <div className="text-center">
                  <div className="text-lg font-bold text-slate-800">{campaign.metrics[0]?.value}</div>
                  <div className="text-xs text-text-muted">Meetings</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-slate-800">{campaign.metrics[1]?.value}</div>
                  <div className="text-xs text-text-muted">Reply Rate</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-slate-800">{campaign.metrics[4]?.value}</div>
                  <div className="text-xs text-text-muted">Avg ALS</div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Selected Campaign Detail */}
      <CampaignCard campaign={selectedCampaign} />

      {/* Best Performing Content */}
      <BestContentCard content={mockBestContent} />

      {/* AI Recommendations */}
      <RecommendationsCard recommendations={mockRecommendations} />
    </AppShell>
  );
}
