/**
 * FILE: frontend/components/elliot/cost-overview.tsx
 * PURPOSE: Cost Overview component showing monthly service spend
 * PHASE: Elliot Dashboard
 */

"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useCosts, type CostCategory } from "@/hooks/use-elliot";
import {
  DollarSign,
  Server,
  Brain,
  Users,
  Mail,
  Linkedin,
  Phone,
  MessageSquare,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
} from "lucide-react";

const categoryIcons: Record<string, typeof Server> = {
  "Core Infrastructure": Server,
  "AI/LLM": Brain,
  "Lead Enrichment": Users,
  "Email Channel": Mail,
  "LinkedIn Channel": Linkedin,
  "Voice Channel": Phone,
  "SMS/Mail": MessageSquare,
};

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function CostCategoryCard({ category }: { category: CostCategory }) {
  const Icon = categoryIcons[category.name] || Server;
  const midEstimate = (category.lowEstimate + category.highEstimate) / 2;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{category.name}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold">{formatCurrency(midEstimate)}</span>
          <span className="text-xs text-muted-foreground">
            /mo est.
          </span>
        </div>
        <div className="text-xs text-muted-foreground mt-1">
          Range: {formatCurrency(category.lowEstimate)} - {formatCurrency(category.highEstimate)}
        </div>
        
        <div className="mt-4 space-y-2">
          {category.services.slice(0, 4).map((service, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className="truncate">{service.name}</span>
              <span className="font-medium text-muted-foreground ml-2 shrink-0">
                {service.cost}
              </span>
            </div>
          ))}
          {category.services.length > 4 && (
            <div className="text-xs text-muted-foreground text-center pt-1">
              +{category.services.length - 4} more
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryCards({ summary }: { summary: { low: number; high: number } }) {
  const midEstimate = (summary.low + summary.high) / 2;
  const range = summary.high - summary.low;
  
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card className="bg-gradient-to-br from-primary/10 to-primary/5">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Monthly Estimate</CardTitle>
          <DollarSign className="h-4 w-4 text-primary" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">{formatCurrency(midEstimate)}</div>
          <p className="text-xs text-muted-foreground mt-1">
            Average of low/high estimates
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Low Estimate</CardTitle>
          <TrendingDown className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">{formatCurrency(summary.low)}</div>
          <p className="text-xs text-muted-foreground mt-1">
            Minimum expected spend
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">High Estimate</CardTitle>
          <TrendingUp className="h-4 w-4 text-red-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">{formatCurrency(summary.high)}</div>
          <p className="text-xs text-muted-foreground mt-1">
            Maximum expected spend
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function CostBreakdownChart({ categories }: { categories: CostCategory[] }) {
  const totalMid = categories.reduce((sum, c) => sum + (c.lowEstimate + c.highEstimate) / 2, 0);
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost Breakdown</CardTitle>
        <CardDescription>Proportion of spend by category</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {categories.map((category, i) => {
            const midEstimate = (category.lowEstimate + category.highEstimate) / 2;
            const percent = (midEstimate / totalMid) * 100;
            const Icon = categoryIcons[category.name] || Server;
            
            return (
              <div key={i} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    {category.name}
                  </span>
                  <span className="font-medium">
                    {formatCurrency(midEstimate)}
                    <span className="text-muted-foreground ml-1 text-xs">
                      ({percent.toFixed(0)}%)
                    </span>
                  </span>
                </div>
                <Progress value={percent} className="h-2" />
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function CostOptimizationTips() {
  const tips = [
    {
      title: "Batch API Calls",
      description: "Anthropic offers 50% off for batch processing",
      savings: "Up to 50% on LLM costs",
    },
    {
      title: "Prompt Caching",
      description: "Reduces costs for repeated context in LLM calls",
      savings: "20-40% on LLM costs",
    },
    {
      title: "Annual Billing",
      description: "Most services offer discounts for yearly commitment",
      savings: "15-20% across services",
    },
    {
      title: "Tiered Enrichment",
      description: "Use expensive sources only when cheaper ones fail",
      savings: "30-50% on enrichment",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Optimization Tips</CardTitle>
        <CardDescription>Ways to reduce operational costs</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {tips.map((tip, i) => (
            <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-500/20">
                <DollarSign className="h-4 w-4 text-green-600" />
              </div>
              <div>
                <p className="font-medium text-sm">{tip.title}</p>
                <p className="text-xs text-muted-foreground">{tip.description}</p>
                <Badge variant="secondary" className="mt-1 text-xs">
                  {tip.savings}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function CostOverview() {
  const { data, isLoading, error } = useCosts();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-10 w-20" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
                <Skeleton className="h-4 w-32 mt-2" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <AlertTriangle className="mr-2 h-5 w-5 text-muted-foreground" />
          <span className="text-muted-foreground">Failed to load cost data</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <SummaryCards summary={data.summary} />

      {/* Category Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {data.categories.slice(0, 4).map((category, i) => (
          <CostCategoryCard key={i} category={category} />
        ))}
      </div>
      
      {data.categories.length > 4 && (
        <div className="grid gap-4 md:grid-cols-3">
          {data.categories.slice(4).map((category, i) => (
            <CostCategoryCard key={i} category={category} />
          ))}
        </div>
      )}

      {/* Breakdown & Tips */}
      <div className="grid gap-4 md:grid-cols-2">
        <CostBreakdownChart categories={data.categories} />
        <CostOptimizationTips />
      </div>

      {/* Note about data source */}
      <Card className="bg-muted/30">
        <CardContent className="py-3">
          <p className="text-xs text-muted-foreground text-center">
            💡 Cost estimates are derived from <code>knowledge/costs.md</code> and may vary based on actual usage.
            For real-time cost tracking, connect to billing APIs.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
