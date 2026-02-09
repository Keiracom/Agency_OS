/**
 * FILE: app/(auth)/login/page.tsx
 * PURPOSE: Login page - Server Component wrapper for SSG
 * 
 * SSG Strategy:
 * - Static shell (form is client-side)
 * - Revalidate daily (86400s) - page structure never changes
 * - Client interactivity handled by LoginClient component
 */

import { Metadata } from "next";
import LoginClient from "./LoginClient";

// SSG: Revalidate daily (login page structure never changes)
export const revalidate = 86400;

export const metadata: Metadata = {
  title: "Sign In - Agency OS",
  description: "Sign in to your Agency OS account to access your client acquisition dashboard.",
  robots: {
    index: false, // Don't index login pages
    follow: false,
  },
};

export default function LoginPage() {
  return <LoginClient />;
}
