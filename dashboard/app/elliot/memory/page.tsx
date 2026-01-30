'use client';

import { useEffect, useState, useCallback } from 'react';
import { MemoryCard } from '@/components/Card';
import { PageHeader } from '@/components/Navigation';
import { Search, FilterChips } from '@/components/Search';
import { ActivityListSkeleton, EmptyState, ErrorState } from '@/components/Loading';
import { timeAgo } from '@/lib/utils';
import type { Memory, Learning, Pattern, Rule } from '@/lib/supabase';

type MemoryType = 'all' | 'memory' | 'learnings' | 'patterns' | 'rules';

interface MemoryData {
  memory: Memory[];
  learnings: Learning[];
  patterns: Pattern[];
  rules: Rule[];
}

export default function MemoryPage() {
  const [data, setData] = useState<MemoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<MemoryType>('all');
  const [search, setSearch] = useState('');
  const [selectedItem, setSelectedItem] = useState<any>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch('/api/elliot/stats?include=memory,learnings,patterns,rules');
      if (!response.ok) throw new Error('Failed to fetch memory');
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
  }, []);

  const handleSearch = useCallback((query: string) => {
    setSearch(query.toLowerCase());
  }, []);

  const filterItems = useCallback((items: any[], type: string) => {
    if (!search) return items;
    return items.filter(item => {
      const searchFields = {
        memory: ['key', 'value', 'category'],
        learnings: ['lesson', 'source', 'category'],
        patterns: ['pattern', 'description', 'category'],
        rules: ['rule', 'category', 'source'],
      }[type] || [];
      
      return searchFields.some(field => 
        item[field]?.toLowerCase().includes(search)
      );
    });
  }, [search]);

  if (loading && !data) return <ActivityListSkeleton count={6} />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;
  if (!data) return <EmptyState icon="🧠" title="No memory data" />;

  const getFilteredContent = () => {
    const items: { type: string; data: any; title: string; content: string; category: string; time: string; importance?: number }[] = [];

    if (filter === 'all' || filter === 'memory') {
      filterItems(data.memory, 'memory').forEach(m => items.push({
        type: 'memory',
        data: m,
        title: m.key,
        content: m.value,
        category: m.category,
        time: timeAgo(m.updated_at),
        importance: m.importance,
      }));
    }

    if (filter === 'all' || filter === 'learnings') {
      filterItems(data.learnings, 'learnings').forEach(l => items.push({
        type: 'learning',
        data: l,
        title: l.source || 'Learning',
        content: l.lesson,
        category: l.category,
        time: timeAgo(l.created_at),
      }));
    }

    if (filter === 'all' || filter === 'patterns') {
      filterItems(data.patterns, 'patterns').forEach(p => items.push({
        type: 'pattern',
        data: p,
        title: `Pattern (×${p.occurrences})`,
        content: p.pattern,
        category: p.category,
        time: timeAgo(p.last_seen),
      }));
    }

    if (filter === 'all' || filter === 'rules') {
      filterItems(data.rules, 'rules').forEach(r => items.push({
        type: 'rule',
        data: r,
        title: r.source || 'Rule',
        content: r.rule,
        category: r.category,
        time: timeAgo(r.created_at),
        importance: r.priority,
      }));
    }

    return items;
  };

  const filteredItems = getFilteredContent();

  return (
    <div className="space-y-4 py-4">
      <PageHeader 
        title="Memory" 
        subtitle={`${filteredItems.length} items`}
      />

      <Search 
        placeholder="Search memory, learnings, patterns..." 
        onSearch={handleSearch}
      />

      <FilterChips
        options={['memory', 'learnings', 'patterns', 'rules']}
        selected={filter === 'all' ? null : filter}
        onSelect={(opt) => setFilter((opt as MemoryType) || 'all')}
      />

      {filteredItems.length === 0 ? (
        <EmptyState 
          icon="🔍" 
          title="No results" 
          description={search ? `No matches for "${search}"` : 'No memory items found'}
        />
      ) : (
        <div className="space-y-3">
          {filteredItems.map((item, idx) => (
            <MemoryCard
              key={`${item.type}-${idx}`}
              title={item.title}
              content={item.content}
              category={item.category}
              importance={item.importance}
              time={item.time}
              onClick={() => setSelectedItem(item)}
            />
          ))}
        </div>
      )}

      {/* Detail Modal */}
      {selectedItem && (
        <div 
          className="fixed inset-0 z-50 bg-black/50 flex items-end justify-center"
          onClick={() => setSelectedItem(null)}
        >
          <div 
            className="bg-white w-full max-w-2xl rounded-t-2xl p-6 max-h-[80vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">{selectedItem.title}</h2>
              <button 
                onClick={() => setSelectedItem(null)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                ✕
              </button>
            </div>
            <div className="space-y-4">
              <p className="text-gray-700 whitespace-pre-wrap">{selectedItem.content}</p>
              <div className="flex flex-wrap gap-2 text-sm text-gray-500">
                <span className="bg-gray-100 px-2 py-1 rounded">{selectedItem.type}</span>
                <span className="bg-gray-100 px-2 py-1 rounded">{selectedItem.category}</span>
                <span>{selectedItem.time}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
