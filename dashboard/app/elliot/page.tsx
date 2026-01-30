'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, StatCard, ActivityCard } from '@/components/Card';
import { PageHeader } from '@/components/Navigation';
import { DashboardSkeleton, EmptyState, ErrorState } from '@/components/Loading';
import { timeAgo, formatCost, formatNumber } from '@/lib/utils';
import type { DashboardStats, Activity } from '@/lib/supabase';

interface DashboardData {
  stats: DashboardStats;
  recentActivity: Activity[];
}

export default function ElliotDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/elliot/stats');
      if (!response.ok) throw new Error('Failed to fetch stats');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) return <DashboardSkeleton />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;
  if (!data) return <EmptyState icon="📊" title="No data yet" description="Start using Elliot to see stats" />;

  const { stats, recentActivity } = data;

  return (
    <div className="space-y-6 py-4">
      <PageHeader 
        title="Dashboard" 
        subtitle={`Last active ${stats.last_activity ? timeAgo(stats.last_activity) : 'never'}`}
      />

      {/* Quick Stats */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          icon="🧠"
          label="Decisions"
          value={formatNumber(stats.decisions_count)}
          color="purple"
        />
        <StatCard
          icon="📚"
          label="Learnings"
          value={formatNumber(stats.learnings_count)}
          color="blue"
        />
        <StatCard
          icon="🔄"
          label="Today's Actions"
          value={formatNumber(stats.today_activities)}
          color="green"
        />
        <StatCard
          icon="🪙"
          label="Today's Cost"
          value={formatCost(stats.today_cost)}
          color="yellow"
        />
      </div>

      {/* Session Health */}
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Session Health</h2>
          <span className="text-sm text-gray-500">{stats.active_sessions} active</span>
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-gray-900">{formatNumber(stats.today_tokens)}</p>
            <p className="text-xs text-gray-500">Tokens Today</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{stats.memory_items}</p>
            <p className="text-xs text-gray-500">Memory Items</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{stats.patterns_count}</p>
            <p className="text-xs text-gray-500">Patterns</p>
          </div>
        </div>
      </Card>

      {/* Recent Activity */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Recent Activity</h2>
          <Link href="/elliot/activity" className="text-sm text-blue-500 font-medium">
            View All →
          </Link>
        </div>
        
        {recentActivity.length === 0 ? (
          <EmptyState 
            icon="📭" 
            title="No activity yet" 
            description="Activity will appear here as Elliot works"
          />
        ) : (
          <div className="space-y-2">
            {recentActivity.slice(0, 5).map((activity) => (
              <ActivityCard
                key={activity.id}
                action={activity.action}
                type={activity.action_type}
                status={activity.status}
                time={timeAgo(activity.created_at)}
                tokens={activity.tokens_used}
              />
            ))}
          </div>
        )}
      </section>

      {/* Quick Links */}
      <section className="grid grid-cols-2 gap-3">
        <Link href="/elliot/memory">
          <Card className="flex items-center gap-3 hover:bg-gray-50">
            <span className="text-2xl">🧠</span>
            <div>
              <p className="font-medium text-gray-900">Memory</p>
              <p className="text-xs text-gray-500">{stats.memory_items} items</p>
            </div>
          </Card>
        </Link>
        <Link href="/elliot/decisions">
          <Card className="flex items-center gap-3 hover:bg-gray-50">
            <span className="text-2xl">⚖️</span>
            <div>
              <p className="font-medium text-gray-900">Decisions</p>
              <p className="text-xs text-gray-500">{stats.decisions_count} logged</p>
            </div>
          </Card>
        </Link>
      </section>
    </div>
  );
}
