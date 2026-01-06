/**
 * FILE: frontend/lib/api/linkedin.ts
 * PURPOSE: LinkedIn connection API fetchers
 * PHASE: 24H - LinkedIn Credential Connection
 */

import api from "./index";

// ============================================
// Types
// ============================================

export interface LinkedInConnectRequest {
  linkedin_email: string;
  linkedin_password: string;
}

export interface TwoFactorRequest {
  code: string;
}

export interface LinkedInStatusResponse {
  status:
    | "not_connected"
    | "pending"
    | "connecting"
    | "awaiting_2fa"
    | "connected"
    | "failed"
    | "disconnected";
  profile_url?: string | null;
  profile_name?: string | null;
  headline?: string | null;
  connection_count?: number | null;
  connected_at?: string | null;
  error?: string | null;
  two_fa_method?: string | null;
}

export interface LinkedInConnectResponse {
  status: "connected" | "awaiting_2fa" | "failed";
  profile_url?: string | null;
  profile_name?: string | null;
  method?: string | null;
  message?: string | null;
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
 * Start LinkedIn connection
 */
export async function connectLinkedIn(
  data: LinkedInConnectRequest
): Promise<LinkedInConnectResponse> {
  return api.post<LinkedInConnectResponse>("/api/v1/linkedin/connect", data);
}

/**
 * Submit 2FA verification code
 */
export async function verify2FA(
  data: TwoFactorRequest
): Promise<LinkedInConnectResponse> {
  return api.post<LinkedInConnectResponse>("/api/v1/linkedin/verify-2fa", data);
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
  connect: connectLinkedIn,
  verify2FA,
  disconnect: disconnectLinkedIn,
};

export default linkedinApi;
