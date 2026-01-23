"use client";

/**
 * Content Archive Page - Phase H, Item 46
 *
 * Displays all sent content (emails, SMS, LinkedIn, voice) in a searchable,
 * filterable archive. Clients can browse their outreach history and see
 * engagement metrics for each piece of content.
 */

import { useState, useMemo } from "react";
import { useContentArchive } from "@/hooks/use-reports";
import { useCampaigns } from "@/hooks/use-campaigns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import {
  Mail,
  MessageSquare,
  Linkedin,
  Phone,
  Send,
  Search,
  Eye,
  MousePointer,
  ChevronLeft,
  ChevronRight,
  Calendar,
  Filter,
  X,
} from "lucide-react";
import type { ArchiveContentItem, ContentArchiveFilters } from "@/lib/api/types";

// Channel icons and colors
const channelConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  email: { icon: <Mail className="h-4 w-4" />, color: "bg-blue-500/10 text-blue-400", label: "Email" },
  sms: { icon: <MessageSquare className="h-4 w-4" />, color: "bg-purple-500/10 text-purple-400", label: "SMS" },
  linkedin: { icon: <Linkedin className="h-4 w-4" />, color: "bg-sky-500/10 text-sky-400", label: "LinkedIn" },
  voice: { icon: <Phone className="h-4 w-4" />, color: "bg-green-500/10 text-green-400", label: "Voice" },
  mail: { icon: <Send className="h-4 w-4" />, color: "bg-orange-500/10 text-orange-400", label: "Direct Mail" },
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-AU", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function ContentCard({
  item,
  onClick,
}: {
  item: ArchiveContentItem;
  onClick: () => void;
}) {
  const channel = channelConfig[item.channel] || channelConfig.email;

  return (
    <Card
      className="cursor-pointer hover:border-white/20 transition-colors"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Channel Icon */}
          <div className={`p-2 rounded-lg ${channel.color}`}>
            {channel.icon}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-sm font-medium text-white truncate">
                {item.lead_name || item.lead_email || "Unknown recipient"}
              </span>
              <span className="text-xs text-gray-500 flex-shrink-0">
                {formatDate(item.timestamp)}
              </span>
            </div>

            {/* Company */}
            {item.lead_company && (
              <p className="text-xs text-gray-400 mb-1">{item.lead_company}</p>
            )}

            {/* Subject */}
            {item.subject && (
              <p className="text-sm text-gray-300 truncate mb-2">{item.subject}</p>
            )}

            {/* Preview */}
            <p className="text-xs text-gray-500 line-clamp-2">
              {item.content_preview || "No preview available"}
            </p>

            {/* Footer */}
            <div className="flex items-center gap-3 mt-3">
              {/* Campaign */}
              {item.campaign_name && (
                <Badge variant="outline" className="text-xs">
                  {item.campaign_name}
                </Badge>
              )}

              {/* Engagement */}
              {item.email_opened && (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <Eye className="h-3 w-3" />
                  {item.email_open_count}
                </span>
              )}
              {item.email_clicked && (
                <span className="flex items-center gap-1 text-xs text-blue-400">
                  <MousePointer className="h-3 w-3" />
                  {item.email_click_count}
                </span>
              )}

              {/* Sequence position */}
              {item.sequence_step && (
                <span className="text-xs text-gray-500">
                  Step {item.sequence_step}
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ContentDetailModal({
  item,
  open,
  onClose,
}: {
  item: ArchiveContentItem | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!item) return null;

  const channel = channelConfig[item.channel] || channelConfig.email;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className={`p-1.5 rounded ${channel.color}`}>
              {channel.icon}
            </span>
            {channel.label} to {item.lead_name || item.lead_email}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Sent:</span>
              <span className="ml-2 text-gray-300">{formatDate(item.timestamp)}</span>
            </div>
            <div>
              <span className="text-gray-500">Campaign:</span>
              <span className="ml-2 text-gray-300">{item.campaign_name || "—"}</span>
            </div>
            <div>
              <span className="text-gray-500">Recipient:</span>
              <span className="ml-2 text-gray-300">{item.lead_email || "—"}</span>
            </div>
            <div>
              <span className="text-gray-500">Company:</span>
              <span className="ml-2 text-gray-300">{item.lead_company || "—"}</span>
            </div>
          </div>

          {/* Engagement */}
          <div className="flex items-center gap-4 p-3 bg-white/5 rounded-lg">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-gray-400" />
              <span className="text-sm">
                {item.email_opened ? (
                  <span className="text-green-400">
                    Opened {item.email_open_count} time{item.email_open_count !== 1 ? "s" : ""}
                  </span>
                ) : (
                  <span className="text-gray-500">Not opened</span>
                )}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <MousePointer className="h-4 w-4 text-gray-400" />
              <span className="text-sm">
                {item.email_clicked ? (
                  <span className="text-blue-400">
                    Clicked {item.email_click_count} time{item.email_click_count !== 1 ? "s" : ""}
                  </span>
                ) : (
                  <span className="text-gray-500">No clicks</span>
                )}
              </span>
            </div>
          </div>

          {/* Subject */}
          {item.subject && (
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-1">Subject</h4>
              <p className="text-gray-200">{item.subject}</p>
            </div>
          )}

          {/* Full Content */}
          <div>
            <h4 className="text-sm font-medium text-gray-400 mb-1">Content</h4>
            <div className="p-4 bg-white/5 rounded-lg">
              <pre className="whitespace-pre-wrap text-sm text-gray-300 font-sans">
                {item.full_message_body || item.content_preview || "No content available"}
              </pre>
            </div>
          </div>

          {/* Links */}
          {item.links_included && item.links_included.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-1">Links Included</h4>
              <ul className="space-y-1">
                {item.links_included.map((link, idx) => (
                  <li key={idx} className="text-sm text-blue-400 truncate">
                    {link}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Personalization */}
          {item.personalization_fields_used && item.personalization_fields_used.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-1">Personalization Used</h4>
              <div className="flex flex-wrap gap-1">
                {item.personalization_fields_used.map((field, idx) => (
                  <Badge key={idx} variant="secondary" className="text-xs">
                    {field}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* AI Info */}
          {item.ai_model_used && (
            <div className="text-xs text-gray-500">
              Generated by {item.ai_model_used}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function ContentArchivePage() {
  // Filters state
  const [filters, setFilters] = useState<ContentArchiveFilters>({
    page: 1,
    page_size: 20,
  });
  const [searchInput, setSearchInput] = useState("");
  const [selectedItem, setSelectedItem] = useState<ArchiveContentItem | null>(null);

  // Data fetching
  const { data: archiveData, isLoading, error } = useContentArchive(filters);
  const { data: campaigns } = useCampaigns();

  // Debounced search
  const handleSearch = () => {
    setFilters((prev) => ({ ...prev, search: searchInput, page: 1 }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleFilterChange = (key: keyof ContentArchiveFilters, value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
      page: 1, // Reset to page 1 when filters change
    }));
  };

  const clearFilters = () => {
    setFilters({ page: 1, page_size: 20 });
    setSearchInput("");
  };

  const hasActiveFilters = useMemo(() => {
    return !!(filters.search || filters.channel || filters.campaign_id || filters.start_date || filters.end_date);
  }, [filters]);

  // Pagination
  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white">Content Archive</h1>
        <p className="text-gray-400 mt-1">
          Browse all content sent on your behalf
        </p>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4">
            {/* Search */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <Input
                  placeholder="Search content..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Channel Filter */}
            <Select
              value={filters.channel || "all"}
              onValueChange={(value) => handleFilterChange("channel", value === "all" ? undefined : value)}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                <SelectItem value="email">Email</SelectItem>
                <SelectItem value="sms">SMS</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="voice">Voice</SelectItem>
              </SelectContent>
            </Select>

            {/* Campaign Filter */}
            <Select
              value={filters.campaign_id || "all"}
              onValueChange={(value) => handleFilterChange("campaign_id", value === "all" ? undefined : value)}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Campaign" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Campaigns</SelectItem>
                {campaigns?.items?.map((campaign) => (
                  <SelectItem key={campaign.id} value={campaign.id}>
                    {campaign.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Date Filter */}
            <Input
              type="date"
              placeholder="From"
              value={filters.start_date || ""}
              onChange={(e) => handleFilterChange("start_date", e.target.value)}
              className="w-[150px]"
            />
            <Input
              type="date"
              placeholder="To"
              value={filters.end_date || ""}
              onChange={(e) => handleFilterChange("end_date", e.target.value)}
              className="w-[150px]"
            />

            {/* Search Button */}
            <Button onClick={handleSearch}>
              <Filter className="h-4 w-4 mr-2" />
              Apply
            </Button>

            {/* Clear Filters */}
            {hasActiveFilters && (
              <Button variant="ghost" onClick={clearFilters}>
                <X className="h-4 w-4 mr-2" />
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          {archiveData?.total ?? 0} items found
          {hasActiveFilters && " (filtered)"}
        </p>
        {archiveData && archiveData.total_pages > 1 && (
          <p className="text-sm text-gray-500">
            Page {archiveData.page} of {archiveData.total_pages}
          </p>
        )}
      </div>

      {/* Content Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4 h-32 bg-white/5" />
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card>
          <CardContent className="p-8 text-center">
            <p className="text-red-400">Failed to load content archive</p>
          </CardContent>
        </Card>
      ) : archiveData?.items.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <Mail className="h-12 w-12 mx-auto text-gray-600 mb-4" />
            <p className="text-gray-400">
              {hasActiveFilters
                ? "No content matches your filters"
                : "No content sent yet"}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {archiveData?.items.map((item) => (
            <ContentCard
              key={item.id}
              item={item}
              onClick={() => setSelectedItem(item)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {archiveData && archiveData.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(archiveData.page - 1)}
            disabled={archiveData.page <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="text-sm text-gray-400 px-4">
            Page {archiveData.page} of {archiveData.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(archiveData.page + 1)}
            disabled={!archiveData.has_more}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Detail Modal */}
      <ContentDetailModal
        item={selectedItem}
        open={!!selectedItem}
        onClose={() => setSelectedItem(null)}
      />
    </div>
  );
}
