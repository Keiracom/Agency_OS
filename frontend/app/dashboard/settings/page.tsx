/**
 * FILE: frontend/app/dashboard/settings/page.tsx
 * PURPOSE: Settings page
 * PHASE: 8 (Frontend)
 * TASK: FE-014
 */

import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Target, ChevronRight } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and organization settings
        </p>
      </div>

      {/* ICP Settings Link */}
      <Link href="/dashboard/settings/icp">
        <Card className="cursor-pointer hover:border-primary/50 transition-colors">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Target className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">Ideal Customer Profile</p>
                <p className="text-sm text-muted-foreground">
                  Define your target audience for all campaigns
                </p>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </CardContent>
        </Card>
      </Link>

      {/* Organization */}
      <Card>
        <CardHeader>
          <CardTitle>Organization</CardTitle>
          <CardDescription>Update your organization details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="orgName">Organization Name</Label>
              <Input id="orgName" defaultValue="Acme Agency" />
            </div>
            <div className="space-y-2">
              <Label>Subscription Tier</Label>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="text-base px-3 py-1">
                  Velocity
                </Badge>
                <Button variant="link" className="text-sm">Upgrade</Button>
              </div>
            </div>
          </div>
          <Button>Save Changes</Button>
        </CardContent>
      </Card>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Update your personal information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <Input id="fullName" defaultValue="John Smith" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" defaultValue="john@acmeagency.com" />
            </div>
          </div>
          <Button>Update Profile</Button>
        </CardContent>
      </Card>

      {/* Default Permission Mode */}
      <Card>
        <CardHeader>
          <CardTitle>Default Permission Mode</CardTitle>
          <CardDescription>
            Set the default automation level for new campaigns
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                mode: "autopilot",
                title: "Autopilot",
                description: "Full automation. AI handles all decisions.",
              },
              {
                mode: "co_pilot",
                title: "Co-Pilot",
                description: "AI suggests, you approve key decisions.",
              },
              {
                mode: "manual",
                title: "Manual",
                description: "Full control. Approve every action.",
              },
            ].map((option) => (
              <Card
                key={option.mode}
                className={`cursor-pointer hover:border-primary transition-colors ${
                  option.mode === "co_pilot" ? "border-primary" : ""
                }`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium">{option.title}</span>
                    {option.mode === "co_pilot" && (
                      <Badge variant="active">Selected</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{option.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Integrations */}
      <Card>
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
          <CardDescription>Connect your tools and services</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4">
            {[
              { name: "Apollo", status: "connected", description: "Lead enrichment" },
              { name: "LinkedIn", status: "connected", description: "Via HeyReach" },
              { name: "Resend", status: "connected", description: "Email sending" },
              { name: "Twilio", status: "not_connected", description: "SMS sending" },
            ].map((integration) => (
              <div
                key={integration.name}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div>
                  <p className="font-medium">{integration.name}</p>
                  <p className="text-sm text-muted-foreground">{integration.description}</p>
                </div>
                <Badge
                  variant={integration.status === "connected" ? "active" : "outline"}
                  className="capitalize"
                >
                  {integration.status.replace("_", " ")}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>
            Irreversible actions for your organization
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border border-destructive/50 p-4">
            <div>
              <p className="font-medium">Delete Organization</p>
              <p className="text-sm text-muted-foreground">
                Permanently delete your organization and all data
              </p>
            </div>
            <Button variant="destructive">Delete</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
