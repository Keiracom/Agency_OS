/**
 * FILE: frontend/app/admin/leads/page.tsx
 * PURPOSE: Global leads view for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Leads
 */

"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { createBrowserClient } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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

// Phase 4 admin Tier A wiring (2026-05-10): replaces the prior empty-array
// honesty pass (PR #661) with live Supabase queries against `leads` table
// joined with `clients` for cross-client display name. Filters + stats logic
// below unchanged — operates on the fetched array.
interface Lead {
  id: string;
  email: string;
  name: string;
  company: string;
  client: string;
  als: number;
  tier: "hot" | "warm" | "cold";
  status: "new" | "enriched" | "scored" | "in_sequence" | "converted" | "unsubscribed" | "bounced";
}

type LeadRow = {
  id: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
  company: string | null;
  als_score: number | null;
  als_tier: string | null;
  status: string | null;
  client_id: string | null;
  clients: { name: string | null } | null;
};

const TIER_OF = (score: number | null): "hot" | "warm" | "cold" => {
  if (score == null) return "cold";
  if (score >= 70) return "hot";
  if (score >= 40) return "warm";
  return "cold";
};

const STATUS_OF = (raw: string | null): Lead["status"] => {
  const allowed = ["new", "enriched", "scored", "in_sequence", "converted", "unsubscribed", "bounced"];
  return (allowed.includes(raw ?? "") ? raw : "new") as Lead["status"];
};

async function fetchAdminLeads(): Promise<Lead[]> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const { data, error } = await client
    .from("leads")
    .select("id, email, first_name, last_name, company, als_score, als_tier, status, client_id, clients(name)")
    .order("als_score", { ascending: false, nullsFirst: false })
    .limit(500);
  if (error) throw error;
  return ((data ?? []) as LeadRow[]).map((row) => ({
    id: row.id,
    email: row.email ?? "",
    name: [row.first_name, row.last_name].filter(Boolean).join(" ") || "Unknown",
    company: row.company ?? "",
    client: row.clients?.name ?? "",
    als: row.als_score ?? 0,
    tier: (["hot", "warm", "cold"].includes(row.als_tier ?? "") ? row.als_tier : TIER_OF(row.als_score)) as Lead["tier"],
    status: STATUS_OF(row.status),
  }));
}

const tierColors = {
  hot: "bg-amber-glow text-error border-amber/20",
  warm: "bg-orange-500/10 text-orange-700 border-orange-500/20",
  cold: "bg-panel/10 text-amber border-default/20",
};

const statusColors = {
  new: "bg-bg-surface0/10 text-ink-3 border-gray-500/20",
  enriched: "bg-panel/10 text-amber border-default/20",
  scored: "bg-amber/10 text-amber border-amber/20",
  in_sequence: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  converted: "bg-amber/10 text-amber border-amber/20",
  unsubscribed: "bg-amber-glow text-error border-amber/20",
  bounced: "bg-amber-glow text-error border-amber/20",
};

export default function AdminLeadsPage() {
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data: leads = [], isLoading } = useQuery({
    queryKey: ["admin-leads"],
    queryFn: fetchAdminLeads,
    staleTime: 30 * 1000,
  });

  const filteredLeads = leads.filter((lead) => {
    const matchesSearch =
      lead.email.toLowerCase().includes(search.toLowerCase()) ||
      lead.name.toLowerCase().includes(search.toLowerCase()) ||
      lead.company.toLowerCase().includes(search.toLowerCase()) ||
      lead.client.toLowerCase().includes(search.toLowerCase());
    const matchesTier = tierFilter === "all" || lead.tier === tierFilter;
    const matchesStatus = statusFilter === "all" || lead.status === statusFilter;
    return matchesSearch && matchesTier && matchesStatus;
  });

  // ALS distribution
  const hotLeads = leads.filter((l) => l.als >= 70).length;
  const warmLeads = leads.filter((l) => l.als >= 40 && l.als < 70).length;
  const coldLeads = leads.filter((l) => l.als < 40).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Leads</h1>
        <p className="text-muted-foreground">All leads across all clients</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Leads
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "…" : leads.length.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Hot (70+)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber">{hotLeads}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Warm (40-69)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{warmLeads}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Cold (&lt;40)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-ink-2">{coldLeads}</div>
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
                placeholder="Search leads..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={tierFilter} onValueChange={setTierFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="ALS Tier" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tiers</SelectItem>
                <SelectItem value="hot">Hot (70+)</SelectItem>
                <SelectItem value="warm">Warm (40-69)</SelectItem>
                <SelectItem value="cold">Cold (&lt;40)</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="enriched">Enriched</SelectItem>
                <SelectItem value="in_sequence">In Sequence</SelectItem>
                <SelectItem value="converted">Converted</SelectItem>
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
                <TableHead>Lead</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>ALS</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredLeads.map((lead) => (
                <TableRow key={lead.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{lead.name}</p>
                      <p className="text-sm text-muted-foreground">{lead.email}</p>
                    </div>
                  </TableCell>
                  <TableCell>{lead.company}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {lead.client}
                  </TableCell>
                  <TableCell>
                    <span className="font-bold">{lead.als}</span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={tierColors[lead.tier as keyof typeof tierColors]}
                    >
                      {lead.tier}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={statusColors[lead.status as keyof typeof statusColors]}
                    >
                      {lead.status.replace("_", " ")}
                    </Badge>
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
