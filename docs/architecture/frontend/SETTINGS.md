# Frontend Settings Architecture

**Purpose:** Architecture spec for Agency OS settings and configuration pages.
**Last Updated:** 2026-01-23
**Status:** Specification Complete

---

## 1. Overview

### Purpose

The settings pages enable clients to configure their Agency OS account, define their Ideal Customer Profile (ICP), manage LinkedIn connections, and control notification preferences. Settings are outcome-focused, helping clients optimize for meeting bookings.

### Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Outcome-Focused** | Settings exist to help book more meetings |
| **Simple ICP** | Clients describe ideal customer, system handles complexity |
| **LinkedIn as Channel** | Not primary focus, just another outreach channel |
| **Transparency** | Client controls what they see (daily digest, live feed, etc.) |
| **Emergency Controls** | Quick access to pause/resume all outreach |

### Key Settings Sections

| Section | Purpose | Priority |
|---------|---------|----------|
| **ICP Configuration** | Define target audience for all campaigns | P1 |
| **LinkedIn Connection** | Connect LinkedIn for automated outreach | P2 |
| **Profile Settings** | Company details, timezone, contact info | P2 |
| **Notification Settings** | Daily digest, alerts, activity feed | P2 |
| **Emergency Controls** | Pause/resume all outreach | P1 |
| **Integrations** | View connected services status | P3 |

---

## 2. Routes

### Settings Route Structure

```
/dashboard/settings              -> Main settings hub
/dashboard/settings/icp          -> ICP configuration form
/dashboard/settings/linkedin     -> LinkedIn connection management
/dashboard/settings/profile      -> Client profile settings (planned)
/dashboard/settings/notifications -> Notification preferences (planned)
```

### Route Files

| Route | File | Purpose | Status |
|-------|------|---------|--------|
| `/dashboard/settings` | `frontend/app/dashboard/settings/page.tsx` | Settings hub with links to subsections | IMPLEMENTED |
| `/dashboard/settings/icp` | `frontend/app/dashboard/settings/icp/page.tsx` | ICP form with re-analyze button | IMPLEMENTED |
| `/dashboard/settings/linkedin` | `frontend/app/dashboard/settings/linkedin/page.tsx` | LinkedIn credential management | IMPLEMENTED |
| `/dashboard/settings/profile` | `frontend/app/dashboard/settings/profile/page.tsx` | Company profile settings | NOT IMPLEMENTED |
| `/dashboard/settings/notifications` | `frontend/app/dashboard/settings/notifications/page.tsx` | Notification preferences | NOT IMPLEMENTED |

---

## 3. Data Available

### Client Model

```typescript
// frontend/lib/api/types.ts

interface Client {
  id: UUID;
  name: string;
  tier: TierType;                        // "ignition" | "velocity" | "dominance"
  subscription_status: SubscriptionStatus;
  credits_remaining: number;             // Internal - not shown to client
  default_permission_mode: PermissionMode;
  created_at: string;
  updated_at: string;
}

// Extended client with profile fields (backend model)
interface ClientProfile extends Client {
  // Contact info
  contact_email: string | null;
  contact_phone: string | null;
  timezone: string | null;              // e.g., "Australia/Sydney"

  // Company info
  company_website: string | null;
  company_logo_url: string | null;
  company_description: string | null;

  // Outreach status
  outreach_paused: boolean;
  outreach_paused_at: string | null;
  outreach_paused_by: string | null;

  // Notification preferences
  daily_digest_enabled: boolean;
  daily_digest_time: string | null;     // "09:00" format
  meeting_alerts_enabled: boolean;
  reply_alerts_enabled: boolean;
  activity_feed_enabled: boolean;

  // Billing (read-only display)
  stripe_customer_id: string | null;
  current_period_end: string | null;
}

type TierType = "ignition" | "velocity" | "dominance";
type SubscriptionStatus = "trialing" | "active" | "past_due" | "cancelled" | "paused";
type PermissionMode = "autopilot" | "co_pilot" | "manual";
```

### ICP Model

```typescript
// frontend/app/dashboard/settings/icp/page.tsx

interface ICPProfile {
  id: string;
  client_id: string;

  // Target companies
  target_industries: string[];         // ["Technology", "SaaS", "Fintech"]
  target_company_sizes: string[];      // ["10-50", "51-200", "201-500"]
  target_locations: string[];          // ["Sydney", "Melbourne", "Brisbane"]
  revenue_range_min: number | null;    // Minimum revenue in AUD
  revenue_range_max: number | null;    // Maximum revenue in AUD

  // Target contacts
  target_job_titles: string[];         // ["CEO", "CTO", "VP Engineering"]

  // Filtering
  keywords: string[];                  // Include keywords
  exclusions: string[];                // Exclude keywords (competitors, etc.)

  // Messaging context
  pain_points: string[];               // Problems ideal customers face
  value_propositions: string[];        // How client solves problems

  // Extraction metadata
  extracted_from_website: boolean;
  last_extraction_at: string | null;

  created_at: string;
  updated_at: string;
}

// Global ICPProfile type (from types.ts)
interface ICPProfile {
  target_industries: string[];
  target_locations: string[];
  target_company_sizes: string[];
  target_job_titles: string[];
  target_keywords: string[];
  exclusion_keywords: string[];
  value_proposition: string | null;
  messaging_context: string | null;
  last_extracted_at: string | null;
}
```

### LinkedIn Status Model

```typescript
// frontend/lib/api/linkedin.ts

interface LinkedInStatusResponse {
  status: "connected" | "disconnected" | "connecting" | "awaiting_2fa" | "failed";
  profile_name: string | null;
  profile_url: string | null;
  connected_at: string | null;
  two_fa_method: string | null;        // "sms" | "authenticator" | "email"
  error: string | null;
}

interface LinkedInConnectRequest {
  linkedin_email: string;
  linkedin_password: string;
}

interface LinkedInConnectResponse {
  status: "connected" | "awaiting_2fa" | "failed";
  method?: string;                     // 2FA method if awaiting
  error?: string;
}

interface TwoFactorRequest {
  code: string;
}
```

### Notification Preferences Model

```typescript
// Planned structure for notification settings

interface NotificationPreferences {
  // Daily digest
  daily_digest_enabled: boolean;
  daily_digest_time: string;           // "09:00" in client timezone
  daily_digest_include_metrics: boolean;
  daily_digest_include_meetings: boolean;
  daily_digest_include_replies: boolean;

  // Real-time alerts
  meeting_alerts_enabled: boolean;     // New meeting booked
  reply_alerts_enabled: boolean;       // Hot lead replied
  reply_alert_tiers: ALSTier[];        // Which tiers trigger alerts

  // Activity feed
  activity_feed_enabled: boolean;      // Show live feed on dashboard

  // Email preferences
  weekly_summary_enabled: boolean;
  marketing_emails_enabled: boolean;
}
```

---

## 4. User Actions

### Main Settings Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Navigate to ICP settings | Link card | - | IMPLEMENTED |
| Edit organization name | Input | `PATCH /clients/{id}` | PLACEHOLDER |
| View subscription tier | Badge (read-only) | - | IMPLEMENTED |
| Navigate to upgrade | Button link | Stripe portal | NOT IMPLEMENTED |
| Change default permission mode | Permission cards | `PATCH /clients/{id}` | PLACEHOLDER |
| View integration status | Integration cards | - | PLACEHOLDER |
| Delete organization | Danger zone button | `DELETE /clients/{id}` | NOT IMPLEMENTED |

### ICP Settings Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Edit target industries | Input | Local state | IMPLEMENTED |
| Edit company sizes | Input | Local state | IMPLEMENTED |
| Edit locations | Input | Local state | IMPLEMENTED |
| Edit revenue range | Number inputs | Local state | IMPLEMENTED |
| Edit job titles | Input | Local state | IMPLEMENTED |
| Edit include keywords | Input | Local state | IMPLEMENTED |
| Edit exclude keywords | Input | Local state | IMPLEMENTED |
| Edit pain points | Textarea | Local state | IMPLEMENTED |
| Edit value propositions | Textarea | Local state | IMPLEMENTED |
| Save changes | Button | `PUT /clients/{id}/icp` | IMPLEMENTED |
| Re-analyze website | Button | `POST /clients/{id}/icp/reanalyze` | IMPLEMENTED |
| Cancel and go back | Button | - | IMPLEMENTED |

### LinkedIn Settings Page Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| View connection status | Badge | `GET /linkedin/status` | IMPLEMENTED |
| Start connection | Button | Opens form | IMPLEMENTED |
| Submit credentials | Form | `POST /linkedin/connect` | IMPLEMENTED |
| Submit 2FA code | Form | `POST /linkedin/verify-2fa` | IMPLEMENTED |
| Disconnect account | Button (with dialog) | `POST /linkedin/disconnect` | IMPLEMENTED |
| Reconnect account | Button | Opens form | IMPLEMENTED |

### Profile Settings Page Actions (Planned)

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Edit company name | Input | `PATCH /clients/{id}` | NOT IMPLEMENTED |
| Upload company logo | FileInput | `POST /clients/{id}/logo` | NOT IMPLEMENTED |
| Edit contact email | Input | `PATCH /clients/{id}` | NOT IMPLEMENTED |
| Edit timezone | Select | `PATCH /clients/{id}` | NOT IMPLEMENTED |
| View billing info | Card (read-only) | `GET /clients/{id}/billing` | NOT IMPLEMENTED |
| Manage billing | Button | Stripe portal redirect | NOT IMPLEMENTED |

### Notification Settings Page Actions (Planned)

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Toggle daily digest | Switch | `PATCH /clients/{id}/notifications` | NOT IMPLEMENTED |
| Set digest time | TimePicker | `PATCH /clients/{id}/notifications` | NOT IMPLEMENTED |
| Toggle meeting alerts | Switch | `PATCH /clients/{id}/notifications` | NOT IMPLEMENTED |
| Toggle reply alerts | Switch | `PATCH /clients/{id}/notifications` | NOT IMPLEMENTED |
| Select reply alert tiers | Checkbox group | `PATCH /clients/{id}/notifications` | NOT IMPLEMENTED |
| Toggle activity feed | Switch | `PATCH /clients/{id}/notifications` | NOT IMPLEMENTED |

### Emergency Controls Actions

| Action | Component | API Call | Status |
|--------|-----------|----------|--------|
| Pause all outreach | EmergencyPauseButton | `POST /clients/{id}/pause` | NOT IMPLEMENTED |
| Resume outreach | ResumeButton | `POST /clients/{id}/resume` | NOT IMPLEMENTED |
| View pause status | StatusIndicator | `GET /clients/{id}` | NOT IMPLEMENTED |

---

## 5. Components (Existing)

### Settings Page Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| SettingsPage | `app/dashboard/settings/page.tsx` | None | Settings hub with navigation cards |
| ICPSettingsPage | `app/dashboard/settings/icp/page.tsx` | None | ICP configuration form |
| LinkedInSettingsPage | `app/dashboard/settings/linkedin/page.tsx` | None | LinkedIn connection management |

### LinkedIn Components

| Component | File | Props | Purpose |
|-----------|------|-------|---------|
| LinkedInCredentialForm | `components/onboarding/LinkedInCredentialForm.tsx` | `onSubmit`, `error`, `isLoading` | Email/password input form |
| LinkedInTwoFactor | `components/onboarding/LinkedInTwoFactor.tsx` | `method`, `onSubmit`, `onBack`, `error`, `isLoading` | 2FA code input |
| LinkedInConnecting | `components/onboarding/LinkedInConnecting.tsx` | None | Loading state during connection |

### Shared UI Components

| Component | File | Purpose |
|-----------|------|---------|
| Card, CardHeader, CardContent | `components/ui/card.tsx` | Section containers |
| Badge | `components/ui/badge.tsx` | Status badges (connected, tier) |
| Button | `components/ui/button.tsx` | Actions |
| Input | `components/ui/input.tsx` | Text fields |
| Label | `components/ui/label.tsx` | Form labels |
| Textarea | `components/ui/textarea.tsx` | Multi-line text |
| AlertDialog | `components/ui/alert-dialog.tsx` | Confirmation dialogs |

---

## 6. Components to Create

### EmergencyPauseButton

```typescript
// frontend/components/settings/EmergencyPauseButton.tsx

interface EmergencyPauseButtonProps {
  isPaused: boolean;
  pausedAt: string | null;
  pausedBy: string | null;
  onPause: () => void;
  onResume: () => void;
  isLoading: boolean;
}

/**
 * Prominent button for pausing/resuming all outreach:
 * - Red "Pause All Outreach" when active
 * - Green "Resume Outreach" when paused
 * - Shows pause timestamp and who paused
 * - Confirmation dialog before pause
 * - Placed prominently in settings or header
 */
```

**Design:**
```
ACTIVE STATE:
+----------------------------------------------------------+
| [!] Emergency Controls                                    |
|                                                           |
| All outreach is currently ACTIVE                          |
|                                                           |
| [ Pause All Outreach ]  <-- Red destructive button        |
+----------------------------------------------------------+

PAUSED STATE:
+----------------------------------------------------------+
| [!] Emergency Controls                                    |
|                                                           |
| Outreach PAUSED since Jan 23, 2026 at 2:15 PM            |
| Paused by: john@acme.com                                  |
|                                                           |
| [ Resume Outreach ]  <-- Green success button             |
+----------------------------------------------------------+
```

### NotificationSettingsForm

```typescript
// frontend/components/settings/NotificationSettingsForm.tsx

interface NotificationSettingsFormProps {
  preferences: NotificationPreferences;
  onSave: (prefs: NotificationPreferences) => void;
  isSaving: boolean;
  timezone: string;
}

/**
 * Form for managing notification preferences:
 * - Daily digest toggle + time picker
 * - Meeting alert toggle
 * - Reply alert toggle with tier selection
 * - Activity feed toggle
 * - Save button with optimistic update
 */
```

**Design:**
```
+----------------------------------------------------------+
| Daily Digest                                              |
|                                                           |
| [x] Send daily summary email                              |
| Time: [ 09:00 AM v ] (Australia/Sydney)                   |
|                                                           |
| Include:                                                  |
| [x] Yesterday's metrics                                   |
| [x] Upcoming meetings                                     |
| [x] Hot lead replies                                      |
+----------------------------------------------------------+

+----------------------------------------------------------+
| Real-time Alerts                                          |
|                                                           |
| [x] New meeting booked                                    |
| [x] Hot lead replied                                      |
|     Alert for: [x] Hot [x] Warm [ ] Cool [ ] Cold         |
+----------------------------------------------------------+

+----------------------------------------------------------+
| Dashboard                                                 |
|                                                           |
| [x] Show live activity feed                               |
+----------------------------------------------------------+
```

### ProfileSettingsForm

```typescript
// frontend/components/settings/ProfileSettingsForm.tsx

interface ProfileSettingsFormProps {
  client: ClientProfile;
  onSave: (updates: Partial<ClientProfile>) => void;
  isSaving: boolean;
}

/**
 * Form for editing client profile:
 * - Company name
 * - Company logo upload
 * - Contact email
 * - Timezone selector
 * - Read-only billing info with link to Stripe
 */
```

**Design:**
```
+----------------------------------------------------------+
| Company Information                                       |
|                                                           |
| Company Name                                              |
| [ Acme Agency                                   ]         |
|                                                           |
| Logo                                                      |
| [Logo Preview] [ Upload New ]                             |
|                                                           |
| Website                                                   |
| [ https://acmeagency.com                        ]         |
+----------------------------------------------------------+

+----------------------------------------------------------+
| Contact Information                                       |
|                                                           |
| Contact Email                                             |
| [ john@acmeagency.com                           ]         |
|                                                           |
| Timezone                                                  |
| [ Australia/Sydney                            v ]         |
+----------------------------------------------------------+

+----------------------------------------------------------+
| Billing                                                   |
|                                                           |
| Current Plan: Velocity                                    |
| Status: Active                                            |
| Next billing: February 1, 2026                            |
|                                                           |
| [ Manage Billing ]  --> Opens Stripe portal               |
+----------------------------------------------------------+
```

### IntegrationStatusCard

```typescript
// frontend/components/settings/IntegrationStatusCard.tsx

interface IntegrationStatusCardProps {
  name: string;
  description: string;
  status: "connected" | "not_connected" | "error";
  connectedAt?: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  isManaged?: boolean;    // true for platform-managed (Apollo, Resend)
}

/**
 * Display card for integration status:
 * - Integration name and description
 * - Connection status badge
 * - Connect/Disconnect actions (if applicable)
 * - "Managed by Agency OS" label for platform integrations
 */
```

### TimezoneSelector

```typescript
// frontend/components/settings/TimezoneSelector.tsx

interface TimezoneSelectorProps {
  value: string;
  onChange: (timezone: string) => void;
  label?: string;
  showCurrentTime?: boolean;
}

/**
 * Timezone selector with search:
 * - Searchable dropdown of timezones
 * - Shows current time in selected timezone
 * - Grouped by region (Australia, US, Europe)
 * - Prioritizes Australian timezones
 */
```

### ICPSectionCard

```typescript
// frontend/components/settings/ICPSectionCard.tsx

interface ICPSectionCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}

/**
 * Wrapper card for ICP form sections:
 * - Consistent styling across ICP form
 * - Icon + title header
 * - Description text
 * - Form content as children
 */
```

---

## 7. API Integration

### Current Hooks

| Hook | File | Query Key | Endpoint | Status |
|------|------|-----------|----------|--------|
| `useClient` | `hooks/use-client.ts` | `["current-client"]` | Supabase direct | IMPLEMENTED |
| `useLinkedInStatus` | `hooks/use-linkedin.ts` | `["linkedin", "status"]` | `GET /linkedin/status` | IMPLEMENTED |
| `useLinkedInConnect` | `hooks/use-linkedin.ts` | N/A (mutation) | `POST /linkedin/connect` | IMPLEMENTED |
| `useLinkedInVerify2FA` | `hooks/use-linkedin.ts` | N/A (mutation) | `POST /linkedin/verify-2fa` | IMPLEMENTED |
| `useLinkedInDisconnect` | `hooks/use-linkedin.ts` | N/A (mutation) | `POST /linkedin/disconnect` | IMPLEMENTED |

### ICP API (Inline in Page)

```typescript
// Current implementation in icp/page.tsx

// Fetch ICP
async function fetchICP(clientId: string): Promise<ICPProfile> {
  const response = await fetch(`/api/v1/clients/${clientId}/icp`);
  if (!response.ok) throw new Error("Failed to fetch ICP profile");
  return response.json();
}

// Update ICP
async function updateICP(clientId: string, data: Partial<ICPProfile>): Promise<ICPProfile> {
  const response = await fetch(`/api/v1/clients/${clientId}/icp`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to update ICP profile");
  return response.json();
}

// Re-analyze website
async function reanalyzeWebsite(clientId: string): Promise<{ task_id: string }> {
  const response = await fetch(`/api/v1/clients/${clientId}/icp/reanalyze`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to start website re-analysis");
  return response.json();
}
```

### Hooks to Create

| Hook | Query Key | Endpoint | Purpose |
|------|-----------|----------|---------|
| `useICP` | `["icp", clientId]` | `GET /clients/{id}/icp` | Fetch ICP profile |
| `useUpdateICP` | N/A (mutation) | `PUT /clients/{id}/icp` | Update ICP profile |
| `useReanalyzeICP` | N/A (mutation) | `POST /clients/{id}/icp/reanalyze` | Trigger website re-analysis |
| `useClientProfile` | `["client-profile", clientId]` | `GET /clients/{id}/profile` | Full client profile |
| `useUpdateClientProfile` | N/A (mutation) | `PATCH /clients/{id}` | Update profile fields |
| `useNotificationPrefs` | `["notifications", clientId]` | `GET /clients/{id}/notifications` | Notification preferences |
| `useUpdateNotifications` | N/A (mutation) | `PATCH /clients/{id}/notifications` | Update notifications |
| `usePauseOutreach` | N/A (mutation) | `POST /clients/{id}/pause` | Pause all outreach |
| `useResumeOutreach` | N/A (mutation) | `POST /clients/{id}/resume` | Resume outreach |

### Proposed Hooks Implementation

```typescript
// frontend/hooks/use-settings.ts

export function useICP() {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["icp", clientId],
    queryFn: () => fetchICP(clientId!),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000, // 5 minutes - ICP rarely changes
  });
}

export function useUpdateICP() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<ICPProfile>) => updateICP(clientId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["icp", clientId] });
    },
  });
}

export function usePauseOutreach() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post(`/clients/${clientId}/pause`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["current-client"] });
      queryClient.invalidateQueries({ queryKey: ["client-profile", clientId] });
    },
  });
}
```

---

## 8. API Gaps

### Missing Endpoints

| Endpoint | Purpose | Priority | Backend File |
|----------|---------|----------|--------------|
| `GET /clients/{id}/profile` | Extended client profile with all settings | P1 | `src/api/routes/clients.py` |
| `PATCH /clients/{id}` | Partial client update | P1 | `src/api/routes/clients.py` |
| `GET /clients/{id}/notifications` | Notification preferences | P2 | `src/api/routes/clients.py` |
| `PATCH /clients/{id}/notifications` | Update notification preferences | P2 | `src/api/routes/clients.py` |
| `POST /clients/{id}/pause` | Pause all outreach | P1 | `src/api/routes/clients.py` |
| `POST /clients/{id}/resume` | Resume outreach | P1 | `src/api/routes/clients.py` |
| `POST /clients/{id}/logo` | Upload company logo | P3 | `src/api/routes/clients.py` |
| `GET /clients/{id}/billing` | Billing info (Stripe summary) | P2 | `src/api/routes/billing.py` |
| `POST /clients/{id}/billing/portal` | Create Stripe portal session | P2 | `src/api/routes/billing.py` |

### Missing Database Fields

| Field | Table | Purpose | Priority |
|-------|-------|---------|----------|
| `outreach_paused` | `clients` | Whether outreach is paused | P1 |
| `outreach_paused_at` | `clients` | When outreach was paused | P1 |
| `outreach_paused_by` | `clients` | Who paused outreach | P1 |
| `daily_digest_enabled` | `clients` | Daily digest toggle | P2 |
| `daily_digest_time` | `clients` | Daily digest send time | P2 |
| `meeting_alerts_enabled` | `clients` | Meeting alert toggle | P2 |
| `reply_alerts_enabled` | `clients` | Reply alert toggle | P2 |
| `reply_alert_tiers` | `clients` | Which tiers trigger alerts | P2 |
| `activity_feed_enabled` | `clients` | Activity feed toggle | P2 |
| `company_logo_url` | `clients` | Company logo URL | P3 |
| `contact_phone` | `clients` | Contact phone number | P3 |

### API Response Shapes Needed

```typescript
// GET /clients/{id}/profile
interface ClientProfileResponse {
  id: string;
  name: string;
  tier: TierType;
  subscription_status: SubscriptionStatus;
  default_permission_mode: PermissionMode;

  // Profile
  contact_email: string | null;
  contact_phone: string | null;
  timezone: string;
  company_website: string | null;
  company_logo_url: string | null;
  company_description: string | null;

  // Outreach status
  outreach_paused: boolean;
  outreach_paused_at: string | null;
  outreach_paused_by: string | null;

  // Notification preferences
  daily_digest_enabled: boolean;
  daily_digest_time: string | null;
  meeting_alerts_enabled: boolean;
  reply_alerts_enabled: boolean;
  reply_alert_tiers: ALSTier[];
  activity_feed_enabled: boolean;

  // Billing (read-only)
  billing: {
    current_plan: string;
    status: string;
    next_billing_date: string | null;
    monthly_amount: number;
    currency: string;
  };
}

// POST /clients/{id}/pause
interface PauseResponse {
  success: boolean;
  paused_at: string;
  paused_by: string;
  affected_campaigns: number;
}

// POST /clients/{id}/resume
interface ResumeResponse {
  success: boolean;
  resumed_at: string;
  resumed_by: string;
  resumed_campaigns: number;
}
```

---

## 9. State Management

### ICP Form State

```typescript
// Current implementation uses useState for each field
// Form state is synced with API data on load via useEffect

interface ICPFormState {
  industries: string;           // Comma-separated
  companySizes: string;         // Comma-separated
  locations: string;            // Comma-separated
  jobTitles: string;            // Comma-separated
  revenueMin: string;           // Number as string
  revenueMax: string;           // Number as string
  keywords: string;             // Comma-separated
  exclusions: string;           // Comma-separated
  painPoints: string;           // Newline-separated
  valueProps: string;           // Newline-separated
}

// Parser functions
const parseList = (value: string): string[] =>
  value.split(",").map(s => s.trim()).filter(Boolean);

const parseLines = (value: string): string[] =>
  value.split("\n").map(s => s.trim()).filter(Boolean);
```

### Form Validation

```typescript
// ICP form validation rules

interface ICPValidation {
  // Required: at least one industry
  industries: {
    required: true,
    minItems: 1,
    message: "Please enter at least one target industry"
  };

  // Required: at least one job title
  jobTitles: {
    required: true,
    minItems: 1,
    message: "Please enter at least one target job title"
  };

  // Optional but recommended
  companySizes: {
    recommended: true,
    message: "Adding company sizes helps improve targeting"
  };

  // Revenue validation
  revenueRange: {
    validate: (min, max) => !min || !max || parseInt(min) < parseInt(max),
    message: "Minimum revenue must be less than maximum"
  };
}
```

### LinkedIn Connection State Machine

```typescript
// LinkedIn settings uses a state machine pattern

type LinkedInState = "idle" | "form" | "connecting" | "2fa";

// State transitions:
// idle -> form (click "Connect LinkedIn")
// form -> connecting (submit credentials)
// connecting -> idle (success)
// connecting -> 2fa (2FA required)
// connecting -> form (error)
// 2fa -> idle (success)
// 2fa -> form (error)
// 2fa -> form (back button)
```

### React Query Configuration

```typescript
const SETTINGS_STALE_TIMES = {
  icp: 5 * 60 * 1000,           // 5 minutes - rarely changes
  linkedin: 30 * 1000,          // 30 seconds - status can change
  profile: 5 * 60 * 1000,       // 5 minutes
  notifications: 5 * 60 * 1000, // 5 minutes
};

const SETTINGS_REFETCH = {
  linkedin: 60 * 1000,          // Poll every minute for status changes
};
```

---

## 10. v0 Integration

### Ready for Visual Design

| Section | Component | Ready? | Notes |
|---------|-----------|--------|-------|
| Settings Hub | SettingsPage | PARTIAL | Layout exists, needs styling polish |
| ICP Link Card | Card + Link | YES | Functional with icon |
| Organization Card | Card + Form | PARTIAL | Placeholder data |
| Permission Mode | Cards + Selection | YES | Visual selection working |
| Integrations | Integration cards | PARTIAL | Static data |
| Danger Zone | Destructive card | YES | Styled correctly |
| ICP Form | Full form | YES | All fields implemented |
| ICP Sections | Section cards | YES | Icons and descriptions |
| LinkedIn Status | Status card | YES | All states handled |
| LinkedIn Form | Credential form | YES | Email/password inputs |
| LinkedIn 2FA | 2FA form | YES | Code input with method display |
| Emergency Pause | - | NO | Needs EmergencyPauseButton |
| Notifications | - | NO | Needs NotificationSettingsForm |
| Profile | - | NO | Needs ProfileSettingsForm |

### CSS Variables (Tailwind)

```typescript
// Settings-specific styles

// Section cards
.settings-card {
  @apply border rounded-lg;
}

// ICP extraction badge
.badge-ai-extracted {
  @apply bg-primary/10 text-primary;
}

// Integration status badges
.badge-connected {
  @apply bg-green-500 text-white;
}

.badge-not-connected {
  @apply border border-input;
}

// LinkedIn branding
.linkedin-blue {
  color: #0077b5;
}

// Danger zone
.danger-card {
  @apply border-destructive;
}

.danger-button {
  @apply bg-destructive text-destructive-foreground hover:bg-destructive/90;
}

// Emergency pause states
.pause-active {
  @apply border-green-500 bg-green-50;
}

.pause-paused {
  @apply border-yellow-500 bg-yellow-50;
}
```

### Component States for Design

All settings components should handle:
- **Loading** - Skeleton states for form fields
- **Error** - Error messages with retry
- **Empty** - Helpful guidance text
- **Dirty** - Unsaved changes indicator
- **Submitting** - Loading state on buttons
- **Success** - Toast notifications

---

## 11. Wireframes

### Main Settings Page

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  SETTINGS                                                |
|        |                                                          |
| [Home] |  +------------------------------------------------------+|
| [Camp] |  | [Target] Ideal Customer Profile              >       ||
| [Leads]|  |          Define your target audience                 ||
| [Reply]|  +------------------------------------------------------+|
| [Reprt]|                                                          |
| [Setng]|  +------------------------------------------------------+|
|        |  | Organization                                         ||
|        |  |                                                      ||
|        |  | Organization Name        Subscription Tier           ||
|        |  | [ Acme Agency      ]     [Velocity] [Upgrade]        ||
|        |  |                                                      ||
|        |  | [ Save Changes ]                                     ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | Profile                                              ||
|        |  |                                                      ||
|        |  | Full Name               Email                        ||
|        |  | [ John Smith     ]      [ john@acme.com        ]     ||
|        |  |                                                      ||
|        |  | [ Update Profile ]                                   ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | Default Permission Mode                              ||
|        |  |                                                      ||
|        |  | +----------+ +----------+ +----------+               ||
|        |  | | Autopilot| | Co-Pilot | | Manual   |               ||
|        |  | | Full auto| | [Selected]| | Full    |               ||
|        |  | +----------+ +----------+ +----------+               ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | Emergency Controls                          [!]      ||
|        |  |                                                      ||
|        |  | All outreach is currently ACTIVE                     ||
|        |  |                                                      ||
|        |  | [ Pause All Outreach ]                               ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | Integrations                                         ||
|        |  |                                                      ||
|        |  | Apollo         Lead enrichment     [Connected]       ||
|        |  | LinkedIn       Via HeyReach        [Connected]       ||
|        |  | Resend         Email sending       [Connected]       ||
|        |  | Twilio         SMS sending         [Not Connected]   ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +--------------------[DANGER ZONE]---------------------+|
|        |  | Delete Organization                                  ||
|        |  | Permanently delete your organization and all data    ||
|        |  |                                        [ Delete ]    ||
|        |  +------------------------------------------------------+|
|        |                                                          |
+------------------------------------------------------------------+
```

### ICP Settings Page

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  < Back to Settings                                      |
|        |                                                          |
| [Home] |  Ideal Customer Profile          [ Re-analyze Website ] |
| [Camp] |  Define who you want to reach.                          |
| [Leads]|                                                          |
| [Reply]|  +------------------------------------------------------+|
| [Reprt]|  | [*] AI-Extracted Profile                             ||
| [Setng]|  |     Last extracted from your website on Jan 20, 2026 ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | [Building] Target Companies                          ||
|        |  |            Define the types of companies to reach    ||
|        |  |                                                      ||
|        |  | Industries                                           ||
|        |  | [ Technology, SaaS, Fintech, Healthcare        ]     ||
|        |  |                                                      ||
|        |  | Company Sizes          Locations                     ||
|        |  | [ 10-50, 51-200  ]     [ Sydney, Melbourne     ]     ||
|        |  |                                                      ||
|        |  | Revenue Min ($)        Revenue Max ($)               ||
|        |  | [ 1000000        ]     [ 50000000              ]     ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | [Users] Target Contacts                              ||
|        |  |         Define the roles you want to reach           ||
|        |  |                                                      ||
|        |  | Job Titles                                           ||
|        |  | [ CEO, CTO, VP Engineering, Founder            ]     ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | [Target] Keywords & Exclusions                       ||
|        |  |          Refine your targeting with keywords         ||
|        |  |                                                      ||
|        |  | Include Keywords                                     ||
|        |  | [ AI, machine learning, automation, B2B        ]     ||
|        |  |                                                      ||
|        |  | Exclude Keywords                                     ||
|        |  | [ agency, consulting, freelance                ]     ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | [Sparkles] Messaging Context                         ||
|        |  |            Help the AI craft better messages         ||
|        |  |                                                      ||
|        |  | Pain Points                                          ||
|        |  | +--------------------------------------------------+ ||
|        |  | | Struggling to scale lead generation              | ||
|        |  | | Manual outreach is time-consuming                | ||
|        |  | | Low reply rates from cold outreach               | ||
|        |  | +--------------------------------------------------+ ||
|        |  |                                                      ||
|        |  | Value Propositions                                   ||
|        |  | +--------------------------------------------------+ ||
|        |  | | Automated multi-channel outreach                 | ||
|        |  | | AI-powered personalization at scale              | ||
|        |  | | Consistent pipeline of qualified meetings        | ||
|        |  | +--------------------------------------------------+ ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  [ Save Changes ]  [ Cancel ]                            |
|        |                                                          |
+------------------------------------------------------------------+
```

### LinkedIn Settings Page

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  LinkedIn Settings                                       |
|        |  Manage your LinkedIn connection for automated outreach  |
|        |                                                          |
| [Home] |  +------------------------------------------------------+|
| [Camp] |  | Connection Status                     [Connected]    ||
| [Leads]|  |                                                      ||
| [Reply]|  | +--------------------------------------------------+ ||
| [Reprt]|  | | [LI Logo]  John Smith                            | ||
| [Setng]|  | |            View Profile                          | ||
|        |  | |            Connected on Jan 15, 2026             | ||
|        |  | +--------------------------------------------------+ ||
|        |  |                                                      ||
|        |  | [ Disconnect ]  [ Reconnect ]                        ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | Security Information                                 ||
|        |  |                                                      ||
|        |  | [Shield] Credentials encrypted using AES-256         ||
|        |  | [Shield] Password never stored in plain text         ||
|        |  | [Shield] Only used for automated outreach            ||
|        |  | [Shield] We never post to your LinkedIn feed         ||
|        |  +------------------------------------------------------+|
|        |                                                          |
+------------------------------------------------------------------+

DISCONNECTED STATE:
+------------------------------------------------------+
| Connection Status                    [Not Connected] |
|                                                      |
| Connect your LinkedIn account to enable automated    |
| outreach to prospects.                               |
|                                                      |
|              [ Connect LinkedIn ]                    |
+------------------------------------------------------+

CONNECTION FORM:
+------------------------------------------------------+
| Connect LinkedIn                                     |
| Enter your LinkedIn credentials to connect           |
|                                                      |
| Email                                                |
| [ john@example.com                             ]     |
|                                                      |
| Password                                             |
| [ ********                                     ]     |
|                                                      |
| [ Connect ]                                          |
| [ Cancel  ]                                          |
+------------------------------------------------------+

2FA REQUIRED:
+------------------------------------------------------+
| Verification Required                                |
|                                                      |
| LinkedIn sent a verification code via SMS.           |
| Enter the code to complete connection.               |
|                                                      |
| Verification Code                                    |
| [ _ _ _ _ _ _                                  ]     |
|                                                      |
| [ Verify ]                                           |
| [ Back   ]                                           |
+------------------------------------------------------+
```

### Notification Settings Page (Planned)

```
+------------------------------------------------------------------+
| AGENCY OS                                    [Client] [Settings] |
+------------------------------------------------------------------+
|        |                                                          |
| SIDEBAR|  Notification Settings                                   |
|        |  Configure how you receive updates from Agency OS        |
|        |                                                          |
| [Home] |  +------------------------------------------------------+|
| [Camp] |  | Daily Digest                                         ||
| [Leads]|  |                                                      ||
| [Reply]|  | [x] Send daily summary email                         ||
| [Reprt]|  |                                                      ||
| [Setng]|  | Time: [ 09:00 AM         v ]                         ||
|        |  |       (Australia/Sydney)                             ||
|        |  |                                                      ||
|        |  | Include in digest:                                   ||
|        |  | [x] Yesterday's metrics                              ||
|        |  | [x] Upcoming meetings                                ||
|        |  | [x] Hot lead activity                                ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | Real-time Alerts                                     ||
|        |  |                                                      ||
|        |  | [x] New meeting booked                               ||
|        |  |     Get notified when a prospect books a meeting     ||
|        |  |                                                      ||
|        |  | [x] Hot lead replied                                 ||
|        |  |     Get notified when a high-value lead responds     ||
|        |  |                                                      ||
|        |  |     Notify me for:                                   ||
|        |  |     [x] Hot leads (85+)                              ||
|        |  |     [x] Warm leads (60-84)                           ||
|        |  |     [ ] Cool leads (35-59)                           ||
|        |  |     [ ] Cold leads (20-34)                           ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  +------------------------------------------------------+|
|        |  | Dashboard                                            ||
|        |  |                                                      ||
|        |  | [x] Show live activity feed                          ||
|        |  |     See real-time outreach activity on your          ||
|        |  |     dashboard home page                              ||
|        |  +------------------------------------------------------+|
|        |                                                          |
|        |  [ Save Changes ]                                        |
|        |                                                          |
+------------------------------------------------------------------+
```

### Responsive Breakpoints

| Breakpoint | Layout |
|------------|--------|
| `lg` (1024px+) | Sidebar visible, full-width cards |
| `md` (768px) | Sidebar collapsible, 2-column grids |
| `sm` (< 768px) | Sidebar hidden, single column stacked |

### Form Grid

```
Desktop (lg):
+---------------------------+---------------------------+
| Company Sizes             | Locations                 |  grid-cols-2
+---------------------------+---------------------------+
| Revenue Min               | Revenue Max               |  grid-cols-2
+---------------------------+---------------------------+

Mobile (sm):
+-------------------------------------------------------+
| Company Sizes                                         |  grid-cols-1
+-------------------------------------------------------+
| Locations                                             |
+-------------------------------------------------------+
```

---

## Related Documentation

| Doc | Purpose |
|-----|---------|
| `docs/architecture/flows/ONBOARDING.md` | ICP extraction flow details |
| `docs/architecture/frontend/DASHBOARD.md` | Dashboard where activity feed appears |
| `docs/architecture/frontend/TECHNICAL.md` | Tech stack and patterns |
| `docs/architecture/business/TIERS_AND_BILLING.md` | Tier details for billing display |

---

For gaps and implementation status, see `../TODO.md`.
