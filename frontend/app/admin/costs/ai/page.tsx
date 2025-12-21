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
import { AlertCircle, TrendingUp, TrendingDown, Minus } from "lucide-react";

// Mock data
const mockSpendData = {
  today: {
    spent: 89.42,
    limit: 500,
  },
  monthToDate: {
    spent: 1247.83,
    projected: 1890,
  },
  byAgent: [
    { name: "Content Agent", spent: 523, percentage: 42 },
    { name: "Reply Agent", spent: 412, percentage: 33 },
    { name: "CMO Agent", spent: 312, percentage: 25 },
  ],
  byClient: [
    { name: "LeadGen Pro", spent: 287, change: 12 },
    { name: "GrowthLab", spent: 245, change: -5 },
    { name: "ScaleUp Co", spent: 198, change: 8 },
    { name: "Marketing Plus", spent: 156, change: 0 },
    { name: "Enterprise Co", spent: 134, change: 23 },
    { name: "StartupXYZ", spent: 89, change: -12 },
    { name: "TechVentures", spent: 67, change: 5 },
    { name: "GrowthHQ", spent: 45, change: -3 },
    { name: "SalesForce Pro", spent: 23, change: 15 },
    { name: "MarketingMax", spent: 12, change: 0 },
  ],
  dailyTrend: [
    { date: "Dec 1", spent: 78 },
    { date: "Dec 2", spent: 92 },
    { date: "Dec 3", spent: 65 },
    { date: "Dec 4", spent: 88 },
    { date: "Dec 5", spent: 103 },
    { date: "Dec 6", spent: 95 },
    { date: "Dec 7", spent: 110 },
    { date: "Dec 8", spent: 82 },
    { date: "Dec 9", spent: 76 },
    { date: "Dec 10", spent: 89 },
  ],
};

export default function AdminAISpendPage() {
  const todayPercent = Math.round(
    (mockSpendData.today.spent / mockSpendData.today.limit) * 100
  );
  const isNearLimit = todayPercent >= 80;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Spend</h1>
          <p className="text-muted-foreground">
            December 2025 - Token usage and cost tracking
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
                ${mockSpendData.today.spent.toFixed(2)}
              </span>
              <span className="text-muted-foreground mb-1">
                / ${mockSpendData.today.limit}
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
                ${mockSpendData.monthToDate.spent.toFixed(2)}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Projected end of month:{" "}
              <span className="font-medium">
                ${mockSpendData.monthToDate.projected.toFixed(2)}
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
          {mockSpendData.byAgent.map((agent) => (
            <div key={agent.name} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">{agent.name}</span>
                <span className="text-muted-foreground">
                  ${agent.spent} ({agent.percentage}%)
                </span>
              </div>
              <Progress value={agent.percentage} className="h-2" />
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
                <TableHead className="text-right">Spend (MTD)</TableHead>
                <TableHead className="text-right">vs Last Month</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockSpendData.byClient.map((client) => (
                <TableRow key={client.name}>
                  <TableCell className="font-medium">{client.name}</TableCell>
                  <TableCell className="text-right">${client.spent}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {client.change > 0 ? (
                        <TrendingUp className="h-4 w-4 text-red-500" />
                      ) : client.change < 0 ? (
                        <TrendingDown className="h-4 w-4 text-green-500" />
                      ) : (
                        <Minus className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span
                        className={
                          client.change > 0
                            ? "text-red-500"
                            : client.change < 0
                            ? "text-green-500"
                            : "text-muted-foreground"
                        }
                      >
                        {client.change > 0 ? "+" : ""}
                        {client.change}%
                      </span>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Daily Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Trend (Last 10 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end justify-between h-40 gap-2">
            {mockSpendData.dailyTrend.map((day) => {
              const height = (day.spent / 120) * 100; // max ~120
              return (
                <div
                  key={day.date}
                  className="flex flex-col items-center gap-2 flex-1"
                >
                  <span className="text-xs text-muted-foreground">
                    ${day.spent}
                  </span>
                  <div
                    className="w-full bg-primary rounded-t"
                    style={{ height: `${height}%` }}
                  />
                  <span className="text-xs text-muted-foreground">
                    {day.date.split(" ")[1]}
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
