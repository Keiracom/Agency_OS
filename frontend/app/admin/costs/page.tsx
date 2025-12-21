/**
 * FILE: frontend/app/admin/costs/page.tsx
 * PURPOSE: Costs overview for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Costs Overview
 */

"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Cpu, Send, ArrowRight, TrendingUp, TrendingDown } from "lucide-react";

// Mock data
const mockCosts = {
  totalMTD: 2847.52,
  aiCosts: 1247.83,
  channelCosts: 1599.69,
  lastMonth: 2650.00,
  projectedEOM: 3200.00,
  byCategory: {
    ai: {
      content: 523,
      reply: 412,
      cmo: 312,
    },
    channels: {
      email: 456,
      sms: 389,
      linkedin: 534,
      voice: 156,
      mail: 64,
    },
  },
};

export default function AdminCostsOverviewPage() {
  const changePercent = ((mockCosts.totalMTD - mockCosts.lastMonth) / mockCosts.lastMonth) * 100;
  const aiPercent = Math.round((mockCosts.aiCosts / mockCosts.totalMTD) * 100);
  const channelPercent = 100 - aiPercent;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Costs Overview</h1>
        <p className="text-muted-foreground">
          Platform-wide cost tracking and analysis
        </p>
      </div>

      {/* Total Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total MTD
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${mockCosts.totalMTD.toLocaleString()}</div>
            <div className="flex items-center gap-1 mt-1">
              {changePercent > 0 ? (
                <TrendingUp className="h-4 w-4 text-red-500" />
              ) : (
                <TrendingDown className="h-4 w-4 text-green-500" />
              )}
              <span className={changePercent > 0 ? "text-red-500" : "text-green-500"}>
                {changePercent > 0 ? "+" : ""}
                {changePercent.toFixed(1)}% vs last month
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Last Month
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${mockCosts.lastMonth.toLocaleString()}</div>
            <p className="text-sm text-muted-foreground mt-1">November 2025</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Projected EOM
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${mockCosts.projectedEOM.toLocaleString()}</div>
            <p className="text-sm text-muted-foreground mt-1">Based on current run rate</p>
          </CardContent>
        </Card>
      </div>

      {/* Cost Breakdown */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* AI Costs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Cpu className="h-5 w-5" />
                  AI Costs
                </CardTitle>
                <CardDescription>Anthropic API usage</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/admin/costs/ai">
                  View Details
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-4">
              ${mockCosts.aiCosts.toLocaleString()}
              <span className="text-sm font-normal text-muted-foreground ml-2">
                ({aiPercent}% of total)
              </span>
            </div>
            <div className="space-y-3">
              {Object.entries(mockCosts.byCategory.ai).map(([agent, cost]) => (
                <div key={agent} className="flex items-center justify-between">
                  <span className="capitalize">{agent} Agent</span>
                  <span className="font-medium">${cost}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Channel Costs */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Send className="h-5 w-5" />
                  Channel Costs
                </CardTitle>
                <CardDescription>Outreach platform usage</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/admin/costs/channels">
                  View Details
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-4">
              ${mockCosts.channelCosts.toLocaleString()}
              <span className="text-sm font-normal text-muted-foreground ml-2">
                ({channelPercent}% of total)
              </span>
            </div>
            <div className="space-y-3">
              {Object.entries(mockCosts.byCategory.channels).map(([channel, cost]) => (
                <div key={channel} className="flex items-center justify-between">
                  <span className="capitalize">{channel}</span>
                  <span className="font-medium">${cost}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cost Distribution Visual */}
      <Card>
        <CardHeader>
          <CardTitle>Cost Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-8 rounded-lg overflow-hidden">
            <div
              className="bg-purple-500 flex items-center justify-center text-white text-sm font-medium"
              style={{ width: `${aiPercent}%` }}
            >
              AI {aiPercent}%
            </div>
            <div
              className="bg-blue-500 flex items-center justify-center text-white text-sm font-medium"
              style={{ width: `${channelPercent}%` }}
            >
              Channels {channelPercent}%
            </div>
          </div>
          <div className="flex justify-between mt-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded bg-purple-500" />
              AI Costs (Anthropic)
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded bg-blue-500" />
              Channel Costs (Email, SMS, LinkedIn, Voice, Mail)
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
