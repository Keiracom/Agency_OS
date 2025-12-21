/**
 * FILE: frontend/app/admin/compliance/page.tsx
 * PURPOSE: Compliance overview for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Compliance Overview
 */

"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Shield,
  AlertTriangle,
  XCircle,
  PhoneOff,
  ArrowRight,
  CheckCircle,
} from "lucide-react";

// Mock data
const mockCompliance = {
  suppressionCount: 1247,
  bounceRate: 2.3,
  spamComplaints: 5,
  dncrBlocks: 23,
  lastAudit: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
  status: "healthy" as const,
  recentIssues: [
    { type: "bounce", count: 12, client: "GrowthLab" },
    { type: "spam", count: 2, client: "LeadGen Pro" },
    { type: "dncr", count: 5, client: "ScaleUp Co" },
  ],
};

export default function AdminCompliancePage() {
  const bounceStatus = mockCompliance.bounceRate < 2 ? "good" : mockCompliance.bounceRate < 5 ? "warning" : "critical";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Compliance</h1>
          <p className="text-muted-foreground">
            Email deliverability and regulatory compliance
          </p>
        </div>
        <Badge
          variant="outline"
          className={
            mockCompliance.status === "healthy"
              ? "bg-green-500/10 text-green-700"
              : "bg-yellow-500/10 text-yellow-700"
          }
        >
          <CheckCircle className="mr-1 h-3 w-3" />
          {mockCompliance.status === "healthy" ? "All Systems Compliant" : "Issues Detected"}
        </Badge>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Suppression List
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockCompliance.suppressionCount.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">emails blocked</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Bounce Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              bounceStatus === "good" ? "text-green-600" :
              bounceStatus === "warning" ? "text-yellow-600" : "text-red-600"
            }`}>
              {mockCompliance.bounceRate}%
            </div>
            <p className="text-xs text-muted-foreground">
              {bounceStatus === "good" ? "Healthy" : bounceStatus === "warning" ? "Monitor" : "Action needed"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <XCircle className="h-4 w-4" />
              Spam Complaints
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${mockCompliance.spamComplaints > 10 ? "text-red-600" : ""}`}>
              {mockCompliance.spamComplaints}
            </div>
            <p className="text-xs text-muted-foreground">this month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <PhoneOff className="h-4 w-4" />
              DNCR Blocks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockCompliance.dncrBlocks}</div>
            <p className="text-xs text-muted-foreground">Australian registry</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Suppression List
                </CardTitle>
                <CardDescription>Manage blocked emails</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/admin/compliance/suppression">
                  Manage
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Spam complaints</span>
                <span>{mockCompliance.suppressionCount * 0.15 | 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Unsubscribes</span>
                <span>{mockCompliance.suppressionCount * 0.45 | 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Bounces</span>
                <span>{mockCompliance.suppressionCount * 0.30 | 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Manual blocks</span>
                <span>{mockCompliance.suppressionCount * 0.10 | 0}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Bounce Tracker
                </CardTitle>
                <CardDescription>Monitor email deliverability</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/admin/compliance/bounces">
                  View All
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockCompliance.recentIssues.map((issue, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={
                        issue.type === "spam"
                          ? "bg-red-500/10 text-red-700"
                          : issue.type === "bounce"
                          ? "bg-yellow-500/10 text-yellow-700"
                          : "bg-gray-500/10 text-gray-700"
                      }
                    >
                      {issue.type}
                    </Badge>
                    <span className="text-muted-foreground">{issue.client}</span>
                  </div>
                  <span className="font-medium">{issue.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Compliance Guidelines */}
      <Card>
        <CardHeader>
          <CardTitle>Compliance Thresholds</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Bounce Rate</p>
              <p className="text-lg font-medium">&lt; 2%</p>
              <Badge variant="outline" className="mt-2 bg-green-500/10 text-green-700">
                Target
              </Badge>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Bounce Rate</p>
              <p className="text-lg font-medium">2-5%</p>
              <Badge variant="outline" className="mt-2 bg-yellow-500/10 text-yellow-700">
                Warning
              </Badge>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Bounce Rate</p>
              <p className="text-lg font-medium">&gt; 5%</p>
              <Badge variant="outline" className="mt-2 bg-red-500/10 text-red-700">
                Critical
              </Badge>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Spam Complaints</p>
              <p className="text-lg font-medium">&lt; 0.1%</p>
              <Badge variant="outline" className="mt-2 bg-green-500/10 text-green-700">
                Industry Standard
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
