/**
 * FILE: frontend/app/admin/compliance/suppression/page.tsx
 * PURPOSE: Global suppression list management
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Suppression
 */

"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Plus, Upload, Trash2 } from "lucide-react";
import { createBrowserClient } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

// Phase 4 admin Tier B wiring (2026-05-10): live query against
// `email_suppression` table from PR #664. Schema:
// id, email, client_id, reason, source, notes, created_at, deleted_at.
// Mock had `addedBy` field — schema has no per-row author column today,
// so we display `source` in its place (good enough until a created_by
// column is added in a follow-up).
type SuppressionRow = {
  id: string;
  email: string;
  reason: string;
  source: string;
  notes: string | null;
  created_at: string;
};

async function fetchSuppressionList() {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const { data, error } = await client
    .from("email_suppression")
    .select("id, email, reason, source, notes, created_at")
    .is("deleted_at", null)
    .order("created_at", { ascending: false })
    .limit(500);
  if (error) throw error;
  return ((data ?? []) as SuppressionRow[]).map((row) => ({
    id: row.id,
    email: row.email,
    reason: row.reason,
    source: row.source,
    addedBy: row.notes ?? row.source,
    addedAt: new Date(row.created_at),
  }));
}

const reasonColors = {
  spam: "bg-amber-glow text-error border-amber/20",
  unsubscribe: "bg-panel/10 text-amber border-default/20",
  bounce: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  manual: "bg-bg-surface0/10 text-ink-3 border-gray-500/20",
};

function formatDate(date: Date): string {
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function AdminSuppressionPage() {
  const [search, setSearch] = useState("");
  const [reasonFilter, setReasonFilter] = useState("all");
  const [newEmail, setNewEmail] = useState("");
  const [newReason, setNewReason] = useState("manual");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);

  const { data: mockSuppressionList = [] } = useQuery({
    queryKey: ["admin-suppression"],
    queryFn: fetchSuppressionList,
    staleTime: 30 * 1000,
  });

  const filteredList = mockSuppressionList.filter((item) => {
    const matchesSearch = item.email.toLowerCase().includes(search.toLowerCase());
    const matchesReason = reasonFilter === "all" || item.reason === reasonFilter;
    return matchesSearch && matchesReason;
  });

  const handleAddEmail = () => {
    // Would call API to add email
    console.log("Adding:", newEmail, newReason);
    setNewEmail("");
    setIsAddDialogOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Suppression List</h1>
          <p className="text-muted-foreground">
            Global email suppression management
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            Bulk Import
          </Button>
          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Email
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add to Suppression List</DialogTitle>
                <DialogDescription>
                  This email will be blocked from all future outreach.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    placeholder="email@example.com"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reason">Reason</Label>
                  <Select value={newReason} onValueChange={setNewReason}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manual">Manual Block</SelectItem>
                      <SelectItem value="unsubscribe">Unsubscribe Request</SelectItem>
                      <SelectItem value="bounce">Bounced</SelectItem>
                      <SelectItem value="spam">Spam Complaint</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleAddEmail}>Add to List</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Suppressed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSuppressionList.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Spam Complaints
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber">
              {mockSuppressionList.filter((s) => s.reason === "spam").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Unsubscribes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-ink-2">
              {mockSuppressionList.filter((s) => s.reason === "unsubscribe").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Bounces
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {mockSuppressionList.filter((s) => s.reason === "bounce").length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search emails..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={reasonFilter} onValueChange={setReasonFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Reason" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Reasons</SelectItem>
                <SelectItem value="spam">Spam</SelectItem>
                <SelectItem value="unsubscribe">Unsubscribe</SelectItem>
                <SelectItem value="bounce">Bounce</SelectItem>
                <SelectItem value="manual">Manual</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Email</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Added By</TableHead>
                <TableHead>Added Date</TableHead>
                <TableHead className="w-[50px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredList.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono">{item.email}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={reasonColors[item.reason as keyof typeof reasonColors]}
                    >
                      {item.reason}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {item.source}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {item.addedBy}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(item.addedAt)}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-amber">
                      <Trash2 className="h-4 w-4" />
                    </Button>
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
