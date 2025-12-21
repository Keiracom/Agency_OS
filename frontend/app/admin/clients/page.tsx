/**
 * FILE: frontend/app/admin/clients/page.tsx
 * PURPOSE: Admin client directory
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Clients
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, Filter, MoreHorizontal, Eye, Pause, X } from "lucide-react";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ClientHealthBadge } from "@/components/admin/ClientHealthIndicator";

interface Client {
  id: string;
  name: string;
  tier: "ignition" | "velocity" | "dominance";
  mrr: number;
  status: "active" | "trialing" | "past_due" | "paused" | "cancelled";
  campaigns: number;
  leads: number;
  lastActivity: Date;
  healthScore: number;
}

// Mock data
const mockClients: Client[] = [
  {
    id: "1",
    name: "LeadGen Pro",
    tier: "dominance",
    mrr: 999,
    status: "active",
    campaigns: 5,
    leads: 2340,
    lastActivity: new Date(Date.now() - 1000 * 60 * 5),
    healthScore: 92,
  },
  {
    id: "2",
    name: "GrowthLab",
    tier: "velocity",
    mrr: 499,
    status: "active",
    campaigns: 3,
    leads: 1456,
    lastActivity: new Date(Date.now() - 1000 * 60 * 30),
    healthScore: 45,
  },
  {
    id: "3",
    name: "ScaleUp Co",
    tier: "velocity",
    mrr: 499,
    status: "active",
    campaigns: 2,
    leads: 890,
    lastActivity: new Date(Date.now() - 1000 * 60 * 60 * 50),
    healthScore: 28,
  },
  {
    id: "4",
    name: "Marketing Plus",
    tier: "ignition",
    mrr: 199,
    status: "trialing",
    campaigns: 1,
    leads: 245,
    lastActivity: new Date(Date.now() - 1000 * 60 * 60 * 2),
    healthScore: 78,
  },
  {
    id: "5",
    name: "Enterprise Co",
    tier: "dominance",
    mrr: 999,
    status: "active",
    campaigns: 8,
    leads: 4567,
    lastActivity: new Date(Date.now() - 1000 * 60 * 15),
    healthScore: 95,
  },
  {
    id: "6",
    name: "StartupXYZ",
    tier: "ignition",
    mrr: 199,
    status: "past_due",
    campaigns: 1,
    leads: 123,
    lastActivity: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3),
    healthScore: 15,
  },
];

const tierColors = {
  ignition: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  velocity: "bg-purple-500/10 text-purple-700 border-purple-500/20",
  dominance: "bg-amber-500/10 text-amber-700 border-amber-500/20",
};

const statusColors = {
  active: "bg-green-500/10 text-green-700 border-green-500/20",
  trialing: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  past_due: "bg-red-500/10 text-red-700 border-red-500/20",
  paused: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  cancelled: "bg-gray-500/10 text-gray-700 border-gray-500/20",
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminClientsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [tierFilter, setTierFilter] = useState("all");
  const [healthFilter, setHealthFilter] = useState("all");

  const filteredClients = mockClients.filter((client) => {
    const matchesSearch = client.name.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || client.status === statusFilter;
    const matchesTier = tierFilter === "all" || client.tier === tierFilter;
    const matchesHealth =
      healthFilter === "all" ||
      (healthFilter === "healthy" && client.healthScore >= 70) ||
      (healthFilter === "at_risk" && client.healthScore >= 40 && client.healthScore < 70) ||
      (healthFilter === "critical" && client.healthScore < 40);

    return matchesSearch && matchesStatus && matchesTier && matchesHealth;
  });

  const totalMRR = filteredClients.reduce((sum, c) => sum + c.mrr, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Clients</h1>
          <p className="text-muted-foreground">
            {filteredClients.length} clients | ${totalMRR.toLocaleString()} MRR
          </p>
        </div>
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
            <Select value={healthFilter} onValueChange={setHealthFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Health" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Health</SelectItem>
                <SelectItem value="healthy">Healthy (70+)</SelectItem>
                <SelectItem value="at_risk">At Risk (40-69)</SelectItem>
                <SelectItem value="critical">Critical (&lt;40)</SelectItem>
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
                    <Badge variant="outline" className={tierColors[client.tier]}>
                      {client.tier}
                    </Badge>
                  </TableCell>
                  <TableCell>${client.mrr}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={statusColors[client.status]}>
                      {client.status.replace("_", " ")}
                    </Badge>
                  </TableCell>
                  <TableCell>{client.campaigns}</TableCell>
                  <TableCell>{client.leads.toLocaleString()}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatTimeAgo(client.lastActivity)}
                  </TableCell>
                  <TableCell>
                    <ClientHealthBadge score={client.healthScore} />
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
        </CardContent>
      </Card>
    </div>
  );
}
