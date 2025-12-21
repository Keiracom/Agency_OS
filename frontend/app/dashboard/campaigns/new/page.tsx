/**
 * FILE: frontend/app/dashboard/campaigns/new/page.tsx
 * PURPOSE: New campaign creation page
 * PHASE: 8 (Frontend)
 * TASK: FE-010
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Loader2 } from "lucide-react";
import { PermissionModeSelector } from "@/components/campaigns/permission-mode-selector";
import { useToast } from "@/hooks/use-toast";

export default function NewCampaignPage() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [permissionMode, setPermissionMode] = useState<"autopilot" | "co_pilot" | "manual">("co_pilot");
  const [dailyLimit, setDailyLimit] = useState(50);
  const [loading, setLoading] = useState(false);

  // Channel allocation
  const [emailAlloc, setEmailAlloc] = useState(60);
  const [smsAlloc, setSmsAlloc] = useState(20);
  const [linkedinAlloc, setLinkedinAlloc] = useState(20);
  const [voiceAlloc, setVoiceAlloc] = useState(0);
  const [mailAlloc, setMailAlloc] = useState(0);

  const router = useRouter();
  const { toast } = useToast();

  const totalAllocation = emailAlloc + smsAlloc + linkedinAlloc + voiceAlloc + mailAlloc;
  const isValidAllocation = totalAllocation === 100;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isValidAllocation) {
      toast({
        title: "Invalid allocation",
        description: "Channel allocations must sum to 100%",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);

    // Would call API here
    await new Promise((resolve) => setTimeout(resolve, 1000));

    toast({
      title: "Campaign created",
      description: "Your campaign has been created successfully",
    });

    router.push("/dashboard/campaigns");
  };

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back Button */}
      <Link href="/dashboard/campaigns">
        <Button variant="ghost" className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back to Campaigns
        </Button>
      </Link>

      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create Campaign</h1>
        <p className="text-muted-foreground">
          Set up a new outreach campaign
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>Name and describe your campaign</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Campaign Name</Label>
              <Input
                id="name"
                placeholder="e.g., Tech Startups Q1 2025"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                placeholder="Brief description of your target audience"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="dailyLimit">Daily Outreach Limit</Label>
              <Input
                id="dailyLimit"
                type="number"
                min={1}
                max={500}
                value={dailyLimit}
                onChange={(e) => setDailyLimit(parseInt(e.target.value))}
              />
              <p className="text-sm text-muted-foreground">
                Maximum leads to contact per day (1-500)
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Permission Mode */}
        <Card>
          <CardHeader>
            <CardTitle>Permission Mode</CardTitle>
            <CardDescription>Choose your automation level</CardDescription>
          </CardHeader>
          <CardContent>
            <PermissionModeSelector
              value={permissionMode}
              onChange={setPermissionMode}
            />
          </CardContent>
        </Card>

        {/* Channel Allocation */}
        <Card>
          <CardHeader>
            <CardTitle>Channel Allocation</CardTitle>
            <CardDescription>
              Distribute your outreach across channels (must sum to 100%)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="emailAlloc">Email (%)</Label>
                <Input
                  id="emailAlloc"
                  type="number"
                  min={0}
                  max={100}
                  value={emailAlloc}
                  onChange={(e) => setEmailAlloc(parseInt(e.target.value) || 0)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="smsAlloc">SMS (%)</Label>
                <Input
                  id="smsAlloc"
                  type="number"
                  min={0}
                  max={100}
                  value={smsAlloc}
                  onChange={(e) => setSmsAlloc(parseInt(e.target.value) || 0)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="linkedinAlloc">LinkedIn (%)</Label>
                <Input
                  id="linkedinAlloc"
                  type="number"
                  min={0}
                  max={100}
                  value={linkedinAlloc}
                  onChange={(e) => setLinkedinAlloc(parseInt(e.target.value) || 0)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="voiceAlloc">Voice (%)</Label>
                <Input
                  id="voiceAlloc"
                  type="number"
                  min={0}
                  max={100}
                  value={voiceAlloc}
                  onChange={(e) => setVoiceAlloc(parseInt(e.target.value) || 0)}
                />
              </div>
            </div>
            <div className="flex items-center justify-between pt-2 border-t">
              <span className="font-medium">Total:</span>
              <span className={`font-bold ${isValidAllocation ? "text-green-600" : "text-red-600"}`}>
                {totalAllocation}%
              </span>
            </div>
            {!isValidAllocation && (
              <p className="text-sm text-red-600">
                Allocations must sum to exactly 100%
              </p>
            )}
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex gap-4">
          <Button type="submit" disabled={loading || !isValidAllocation}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              "Create Campaign"
            )}
          </Button>
          <Link href="/dashboard/campaigns">
            <Button type="button" variant="outline">Cancel</Button>
          </Link>
        </div>
      </form>
    </div>
  );
}
