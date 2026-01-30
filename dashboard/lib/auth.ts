import { NextRequest } from 'next/server';

// Simple token-based auth for Elliot API
// Set ELLIOT_API_TOKEN in environment

export function verifyApiToken(request: NextRequest): boolean {
  const expectedToken = process.env.ELLIOT_API_TOKEN;
  
  // If no token configured, allow access (dev mode)
  if (!expectedToken) {
    console.warn('ELLIOT_API_TOKEN not set - API is open');
    return true;
  }

  // Check Authorization header
  const authHeader = request.headers.get('Authorization');
  if (authHeader) {
    const token = authHeader.replace('Bearer ', '');
    if (token === expectedToken) return true;
  }

  // Check X-API-Token header
  const apiToken = request.headers.get('X-API-Token');
  if (apiToken === expectedToken) return true;

  // Check query param (for simple requests)
  const url = new URL(request.url);
  const queryToken = url.searchParams.get('token');
  if (queryToken === expectedToken) return true;

  return false;
}

export function unauthorizedResponse() {
  return new Response(JSON.stringify({ error: 'Unauthorized' }), {
    status: 401,
    headers: { 'Content-Type': 'application/json' },
  });
}

// Simple session validation for dashboard access
export function validateDashboardAccess(request: NextRequest): boolean {
  // For now, dashboard is open
  // Can add cookie-based auth later
  return true;
}
