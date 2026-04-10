/**
 * FILE: frontend/lib/api/linkedin.ts
 * PURPOSE: LinkedIn connection API fetchers
 * PHASE: 309 - Onboarding Rebuild
 *
 * NOTE: connectLinkedIn (POST /connect with email/password) and verify2FA
 * removed — credential-based LinkedIn is deprecated. Use Unipile OAuth
 * via GET /api/v1/linkedin/connect instead.
 */

import api from "./index";

// ============================================
// Types
// ============================================

export interface LinkedInStatusResponse {
  status:
    | "not_connected"
    | "pending"
    | "connecting"
    | "connected"
    | "failed"
    | "disconnected";
  profile_url?: string | null;
  profile_name?: string | null;
  headline?: string | null;
  connection_count?: number | null;
  connected_at?: string | null;
  error?: string | null;
}

export interface LinkedInDisconnectResponse {
  status: "disconnected";
}

// ============================================
// API Functions
// ============================================

/**
 * Get LinkedIn connection status
 */
export async function getLinkedInStatus(): Promise<LinkedInStatusResponse> {
  return api.get<LinkedInStatusResponse>("/api/v1/linkedin/status");
}

/**
 * Disconnect LinkedIn account
 */
export async function disconnectLinkedIn(): Promise<LinkedInDisconnectResponse> {
  return api.post<LinkedInDisconnectResponse>("/api/v1/linkedin/disconnect");
}

// Export as linkedinApi for convenience
export const linkedinApi = {
  getStatus: getLinkedInStatus,
  disconnect: disconnectLinkedIn,
};

export default linkedinApi;
