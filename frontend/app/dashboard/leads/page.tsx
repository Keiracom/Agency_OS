/**
 * FILE: frontend/app/dashboard/leads/page.tsx
 * PURPOSE: Leads list page with ALS tiers
 * PHASE: 8 (Frontend)
 * TASK: FE-011
 */

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, Filter, Download, Upload } from "lucide-react";

// Placeholder data
const leads = [
  {
    id: "1",
    email: "sarah.johnson@techcorp.com",
    firstName: "Sarah",
    lastName: "Johnson",
    title: "CEO",
    company: "TechCorp",
    alsScore: 92,
    alsTier: "hot",
    status: "in_sequence",
    campaign: "Tech Startups Q1 2025",
    lastActivity: "Opened email 2h ago",
  },
  {
    id: "2",
    email: "michael.chen@startupxyz.com",
    firstName: "Michael",
    lastName: "Chen",
    title: "CTO",
    company: "StartupXYZ",
    alsScore: 78,
    alsTier: "warm",
    status: "in_sequence",
    campaign: "SaaS Decision Makers",
    lastActivity: "Clicked link 1d ago",
  },
  {
    id: "3",
    email: "emma.wilson@growthagency.com",
    firstName: "Emma",
    lastName: "Wilson",
    title: "Director of Marketing",
    company: "Growth Agency",
    alsScore: 65,
    alsTier: "warm",
    status: "converted",
    campaign: "Agency Partnerships",
    lastActivity: "Meeting booked",
  },
  {
    id: "4",
    email: "david.brown@enterprise.co",
    firstName: "David",
    lastName: "Brown",
    title: "VP Sales",
    company: "Enterprise Co",
    alsScore: 45,
    alsTier: "cool",
    status: "enriched",
    campaign: "Tech Startups Q1 2025",
    lastActivity: "Enriched 3h ago",
  },
  {
    id: "5",
    email: "lisa.taylor@smallbiz.com",
    firstName: "Lisa",
    lastName: "Taylor",
    title: "Owner",
    company: "SmallBiz Inc",
    alsScore: 28,
    alsTier: "cold",
    status: "new",
    campaign: "E-commerce Brands",
    lastActivity: "Added 1d ago",
  },
];

export default function LeadsPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Leads</h1>
          <p className="text-muted-foreground">
            View and manage all leads across your campaigns
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            Import
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search by name, email, company..." className="pl-9" />
        </div>
        <Button variant="outline">
          <Filter className="mr-2 h-4 w-4" />
          Filters
        </Button>
      </div>

      {/* Tier Summary */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { tier: "hot", count: 45, label: "Hot" },
          { tier: "warm", count: 123, label: "Warm" },
          { tier: "cool", count: 234, label: "Cool" },
          { tier: "cold", count: 189, label: "Cold" },
          { tier: "dead", count: 23, label: "Dead" },
        ].map((item) => (
          <Card key={item.tier} className="cursor-pointer hover:border-primary/50 transition-colors">
            <CardContent className="p-4 text-center">
              <Badge variant={item.tier as "hot" | "warm" | "cool" | "cold" | "dead"} className="mb-2">
                {item.label}
              </Badge>
              <p className="text-2xl font-bold">{item.count}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Leads Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Leads</CardTitle>
          <CardDescription>
            Click on a lead to view details and activity timeline
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="p-3 text-left text-sm font-medium">Lead</th>
                  <th className="p-3 text-left text-sm font-medium">Company</th>
                  <th className="p-3 text-left text-sm font-medium">ALS Score</th>
                  <th className="p-3 text-left text-sm font-medium">Status</th>
                  <th className="p-3 text-left text-sm font-medium">Campaign</th>
                  <th className="p-3 text-left text-sm font-medium">Last Activity</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <td className="p-3">
                      <div>
                        <p className="font-medium">
                          {lead.firstName} {lead.lastName}
                        </p>
                        <p className="text-sm text-muted-foreground">{lead.email}</p>
                      </div>
                    </td>
                    <td className="p-3">
                      <div>
                        <p className="font-medium">{lead.company}</p>
                        <p className="text-sm text-muted-foreground">{lead.title}</p>
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold">{lead.alsScore}</span>
                        <Badge
                          variant={lead.alsTier as "hot" | "warm" | "cool" | "cold" | "dead"}
                          className="capitalize"
                        >
                          {lead.alsTier}
                        </Badge>
                      </div>
                    </td>
                    <td className="p-3">
                      <Badge variant="outline" className="capitalize">
                        {lead.status.replace("_", " ")}
                      </Badge>
                    </td>
                    <td className="p-3 text-sm text-muted-foreground">
                      {lead.campaign}
                    </td>
                    <td className="p-3 text-sm text-muted-foreground">
                      {lead.lastActivity}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
