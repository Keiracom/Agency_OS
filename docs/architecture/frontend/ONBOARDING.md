# Frontend Onboarding Architecture

**Purpose:** Architecture spec for Agency OS client onboarding flow.
**Last Updated:** 2026-01-23
**Status:** Specification Complete

---

## 1. Overview

### Purpose

The onboarding flow guides new clients from signup to their first dashboard view. It collects essential data (website URL), extracts their Ideal Customer Profile (ICP) using AI, and optionally connects their LinkedIn account for automated outreach.

### Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Quick to Value** | Get clients to dashboard as fast as possible |
| **AI Does the Work** | Client provides website, AI extracts ICP |
| **Optional Steps** | LinkedIn is optional, can add later |
| **Background Processing** | ICP extraction happens async, client proceeds immediately |
| **Simple 4-Step Flow** | Website -> ICP Review -> LinkedIn -> Complete |

### Key Goals

1. **Minimize friction** - Single input (website URL) starts the process
2. **Demonstrate AI value** - Show extracted ICP to prove system capability
3. **Flexible LinkedIn** - Optional connection, skippable
4. **Fast completion** - Under 5 minutes to dashboard

---

## 2. Routes

### Onboarding Route Structure

```
/onboarding                  -> Website input (main entry)
/onboarding/linkedin         -> LinkedIn connection (optional)
/onboarding/skip             -> Skip onboarding (testing only)
/onboarding/manual-entry     -> Manual ICP entry (fallback)
```

### Route Files

| Route | File | Purpose | Status |
|-------|------|---------|--------|
| `/onboarding` | `frontend/app/onboarding/page.tsx` | Website URL input, starts ICP extraction | IMPLEMENTED |
| `/onboarding/linkedin` | `frontend/app/onboarding/linkedin/page.tsx` | LinkedIn credential connection | IMPLEMENTED |
| `/onboarding/skip` | `frontend/app/onboarding/skip/page.tsx` | Skip with default ICP (testing) | IMPLEMENTED |
| `/onboarding/manual-entry` | `frontend/app/onboarding/manual-entry/page.tsx` | Manual ICP form entry | IMPLEMENTED |

### Post-Onboarding Redirect

After website submission, users are redirected to:
```
/dashboard?icp_job={job_id}
```

The dashboard shows an ICP extraction progress modal while extraction runs in background.

---

## 3. Data Available

### Onboarding State

```typescript
// frontend/lib/api/types.ts

// ICP Extraction Job
interface ICPExtractionJob {
  id: string;                    // Job UUID
  client_id: string;             // Client being onboarded
  status: "pending" | "running" | "completed" | "failed";
  website_url: string;           // URL being analyzed
  current_step: string;          // Current step name
  completed_steps: number;       // Progress tracking
  total_steps: number;           // Total steps (default 8)
  extracted_icp: ICPProfile | null; // Extracted data
  error_message: string | null;  // Error if failed
  started_at: string | null;     // When extraction started
  completed_at: string | null;   // When extraction finished
}

// Extracted ICP Profile
interface ICPProfile {
  // Target companies
  target_industries: string[];       // ["Technology", "SaaS", "Fintech"]
  target_company_sizes: string[];    // ["10-50", "51-200", "201-500"]
  target_locations: string[];        // ["Sydney", "Melbourne"]
  revenue_range_min: number | null;
  revenue_range_max: number | null;

  // Target contacts
  target_job_titles: string[];       // ["CEO", "CTO", "VP Engineering"]

  // Keywords
  keywords: string[];                // Include keywords
  exclusions: string[];              // Exclude keywords

  // Messaging context
  pain_points: string[];             // Problems ideal customers face
  value_propositions: string[];      // How client solves problems

  // Client data (extracted)
  company_description: string | null;
  services_offered: string[];

  // Metadata
  extracted_from_website: boolean;
  last_extraction_at: string | null;
  extraction_source: "website" | "manual" | "manual_skip";
}

// Onboarding Status (from Supabase RPC)
interface OnboardingStatus {
  client_id: string;
  needs_onboarding: boolean;
  icp_confirmed_at: string | null;
  website_url: string | null;
}
```

### LinkedIn Connection State

```typescript
// frontend/lib/api/linkedin.ts

interface LinkedInStatusResponse {
  status: "connected" | "disconnected" | "connecting" | "awaiting_2fa" | "failed";
  profile_name: string | null;
  profile_url: string | null;
  connected_at: string | null;
  two_fa_method: "sms" | "authenticator" | "email" | null;
  error: string | null;
}

interface LinkedInConnectRequest {
  linkedin_email: string;
  linkedin_password: string;
}

interface LinkedInConnectResponse {
  status: "connected" | "awaiting_2fa" | "connecting" | "failed";
  method?: string;           // 2FA method if awaiting
  profile_name?: string;
  profile_url?: string;
  error?: string;
}

interface TwoFactorRequest {
  code: string;
}
```

---

## 4. User Actions

### Website Input Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Enter website URL | Input | Local state | IMPLEMENTED |
| Submit URL | Button | `POST /onboarding/analyze` | IMPLEMENTED |
| Skip onboarding | Link | Redirect to /onboarding/skip | IMPLEMENTED |
| View validation error | Error display | - | IMPLEMENTED |

### ICP Review Actions (In Dashboard Modal)

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| View extraction progress | Progress display | `GET /onboarding/status/{job_id}` | IMPLEMENTED |
| View extracted ICP | ICP display | `GET /onboarding/result/{job_id}` | IMPLEMENTED |
| Confirm ICP | Button | `POST /onboarding/confirm` | IMPLEMENTED |
| Edit ICP | Link | Redirect to /dashboard/settings/icp | IMPLEMENTED |

### LinkedIn Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Enter credentials | LinkedInCredentialForm | Local state | IMPLEMENTED |
| Submit credentials | Button | `POST /linkedin/connect` | IMPLEMENTED |
| Enter 2FA code | LinkedInTwoFactor | Local state | IMPLEMENTED |
| Submit 2FA | Button | `POST /linkedin/verify-2fa` | IMPLEMENTED |
| Skip LinkedIn | Button | Redirect to /dashboard | IMPLEMENTED |
| Back to form | Button | Local state | IMPLEMENTED |
| Continue to dashboard | Button | Redirect to /dashboard | IMPLEMENTED |

### Skip Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Go back | Button | Redirect to /onboarding | IMPLEMENTED |
| Skip & Continue | Button | Supabase direct update | IMPLEMENTED |

---

## 5. Components (Existing)

### Onboarding Page Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| OnboardingPage | `app/onboarding/page.tsx` | None | Website URL input form |
| LinkedInOnboardingPage | `app/onboarding/linkedin/page.tsx` | None | LinkedIn connection flow |
| SkipOnboardingPage | `app/onboarding/skip/page.tsx` | None | Skip with defaults (testing) |
| ManualEntryPage | `app/onboarding/manual-entry/page.tsx` | None | Manual ICP form |

### LinkedIn Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| LinkedInCredentialForm | `components/onboarding/LinkedInCredentialForm.tsx` | `onSubmit`, `error`, `isLoading` | Email/password input form |
| LinkedInTwoFactor | `components/onboarding/LinkedInTwoFactor.tsx` | `method`, `onSubmit`, `onBack`, `error`, `isLoading` | 2FA code input |
| LinkedInConnecting | `components/onboarding/LinkedInConnecting.tsx` | `message?` | Loading state during connection |
| LinkedInSuccess | `components/onboarding/LinkedInSuccess.tsx` | `profileName`, `profileUrl`, `onContinue` | Success state with profile |

### Shared UI Components

| Component | File | Purpose |
|-----------|------|---------|
| Card, CardHeader, CardContent, CardFooter | `components/ui/card.tsx` | Section containers |
| Button | `components/ui/button.tsx` | Actions |
| Input | `components/ui/input.tsx` | Text fields |
| Label | `components/ui/label.tsx` | Form labels |
| Progress | `components/ui/progress.tsx` | Progress bars |

---

## 6. Components to Create

### OnboardingSteps

```typescript
// frontend/components/onboarding/OnboardingSteps.tsx

interface OnboardingStepsProps {
  currentStep: 1 | 2 | 3 | 4;
  steps?: Array<{
    number: number;
    label: string;
    description?: string;
  }>;
}

/**
 * Step indicator showing progress through onboarding:
 * - Step 1: Website Input
 * - Step 2: ICP Review
 * - Step 3: LinkedIn Connect
 * - Step 4: Complete
 *
 * Shows completed/current/upcoming states
 */
```

**Design:**
```
+----------------------------------------------------------+
|  [1] Website  >  [2] ICP Review  >  [3] LinkedIn  >  [4]  |
|  [*]             [ ]                 [ ]             [ ]  |
|  Enter URL       AI Extraction       Connect         Done |
+----------------------------------------------------------+
```

### ICPExtractionProgress

```typescript
// frontend/components/onboarding/ICPExtractionProgress.tsx

interface ICPExtractionProgressProps {
  jobId: string;
  onComplete: (icp: ICPProfile) => void;
  onError: (error: string) => void;
}

/**
 * Polls extraction job status and shows progress:
 * - Step name and progress percentage
 * - Animated loading states per step
 * - Error handling with retry option
 * - Calls onComplete when done
 */
```

**Design:**
```
+----------------------------------------------------------+
| Analyzing Your Website                                    |
|                                                           |
| [====================>          ] 68%                     |
|                                                           |
| [X] Validating URL                                        |
| [X] Scraping website content                              |
| [X] Extracting company information                        |
| [>] Identifying target audience       <-- Currently here  |
| [ ] Analyzing pain points                                 |
| [ ] Building ICP profile                                  |
|                                                           |
| This usually takes 30-60 seconds                          |
+----------------------------------------------------------+
```

### ICPReviewCard

```typescript
// frontend/components/onboarding/ICPReviewCard.tsx

interface ICPReviewCardProps {
  icp: ICPProfile;
  onConfirm: () => void;
  onEdit: () => void;
  isConfirming: boolean;
}

/**
 * Displays extracted ICP for user review:
 * - Target industries, company sizes, locations
 * - Target job titles
 * - Pain points and value props
 * - Confirm and Edit buttons
 */
```

**Design:**
```
+----------------------------------------------------------+
| Your Ideal Customer Profile                   [AI Badge]  |
|                                                           |
| TARGET COMPANIES                                          |
| Industries:  Technology, SaaS, Fintech                    |
| Sizes:       11-50, 51-200 employees                      |
| Locations:   Sydney, Melbourne, Brisbane                  |
|                                                           |
| TARGET CONTACTS                                           |
| Roles:       CEO, CTO, VP Engineering, Founder            |
|                                                           |
| MESSAGING CONTEXT                                         |
| Pain Points:                                              |
| - Struggling to scale lead generation                     |
| - Manual outreach is time-consuming                       |
|                                                           |
| Value Propositions:                                       |
| - Automated multi-channel outreach                        |
| - AI-powered personalization at scale                     |
|                                                           |
| [ Edit ICP ]                    [ Confirm & Continue ]    |
+----------------------------------------------------------+
```

### OnboardingHeader

```typescript
// frontend/components/onboarding/OnboardingHeader.tsx

interface OnboardingHeaderProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  showLogo?: boolean;
}

/**
 * Consistent header for onboarding pages:
 * - Agency OS logo
 * - Step title
 * - Description text
 * - Optional icon
 */
```

### OnboardingComplete

```typescript
// frontend/components/onboarding/OnboardingComplete.tsx

interface OnboardingCompleteProps {
  clientName?: string;
  onGoToDashboard: () => void;
  showCampaignSuggestion?: boolean;
}

/**
 * Final completion screen:
 * - Success message and celebration
 * - Summary of what was set up
 * - "Go to Dashboard" CTA
 * - Optional: first campaign suggestion
 */
```

**Design:**
```
+----------------------------------------------------------+
|              [Celebration Icon/Animation]                 |
|                                                           |
|              You're All Set!                              |
|                                                           |
| Your Agency OS account is ready. Here's what's next:      |
|                                                           |
| [X] ICP configured - targeting Tech CEOs in Sydney        |
| [X] LinkedIn connected - ready for outreach               |
| [>] Your first campaign is being prepared                 |
|                                                           |
|           [ Go to Dashboard ]                             |
|                                                           |
| We'll notify you when your first campaign is ready        |
+----------------------------------------------------------+
```

### WebsiteInput

```typescript
// frontend/components/onboarding/WebsiteInput.tsx

interface WebsiteInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  error?: string | null;
  isLoading: boolean;
}

/**
 * Website URL input component:
 * - URL input with validation
 * - Submit button with loading state
 * - Error display
 * - Auto-prepend https:// if missing
 */
```

---

## 7. API Integration

### Current API Calls (Inline)

The onboarding pages currently make direct fetch calls:

```typescript
// In app/onboarding/page.tsx

// Start ICP extraction
const response = await fetch(
  `${process.env.NEXT_PUBLIC_API_URL}/api/v1/onboarding/analyze`,
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ website_url: websiteUrl }),
  }
);

// Returns: { job_id: string }
```

### Current Hooks

| Hook | File | Query Key | Endpoint | Status |
|------|------|-----------|----------|--------|
| `useLinkedInStatus` | `hooks/use-linkedin.ts` | `["linkedin", "status"]` | `GET /linkedin/status` | IMPLEMENTED |
| `useLinkedInConnect` | `hooks/use-linkedin.ts` | N/A (mutation) | `POST /linkedin/connect` | IMPLEMENTED |
| `useLinkedInVerify2FA` | `hooks/use-linkedin.ts` | N/A (mutation) | `POST /linkedin/verify-2fa` | IMPLEMENTED |
| `useLinkedInDisconnect` | `hooks/use-linkedin.ts` | N/A (mutation) | `POST /linkedin/disconnect` | IMPLEMENTED |

### Hooks to Create

| Hook | Query Key | Endpoint | Purpose |
|------|-----------|----------|---------|
| `useStartICPExtraction` | N/A (mutation) | `POST /onboarding/analyze` | Start extraction job |
| `useICPExtractionStatus` | `["icp-extraction", jobId]` | `GET /onboarding/status/{job_id}` | Poll extraction progress |
| `useICPExtractionResult` | `["icp-result", jobId]` | `GET /onboarding/result/{job_id}` | Get extracted ICP |
| `useConfirmICP` | N/A (mutation) | `POST /onboarding/confirm` | Confirm ICP and trigger post-onboarding |
| `useOnboardingStatus` | `["onboarding-status"]` | Supabase RPC | Check if onboarding needed |

### Proposed Hooks Implementation

```typescript
// frontend/hooks/use-onboarding.ts

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useStartICPExtraction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (websiteUrl: string) =>
      api.post<{ job_id: string }>('/onboarding/analyze', { website_url: websiteUrl }),
    onSuccess: (data) => {
      // Store job_id for polling
      localStorage.setItem('icp_job_id', data.job_id);
    },
  });
}

export function useICPExtractionStatus(jobId: string | null) {
  return useQuery({
    queryKey: ["icp-extraction", jobId],
    queryFn: () => api.get<ICPExtractionJob>(`/onboarding/status/${jobId}`),
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Poll every 2 seconds until complete or failed
      if (data?.status === "completed" || data?.status === "failed") {
        return false;
      }
      return 2000;
    },
  });
}

export function useICPExtractionResult(jobId: string | null) {
  return useQuery({
    queryKey: ["icp-result", jobId],
    queryFn: () => api.get<{ icp: ICPProfile }>(`/onboarding/result/${jobId}`),
    enabled: !!jobId,
    staleTime: Infinity, // Result doesn't change once extracted
  });
}

export function useConfirmICP() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) =>
      api.post('/onboarding/confirm', { job_id: jobId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["onboarding-status"] });
      queryClient.invalidateQueries({ queryKey: ["current-client"] });
    },
  });
}
```

---

## 8. API Gaps

### Missing Endpoints

All onboarding endpoints are implemented:

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `POST /onboarding/analyze` | Start ICP extraction | IMPLEMENTED |
| `GET /onboarding/status/{job_id}` | Get extraction progress | IMPLEMENTED |
| `GET /onboarding/result/{job_id}` | Get extracted ICP | IMPLEMENTED |
| `POST /onboarding/confirm` | Confirm ICP | IMPLEMENTED |

### Missing Frontend Features

| Feature | Priority | Notes |
|---------|----------|-------|
| ICP extraction progress modal | P1 | Show in dashboard after redirect |
| Onboarding step indicator | P2 | Visual progress through steps |
| Re-extraction from dashboard | P2 | Allow re-running ICP extraction |
| Manual ICP entry | P3 | Already has page, needs hooks |

### API Response Shapes

```typescript
// POST /onboarding/analyze
interface AnalyzeResponse {
  job_id: string;
  message: string;
}

// GET /onboarding/status/{job_id}
interface StatusResponse {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  current_step: string;
  completed_steps: number;
  total_steps: number;
  error_message: string | null;
}

// GET /onboarding/result/{job_id}
interface ResultResponse {
  icp: ICPProfile;
  extraction_metadata: {
    scraper_tier_used: number;
    sdk_enhanced: boolean;
    cost_aud: number;
  };
}

// POST /onboarding/confirm
interface ConfirmResponse {
  success: boolean;
  client_id: string;
  icp_confirmed_at: string;
  post_onboarding_triggered: boolean;
}
```

---

## 9. State Management

### Onboarding State Machine

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                                                         │
                    ▼                                                         │
┌────────┐    ┌───────────┐    ┌─────────────┐    ┌───────────┐    ┌──────────┐
│ entry  │───>│  website  │───>│ extracting  │───>│ icp_review│───>│ linkedin │
└────────┘    └───────────┘    └─────────────┘    └───────────┘    └──────────┘
                    │                 │                 │                │
                    │                 ▼                 │                ▼
                    │            ┌────────┐            │           ┌─────────┐
                    │            │ failed │            │           │  skip   │
                    │            └────────┘            │           └─────────┘
                    │                 │                │                │
                    │                 ▼                │                │
                    │            ┌────────────┐        │                │
                    │            │manual_entry│        │                │
                    │            └────────────┘        │                │
                    │                 │                │                │
                    │                 ▼                ▼                ▼
                    │            ┌──────────────────────────────────────────┐
                    └───────────>│                complete                   │
                                 └──────────────────────────────────────────┘
                                                      │
                                                      ▼
                                                ┌───────────┐
                                                │ dashboard │
                                                └───────────┘
```

### State Transitions

| From | Event | To |
|------|-------|-----|
| entry | User lands on /onboarding | website |
| website | Submit URL | extracting |
| website | Click skip | skip_page |
| extracting | Extraction complete | icp_review |
| extracting | Extraction failed | failed |
| failed | Click manual entry | manual_entry |
| failed | Click retry | extracting |
| icp_review | Confirm ICP | linkedin |
| icp_review | Click edit | settings_icp |
| linkedin | Connect success | complete |
| linkedin | Skip | complete |
| linkedin | 2FA required | linkedin_2fa |
| linkedin_2fa | Verify success | complete |
| complete | Go to dashboard | dashboard |
| skip_page | Skip & continue | dashboard |
| manual_entry | Save ICP | linkedin |

### Progress Tracking

```typescript
// localStorage keys for persistence
const ONBOARDING_KEYS = {
  JOB_ID: 'icp_job_id',        // Current extraction job
  STEP: 'onboarding_step',     // Current step (1-4)
  SKIPPED: 'onboarding_skipped', // Boolean if skipped
};

// Check onboarding status
async function checkOnboardingNeeded(): Promise<boolean> {
  const supabase = createClient();
  const { data } = await supabase.rpc('get_onboarding_status');
  return data?.[0]?.needs_onboarding ?? false;
}
```

### LinkedIn Connection State Machine

```typescript
// In app/onboarding/linkedin/page.tsx

type ConnectionState = "form" | "connecting" | "2fa" | "success" | "error";

// State transitions:
// form -> connecting (submit credentials)
// connecting -> success (connected)
// connecting -> 2fa (2FA required)
// connecting -> form (error)
// 2fa -> success (verified)
// 2fa -> form (error or back)
// success -> dashboard (continue)
```

### React Query Configuration

```typescript
const ONBOARDING_STALE_TIMES = {
  extractionStatus: 0,          // Always refetch (polling)
  extractionResult: Infinity,   // Never stale once fetched
  linkedinStatus: 30 * 1000,    // 30 seconds
};

const ONBOARDING_REFETCH = {
  extractionStatus: 2000,       // Poll every 2 seconds during extraction
  linkedinStatus: null,         // No polling by default
};
```

---

## 10. v0 Integration

### Ready for Visual Design

| Section | Component | Ready? | Notes |
|---------|-----------|--------|-------|
| Website Input | OnboardingPage | YES | Clean card layout, single input |
| Loading States | - | PARTIAL | Needs ICPExtractionProgress component |
| ICP Review | - | NO | Needs ICPReviewCard component in dashboard |
| LinkedIn Form | LinkedInCredentialForm | YES | Form with security notice |
| LinkedIn 2FA | LinkedInTwoFactor | YES | Code input with method display |
| LinkedIn Loading | LinkedInConnecting | YES | Animated loading with logo |
| LinkedIn Success | LinkedInSuccess | YES | Success with profile card |
| Skip Page | SkipOnboardingPage | YES | Warning card with defaults |
| Step Indicator | - | NO | Needs OnboardingSteps component |
| Completion | - | NO | Needs OnboardingComplete component |

### CSS Variables (Tailwind)

```typescript
// Onboarding-specific styles

// Background gradient
.onboarding-bg {
  @apply bg-gradient-to-b from-background to-muted/20;
}

// Step indicator
.step-active {
  @apply bg-primary text-primary-foreground;
}

.step-completed {
  @apply bg-primary/20 text-primary;
}

.step-upcoming {
  @apply bg-muted text-muted-foreground;
}

// LinkedIn branding
.linkedin-blue {
  color: #0077b5;
}

// Progress steps
.progress-step-done {
  @apply text-green-500;
}

.progress-step-current {
  @apply text-primary animate-pulse;
}

.progress-step-pending {
  @apply text-muted-foreground;
}

// AI badge
.badge-ai {
  @apply bg-primary/10 text-primary text-xs;
}

// Security notice
.security-notice {
  @apply bg-blue-50 border-blue-200 text-blue-900;
}
```

### Component States for Design

All onboarding components should handle:
- **Loading** - Skeleton or spinner states
- **Error** - Error messages with retry
- **Empty** - Guidance text when needed
- **Success** - Celebration/confirmation states
- **Disabled** - When actions not available

---

## 11. Wireframes

### Step 1: Website Input

```
+------------------------------------------------------------------+
|                                                                    |
|                    [Agency OS Logo]                               |
|                                                                    |
+------------------------------------------------------------------+
|                                                                    |
|                         [Globe Icon]                               |
|                                                                    |
|                   Welcome to Agency OS                             |
|                                                                    |
|           Enter your website URL and we'll automatically           |
|              discover your ideal customer profile                  |
|                                                                    |
|    +------------------------------------------------------+       |
|    | Your Website URL                                      |       |
|    +------------------------------------------------------+       |
|    | https://youragency.com                              |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    [ Error message displays here if validation fails ]            |
|                                                                    |
|    +------------------------------------------------------+       |
|    |              Discover My ICP              [>]        |       |
|    +------------------------------------------------------+       |
|                                                                    |
|                   Skip for now (testing only)                      |
|                                                                    |
+------------------------------------------------------------------+
```

### Step 2: ICP Extraction (Dashboard Modal)

```
+------------------------------------------------------------------+
|                                                                    |
|                   Analyzing Your Website                           |
|                                                                    |
|    +------------------------------------------------------+       |
|    |  [==========>                           ] 34%         |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    [X] Validating URL                                              |
|    [X] Scraping website content                                    |
|    [>] Extracting company information                              |
|    [ ] Identifying target audience                                 |
|    [ ] Analyzing pain points                                       |
|    [ ] Building ICP profile                                        |
|    [ ] Enhancing with AI research                                  |
|    [ ] Finalizing profile                                          |
|                                                                    |
|    This usually takes 30-60 seconds                                |
|                                                                    |
+------------------------------------------------------------------+
```

### Step 3: ICP Review (Dashboard Modal)

```
+------------------------------------------------------------------+
|                                                                    |
|    Your Ideal Customer Profile             [AI Extracted Badge]    |
|                                                                    |
|    +------------------------------------------------------+       |
|    | TARGET COMPANIES                                      |       |
|    |                                                       |       |
|    | Industries:   Technology, SaaS, Fintech               |       |
|    | Sizes:        11-50, 51-200 employees                 |       |
|    | Locations:    Sydney, Melbourne, Brisbane             |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    +------------------------------------------------------+       |
|    | TARGET CONTACTS                                       |       |
|    |                                                       |       |
|    | Roles:  CEO, CTO, VP Engineering, Founder             |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    +------------------------------------------------------+       |
|    | MESSAGING CONTEXT                                     |       |
|    |                                                       |       |
|    | Pain Points:                                          |       |
|    | - Struggling to scale lead generation                 |       |
|    | - Manual outreach is time-consuming                   |       |
|    |                                                       |       |
|    | Value Props:                                          |       |
|    | - Automated multi-channel outreach                    |       |
|    | - AI-powered personalization at scale                 |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    [ Edit ICP ]                   [ Confirm & Continue ]           |
|                                                                    |
+------------------------------------------------------------------+
```

### Step 4: LinkedIn Connection

```
+------------------------------------------------------------------+
|                                                                    |
|                   Connect LinkedIn                                 |
|      Connect your LinkedIn account to enable automated outreach    |
|                                                                    |
|    +------------------------------------------------------+       |
|    | LinkedIn Email                                        |       |
|    +------------------------------------------------------+       |
|    | your@email.com                                       |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    +------------------------------------------------------+       |
|    | LinkedIn Password                                     |       |
|    +------------------------------------------------------+       |
|    | ********                                             |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    +------------------------------------------------------+       |
|    | [Blue Card] Your credentials are secure               |       |
|    |                                                       |       |
|    | [X] Encrypted at rest using AES-256                   |       |
|    | [X] Only used for outreach automation                 |       |
|    | [X] We never post to your feed                        |       |
|    | [X] Disconnect anytime from settings                  |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    +------------------------------------------------------+       |
|    |               Connect LinkedIn                        |       |
|    +------------------------------------------------------+       |
|                                                                    |
|                          ─── Or ───                                |
|                                                                    |
|    +------------------------------------------------------+       |
|    |               Skip for now                            |       |
|    +------------------------------------------------------+       |
|                                                                    |
|           You can connect LinkedIn later from Settings             |
|                                                                    |
+------------------------------------------------------------------+
```

### LinkedIn 2FA Required

```
+------------------------------------------------------------------+
|                                                                    |
|                      [Phone Icon]                                  |
|                                                                    |
|                  Verification Required                             |
|                                                                    |
|        LinkedIn sent a code to your phone.                         |
|        Enter the code below to complete connection.                |
|                                                                    |
|    +------------------------------------------------------+       |
|    |                   [ _ _ _ _ _ _ ]                      |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    [ Error: Invalid code. Please try again. ]                      |
|                                                                    |
|    +------------------------------------------------------+       |
|    |                   Verify Code                         |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    +------------------------------------------------------+       |
|    |                   Back to Login                       |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    Code not received? Check spam or try again in a few minutes     |
|                                                                    |
+------------------------------------------------------------------+
```

### LinkedIn Success

```
+------------------------------------------------------------------+
|                                                                    |
|                  [Green Checkmark Icon]                            |
|                                                                    |
|                  LinkedIn Connected!                               |
|                                                                    |
|     Your LinkedIn account is now connected for automated outreach. |
|                                                                    |
|    +------------------------------------------------------+       |
|    | [LI Logo]  John Smith                                 |       |
|    |            View Profile                               |       |
|    +------------------------------------------------------+       |
|                                                                    |
|                   Agency OS can now:                               |
|                                                                    |
|                   - Send connection requests to prospects          |
|                   - Send personalized messages                     |
|                   - Follow up with interested leads                |
|                                                                    |
|    +------------------------------------------------------+       |
|    |                    Continue                           |       |
|    +------------------------------------------------------+       |
|                                                                    |
+------------------------------------------------------------------+
```

### Step 5: Complete

```
+------------------------------------------------------------------+
|                                                                    |
|                   [Celebration Animation]                          |
|                                                                    |
|                     You're All Set!                                |
|                                                                    |
|      Your Agency OS account is ready. Here's what's next:          |
|                                                                    |
|    +------------------------------------------------------+       |
|    | [X] ICP configured                                    |       |
|    |     Targeting Tech CEOs in Sydney                     |       |
|    |                                                       |       |
|    | [X] LinkedIn connected                                |       |
|    |     Ready for automated outreach                      |       |
|    |                                                       |       |
|    | [>] First campaign being prepared                     |       |
|    |     AI is generating your campaign suggestions        |       |
|    +------------------------------------------------------+       |
|                                                                    |
|    +------------------------------------------------------+       |
|    |               Go to Dashboard                         |       |
|    +------------------------------------------------------+       |
|                                                                    |
|     We'll notify you when your first campaign is ready             |
|                                                                    |
+------------------------------------------------------------------+
```

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `lg` (1024px+) | Centered card, max-width 500px |
| `md` (768px) | Centered card, max-width 450px |
| `sm` (< 768px) | Full-width with padding, stacked elements |

### Mobile Layout

```
Mobile (sm):
+--------------------------------+
|       [Agency OS Logo]         |
+--------------------------------+
|                                |
|         [Globe Icon]           |
|                                |
|    Welcome to Agency OS        |
|                                |
| Enter your website URL and     |
| we'll automatically discover   |
| your ideal customer profile    |
|                                |
| Your Website URL               |
| +----------------------------+ |
| | https://youragency.com     | |
| +----------------------------+ |
|                                |
| +----------------------------+ |
| |      Discover My ICP       | |
| +----------------------------+ |
|                                |
|   Skip for now (testing only)  |
|                                |
+--------------------------------+
```

---

## Related Documentation

| Doc | Purpose |
|-----|---------|
| `docs/architecture/flows/ONBOARDING.md` | Backend onboarding flow details |
| `docs/architecture/frontend/SETTINGS.md` | ICP settings (post-onboarding edits) |
| `docs/architecture/frontend/DASHBOARD.md` | Where users land after onboarding |
| `docs/architecture/content/SDK_AND_PROMPTS.md` | SDK enhancement for ICP |

---

For gaps and implementation status, see `../TODO.md`.
