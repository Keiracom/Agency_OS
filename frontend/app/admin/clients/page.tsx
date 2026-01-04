/**
 * FILE: frontend/app/admin/clients/page.tsx
 * PURPOSE: Admin client directory (LIVE DATA)
 * PHASE: 18 (Admin Dashboard Fixes)
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, MoreHorizontal, Eye, Pause, X, RefreshCw } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ClientHealthBadge } from "@/components/admin/ClientHealthIndicator";
import { useAdminClients } from "@/hooks/use-admin";

const tierColors: Record<string, string> = {
  ignition: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  velocity: "bg-purple-500/10 text-purple-700 border-purple-500/20",
  dominance: "bg-amber-500/10 text-amber-700 border-amber-500/20",
};

const statusColors: Record<string, string> = {
  active: "bg-green-500/10 text-green-700 border-green-500/20",
  trialing: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  past_due: "bg-red-500/10 text-red-700 border-red-500/20",
  paused: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  cancelled: "bg-gray-500/10 text-gray-700 border-gray-500/20",
};

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const date = new Date(dateStr);
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function TableSkeleton() {
  return (
    <div className="space-y-3 p-4">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex gap-4">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-16" />
        </div>
      ))}
    </div>
  );
}

export default function AdminClientsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [tierFilter, setTierFilter] = useState("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useAdminClients({
    page,
    page_size: 20,
    search: search || undefined,
    status: statusFilter !== "all" ? statusFilter : undefined,
  });

  const clients = data?.items || [];
  const total = data?.total || 0;

  // Client-side tier filter since API may not support it
  const filteredClients = tierFilter === "all"
    ? clients
    : clients.filter((c) => c.tier === tierFilter);

  const totalMRR = filteredClients.reduce((sum, c) => sum + Number(c.mrr || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Clients</h1>
          <p className="text-muted-foreground">
            {total} clients | ${totalMRR.toLocaleString()} MRR
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search clients..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="trialing">Trialing</SelectItem>
                <SelectItem value="past_due">Past Due</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Select value={tierFilter} onValueChange={setTierFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Tier" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tiers</SelectItem>
                <SelectItem value="ignition">Ignition</SelectItem>
                <SelectItem value="velocity">Velocity</SelectItem>
                <SelectItem value="dominance">Dominance</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <TableSkeleton />
          ) : error ? (
            <div className="p-8 text-center text-muted-foreground">
              <p>Failed to load clients</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          ) : filteredClients.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No clients found
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Client</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>MRR</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Campaigns</TableHead>
                  <TableHead>Leads</TableHead>
                  <TableHead>Last Activity</TableHead>
                  <TableHead>Health</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredClients.map((client) => (
                  <TableRow key={client.id}>
                    <TableCell>
                      <Link
                        href={`/admin/clients/${client.id}`}
                        className="font-medium hover:underline"
                      >
                        {client.name}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={tierColors[client.tier] || ""}>
                        {client.tier}
                      </Badge>
                    </TableCell>
                    <TableCell>${Number(client.mrr || 0).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={statusColors[client.subscription_status] || ""}>
                        {client.subscription_status?.replace("_", " ") || "unknown"}
                      </Badge>
                    </TableCell>
                    <TableCell>{client.campaigns_count || 0}</TableCell>
                    <TableCell>{(client.leads_count || 0).toLocaleString()}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatTimeAgo(client.last_activity ?? client.last_activity_at ?? null)}
                    </TableCell>
                    <TableCell>
                      <ClientHealthBadge score={client.health_score || 0} />
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem asChild>
                            <Link href={`/admin/clients/${client.id}`}>
                              <Eye className="mr-2 h-4 w-4" />
                              View Details
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Eye className="mr-2 h-4 w-4" />
                            Impersonate
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem>
                            <Pause className="mr-2 h-4 w-4" />
                            Pause Subscription
                          </DropdownMenuItem>
                          <DropdownMenuItem className="text-red-600">
                            <X className="mr-2 h-4 w-4" />
                            Cancel Subscription
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Previous
          </Button>
          <span className="py-2 px-4 text-sm text-muted-foreground">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
