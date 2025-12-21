/**
 * FILE: frontend/app/admin/leads/page.tsx
 * PURPOSE: Global leads view for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Leads
 */

"use client";

import { useState } from "react";
import { Search } from "lucide-react";
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

// Mock data
const mockLeads = [
  { id: "1", email: "john@acme.com", name: "John Smith", company: "Acme Corp", client: "LeadGen Pro", als: 85, tier: "hot", status: "in_sequence" },
  { id: "2", email: "sarah@tech.co", name: "Sarah Johnson", company: "TechCo", client: "GrowthLab", als: 72, tier: "warm", status: "enriched" },
  { id: "3", email: "mike@startup.io", name: "Mike Wilson", company: "StartupIO", client: "ScaleUp Co", als: 91, tier: "hot", status: "converted" },
  { id: "4", email: "lisa@enterprise.com", name: "Lisa Brown", company: "Enterprise Inc", client: "Enterprise Co", als: 45, tier: "cold", status: "new" },
  { id: "5", email: "david@agency.com", name: "David Lee", company: "Agency XYZ", client: "Marketing Plus", als: 78, tier: "warm", status: "in_sequence" },
  { id: "6", email: "emma@corp.net", name: "Emma Davis", company: "CorpNet", client: "LeadGen Pro", als: 88, tier: "hot", status: "in_sequence" },
  { id: "7", email: "james@biz.com", name: "James Miller", company: "BizCom", client: "GrowthLab", als: 62, tier: "warm", status: "enriched" },
  { id: "8", email: "anna@global.io", name: "Anna White", company: "GlobalIO", client: "Enterprise Co", als: 95, tier: "hot", status: "converted" },
];

const tierColors = {
  hot: "bg-red-500/10 text-red-700 border-red-500/20",
  warm: "bg-orange-500/10 text-orange-700 border-orange-500/20",
  cold: "bg-blue-500/10 text-blue-700 border-blue-500/20",
};

const statusColors = {
  new: "bg-gray-500/10 text-gray-700 border-gray-500/20",
  enriched: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  scored: "bg-purple-500/10 text-purple-700 border-purple-500/20",
  in_sequence: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  converted: "bg-green-500/10 text-green-700 border-green-500/20",
  unsubscribed: "bg-red-500/10 text-red-700 border-red-500/20",
  bounced: "bg-red-500/10 text-red-700 border-red-500/20",
};

export default function AdminLeadsPage() {
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const filteredLeads = mockLeads.filter((lead) => {
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
  const hotLeads = mockLeads.filter((l) => l.als >= 70).length;
  const warmLeads = mockLeads.filter((l) => l.als >= 40 && l.als < 70).length;
  const coldLeads = mockLeads.filter((l) => l.als < 40).length;

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
            <div className="text-2xl font-bold">{mockLeads.length.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Hot (70+)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{hotLeads}</div>
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
            <div className="text-2xl font-bold text-blue-600">{coldLeads}</div>
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
