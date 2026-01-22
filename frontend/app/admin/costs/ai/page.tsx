/**
 * FILE: frontend/app/admin/costs/ai/page.tsx
 * PURPOSE: AI spend dashboard for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - AI Costs
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AlertCircle, TrendingUp, TrendingDown, Minus, Loader2 } from "lucide-react";
import { useAISpend } from "@/hooks/use-admin";

// Agent name mapping for display
const agentDisplayNames: Record<string, string> = {
  content: "Content Agent",
  reply: "Reply Agent",
  cmo: "CMO Agent",
};

export default function AdminAISpendPage() {
  const { data: spendData, isLoading, error } = useAISpend();

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Error state
  if (error || !spendData) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-lg font-medium">Failed to load AI spend data</p>
          <p className="text-muted-foreground">Please try refreshing the page</p>
        </div>
      </div>
    );
  }

  const todayPercent = Math.round(spendData.today_percentage || 0);
  const isNearLimit = todayPercent >= 80;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Spend</h1>
          <p className="text-muted-foreground">
            {new Date().toLocaleDateString("en-AU", { month: "long", year: "numeric" })} - Token usage and cost tracking
          </p>
        </div>
      </div>

      {/* Alert if near limit */}
      {isNearLimit && (
        <div className="flex items-center gap-3 rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-4 text-yellow-700">
          <AlertCircle className="h-5 w-5" />
          <div>
            <p className="font-medium">Approaching daily limit</p>
            <p className="text-sm opacity-80">
              {todayPercent}% of daily AI spend limit consumed. Circuit breaker
              will activate at 100%.
            </p>
          </div>
        </div>
      )}

      {/* Today and MTD */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 mb-4">
              <span className="text-3xl font-bold">
                ${Number(spendData.today_spend || 0).toFixed(2)}
              </span>
              <span className="text-muted-foreground mb-1">
                / ${Number(spendData.today_limit || 500).toFixed(0)}
              </span>
            </div>
            <Progress value={todayPercent} className="h-3" />
            <p className="text-sm text-muted-foreground mt-2">
              {todayPercent}% of daily limit
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Month to Date
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2 mb-4">
              <span className="text-3xl font-bold">
                ${Number(spendData.mtd_spend || 0).toFixed(2)}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Projected end of month:{" "}
              <span className="font-medium">
                ${Number(spendData.projected_mtd || 0).toFixed(2)}
              </span>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* By Agent */}
      <Card>
        <CardHeader>
          <CardTitle>Spend by Agent</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {(spendData.by_agent || []).map((agent) => (
            <div key={agent.agent} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {agentDisplayNames[agent.agent] || agent.agent}
                </span>
                <span className="text-muted-foreground">
                  ${Number(agent.spend_aud || 0).toFixed(2)} ({agent.percentage?.toFixed(0) || 0}%)
                </span>
              </div>
              <Progress value={agent.percentage || 0} className="h-2" />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* By Client */}
      <Card>
        <CardHeader>
          <CardTitle>Spend by Client (Top 10)</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client</TableHead>
                <TableHead className="text-right">Spend (Today)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(spendData.by_client || []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={2} className="text-center text-muted-foreground py-8">
                    No client spend data available
                  </TableCell>
                </TableRow>
              ) : (
                (spendData.by_client || []).map((client) => (
                  <TableRow key={client.client_id}>
                    <TableCell className="font-medium">{client.client_name}</TableCell>
                    <TableCell className="text-right">
                      ${Number(client.spend_aud || 0).toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Daily Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Trend (Last 7 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end justify-between h-40 gap-2">
            {(spendData.daily_trend || []).map((day, index) => {
              const maxSpend = Math.max(...(spendData.daily_trend || []).map((d) => d.spend || 0), 1);
              const height = ((day.spend || 0) / maxSpend) * 100;
              const dateLabel = day.date ? day.date.split("-").slice(1).join("/") : `Day ${index + 1}`;
              return (
                <div
                  key={day.date || index}
                  className="flex flex-col items-center gap-2 flex-1"
                >
                  <span className="text-xs text-muted-foreground">
                    ${(day.spend || 0).toFixed(0)}
                  </span>
                  <div
                    className="w-full bg-primary rounded-t min-h-[4px]"
                    style={{ height: `${Math.max(height, 2)}%` }}
                  />
                  <span className="text-xs text-muted-foreground">
                    {dateLabel}
                  </span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Model Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Model Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <p className="font-medium">Claude Sonnet</p>
                <p className="text-sm text-muted-foreground">Primary model</p>
              </div>
              <Badge variant="outline">78%</Badge>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <p className="font-medium">Claude Haiku</p>
                <p className="text-sm text-muted-foreground">Fast tasks</p>
              </div>
              <Badge variant="outline">18%</Badge>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <p className="font-medium">Claude Opus</p>
                <p className="text-sm text-muted-foreground">Complex tasks</p>
              </div>
              <Badge variant="outline">4%</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
