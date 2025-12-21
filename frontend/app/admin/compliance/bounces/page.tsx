/**
 * FILE: frontend/app/admin/compliance/bounces/page.tsx
 * PURPOSE: Bounce and spam tracker for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Bounces
 */

"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AlertTriangle, XCircle } from "lucide-react";

interface BounceEntry {
  id: string;
  email: string;
  client: string;
  type: "hard" | "soft" | "spam";
  reason: string;
  timestamp: Date;
}

interface ClientBounceRate {
  client: string;
  sent: number;
  bounced: number;
  bounceRate: number;
  spamComplaints: number;
}

// Mock data
const mockBounces: BounceEntry[] = [
  { id: "1", email: "invalid@nowhere.com", client: "GrowthLab", type: "hard", reason: "Mailbox does not exist", timestamp: new Date(Date.now() - 1000 * 60 * 30) },
  { id: "2", email: "full@mailbox.com", client: "LeadGen Pro", type: "soft", reason: "Mailbox full", timestamp: new Date(Date.now() - 1000 * 60 * 60) },
  { id: "3", email: "spam@marked.com", client: "LeadGen Pro", type: "spam", reason: "Marked as spam by recipient", timestamp: new Date(Date.now() - 1000 * 60 * 90) },
  { id: "4", email: "old@domain.net", client: "ScaleUp Co", type: "hard", reason: "Domain not found", timestamp: new Date(Date.now() - 1000 * 60 * 120) },
  { id: "5", email: "temp@issue.com", client: "GrowthLab", type: "soft", reason: "Temporary delivery failure", timestamp: new Date(Date.now() - 1000 * 60 * 150) },
  { id: "6", email: "blocked@company.com", client: "Enterprise Co", type: "hard", reason: "Recipient blocked sender", timestamp: new Date(Date.now() - 1000 * 60 * 180) },
];

const mockClientRates: ClientBounceRate[] = [
  { client: "GrowthLab", sent: 450, bounced: 32, bounceRate: 7.1, spamComplaints: 2 },
  { client: "LeadGen Pro", sent: 890, bounced: 18, bounceRate: 2.0, spamComplaints: 3 },
  { client: "ScaleUp Co", sent: 320, bounced: 5, bounceRate: 1.6, spamComplaints: 0 },
  { client: "Enterprise Co", sent: 560, bounced: 8, bounceRate: 1.4, spamComplaints: 0 },
  { client: "Marketing Plus", sent: 280, bounced: 3, bounceRate: 1.1, spamComplaints: 0 },
];

const typeColors = {
  hard: "bg-red-500/10 text-red-700 border-red-500/20",
  soft: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  spam: "bg-purple-500/10 text-purple-700 border-purple-500/20",
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminBouncesPage() {
  const [typeFilter, setTypeFilter] = useState("all");

  const filteredBounces = mockBounces.filter(
    (bounce) => typeFilter === "all" || bounce.type === typeFilter
  );

  const totalBounces = mockBounces.length;
  const hardBounces = mockBounces.filter((b) => b.type === "hard").length;
  const softBounces = mockBounces.filter((b) => b.type === "soft").length;
  const spamComplaints = mockBounces.filter((b) => b.type === "spam").length;

  const clientsAtRisk = mockClientRates.filter((c) => c.bounceRate > 5).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Bounce Tracker</h1>
        <p className="text-muted-foreground">
          Email bounces and spam complaints monitoring
        </p>
      </div>

      {/* Alert if clients at risk */}
      {clientsAtRisk > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-700">
          <AlertTriangle className="h-5 w-5" />
          <div>
            <p className="font-medium">{clientsAtRisk} client(s) with high bounce rate</p>
            <p className="text-sm opacity-80">
              Bounce rate exceeds 5%. Review sending practices to avoid deliverability issues.
            </p>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Bounces (7d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalBounces}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Hard Bounces
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{hardBounces}</div>
            <p className="text-xs text-muted-foreground">Permanent failures</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Soft Bounces
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{softBounces}</div>
            <p className="text-xs text-muted-foreground">Temporary failures</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Spam Complaints
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{spamComplaints}</div>
            <p className="text-xs text-muted-foreground">User reports</p>
          </CardContent>
        </Card>
      </div>

      {/* Bounce Rate by Client */}
      <Card>
        <CardHeader>
          <CardTitle>Bounce Rate by Client</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client</TableHead>
                <TableHead>Emails Sent</TableHead>
                <TableHead>Bounced</TableHead>
                <TableHead>Bounce Rate</TableHead>
                <TableHead>Spam Complaints</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockClientRates.map((client) => (
                <TableRow key={client.client}>
                  <TableCell className="font-medium">{client.client}</TableCell>
                  <TableCell>{client.sent.toLocaleString()}</TableCell>
                  <TableCell>{client.bounced}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress
                        value={Math.min(client.bounceRate * 10, 100)}
                        className="h-2 w-16"
                      />
                      <span className={
                        client.bounceRate > 5 ? "text-red-600 font-medium" :
                        client.bounceRate > 2 ? "text-yellow-600" : ""
                      }>
                        {client.bounceRate}%
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>{client.spamComplaints}</TableCell>
                  <TableCell>
                    {client.bounceRate > 5 ? (
                      <Badge variant="outline" className="bg-red-500/10 text-red-700">
                        <XCircle className="mr-1 h-3 w-3" />
                        At Risk
                      </Badge>
                    ) : client.bounceRate > 2 ? (
                      <Badge variant="outline" className="bg-yellow-500/10 text-yellow-700">
                        <AlertTriangle className="mr-1 h-3 w-3" />
                        Monitor
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="bg-green-500/10 text-green-700">
                        Healthy
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Recent Bounces */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Bounces</CardTitle>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="hard">Hard Bounce</SelectItem>
                <SelectItem value="soft">Soft Bounce</SelectItem>
                <SelectItem value="spam">Spam</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredBounces.map((bounce) => (
                <TableRow key={bounce.id}>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatTimeAgo(bounce.timestamp)}
                  </TableCell>
                  <TableCell className="font-mono text-sm">{bounce.email}</TableCell>
                  <TableCell>{bounce.client}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={typeColors[bounce.type]}>
                      {bounce.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground max-w-[300px] truncate">
                    {bounce.reason}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
