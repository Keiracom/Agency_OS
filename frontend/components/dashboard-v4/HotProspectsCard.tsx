/**
 * FILE: frontend/components/dashboard-v4/HotProspectsCard.tsx
 * PURPOSE: Card showing hot prospects with buying signals
 * PHASE: Dashboard V4 Implementation
 */

"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Flame, ArrowRight } from "lucide-react";
import type { HotProspect } from "./types";

interface HotProspectsCardProps {
  prospects: HotProspect[];
}

function ProspectItem({ prospect }: { prospect: HotProspect }) {
  const bgColor = prospect.isVeryHot 
    ? "bg-red-50 dark:bg-red-950/30 border-l-red-500" 
    : "bg-amber-50 dark:bg-amber-950/30 border-l-amber-500";
  
  const signalColor = prospect.isVeryHot 
    ? "text-red-600 dark:text-red-400" 
    : "text-amber-600 dark:text-amber-400";
  
  const scoreColor = prospect.isVeryHot 
    ? "text-red-500" 
    : "text-amber-500";

  return (
    <Link
      href={`/dashboard/leads/${prospect.id}`}
      className={`flex items-center gap-4 p-4 rounded-xl border-l-4 ${bgColor} hover:shadow-md transition-shadow`}
    >
      <Avatar className="h-11 w-11">
        <AvatarFallback className="bg-gradient-to-br from-blue-500 to-violet-500 text-white font-bold">
          {prospect.initials}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-foreground truncate">{prospect.name}</p>
        <p className="text-sm text-muted-foreground truncate">
          {prospect.company} • {prospect.title}
        </p>
        <p className={`text-xs font-medium mt-1 ${signalColor}`}>
          {prospect.signal}
        </p>
      </div>
      <div className="text-right flex-shrink-0">
        <p className={`text-xl font-extrabold ${scoreColor}`}>{prospect.score}</p>
        <p className="text-[10px] text-muted-foreground uppercase">Score</p>
      </div>
    </Link>
  );
}

export function HotProspectsCard({ prospects }: HotProspectsCardProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Flame className="h-5 w-5 text-orange-500" />
            <CardTitle className="text-base">Hot Right Now</CardTitle>
          </div>
          <Link 
            href="/dashboard/leads?tier=hot" 
            className="text-sm text-primary font-medium hover:underline flex items-center gap-1"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {prospects.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No hot prospects right now. Keep nurturing your pipeline!
          </p>
        ) : (
          <div className="space-y-3">
            {prospects.map((prospect) => (
              <ProspectItem key={prospect.id} prospect={prospect} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
