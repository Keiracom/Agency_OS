/**
 * FILE: frontend/components/icp-review-modal.tsx
 * PURPOSE: Slide-over drawer for reviewing and confirming extracted ICP
 * PHASE: 11 (ICP Discovery System)
 */

'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  Building2,
  Target,
  Users,
  Briefcase,
  MapPin,
  TrendingUp,
  Loader2,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ICPProfile {
  company_name: string;
  website_url: string;
  company_description: string;
  services_offered: string[];
  primary_service_categories: string[];
  value_proposition: string;
  taglines: string[];
  differentiators: string[];
  team_size: number | null;
  size_range: string;
  years_in_business: number | null;
  portfolio_companies: string[];
  notable_brands: string[];
  icp_industries: string[];
  icp_company_sizes: string[];
  icp_revenue_ranges: string[];
  icp_locations: string[];
  icp_titles: string[];
  icp_pain_points: string[];
  icp_signals: string[];
  als_weights: Record<string, number>;
  pattern_description: string;
  confidence: number;
}

interface ICPReviewModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  profile: ICPProfile | null;
  onConfirm: () => Promise<void>;
  onStartOver: () => void;
}

export function ICPReviewModal({
  open,
  onOpenChange,
  profile,
  onConfirm,
  onStartOver,
}: ICPReviewModalProps) {
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setError(null);
    setConfirmLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to confirm ICP');
    } finally {
      setConfirmLoading(false);
    }
  };

  if (!profile) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] p-0 gap-0">
        <DialogHeader className="p-6 pb-4 border-b">
          <DialogTitle className="text-xl">Review Your ICP</DialogTitle>
          <DialogDescription>
            We&apos;ve extracted your ideal customer profile. Review the details below
            and confirm to start using Agency OS.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 max-h-[60vh] overflow-y-auto">
          <div className="p-6 space-y-6">
            {/* Company Info Section */}
            <section className="space-y-4">
              <div className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-lg">Your Agency</h3>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-muted-foreground text-xs uppercase tracking-wider">
                    Company Name
                  </Label>
                  <p className="font-medium mt-1">{profile.company_name || 'Not detected'}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground text-xs uppercase tracking-wider">
                    Team Size
                  </Label>
                  <p className="font-medium mt-1">
                    {profile.team_size
                      ? `~${profile.team_size} employees`
                      : profile.size_range || 'Not detected'}
                  </p>
                </div>
              </div>

              {profile.value_proposition && (
                <div>
                  <Label className="text-muted-foreground text-xs uppercase tracking-wider">
                    Value Proposition
                  </Label>
                  <p className="mt-1 text-sm">{profile.value_proposition}</p>
                </div>
              )}

              {profile.services_offered.length > 0 && (
                <div>
                  <Label className="text-muted-foreground text-xs uppercase tracking-wider">
                    Services
                  </Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {profile.services_offered.slice(0, 8).map((service) => (
                      <Badge key={service} variant="secondary">
                        {service}
                      </Badge>
                    ))}
                    {profile.services_offered.length > 8 && (
                      <Badge variant="outline">
                        +{profile.services_offered.length - 8} more
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </section>

            <hr />

            {/* ICP Profile Section */}
            <section className="space-y-4">
              <div className="flex items-center gap-2">
                <Target className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-lg">Ideal Customer Profile</h3>
              </div>

              {profile.pattern_description && (
                <p className="text-sm text-muted-foreground">
                  {profile.pattern_description}
                </p>
              )}

              <div className="grid gap-6 md:grid-cols-2">
                {/* Industries */}
                {profile.icp_industries.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Briefcase className="h-4 w-4 text-muted-foreground" />
                      <Label className="text-xs uppercase tracking-wider">
                        Target Industries
                      </Label>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {profile.icp_industries.map((industry) => (
                        <Badge key={industry} variant="outline">
                          {industry.replace(/_/g, ' ')}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Company Sizes */}
                {profile.icp_company_sizes.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <Label className="text-xs uppercase tracking-wider">
                        Company Sizes
                      </Label>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {profile.icp_company_sizes.map((size) => (
                        <Badge key={size} variant="outline">
                          {size} employees
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Locations */}
                {profile.icp_locations.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <MapPin className="h-4 w-4 text-muted-foreground" />
                      <Label className="text-xs uppercase tracking-wider">
                        Target Locations
                      </Label>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {profile.icp_locations.map((location) => (
                        <Badge key={location} variant="outline">
                          {location}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Titles */}
                {profile.icp_titles.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="h-4 w-4 text-muted-foreground" />
                      <Label className="text-xs uppercase tracking-wider">
                        Target Titles
                      </Label>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {profile.icp_titles.slice(0, 5).map((title) => (
                        <Badge key={title} variant="outline">
                          {title}
                        </Badge>
                      ))}
                      {profile.icp_titles.length > 5 && (
                        <Badge variant="secondary">
                          +{profile.icp_titles.length - 5} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Pain Points */}
              {profile.icp_pain_points.length > 0 && (
                <div>
                  <Label className="text-xs uppercase tracking-wider text-muted-foreground mb-2 block">
                    Pain Points
                  </Label>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    {profile.icp_pain_points.slice(0, 4).map((pain) => (
                      <li key={pain}>{pain}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Confidence */}
              <div className="flex items-center gap-4 pt-4 border-t">
                <span className="text-sm text-muted-foreground">
                  Extraction Confidence:
                </span>
                <Badge
                  variant={
                    profile.confidence >= 0.8
                      ? 'default'
                      : profile.confidence >= 0.6
                      ? 'secondary'
                      : 'outline'
                  }
                  className={cn(
                    profile.confidence >= 0.8 && 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
                    profile.confidence >= 0.6 && profile.confidence < 0.8 && 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                  )}
                >
                  {Math.round(profile.confidence * 100)}%
                </Badge>
              </div>
            </section>
          </div>
        </div>

        <DialogFooter className="p-6 pt-4 border-t">
          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive mr-auto">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
          <Button variant="outline" onClick={onStartOver} disabled={confirmLoading}>
            Start Over
          </Button>
          <Button onClick={handleConfirm} disabled={confirmLoading}>
            {confirmLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                Confirm & Continue
                <ChevronRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
