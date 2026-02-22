/**
 * FILE: frontend/app/providers.tsx
 * PURPOSE: Client-side providers wrapper
 * PHASE: 8 (Frontend)
 * TASK: FE-001
 * CEO Directive #028 — Demo mode provider added
 */

"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, Suspense } from "react";
import { Toaster } from "@/components/ui/toaster";
import { DemoProvider } from "@/lib/demo-context";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={null}>
        <DemoProvider>
          {children}
        </DemoProvider>
      </Suspense>
      <Toaster />
    </QueryClientProvider>
  );
}
