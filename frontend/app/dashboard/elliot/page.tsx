/**
 * FILE: frontend/app/dashboard/elliot/page.tsx
 * PURPOSE: Elliot monitoring dashboard with Task, Signoff, Knowledge, and Cost views
 * PHASE: Elliot Dashboard
 */

"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TaskMonitor } from "@/components/elliot/task-monitor";
import { SignoffQueue } from "@/components/elliot/signoff-queue";
import { KnowledgeFeed } from "@/components/elliot/knowledge-feed";
import { CostOverview } from "@/components/elliot/cost-overview";
import { 
  Bot, 
  ClipboardCheck, 
  Brain, 
  DollarSign,
  Activity,
  Radio,
} from "lucide-react";
import { useTaskStats, useSignoffQueue, useRealtimeStatus } from "@/hooks/use-elliot";
import { Badge } from "@/components/ui/badge";

export default function ElliotDashboardPage() {
  const [activeTab, setActiveTab] = useState("tasks");
  const { data: taskStats } = useTaskStats();
  const { data: signoffItems } = useSignoffQueue("pending");

  const pendingSignoffs = signoffItems?.length || 0;
  const runningTasks = taskStats?.running || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <Bot className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Elliot Monitor</h1>
          <p className="text-muted-foreground">
            Agent tasks, sign-offs, knowledge, and system costs
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="outline" className="flex items-center gap-1 text-green-600 border-green-600/50">
            <Radio className="h-3 w-3 animate-pulse" />
            LIVE
          </Badge>
          {runningTasks > 0 && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Activity className="h-3 w-3 animate-pulse" />
              {runningTasks} running
            </Badge>
          )}
        </div>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="tasks" className="flex items-center gap-2">
            <Bot className="h-4 w-4" />
            <span className="hidden sm:inline">Tasks</span>
            {runningTasks > 0 && (
              <Badge variant="secondary" className="h-5 px-1.5 text-xs">
                {runningTasks}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="signoff" className="flex items-center gap-2">
            <ClipboardCheck className="h-4 w-4" />
            <span className="hidden sm:inline">Sign-off</span>
            {pendingSignoffs > 0 && (
              <Badge variant="destructive" className="h-5 px-1.5 text-xs">
                {pendingSignoffs}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="knowledge" className="flex items-center gap-2">
            <Brain className="h-4 w-4" />
            <span className="hidden sm:inline">Knowledge</span>
          </TabsTrigger>
          <TabsTrigger value="costs" className="flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            <span className="hidden sm:inline">Costs</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="space-y-4">
          <TaskMonitor />
        </TabsContent>

        <TabsContent value="signoff" className="space-y-4">
          <SignoffQueue />
        </TabsContent>

        <TabsContent value="knowledge" className="space-y-4">
          <KnowledgeFeed />
        </TabsContent>

        <TabsContent value="costs" className="space-y-4">
          <CostOverview />
        </TabsContent>
      </Tabs>
    </div>
  );
}
