'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card } from '@/components/Card';
import { PageHeader } from '@/components/Navigation';
import { Search } from '@/components/Search';
import { ActivityListSkeleton, EmptyState, ErrorState } from '@/components/Loading';
import { timeAgo, cn } from '@/lib/utils';
import type { Decision } from '@/lib/supabase';

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedDecision, setSelectedDecision] = useState<Decision | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/elliot/stats?include=decisions');
      if (!response.ok) throw new Error('Failed to fetch decisions');
      const result = await response.json();
      setDecisions(result.decisions || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSearch = useCallback((query: string) => {
    setSearch(query.toLowerCase());
  }, []);

  const filteredDecisions = decisions.filter(d => {
    if (!search) return true;
    return (
      d.decision.toLowerCase().includes(search) ||
      d.context?.toLowerCase().includes(search) ||
      d.rationale?.toLowerCase().includes(search) ||
      d.outcome?.toLowerCase().includes(search)
    );
  });

  if (loading && decisions.length === 0) return <ActivityListSkeleton count={6} />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  const getRatingColor = (rating: number | null) => {
    if (!rating) return 'bg-gray-100 text-gray-600';
    if (rating >= 4) return 'bg-green-100 text-green-700';
    if (rating >= 3) return 'bg-yellow-100 text-yellow-700';
    return 'bg-red-100 text-red-700';
  };

  const getRatingEmoji = (rating: number | null) => {
    if (!rating) return '❓';
    if (rating >= 4) return '✅';
    if (rating >= 3) return '😐';
    return '❌';
  };

  return (
    <div className="space-y-4 py-4">
      <PageHeader 
        title="Decisions" 
        subtitle={`${filteredDecisions.length} decisions logged`}
      />

      <Search 
        placeholder="Search decisions..." 
        onSearch={handleSearch}
      />

      {filteredDecisions.length === 0 ? (
        <EmptyState 
          icon="⚖️" 
          title={search ? 'No matches' : 'No decisions yet'} 
          description={search ? `No decisions matching "${search}"` : 'Decisions will be logged as Elliot makes them'}
        />
      ) : (
        <div className="space-y-3">
          {filteredDecisions.map((decision) => (
            <Card
              key={decision.id}
              onClick={() => setSelectedDecision(decision)}
              className="space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-gray-900 line-clamp-2 flex-1">
                  {decision.decision}
                </p>
                <span className={cn(
                  'text-lg flex-shrink-0',
                  getRatingColor(decision.outcome_rating),
                  'px-2 py-1 rounded-lg'
                )}>
                  {getRatingEmoji(decision.outcome_rating)}
                </span>
              </div>
              
              {decision.context && (
                <p className="text-sm text-gray-500 line-clamp-2">
                  📍 {decision.context}
                </p>
              )}
              
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span>{timeAgo(decision.created_at)}</span>
                {decision.tags && decision.tags.length > 0 && (
                  <>
                    <span>•</span>
                    <span>{decision.tags.slice(0, 3).join(', ')}</span>
                  </>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedDecision && (
        <div 
          className="fixed inset-0 z-50 bg-black/50 flex items-end justify-center"
          onClick={() => setSelectedDecision(null)}
        >
          <div 
            className="bg-white w-full max-w-2xl rounded-t-2xl p-6 max-h-[80vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Decision Details</h2>
              <button 
                onClick={() => setSelectedDecision(null)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">Decision</h3>
                <p className="text-gray-900">{selectedDecision.decision}</p>
              </div>
              
              {selectedDecision.context && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Context</h3>
                  <p className="text-gray-700">{selectedDecision.context}</p>
                </div>
              )}
              
              {selectedDecision.rationale && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Rationale</h3>
                  <p className="text-gray-700">{selectedDecision.rationale}</p>
                </div>
              )}
              
              {selectedDecision.outcome && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Outcome</h3>
                  <p className="text-gray-700">{selectedDecision.outcome}</p>
                  {selectedDecision.outcome_rating && (
                    <div className={cn(
                      'inline-flex items-center gap-2 mt-2 px-3 py-1 rounded-full text-sm font-medium',
                      getRatingColor(selectedDecision.outcome_rating)
                    )}>
                      <span>{getRatingEmoji(selectedDecision.outcome_rating)}</span>
                      <span>Rating: {selectedDecision.outcome_rating}/5</span>
                    </div>
                  )}
                </div>
              )}
              
              <div className="flex flex-wrap gap-2 pt-2 border-t">
                {selectedDecision.tags?.map((tag, i) => (
                  <span 
                    key={i}
                    className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-sm"
                  >
                    {tag}
                  </span>
                ))}
                <span className="text-sm text-gray-400">
                  {timeAgo(selectedDecision.created_at)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
