'use client';

import { CompanyIntel } from '@/data/mock-lead-detail';
import { Building2, Globe, Users, DollarSign, MapPin, TrendingUp, Lightbulb } from 'lucide-react';

interface LeadContactInfoProps {
  company: CompanyIntel;
}

export function LeadContactInfo({ company }: LeadContactInfoProps) {
  return (
    <div className="bg-panel border border-rule rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-rule">
        <span className="text-sm font-semibold text-primary">Company Intel</span>
      </div>

      <div className="p-6">
        {/* Company header */}
        <div className="flex items-center gap-4 mb-5">
          <div className="w-13 h-13 bg-elevated rounded-xl flex items-center justify-center text-2xl border border-rule-strong">
            <Building2 className="w-6 h-6 text-muted" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-primary">{company.name}</h3>
            <a
              href={`https://${company.website}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-accent-primary hover:underline"
            >
              {company.website}
            </a>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <div className="p-4 bg-elevated rounded-lg text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <Users className="w-3.5 h-3.5 text-muted" />
            </div>
            <div className="text-lg font-bold font-mono text-primary">{company.size}</div>
            <div className="text-[10px] text-muted uppercase mt-0.5">Employees</div>
          </div>
          <div className="p-4 bg-elevated rounded-lg text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <DollarSign className="w-3.5 h-3.5 text-muted" />
            </div>
            <div className="text-lg font-bold font-mono text-primary">{company.revenue}</div>
            <div className="text-[10px] text-muted uppercase mt-0.5">Revenue</div>
          </div>
          <div className="p-4 bg-elevated rounded-lg text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <TrendingUp className="w-3.5 h-3.5 text-muted" />
            </div>
            <div className="text-lg font-bold font-mono text-primary">{company.industry.split('/')[0].trim()}</div>
            <div className="text-[10px] text-muted uppercase mt-0.5">Industry</div>
          </div>
          <div className="p-4 bg-elevated rounded-lg text-center">
            <div className="flex items-center justify-center gap-1.5 mb-1">
              <MapPin className="w-3.5 h-3.5 text-muted" />
            </div>
            <div className="text-lg font-bold font-mono text-primary">{company.location.split(',')[0]}</div>
            <div className="text-[10px] text-muted uppercase mt-0.5">Location</div>
          </div>
        </div>

        {/* Insights */}
        {company.insights && company.insights.length > 0 && (
          <div className="pt-5 border-t border-rule">
            <div className="flex items-center gap-2 text-xs font-semibold text-muted uppercase tracking-wider mb-3">
              <Lightbulb className="w-3.5 h-3.5" />
              Key Insights
            </div>
            <div className="space-y-2.5">
              {company.insights.map((insight, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2.5 text-sm text-secondary"
                >
                  <span className="text-accent-primary mt-0.5">•</span>
                  <span className="leading-relaxed">{insight}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
