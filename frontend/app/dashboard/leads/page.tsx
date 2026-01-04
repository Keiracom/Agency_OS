/**
 * FILE: frontend/app/dashboard/leads/page.tsx
 * PURPOSE: Leads list page with real data and ALS tiers
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-006
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, Filter, Download, Upload, ChevronLeft, ChevronRight } from "lucide-react";
import { useLeads } from "@/hooks/use-leads";
import { useALSDistribution } from "@/hooks/use-reports";
import { TableSkeleton, StatsGridSkeleton } from "@/components/ui/loading-skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { NoItemsState, NoSearchResults, EmptyListRow } from "@/components/ui/empty-state";
import type { Lead, ALSTier, LeadStatus } from "@/lib/api/types";

export default function LeadsPage() {
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState<ALSTier | undefined>();
  const [statusFilter, setStatusFilter] = useState<LeadStatus | undefined>();
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading, error, refetch } = useLeads({
    page,
    page_size: pageSize,
    search: search || undefined,
    tier: tierFilter,
    status: statusFilter,
  });

  const { data: alsDistribution, isLoading: alsLoading } = useALSDistribution();

  const leads = data?.items || [];
  const totalPages = data?.total_pages || 1;

  const handleTierClick = (tier: ALSTier) => {
    setTierFilter(tierFilter === tier ? undefined : tier);
    setPage(1);
  };

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
          <Input
            placeholder="Search by name, email, company..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9"
          />
        </div>
        <Button variant="outline">
          <Filter className="mr-2 h-4 w-4" />
          Filters
        </Button>
      </div>

      {/* Tier Summary */}
      {alsLoading ? (
        <div className="grid grid-cols-5 gap-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4 text-center">
                <div className="h-5 w-12 mx-auto rounded bg-muted mb-2" />
                <div className="h-8 w-16 mx-auto rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : alsDistribution ? (
        <div className="grid grid-cols-5 gap-4">
          {(["hot", "warm", "cool", "cold", "dead"] as ALSTier[]).map((tier) => {
            const item = alsDistribution.find((d) => d.tier === tier);
            const isActive = tierFilter === tier;

            return (
              <Card
                key={tier}
                className={`cursor-pointer transition-colors ${
                  isActive ? "border-primary" : "hover:border-primary/50"
                }`}
                onClick={() => handleTierClick(tier)}
              >
                <CardContent className="p-4 text-center">
                  <Badge variant={tier} className="mb-2 capitalize">
                    {tier}
                  </Badge>
                  <p className="text-2xl font-bold">{item?.count || 0}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : null}

      {/* Leads Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Leads</CardTitle>
          <CardDescription>
            {data?.total ? `${data.total.toLocaleString()} total leads` : "Click on a lead to view details"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={10} />
          ) : error ? (
            <ErrorState error={error} onRetry={refetch} />
          ) : leads.length === 0 ? (
            search || tierFilter ? (
              <NoSearchResults
                query={search || tierFilter || ""}
                onClear={() => {
                  setSearch("");
                  setTierFilter(undefined);
                  setPage(1);
                }}
              />
            ) : (
              <NoItemsState itemName="Lead" canCreate={false} />
            )
          ) : (
            <>
              <div className="rounded-md border">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="p-3 text-left text-sm font-medium">Lead</th>
                      <th className="p-3 text-left text-sm font-medium">Company</th>
                      <th className="p-3 text-left text-sm font-medium">ALS Score</th>
                      <th className="p-3 text-left text-sm font-medium">Status</th>
                      <th className="p-3 text-left text-sm font-medium">Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.map((lead: Lead) => (
                      <tr
                        key={lead.id}
                        className="border-b hover:bg-muted/50 cursor-pointer transition-colors"
                        onClick={() => (window.location.href = `/dashboard/leads/${lead.id}`)}
                      >
                        <td className="p-3">
                          <div>
                            <p className="font-medium">
                              {lead.first_name} {lead.last_name}
                            </p>
                            <p className="text-sm text-muted-foreground">{lead.email}</p>
                          </div>
                        </td>
                        <td className="p-3">
                          <div>
                            <p className="font-medium">{lead.company || "-"}</p>
                            <p className="text-sm text-muted-foreground">{lead.title || "-"}</p>
                          </div>
                        </td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold">
                              {lead.als_score !== null ? lead.als_score : "-"}
                            </span>
                            {lead.als_tier && (
                              <Badge
                                variant={lead.als_tier as "hot" | "warm" | "cool" | "cold" | "dead"}
                                className="capitalize"
                              >
                                {lead.als_tier}
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="p-3">
                          <Badge variant="outline" className="capitalize">
                            {lead.status.replace("_", " ")}
                          </Badge>
                        </td>
                        <td className="p-3 text-sm text-muted-foreground">
                          {new Date(lead.updated_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
