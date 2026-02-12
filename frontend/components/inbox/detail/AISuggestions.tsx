/**
 * FILE: frontend/components/inbox/detail/AISuggestions.tsx
 * PURPOSE: AI response suggestions (KEEP VIOLET for AI icon per spec)
 * SPRINT: Dashboard Sprint 3b - Reply Detail
 */
'use client';

import { AISuggestion } from '@/lib/mock/inbox-data';
import { Lightbulb, BarChart2, Target, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AISuggestionsProps {
  suggestions: AISuggestion[];
  onUseSuggestion: (text: string) => void;
}

const iconMap: Record<string, typeof Lightbulb> = {
  sparkles: Sparkles,
  chart: BarChart2,
  target: Target,
};

export function AISuggestions({ suggestions, onUseSuggestion }: AISuggestionsProps) {
  return (
    <div className="max-w-[720px] bg-surface-dark border border-border-subtle rounded-2xl p-6 mt-6">
      {/* Header - VIOLET stays for AI icon */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-blue-500 flex items-center justify-center">
          <Lightbulb className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="font-serif text-base font-bold text-text-primary">Suggested Responses</h3>
          <p className="text-xs text-text-muted">Click to use • Based on conversation context</p>
        </div>
      </div>
      
      {/* Cards */}
      <div className="space-y-3">
        {suggestions.map((suggestion) => {
          const IconComponent = iconMap[suggestion.icon] || Sparkles;
          
          return (
            <div
              key={suggestion.id}
              className="group p-4 bg-violet-500/5 border border-violet-500/15 rounded-xl cursor-pointer hover:bg-violet-500/10 hover:border-violet-500/30 hover:-translate-y-0.5 transition-all"
              onClick={() => onUseSuggestion(suggestion.text)}
            >
              <div className="flex items-center justify-between mb-2.5">
                <span className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wide text-violet-400">
                  {suggestion.label.includes('✨') ? (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      {suggestion.label.replace('✨ ', '')}
                    </>
                  ) : (
                    <>
                      <IconComponent className="w-3.5 h-3.5" />
                      {suggestion.label}
                    </>
                  )}
                </span>
                <button className="px-3 py-1.5 bg-violet-500 text-white text-[11px] font-semibold rounded-md opacity-0 group-hover:opacity-100 transition-opacity">
                  Use This
                </button>
              </div>
              <p className="text-sm text-text-secondary leading-relaxed">{suggestion.text}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
