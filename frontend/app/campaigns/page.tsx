'use client';

import { AppShell } from '@/components/layout/AppShell';
import { CampaignCard, BestContentCard, RecommendationsCard } from '@/components/campaigns';
import { mockCampaigns, mockBestContent, mockRecommendations } from '@/data/mock-campaigns';

export default function CampaignsPage() {
  // For now, show the first (active) campaign in detail
  const featuredCampaign = mockCampaigns[0];

  return (
    <AppShell>
      {/* Page Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Campaigns</h1>
        <button className="px-5 py-2.5 bg-blue-500 text-white rounded-lg font-semibold text-sm hover:bg-blue-600 transition-colors">
          + New Campaign
        </button>
      </div>

      {/* Featured Campaign Detail */}
      <CampaignCard campaign={featuredCampaign} />

      {/* Best Performing Content */}
      <BestContentCard content={mockBestContent} />

      {/* AI Recommendations */}
      <RecommendationsCard recommendations={mockRecommendations} />
    </AppShell>
  );
}
