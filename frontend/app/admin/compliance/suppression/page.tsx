/**
 * FILE: frontend/app/admin/compliance/suppression/page.tsx
 * PURPOSE: Global suppression list management
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Suppression
 */

"use client";

import { useState } from "react";
import { Search, Plus, Upload, Trash2 } from "lucide-react";
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

// Mock data
const mockSuppressionList = [
  { id: "1", email: "spam@badactor.com", reason: "spam", source: "system", addedBy: "System", addedAt: new Date(Date.now() - 1000 * 60 * 60 * 24) },
  { id: "2", email: "john@unsubscribed.com", reason: "unsubscribe", source: "LeadGen Pro", addedBy: "User Request", addedAt: new Date(Date.now() - 1000 * 60 * 60 * 48) },
  { id: "3", email: "bounced@invalid.net", reason: "bounce", source: "GrowthLab", addedBy: "System", addedAt: new Date(Date.now() - 1000 * 60 * 60 * 72) },
  { id: "4", email: "competitor@rival.com", reason: "manual", source: "Admin", addedBy: "dave@agency.com", addedAt: new Date(Date.now() - 1000 * 60 * 60 * 96) },
  { id: "5", email: "noreply@company.com", reason: "manual", source: "Admin", addedBy: "dave@agency.com", addedAt: new Date(Date.now() - 1000 * 60 * 60 * 120) },
];

const reasonColors = {
  spam: "bg-red-500/10 text-red-700 border-red-500/20",
  unsubscribe: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  bounce: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  manual: "bg-gray-500/10 text-gray-700 border-gray-500/20",
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
            <div className="text-2xl font-bold text-red-600">
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
            <div className="text-2xl font-bold text-blue-600">
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
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600">
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
