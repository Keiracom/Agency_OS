'use client';

import { useEffect, useState, useCallback } from 'react';
import { ActivityCard, Card } from '@/components/Card';
import { PageHeader } from '@/components/Navigation';
import { Search, FilterChips } from '@/components/Search';
import { ActivityListSkeleton, EmptyState, ErrorState } from '@/components/Loading';
import { timeAgo, formatCost, formatNumber, cn } from '@/lib/utils';
import type { Activity } from '@/lib/supabase';

type StatusFilter = 'all' | 'completed' | 'running' | 'pending' | 'failed';

export default function ActivityPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/elliot/stats?include=activity&limit=100');
      if (!response.ok) throw new Error('Failed to fetch activity');
      const result = await response.json();
      setActivities(result.recentActivity || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto-refresh every 15 seconds
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSearch = useCallback((query: string) => {
    setSearch(query.toLowerCase());
  }, []);

  const filteredActivities = activities.filter(a => {
    if (statusFilter !== 'all' && a.status !== statusFilter) return false;
    if (!search) return true;
    return (
      a.action.toLowerCase().includes(search) ||
      a.action_type.toLowerCase().includes(search) ||
      a.result?.toLowerCase().includes(search)
    );
  });

  // Calculate summary stats
  const todayStats = activities.reduce((acc, a) => {
    acc.total++;
    acc.tokens += a.tokens_used;
    acc.cost += Number(a.cost_usd);
    if (a.status === 'completed') acc.completed++;
    if (a.status === 'failed') acc.failed++;
    return acc;
  }, { total: 0, tokens: 0, cost: 0, completed: 0, failed: 0 });

  if (loading && activities.length === 0) return <ActivityListSkeleton count={6} />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      completed: 'bg-green-500',
      running: 'bg-blue-500',
      pending: 'bg-yellow-500',
      failed: 'bg-red-500',
    };
    return colors[status] || 'bg-gray-500';
  };

  return (
    <div className="space-y-4 py-4">
      <PageHeader 
        title="Activity" 
        subtitle={`${filteredActivities.length} activities`}
      />

      {/* Stats Summary */}
      <Card className="grid grid-cols-4 gap-2 text-center">
        <div>
          <p className="text-lg font-bold text-gray-900">{todayStats.total}</p>
          <p className="text-xs text-gray-500">Total</p>
        </div>
        <div>
          <p className="text-lg font-bold text-green-600">{todayStats.completed}</p>
          <p className="text-xs text-gray-500">Done</p>
        </div>
        <div>
          <p className="text-lg font-bold text-gray-900">{formatNumber(todayStats.tokens)}</p>
          <p className="text-xs text-gray-500">Tokens</p>
        </div>
        <div>
          <p className="text-lg font-bold text-gray-900">{formatCost(todayStats.cost)}</p>
          <p className="text-xs text-gray-500">Cost</p>
        </div>
      </Card>

      <Search 
        placeholder="Search activities..." 
        onSearch={handleSearch}
      />

      <FilterChips
        options={['completed', 'running', 'pending', 'failed']}
        selected={statusFilter === 'all' ? null : statusFilter}
        onSelect={(opt) => setStatusFilter((opt as StatusFilter) || 'all')}
      />

      {filteredActivities.length === 0 ? (
        <EmptyState 
          icon="📊" 
          title={search || statusFilter !== 'all' ? 'No matches' : 'No activity yet'} 
          description="Activity will appear here as Elliot works"
        />
      ) : (
        <div className="space-y-2">
          {filteredActivities.map((activity) => (
            <ActivityCard
              key={activity.id}
              action={activity.action}
              type={activity.action_type}
              status={activity.status}
              time={timeAgo(activity.created_at)}
              tokens={activity.tokens_used}
              onClick={() => setSelectedActivity(activity)}
            />
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedActivity && (
        <div 
          className="fixed inset-0 z-50 bg-black/50 flex items-end justify-center"
          onClick={() => setSelectedActivity(null)}
        >
          <div 
            className="bg-white w-full max-w-2xl rounded-t-2xl p-6 max-h-[80vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className={cn('w-3 h-3 rounded-full', getStatusColor(selectedActivity.status))} />
                <h2 className="text-lg font-semibold text-gray-900 capitalize">
                  {selectedActivity.status}
                </h2>
              </div>
              <button 
                onClick={() => setSelectedActivity(null)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                ✕
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">Action</h3>
                <p className="text-gray-900">{selectedActivity.action}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Type</h3>
                  <p className="text-gray-700 capitalize">{selectedActivity.action_type}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Duration</h3>
                  <p className="text-gray-700">
                    {selectedActivity.duration_ms ? `${selectedActivity.duration_ms}ms` : 'N/A'}
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Tokens</h3>
                  <p className="text-gray-700">{formatNumber(selectedActivity.tokens_used)}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Cost</h3>
                  <p className="text-gray-700">{formatCost(Number(selectedActivity.cost_usd))}</p>
                </div>
              </div>
              
              {selectedActivity.result && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Result</h3>
                  <p className="text-gray-700 whitespace-pre-wrap bg-gray-50 p-3 rounded-lg text-sm">
                    {selectedActivity.result}
                  </p>
                </div>
              )}
              
              {selectedActivity.metadata && Object.keys(selectedActivity.metadata).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-1">Metadata</h3>
                  <pre className="text-xs bg-gray-50 p-3 rounded-lg overflow-x-auto">
                    {JSON.stringify(selectedActivity.metadata, null, 2)}
                  </pre>
                </div>
              )}
              
              <div className="text-xs text-gray-400 pt-2 border-t">
                <p>Started: {new Date(selectedActivity.created_at).toLocaleString()}</p>
                {selectedActivity.completed_at && (
                  <p>Completed: {new Date(selectedActivity.completed_at).toLocaleString()}</p>
                )}
                {selectedActivity.session_id && (
                  <p>Session: {selectedActivity.session_id}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
