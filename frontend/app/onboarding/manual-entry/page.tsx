/**
 * FILE: frontend/app/onboarding/manual-entry/page.tsx
 * TASK: SCR-007
 * PHASE: 19 (Scraper Waterfall)
 * PURPOSE: Manual ICP entry fallback when automated scraping fails
 *
 * User options:
 * 1. Paste website content directly (textarea)
 * 2. Provide LinkedIn company URL instead
 * 3. Skip ICP extraction, use basic company info
 */

"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertTriangle,
  FileText,
  Linkedin,
  SkipForward,
  Loader2,
  ChevronRight,
  XCircle,
  Globe,
  ArrowLeft,
} from "lucide-react";
import { createClient } from "@/lib/supabase";

function ManualEntryContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const failedUrl = searchParams.get("url") || "";

  const [entryMethod, setEntryMethod] = useState<"paste" | "linkedin" | "skip">(
    "paste"
  );
  const [pastedContent, setPastedContent] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push("/login");
        return;
      }

      let endpoint = "";
      let body: Record<string, string> = {};

      switch (entryMethod) {
        case "paste":
          if (!pastedContent.trim() || pastedContent.length < 100) {
            setError("Please paste at least 100 characters of website content");
            setLoading(false);
            return;
          }
          endpoint = "/api/v1/onboarding/analyze-content";
          body = {
            content: pastedContent,
            source_url: failedUrl,
          };
          break;

        case "linkedin":
          if (
            !linkedinUrl.trim() ||
            !linkedinUrl.includes("linkedin.com/company")
          ) {
            setError("Please enter a valid LinkedIn company URL");
            setLoading(false);
            return;
          }
          endpoint = "/api/v1/onboarding/analyze-linkedin";
          body = {
            linkedin_url: linkedinUrl,
          };
          break;

        case "skip":
          if (!companyName.trim()) {
            setError("Please enter your company name");
            setLoading(false);
            return;
          }
          endpoint = "/api/v1/onboarding/skip-icp";
          body = {
            company_name: companyName,
            industry: industry || "Marketing Agency",
            website_url: failedUrl,
          };
          break;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}${endpoint}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify(body),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to process your request");
      }

      const data = await response.json();

      // Store job_id if returned
      if (data.job_id) {
        localStorage.setItem("icp_job_id", data.job_id);
        router.push(`/dashboard?icp_job=${data.job_id}`);
      } else {
        // Direct completion (skip case)
        router.push("/dashboard");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-yellow-500/10">
            <AlertTriangle className="h-8 w-8 text-yellow-500" />
          </div>
          <CardTitle className="text-2xl">
            We couldn&apos;t read your website
          </CardTitle>
          <CardDescription className="space-y-2">
            <p>
              Your website has protection that prevents automated reading.
              <br />
              Choose how you&apos;d like to proceed:
            </p>
            {failedUrl && (
              <p className="text-xs text-muted-foreground/70 font-mono bg-muted/50 px-2 py-1 rounded inline-block">
                {failedUrl}
              </p>
            )}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Tabs
            value={entryMethod}
            onValueChange={(v) =>
              setEntryMethod(v as "paste" | "linkedin" | "skip")
            }
          >
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="paste" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                <span className="hidden sm:inline">Paste Content</span>
                <span className="sm:hidden">Paste</span>
              </TabsTrigger>
              <TabsTrigger value="linkedin" className="flex items-center gap-2">
                <Linkedin className="h-4 w-4" />
                <span className="hidden sm:inline">Use LinkedIn</span>
                <span className="sm:hidden">LinkedIn</span>
              </TabsTrigger>
              <TabsTrigger value="skip" className="flex items-center gap-2">
                <SkipForward className="h-4 w-4" />
                <span className="hidden sm:inline">Skip for Now</span>
                <span className="sm:hidden">Skip</span>
              </TabsTrigger>
            </TabsList>

            {/* Paste Content Tab */}
            <TabsContent value="paste" className="space-y-4 mt-6">
              <div className="space-y-2">
                <Label htmlFor="content">Website Content</Label>
                <p className="text-sm text-muted-foreground">
                  Copy and paste the text content from your website&apos;s About
                  page, Services page, or homepage. Include information about
                  your services, target clients, and company description.
                </p>
                <Textarea
                  id="content"
                  placeholder="Paste your website content here...

Example:
We are a full-service digital marketing agency specializing in helping B2B SaaS companies grow. Our services include SEO, paid advertising, content marketing, and marketing automation. We've helped over 50 companies achieve 3x growth in qualified leads..."
                  value={pastedContent}
                  onChange={(e) => setPastedContent(e.target.value)}
                  className="min-h-[200px] font-mono text-sm"
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  {pastedContent.length} characters (minimum 100)
                </p>
              </div>
            </TabsContent>

            {/* LinkedIn Tab */}
            <TabsContent value="linkedin" className="space-y-4 mt-6">
              <div className="space-y-2">
                <Label htmlFor="linkedin">LinkedIn Company Page URL</Label>
                <p className="text-sm text-muted-foreground">
                  We&apos;ll extract your company information from LinkedIn
                  instead. Enter your company&apos;s LinkedIn page URL.
                </p>
                <Input
                  id="linkedin"
                  type="url"
                  placeholder="https://linkedin.com/company/your-agency"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="bg-muted/50 rounded-lg p-4 text-sm text-muted-foreground">
                <p className="font-medium text-foreground mb-2">
                  How to find your LinkedIn URL:
                </p>
                <ol className="list-decimal list-inside space-y-1">
                  <li>Go to linkedin.com and search for your company</li>
                  <li>Click on your company page</li>
                  <li>
                    Copy the URL from your browser (should contain
                    &quot;linkedin.com/company/&quot;)
                  </li>
                </ol>
              </div>
            </TabsContent>

            {/* Skip Tab */}
            <TabsContent value="skip" className="space-y-4 mt-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="company">Company Name *</Label>
                  <Input
                    id="company"
                    placeholder="Your Agency Name"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    disabled={loading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="industry">Industry (optional)</Label>
                  <Input
                    id="industry"
                    placeholder="e.g., Digital Marketing, SEO Agency, Creative Agency"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    disabled={loading}
                  />
                </div>
              </div>
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 text-sm">
                <p className="font-medium text-yellow-600 dark:text-yellow-400 mb-1">
                  Limited ICP Discovery
                </p>
                <p className="text-muted-foreground">
                  Skipping will create a basic profile. You can enhance your ICP
                  later from Settings → Company Profile.
                </p>
              </div>
            </TabsContent>
          </Tabs>

          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive mt-4">
              <XCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}
        </CardContent>

        <CardFooter className="flex flex-col gap-3">
          <Button
            className="w-full"
            size="lg"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                {entryMethod === "paste" && "Analyze Content"}
                {entryMethod === "linkedin" && "Analyze LinkedIn"}
                {entryMethod === "skip" && "Continue to Dashboard"}
                <ChevronRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
          <div className="flex gap-4 text-sm">
            <button
              type="button"
              onClick={() => router.push("/onboarding")}
              className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-3 w-3" />
              Try a different URL
            </button>
            <button
              type="button"
              onClick={() => router.push("/dashboard")}
              className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
            >
              <Globe className="h-3 w-3" />
              Go to Dashboard
            </button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}

export default function ManualEntryPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-background">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <ManualEntryContent />
    </Suspense>
  );
}
