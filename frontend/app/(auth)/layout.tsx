/**
 * FILE: frontend/app/(auth)/layout.tsx
 * PURPOSE: Auth pages layout (login, signup)
 * PHASE: 8 (Frontend)
 * TASK: FE-006
 * 
 * SSG: Static shell - forms are client-side
 */

// Static shell, revalidate daily
export const revalidate = 86400;

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30">
      <div className="w-full max-w-md p-8">
        {children}
      </div>
    </div>
  );
}
