/**
 * FILE: frontend/lib/__tests__/provider-labels.test.ts
 * PURPOSE: Verify the provider-leak scrub catches every known vendor name
 *          and that canonicalChannel normalises channel strings correctly.
 * PHASE: PHASE-2.1-REALTIME-VITEST — first real Vitest target
 *
 * Run: `npm test lib/__tests__/provider-labels.test.ts`
 *
 * ⚠ If you add a new vendor to CANONICAL_REPLACEMENTS in provider-labels.ts,
 *   add a row to LEAK_PAIRS below so the invariant is enforced.
 */
import { describe, expect, it } from "vitest";
import {
  canonicalChannel,
  canonicalMetric,
  providerLabel,
} from "@/lib/provider-labels";

/** [raw provider name] → [expected scrubbed substring the user should see] */
const LEAK_PAIRS: Array<[string, string]> = [
  ["Unipile",                 "LinkedIn"],
  ["Sent via Unipile",        "Sent via LinkedIn"],
  ["via Unipile",             "via LinkedIn"],
  ["ElevenAgents",            "Voice AI"],
  ["ElevenLabs Agent",        "Voice AI"],
  ["Salesforge",              "Email"],
  ["via Mailgun",             "via Email"],
  ["via Resend",              "via Email"],
  ["Prospeo",                 "Contact finder"],
  ["Leadmagic",               "Contact finder"],
  ["Bright Data",             "Profile data"],
  ["BrightData",              "Profile data"],
  ["DFS organic ETV",         "Organic traffic value"],
  ["DFS keywords",            "Keyword positions"],
  ["DFS",                     "Organic"],
];

const FORBIDDEN = [
  "Unipile", "Salesforge", "ElevenAgents", "ElevenLabs",
  "Mailgun", "Resend", "Prospeo", "Leadmagic", "Bright Data",
  "BrightData", "DataForSEO", "Proxycurl",
];

describe("providerLabel", () => {
  it("returns empty string unchanged", () => {
    expect(providerLabel("")).toBe("");
  });

  it("passes through plain text without provider names unchanged", () => {
    expect(providerLabel("Booked meeting for Tuesday")).toBe("Booked meeting for Tuesday");
  });

  it.each(LEAK_PAIRS)("scrubs %s → contains %s", (raw, expected) => {
    const out = providerLabel(raw);
    expect(out).toContain(expected);
  });

  it.each(FORBIDDEN)("never leaks raw name %s in its own output", (name) => {
    const out = providerLabel(`Sent via ${name} at 3pm`);
    // After scrub, the raw provider name must be gone (modulo the forbidden
    // DFS substring which legitimately matches 'DFSNewbie' — not a concern
    // for user-facing copy, but the regex already scrubs the standalone token).
    expect(out).not.toContain(name);
  });

  it("scrubs multiple providers in the same string", () => {
    const out = providerLabel("Prospeo then Unipile then Salesforge");
    expect(out).not.toMatch(/Prospeo/);
    expect(out).not.toMatch(/Unipile/);
    expect(out).not.toMatch(/Salesforge/);
    expect(out).toContain("Contact finder");
    expect(out).toContain("LinkedIn");
    expect(out).toContain("Email");
  });
});

describe("canonicalChannel", () => {
  const CHANNEL_MAP: Array<[string, string]> = [
    ["unipile",      "LinkedIn"],
    ["LinkedIn",     "LinkedIn"],
    ["salesforge",   "Email"],
    ["email",        "Email"],
    ["mailgun",      "Email"],
    ["resend",       "Email"],
    ["elevenagents", "Voice AI"],
    ["elevenlabs",   "Voice AI"],
    ["voice",        "Voice AI"],
    ["vapi",         "Voice AI"],
    ["sms",          "SMS"],
    ["telnyx",       "SMS"],
  ];

  it.each(CHANNEL_MAP)("canonicalises %s → %s", (input, expected) => {
    expect(canonicalChannel(input)).toBe(expected);
  });

  it("handles empty / unknown gracefully", () => {
    expect(canonicalChannel("")).not.toMatch(/undefined/);
    // Unknown channels should not throw or return a provider name
    const out = canonicalChannel("mystery");
    for (const name of FORBIDDEN) expect(out).not.toContain(name);
  });
});

describe("canonicalMetric", () => {
  it("delegates to providerLabel under the hood (DFS metric scrubs correctly)", () => {
    expect(canonicalMetric("DFS organic ETV")).toBe("Organic traffic value");
  });
});
