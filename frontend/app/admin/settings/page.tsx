/**
 * FILE: frontend/app/admin/settings/page.tsx
 * PURPOSE: Platform settings for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Settings
 */

"use client";

import { useState } from "react";
import { Save, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";

export default function AdminSettingsPage() {
  // Settings state
  const [settings, setSettings] = useState({
    dailyAiSpendLimit: 500,
    clayFallbackPercentage: 15,
    maintenanceMode: false,
    voiceEnabled: true,
    mailEnabled: true,
    alertEmail: "dave@agency.com",
    slackWebhook: "",
  });

  const handleSave = () => {
    // Would call API to save settings
    console.log("Saving settings:", settings);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Platform Settings</h1>
          <p className="text-muted-foreground">
            Global configuration and feature flags
          </p>
        </div>
        <Button onClick={handleSave}>
          <Save className="mr-2 h-4 w-4" />
          Save Changes
        </Button>
      </div>

      {/* Limits */}
      <Card>
        <CardHeader>
          <CardTitle>Limits</CardTitle>
          <CardDescription>
            Configure spending and rate limits
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="aiLimit">Daily AI Spend Limit (AUD)</Label>
              <Input
                id="aiLimit"
                type="number"
                value={settings.dailyAiSpendLimit}
                onChange={(e) =>
                  setSettings({ ...settings, dailyAiSpendLimit: parseInt(e.target.value) })
                }
              />
              <p className="text-xs text-muted-foreground">
                Circuit breaker activates when this limit is reached
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="clayPercentage">Clay Fallback Percentage</Label>
              <Input
                id="clayPercentage"
                type="number"
                value={settings.clayFallbackPercentage}
                onChange={(e) =>
                  setSettings({ ...settings, clayFallbackPercentage: parseInt(e.target.value) })
                }
              />
              <p className="text-xs text-muted-foreground">
                Percentage of leads to enrich via Clay when primary fails
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Feature Flags */}
      <Card>
        <CardHeader>
          <CardTitle>Feature Flags</CardTitle>
          <CardDescription>
            Enable or disable platform features
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Voice Channel</Label>
              <p className="text-sm text-muted-foreground">
                Enable AI voice calls via Vapi
              </p>
            </div>
            <Switch
              checked={settings.voiceEnabled}
              onCheckedChange={(checked) =>
                setSettings({ ...settings, voiceEnabled: checked })
              }
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Direct Mail Channel</Label>
              <p className="text-sm text-muted-foreground">
                Enable physical mail via PostGrid
              </p>
            </div>
            <Switch
              checked={settings.mailEnabled}
              onCheckedChange={(checked) =>
                setSettings({ ...settings, mailEnabled: checked })
              }
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-yellow-600">Maintenance Mode</Label>
              <p className="text-sm text-muted-foreground">
                Pause all outreach and show maintenance banner
              </p>
            </div>
            <Switch
              checked={settings.maintenanceMode}
              onCheckedChange={(checked) =>
                setSettings({ ...settings, maintenanceMode: checked })
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
          <CardDescription>
            Configure alert destinations
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="alertEmail">Alert Email</Label>
            <Input
              id="alertEmail"
              type="email"
              value={settings.alertEmail}
              onChange={(e) =>
                setSettings({ ...settings, alertEmail: e.target.value })
              }
            />
            <p className="text-xs text-muted-foreground">
              Receive critical alerts via email
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="slackWebhook">Slack Webhook URL</Label>
            <Input
              id="slackWebhook"
              type="url"
              placeholder="https://hooks.slack.com/..."
              value={settings.slackWebhook}
              onChange={(e) =>
                setSettings({ ...settings, slackWebhook: e.target.value })
              }
            />
            <p className="text-xs text-muted-foreground">
              Post alerts to a Slack channel
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            Danger Zone
          </CardTitle>
          <CardDescription>
            Emergency controls - use with caution
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 border border-red-500/20 rounded-lg">
            <div>
              <p className="font-medium">Pause All Campaigns</p>
              <p className="text-sm text-muted-foreground">
                Immediately stop all outreach across all clients
              </p>
            </div>
            <Button variant="destructive">Pause All</Button>
          </div>
          <div className="flex items-center justify-between p-4 border border-red-500/20 rounded-lg">
            <div>
              <p className="font-medium">Reset Rate Limits</p>
              <p className="text-sm text-muted-foreground">
                Clear all rate limit counters in Redis
              </p>
            </div>
            <Button variant="destructive">Reset Limits</Button>
          </div>
          <div className="flex items-center justify-between p-4 border border-red-500/20 rounded-lg">
            <div>
              <p className="font-medium">Clear Redis Cache</p>
              <p className="text-sm text-muted-foreground">
                Flush all cached data (enrichment, templates, etc.)
              </p>
            </div>
            <Button variant="destructive">Clear Cache</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
