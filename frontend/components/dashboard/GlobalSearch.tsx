/**
 * GlobalSearch.tsx - Global Command Palette Search
 * Phase: Operation Modular Cockpit
 * 
 * Features:
 * - Cmd+K to open modal
 * - Search across leads, campaigns, replies
 * - Categorized results with keyboard navigation
 * - Bloomberg dark mode glassmorphic styling
 */

"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";
import {
  Search,
  X,
  User,
  Mail,
  Megaphone,
  MessageSquare,
  ArrowRight,
  CornerDownLeft,
  ChevronUp,
  ChevronDown,
  Hash,
  Building2,
  Sparkles,
  Clock,
  TrendingUp,
} from "lucide-react";

// ============================================
// Types
// ============================================

export type SearchCategory = "lead" | "campaign" | "reply" | "action";

export interface SearchResult {
  id: string;
  category: SearchCategory;
  title: string;
  subtitle: string;
  meta?: string;
  icon?: React.ReactNode;
  href?: string;
  action?: () => void;
  score?: number;
  tier?: string;
}

export interface GlobalSearchProps {
  /** Whether the search modal is open */
  isOpen: boolean;
  /** Called when modal should close */
  onClose: () => void;
  /** Called when a result is selected */
  onSelect?: (result: SearchResult) => void;
  /** Custom search function - returns results for a query */
  onSearch?: (query: string) => Promise<SearchResult[]>;
  /** Placeholder text */
  placeholder?: string;
  /** Recent searches */
  recentSearches?: string[];
  /** Quick actions shown when no query */
  quickActions?: SearchResult[];
}

// ============================================
// Default Quick Actions
// ============================================

const defaultQuickActions: SearchResult[] = [
  {
    id: "action-new-campaign",
    category: "action",
    title: "Create new campaign",
    subtitle: "Start a new outreach campaign",
    icon: <Megaphone className="w-4 h-4" />,
    action: () => console.log("New campaign"),
  },
  {
    id: "action-import-leads",
    category: "action",
    title: "Import leads",
    subtitle: "Upload CSV or connect CRM",
    icon: <User className="w-4 h-4" />,
    action: () => console.log("Import leads"),
  },
  {
    id: "action-view-replies",
    category: "action",
    title: "View unread replies",
    subtitle: "Jump to inbox",
    icon: <MessageSquare className="w-4 h-4" />,
    href: "/dashboard/replies",
  },
  {
    id: "action-analytics",
    category: "action",
    title: "View analytics",
    subtitle: "Campaign performance reports",
    icon: <TrendingUp className="w-4 h-4" />,
    href: "/dashboard/reports",
  },
];

// ============================================
// Mock Search Function (Replace with real API)
// ============================================

const mockSearch = async (query: string): Promise<SearchResult[]> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 150));
  
  if (!query.trim()) return [];
  
  const q = query.toLowerCase();
  
  // Mock data - replace with real API calls
  const mockLeads: SearchResult[] = [
    { id: "lead-1", category: "lead", title: "David Park", subtitle: "CEO at Momentum Media", meta: "ALS 92", tier: "hot" },
    { id: "lead-2", category: "lead", title: "Sarah Chen", subtitle: "CTO at TechFlow", meta: "ALS 85", tier: "warm" },
    { id: "lead-3", category: "lead", title: "Mike Rodriguez", subtitle: "VP Sales at Growthly", meta: "ALS 78", tier: "warm" },
    { id: "lead-4", category: "lead", title: "Emma Wilson", subtitle: "Director at ScaleUp", meta: "ALS 65", tier: "cold" },
    { id: "lead-5", category: "lead", title: "James Liu", subtitle: "Founder at DataDriven", meta: "ALS 91", tier: "hot" },
  ];
  
  const mockCampaigns: SearchResult[] = [
    { id: "camp-1", category: "campaign", title: "SaaS Founders Q1", subtitle: "Active • 2,450 leads • 12% reply rate", meta: "Active" },
    { id: "camp-2", category: "campaign", title: "Enterprise Tech Leaders", subtitle: "Active • 890 leads • 8% reply rate", meta: "Active" },
    { id: "camp-3", category: "campaign", title: "Agency Decision Makers", subtitle: "Paused • 1,200 leads • 15% reply rate", meta: "Paused" },
    { id: "camp-4", category: "campaign", title: "SMB Outreach Pilot", subtitle: "Draft • 0 leads", meta: "Draft" },
  ];
  
  const mockReplies: SearchResult[] = [
    { id: "reply-1", category: "reply", title: "Meeting request from David Park", subtitle: "Yes, I'd be interested in learning more...", meta: "2h ago" },
    { id: "reply-2", category: "reply", title: "Question from Sarah Chen", subtitle: "Can you send me more details about pricing?", meta: "5h ago" },
    { id: "reply-3", category: "reply", title: "Interest from Mike Rodriguez", subtitle: "This looks interesting, let me check with...", meta: "1d ago" },
  ];
  
  // Filter by query
  const filterResults = (items: SearchResult[]) =>
    items.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q)
    );
  
  const leads = filterResults(mockLeads).map((l) => ({
    ...l,
    icon: <User className="w-4 h-4" />,
    href: `/dashboard/leads/${l.id}`,
  }));
  
  const campaigns = filterResults(mockCampaigns).map((c) => ({
    ...c,
    icon: <Megaphone className="w-4 h-4" />,
    href: `/dashboard/campaigns/${c.id}`,
  }));
  
  const replies = filterResults(mockReplies).map((r) => ({
    ...r,
    icon: <MessageSquare className="w-4 h-4" />,
    href: `/dashboard/replies/${r.id}`,
  }));
  
  return [...leads, ...campaigns, ...replies];
};

// ============================================
// Category Badge
// ============================================

function CategoryBadge({ category }: { category: SearchCategory }) {
  const styles: Record<SearchCategory, { bg: string; text: string; label: string }> = {
    lead: { bg: "bg-bg-elevated/20", text: "text-text-secondary", label: "Lead" },
    campaign: { bg: "bg-amber/20", text: "text-amber", label: "Campaign" },
    reply: { bg: "bg-amber/20", text: "text-amber", label: "Reply" },
    action: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Action" },
  };
  
  const style = styles[category];
  
  return (
    <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}

// ============================================
// Tier Badge (for leads)
// ============================================

function TierIndicator({ tier }: { tier?: string }) {
  if (!tier) return null;
  
  const styles: Record<string, string> = {
    hot: "bg-gradient-to-r from-orange-500 to-amber",
    warm: "bg-gradient-to-r from-amber-500 to-amber-light",
    cold: "bg-gradient-to-r from-slate-500 to-slate-600",
  };
  
  return (
    <div className={`w-1.5 h-8 rounded-full ${styles[tier] || styles.cold}`} />
  );
}

// ============================================
// Search Result Item
// ============================================

function ResultItem({
  result,
  isSelected,
  onClick,
}: {
  result: SearchResult;
  isSelected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        w-full flex items-center gap-3 px-4 py-3
        transition-all duration-150 text-left
        ${isSelected
          ? "bg-bg-surface/10 border-l-2 border-default"
          : "hover:bg-bg-surface/5 border-l-2 border-transparent"
        }
      `}
    >
      {/* Tier indicator for leads */}
      {result.category === "lead" && <TierIndicator tier={result.tier} />}
      
      {/* Icon */}
      <div className={`
        flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
        ${result.category === "action" ? "bg-amber-500/20 text-amber-400" : "bg-bg-surface/5 text-text-secondary"}
      `}>
        {result.icon}
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium truncate ${isSelected ? "text-text-primary" : "text-text-secondary"}`}>
            {result.title}
          </span>
          <CategoryBadge category={result.category} />
        </div>
        <p className="text-xs text-text-muted truncate mt-0.5">
          {result.subtitle}
        </p>
      </div>
      
      {/* Meta */}
      {result.meta && (
        <span className={`
          text-xs flex-shrink-0
          ${result.category === "lead" && result.tier === "hot" ? "text-orange-400 font-medium" : "text-text-muted"}
        `}>
          {result.meta}
        </span>
      )}
      
      {/* Arrow */}
      <ArrowRight className={`w-4 h-4 flex-shrink-0 transition-opacity ${isSelected ? "text-text-secondary opacity-100" : "text-text-muted opacity-0"}`} />
    </button>
  );
}

// ============================================
// Grouped Results
// ============================================

function GroupedResults({
  results,
  selectedIndex,
  onSelect,
}: {
  results: SearchResult[];
  selectedIndex: number;
  onSelect: (result: SearchResult) => void;
}) {
  // Group by category
  const grouped = useMemo(() => {
    const groups: Record<SearchCategory, SearchResult[]> = {
      lead: [],
      campaign: [],
      reply: [],
      action: [],
    };
    
    results.forEach((r) => {
      groups[r.category].push(r);
    });
    
    return groups;
  }, [results]);
  
  const categoryLabels: Record<SearchCategory, { label: string; icon: React.ReactNode }> = {
    lead: { label: "Leads", icon: <User className="w-3.5 h-3.5" /> },
    campaign: { label: "Campaigns", icon: <Megaphone className="w-3.5 h-3.5" /> },
    reply: { label: "Replies", icon: <MessageSquare className="w-3.5 h-3.5" /> },
    action: { label: "Quick Actions", icon: <Sparkles className="w-3.5 h-3.5" /> },
  };
  
  let flatIndex = 0;
  
  return (
    <div className="py-2">
      {(["lead", "campaign", "reply", "action"] as SearchCategory[]).map((category) => {
        const items = grouped[category];
        if (items.length === 0) return null;
        
        const { label, icon } = categoryLabels[category];
        
        return (
          <div key={category}>
            {/* Category Header */}
            <div className="flex items-center gap-2 px-4 py-2 text-xs text-text-muted font-medium uppercase tracking-wider">
              {icon}
              {label}
              <span className="ml-auto bg-bg-surface/5 px-1.5 py-0.5 rounded text-[10px]">
                {items.length}
              </span>
            </div>
            
            {/* Items */}
            {items.map((result) => {
              const idx = flatIndex++;
              return (
                <ResultItem
                  key={result.id}
                  result={result}
                  isSelected={idx === selectedIndex}
                  onClick={() => onSelect(result)}
                />
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

// ============================================
// Empty State / Quick Actions
// ============================================

function EmptyState({
  query,
  quickActions,
  recentSearches,
  selectedIndex,
  onSelect,
  onRecentClick,
}: {
  query: string;
  quickActions: SearchResult[];
  recentSearches: string[];
  selectedIndex: number;
  onSelect: (result: SearchResult) => void;
  onRecentClick: (query: string) => void;
}) {
  if (query && query.length > 0) {
    return (
      <div className="py-12 text-center">
        <Search className="w-12 h-12 text-text-muted mx-auto mb-3" />
        <p className="text-sm text-text-secondary">No results found for "{query}"</p>
        <p className="text-xs text-text-muted mt-1">Try a different search term</p>
      </div>
    );
  }
  
  return (
    <div className="py-2">
      {/* Recent Searches */}
      {recentSearches.length > 0 && (
        <>
          <div className="flex items-center gap-2 px-4 py-2 text-xs text-text-muted font-medium uppercase tracking-wider">
            <Clock className="w-3.5 h-3.5" />
            Recent Searches
          </div>
          <div className="px-4 pb-3 flex flex-wrap gap-2">
            {recentSearches.slice(0, 5).map((search, i) => (
              <button
                key={i}
                onClick={() => onRecentClick(search)}
                className="px-3 py-1.5 text-xs text-text-secondary bg-bg-surface/5 hover:bg-bg-surface/10 rounded-lg transition-colors"
              >
                {search}
              </button>
            ))}
          </div>
        </>
      )}
      
      {/* Quick Actions */}
      <GroupedResults
        results={quickActions}
        selectedIndex={selectedIndex}
        onSelect={onSelect}
      />
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function GlobalSearch({
  isOpen,
  onClose,
  onSelect,
  onSearch = mockSearch,
  placeholder = "Search leads, campaigns, replies...",
  recentSearches = [],
  quickActions = defaultQuickActions,
}: GlobalSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const [mounted, setMounted] = useState(false);

  // Client-side only mounting for portal
  useEffect(() => {
    setMounted(true);
  }, []);

  // Get all selectable items
  const selectableItems = useMemo(() => {
    if (query.trim()) {
      return results;
    }
    return quickActions;
  }, [query, results, quickActions]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setResults([]);
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Search handler with debounce
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setSelectedIndex(0);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const searchResults = await onSearch(query);
        setResults(searchResults);
        setSelectedIndex(0);
      } catch (err) {
        console.error("Search error:", err);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query, onSearch]);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < selectableItems.length - 1 ? prev + 1 : 0
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev > 0 ? prev - 1 : selectableItems.length - 1
          );
          break;
        case "Enter":
          e.preventDefault();
          if (selectableItems[selectedIndex]) {
            handleSelect(selectableItems[selectedIndex]);
          }
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    },
    [selectableItems, selectedIndex, onClose]
  );

  // Handle result selection
  const handleSelect = useCallback(
    (result: SearchResult) => {
      if (result.action) {
        result.action();
      }
      onSelect?.(result);
      onClose();
    },
    [onSelect, onClose]
  );

  // Handle recent search click
  const handleRecentClick = useCallback((searchQuery: string) => {
    setQuery(searchQuery);
  }, []);

  // Close on backdrop click
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  if (!mounted || !isOpen) return null;

  const content = (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
      onClick={handleBackdropClick}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" />

      {/* Modal */}
      <div
        className="
          relative w-full max-w-2xl mx-4
          bg-bg-void/95 backdrop-blur-xl
          border border-white/10
          rounded-2xl shadow-2xl shadow-black/50
          overflow-hidden
          animate-in fade-in slide-in-from-top-4 duration-200
        "
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-white/10">
          <Search className={`w-5 h-5 flex-shrink-0 ${loading ? "animate-pulse text-text-secondary" : "text-text-secondary"}`} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="
              flex-1 bg-transparent text-text-primary text-base
              placeholder:text-text-muted focus:outline-none
            "
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="p-1 text-text-secondary hover:text-text-primary transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <div className="flex items-center gap-1 text-text-muted text-xs">
            <kbd className="px-1.5 py-0.5 bg-bg-surface/5 border border-white/10 rounded text-[10px]">esc</kbd>
            <span>to close</span>
          </div>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto">
          {query.trim() ? (
            results.length > 0 ? (
              <GroupedResults
                results={results}
                selectedIndex={selectedIndex}
                onSelect={handleSelect}
              />
            ) : loading ? (
              <div className="py-12 text-center">
                <div className="w-8 h-8 border-2 border-default/30 border-t-amber rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-text-secondary">Searching...</p>
              </div>
            ) : (
              <EmptyState
                query={query}
                quickActions={quickActions}
                recentSearches={recentSearches}
                selectedIndex={selectedIndex}
                onSelect={handleSelect}
                onRecentClick={handleRecentClick}
              />
            )
          ) : (
            <EmptyState
              query=""
              quickActions={quickActions}
              recentSearches={recentSearches}
              selectedIndex={selectedIndex}
              onSelect={handleSelect}
              onRecentClick={handleRecentClick}
            />
          )}
        </div>

        {/* Footer with keyboard hints */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-white/10 bg-bg-surface/[0.02]">
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <div className="flex items-center gap-1.5">
              <kbd className="px-1.5 py-0.5 bg-bg-surface/5 border border-white/10 rounded text-[10px] flex items-center gap-0.5">
                <ChevronUp className="w-2.5 h-2.5" />
                <ChevronDown className="w-2.5 h-2.5" />
              </kbd>
              <span>navigate</span>
            </div>
            <div className="flex items-center gap-1.5">
              <kbd className="px-1.5 py-0.5 bg-bg-surface/5 border border-white/10 rounded text-[10px]">
                <CornerDownLeft className="w-2.5 h-2.5" />
              </kbd>
              <span>select</span>
            </div>
          </div>
          <div className="text-xs text-text-muted">
            Powered by Agency OS
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}

// ============================================
// Hook for Global Search State
// ============================================

export function useGlobalSearch() {
  const [isOpen, setIsOpen] = useState(false);

  // Global Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Listen for custom event from Header SearchTrigger
  useEffect(() => {
    const handleOpen = () => setIsOpen(true);
    window.addEventListener("open-global-search", handleOpen);
    return () => window.removeEventListener("open-global-search", handleOpen);
  }, []);

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen((prev) => !prev),
  };
}

export default GlobalSearch;
