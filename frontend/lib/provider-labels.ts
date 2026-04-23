/**
 * Provider-leak scrub — canonical user-facing label mapping.
 *
 * Purpose: prevent third-party provider names (DataForSEO, Unipile, ElevenAgents,
 * Salesforge, etc.) leaking into user-facing dashboard copy. Our product is
 * presented as Keira's native capability — the underlying vendors are our
 * implementation detail, not the customer's concern.
 *
 * Usage:
 *   import { providerLabel } from "@/lib/provider-labels";
 *   <div>{providerLabel(rawLabel)}</div>
 *
 * When porting any Master v10 dashboard surface, ANY string that contains a
 * provider name MUST pass through `providerLabel()` before render. Prefer
 * `canonicalMetric()` or `canonicalChannel()` when the label is structured.
 */

const CANONICAL_REPLACEMENTS: ReadonlyArray<readonly [RegExp, string]> = [
  // Metrics
  [/\bDFS(?:\s+organic)?\s+ETV\b/gi, "Organic traffic value"],
  [/\bDFS\s+keywords?\b/gi, "Keyword positions"],
  [/\bDFS\b/gi, "Organic"],

  // Channel providers
  [/\bSent via Unipile\b/gi, "Sent via LinkedIn"],
  [/\bvia Unipile\b/gi, "via LinkedIn"],
  [/\bUnipile\b/gi, "LinkedIn"],

  // Voice AI providers
  [/\bElevenAgents\b/gi, "Voice AI"],
  [/\bElevenLabs?\s+Agents?\b/gi, "Voice AI"],

  // Email sending providers
  [/\bSalesforge\b/gi, "Email"],
  [/\bvia\s+Mailgun\b/gi, "via Email"],
  [/\bvia\s+Resend\b/gi, "via Email"],

  // Enrichment providers (should never appear user-facing, but defensive)
  [/\bProspeo\b/gi, "Contact finder"],
  [/\bLeadmagic\b/gi, "Contact finder"],
  [/\bBright\s*Data\b/gi, "Profile data"],
];

/**
 * Scrub a raw label string, replacing all known provider names with their
 * canonical user-facing equivalents. Safe to call on text containing none of
 * the known providers — returns input unchanged.
 */
export function providerLabel(raw: string): string {
  if (!raw) return raw;
  let out = raw;
  for (const [pattern, replacement] of CANONICAL_REPLACEMENTS) {
    out = out.replace(pattern, replacement);
  }
  return out;
}

/**
 * Channel-aware label. Prefer this when you already know the channel context
 * rather than relying on regex fallthrough on free text.
 */
export function canonicalChannel(channel: string): string {
  const key = (channel ?? "").toLowerCase();
  switch (key) {
    case "unipile":
    case "linkedin":
      return "LinkedIn";
    case "salesforge":
    case "email":
    case "mailgun":
    case "resend":
      return "Email";
    case "elevenagents":
    case "elevenlabs":
    case "voice":
    case "vapi":
      return "Voice AI";
    case "sms":
    case "telnyx":
      return "SMS";
    case "mail":
    case "directmail":
      return "Direct mail";
    default:
      return channel;
  }
}

/**
 * Metric-aware label. Drops DataForSEO / provider prefixes from metric names
 * so dashboards show "Organic traffic value" not "DFS organic ETV".
 */
export function canonicalMetric(metric: string): string {
  return providerLabel(metric);
}

/**
 * Agency Profile white-label: render outbound persona as the current agency
 * persona rather than the underlying "Keira" framework name. Falls back to
 * "Keira" if no agency persona is configured (dev / internal).
 */
export function agencyPersona(raw: string | undefined, profile?: { displayName?: string }): string {
  if (!profile?.displayName) return raw ?? "Keira";
  return (raw ?? "").replace(/\bKeira\b/gi, profile.displayName);
}
