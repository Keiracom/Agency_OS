/**
 * FILE: frontend/app/dashboard/settings/profile/page.tsx
 * PURPOSE: User profile settings page
 * PHASE: 8 (Frontend)
 * TASK: FE-031
 */

"use client";

import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useToast } from "@/hooks/use-toast";
import { ArrowLeft, Loader2, User, Upload } from "lucide-react";
import { createBrowserClient } from "@/lib/supabase";

// Common Australian timezones
const TIMEZONES = [
  { value: "Australia/Sydney", label: "Sydney (AEST/AEDT)" },
  { value: "Australia/Melbourne", label: "Melbourne (AEST/AEDT)" },
  { value: "Australia/Brisbane", label: "Brisbane (AEST)" },
  { value: "Australia/Perth", label: "Perth (AWST)" },
  { value: "Australia/Adelaide", label: "Adelaide (ACST/ACDT)" },
  { value: "Australia/Darwin", label: "Darwin (ACST)" },
  { value: "Australia/Hobart", label: "Hobart (AEST/AEDT)" },
  { value: "Pacific/Auckland", label: "Auckland (NZST/NZDT)" },
  { value: "Asia/Singapore", label: "Singapore (SGT)" },
  { value: "America/New_York", label: "New York (EST/EDT)" },
  { value: "America/Los_Angeles", label: "Los Angeles (PST/PDT)" },
  { value: "Europe/London", label: "London (GMT/BST)" },
];

interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  timezone: string | null;
  avatar_url: string | null;
}

interface ProfileFormData {
  full_name: string;
  phone: string;
  timezone: string;
}

/**
 * Fetch current user profile from Supabase
 */
async function fetchUserProfile(): Promise<UserProfile | null> {
  const supabase = createBrowserClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) return null;

  // Get additional user data from users table
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: userData } = await (supabase as any)
    .from("users")
    .select("*")
    .eq("id", user.id)
    .single();

  return {
    id: user.id,
    email: user.email || "",
    full_name: userData?.full_name || user.user_metadata?.full_name || null,
    phone: userData?.phone || user.phone || null,
    timezone: userData?.timezone || "Australia/Sydney",
    avatar_url: userData?.avatar_url || user.user_metadata?.avatar_url || null,
  };
}

/**
 * Update user profile in Supabase
 */
async function updateUserProfile(data: ProfileFormData): Promise<void> {
  const supabase = createBrowserClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) throw new Error("Not authenticated");

  // Update user metadata in auth
  const { error: authError } = await supabase.auth.updateUser({
    data: {
      full_name: data.full_name,
    },
  });

  if (authError) throw authError;

  // Update users table
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { error: dbError } = await (supabase as any)
    .from("users")
    .update({
      full_name: data.full_name,
      phone: data.phone || null,
      timezone: data.timezone,
      updated_at: new Date().toISOString(),
    })
    .eq("id", user.id);

  if (dbError) throw dbError;
}

export default function ProfileSettingsPage() {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  // Form state
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [timezone, setTimezone] = useState("Australia/Sydney");

  // Form validation state
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Load profile on mount
  useEffect(() => {
    async function loadProfile() {
      try {
        const data = await fetchUserProfile();
        if (data) {
          setProfile(data);
          setFullName(data.full_name || "");
          setPhone(data.phone || "");
          setTimezone(data.timezone || "Australia/Sydney");
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load profile",
          variant: "destructive",
        });
      } finally {
        setIsLoading(false);
      }
    }
    loadProfile();
  }, [toast]);

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: updateUserProfile,
    onSuccess: () => {
      toast({
        title: "Profile Updated",
        description: "Your profile has been saved successfully.",
      });
      // Update local profile state
      setProfile((prev) =>
        prev
          ? {
              ...prev,
              full_name: fullName,
              phone: phone,
              timezone: timezone,
            }
          : null
      );
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to update profile",
        variant: "destructive",
      });
    },
  });

  // Form validation
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!fullName.trim()) {
      newErrors.fullName = "Name is required";
    }

    if (phone && !/^[+\d\s()-]*$/.test(phone)) {
      newErrors.phone = "Invalid phone number format";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    updateMutation.mutate({
      full_name: fullName.trim(),
      phone: phone.trim(),
      timezone,
    });
  };

  // Get initials for avatar
  const getInitials = (name: string | null): string => {
    if (!name) return "";
    const parts = name.trim().split(" ");
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Not authenticated
  if (!profile) {
    return (
      <div className="space-y-6 max-w-4xl">
        <Link href="/dashboard/settings">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Back to Settings
          </Button>
        </Link>
        <Card className="border-destructive">
          <CardContent className="p-6">
            <p className="text-destructive">
              Unable to load profile. Please sign in again.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Back Button */}
      <Link href="/dashboard/settings">
        <Button variant="ghost" className="gap-2">
          <ArrowLeft className="h-4 w-4" />
          Back to Settings
        </Button>
      </Link>

      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Profile Settings</h1>
        <p className="text-muted-foreground">
          Manage your personal information and preferences
        </p>
      </div>

      <Separator />

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Avatar Section */}
        <Card>
          <CardHeader>
            <CardTitle>Profile Picture</CardTitle>
            <CardDescription>
              Your profile picture is visible to team members
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-6">
            <Avatar className="h-24 w-24">
              <AvatarImage src={profile.avatar_url || ""} />
              <AvatarFallback className="text-2xl bg-primary/10 text-primary">
                {getInitials(fullName) || <User className="h-10 w-10" />}
              </AvatarFallback>
            </Avatar>
            <div className="space-y-2">
              <Button type="button" variant="outline" size="sm" disabled>
                <Upload className="mr-2 h-4 w-4" />
                Upload Photo
              </Button>
              <p className="text-xs text-muted-foreground">
                Avatar upload coming soon
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Personal Information */}
        <Card>
          <CardHeader>
            <CardTitle>Personal Information</CardTitle>
            <CardDescription>Update your personal details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <Input
                id="fullName"
                value={fullName}
                onChange={(e) => {
                  setFullName(e.target.value);
                  if (errors.fullName) {
                    setErrors((prev) => ({ ...prev, fullName: "" }));
                  }
                }}
                placeholder="Enter your full name"
                className={errors.fullName ? "border-destructive" : ""}
              />
              {errors.fullName && (
                <p className="text-sm text-destructive">{errors.fullName}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={profile.email}
                disabled
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">
                Contact support to change your email address
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone Number</Label>
              <Input
                id="phone"
                type="tel"
                value={phone}
                onChange={(e) => {
                  setPhone(e.target.value);
                  if (errors.phone) {
                    setErrors((prev) => ({ ...prev, phone: "" }));
                  }
                }}
                placeholder="+61 400 000 000"
                className={errors.phone ? "border-destructive" : ""}
              />
              {errors.phone && (
                <p className="text-sm text-destructive">{errors.phone}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Used for account recovery and notifications
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Preferences */}
        <Card>
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
            <CardDescription>
              Customize your experience
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger id="timezone">
                  <SelectValue placeholder="Select timezone" />
                </SelectTrigger>
                <SelectContent>
                  {TIMEZONES.map((tz) => (
                    <SelectItem key={tz.value} value={tz.value}>
                      {tz.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Used for scheduling and activity timestamps
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex gap-4">
          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save Changes"
            )}
          </Button>
          <Link href="/dashboard/settings">
            <Button type="button" variant="outline">
              Cancel
            </Button>
          </Link>
        </div>
      </form>
    </div>
  );
}

// === VERIFICATION CHECKLIST ===
// [x] Contract comment at top
// [x] Uses React Query for API calls
// [x] Shows toast on success/error
// [x] Form validation
// [x] All required fields (name, email, phone, timezone)
// [x] Avatar display with initials fallback
// [x] Navigation link back to settings
// [x] Loading and error states
// [x] Email field disabled (contact support)
