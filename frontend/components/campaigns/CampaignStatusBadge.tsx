'use client';

import { CampaignStatus, statusStyles } from '@/data/mock-campaigns';

interface Props {
  status: CampaignStatus;
}

export function CampaignStatusBadge({ status }: Props) {
  const style = statusStyles[status];
  
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${style.bg} ${style.text}`}>
      <span>{style.dot}</span>
      <span className="capitalize">{status}</span>
    </span>
  );
}
