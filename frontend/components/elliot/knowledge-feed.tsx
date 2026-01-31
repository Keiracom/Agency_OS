/**
 * FILE: frontend/components/elliot/knowledge-feed.tsx
 * PURPOSE: Knowledge Feed component for viewing learned insights
 * PHASE: Elliot Dashboard
 */

"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useKnowledge, useKnowledgeStats, type KnowledgeEntry } from "@/hooks/use-elliot";
import {
  Brain,
  RefreshCw,
  Clock,
  AlertTriangle,
  ExternalLink,
  CheckCircle2,
  Newspaper,
  Rocket,
  Github,
  MessageSquare,
  Sparkles,
  Lightbulb,
} from "lucide-react";

type SourceType = "hackernews" | "producthunt" | "github" | "manual" | "conversation" | "inference" | "all";

const sourceConfig: Record<string, { icon: typeof Newspaper; label: string; color: string }> = {
  hackernews: { icon: Newspaper, label: "Hacker News", color: "text-orange-500" },
  producthunt: { icon: Rocket, label: "Product Hunt", color: "text-red-500" },
  github: { icon: Github, label: "GitHub", color: "text-gray-700 dark:text-gray-300" },
  manual: { icon: Lightbulb, label: "Manual", color: "text-yellow-500" },
  conversation: { icon: MessageSquare, label: "Conversation", color: "text-blue-500" },
  inference: { icon: Sparkles, label: "Inference", color: "text-purple-500" },
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return "text-green-500";
  if (score >= 0.6) return "text-yellow-500";
  if (score >= 0.4) return "text-orange-500";
  return "text-red-500";
}

function KnowledgeCard({ entry }: { entry: KnowledgeEntry }) {
  const sourceType = entry.source_type || "manual";
  const config = sourceConfig[sourceType] || sourceConfig.manual;
  const SourceIcon = config.icon;
  const relevanceScore = entry.relevance_score || entry.confidence_score;

  return (
    <div className="flex items-start gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/50">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
        <SourceIcon className={`h-5 w-5 ${config.color}`} />
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="outline" className="text-xs">
            {entry.category.replace(/_/g, " ")}
          </Badge>
          <Badge variant="secondary" className="text-xs">
            {config.label}
          </Badge>
          {entry.applied && (
            <Badge variant="default" className="text-xs bg-green-600">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Applied
            </Badge>
          )}
        </div>
        
        {entry.summary && (
          <p className="font-medium">{entry.summary}</p>
        )}
        
        <p className="text-sm text-muted-foreground line-clamp-3">
          {entry.content}
        </p>
        
        <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatTimeAgo(entry.learned_at)}
          </span>
          <span className={`font-medium ${getScoreColor(relevanceScore)}`}>
            Score: {(relevanceScore * 100).toFixed(0)}%
          </span>
          {entry.source_url && (
            <a 
              href={entry.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 hover:text-primary"
            >
              <ExternalLink className="h-3 w-3" />
              Source
            </a>
          )}
          {entry.tags && entry.tags.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {entry.tags.slice(0, 3).map((tag, i) => (
                <span key={i} className="bg-muted px-1.5 py-0.5 rounded text-[10px]">
                  {tag}
                </span>
              ))}
              {entry.tags.length > 3 && (
                <span className="text-[10px]">+{entry.tags.length - 3}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatsOverview({ stats }: { stats: { bySource: Record<string, number>; total: number; applied: number } }) {
  const appliedPercent = stats.total > 0 ? (stats.applied / stats.total) * 100 : 0;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Knowledge</CardTitle>
          <Brain className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.total}</div>
          <p className="text-xs text-muted-foreground">Entries in database</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Applied</CardTitle>
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.applied}</div>
          <Progress value={appliedPercent} className="h-2 mt-2" />
          <p className="text-xs text-muted-foreground mt-1">
            {appliedPercent.toFixed(0)}% of total
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">By Source</CardTitle>
          <Sparkles className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            {Object.entries(stats.bySource).slice(0, 4).map(([source, count]) => {
              const config = sourceConfig[source] || sourceConfig.manual;
              return (
                <div key={source} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1">
                    <config.icon className={`h-3 w-3 ${config.color}`} />
                    {config.label}
                  </span>
                  <span className="font-medium">{count}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function KnowledgeFeed() {
  const [filter, setFilter] = useState<SourceType>("all");
  const { data: entries, isLoading, error, refetch } = useKnowledge(filter);
  const { data: stats, isLoading: statsLoading } = useKnowledgeStats();

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      {statsLoading ? (
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : stats ? (
        <StatsOverview stats={stats} />
      ) : null}

      {/* Knowledge List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Knowledge Feed</CardTitle>
              <CardDescription>Recently learned insights and discoveries</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Select value={filter} onValueChange={(v) => setFilter(v as SourceType)}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Source" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sources</SelectItem>
                  <SelectItem value="hackernews">Hacker News</SelectItem>
                  <SelectItem value="producthunt">Product Hunt</SelectItem>
                  <SelectItem value="github">GitHub</SelectItem>
                  <SelectItem value="manual">Manual</SelectItem>
                  <SelectItem value="conversation">Conversation</SelectItem>
                  <SelectItem value="inference">Inference</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-start gap-4 rounded-lg border p-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <AlertTriangle className="mr-2 h-5 w-5" />
              Failed to load knowledge
            </div>
          ) : !entries || entries.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Brain className="h-12 w-12 mb-2 opacity-50" />
              <p>No knowledge entries</p>
              <p className="text-sm">
                {filter === "all" 
                  ? "Knowledge will appear here as Elliot learns" 
                  : "No entries from this source yet."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {entries.map((entry) => (
                <KnowledgeCard key={entry.id} entry={entry} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
