'use client';

import { Link2 } from 'lucide-react';
import { Integration } from '@/lib/mock/settings-data';
import { IntegrationCard } from './IntegrationCard';

interface IntegrationsSectionProps {
  integrations: Integration[];
}

export function IntegrationsSection({ integrations }: IntegrationsSectionProps) {
  return (
    <div className="glass-surface border border-border-subtle rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border-subtle flex items-center gap-2.5">
        <Link2 className="w-5 h-5 text-[#D4956A]" />
        <span className="font-serif font-semibold text-text-primary">Connected Services</span>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-2 gap-4">
          {integrations.map((integration) => (
            <IntegrationCard key={integration.id} integration={integration} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default IntegrationsSection;
