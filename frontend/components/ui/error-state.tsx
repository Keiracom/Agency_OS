/**
 * FILE: frontend/components/ui/error-state.tsx
 * PURPOSE: Error state component for failed data fetching
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-007
 */

"use client";

import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { APIError } from "@/lib/api";

interface ErrorStateProps {
  error: Error | null;
  onRetry?: () => void;
  onBack?: () => void;
  title?: string;
  className?: string;
}

/**
 * Get user-friendly error message from error object
 */
function getErrorMessage(error: Error | null): string {
  if (!error) return "An unknown error occurred";

  if (error instanceof APIError) {
    switch (error.status) {
      case 401:
        return "Your session has expired. Please log in again.";
      case 403:
        return "You don't have permission to access this resource.";
      case 404:
        return "The requested resource was not found.";
      case 429:
        return "Too many requests. Please wait a moment and try again.";
      case 500:
      case 502:
      case 503:
        return "The server is currently unavailable. Please try again later.";
      default:
        // Try to get message from error data
        if (error.data && typeof error.data === "object" && "detail" in error.data) {
          return String(error.data.detail);
        }
        return error.message;
    }
  }

  return error.message || "An unexpected error occurred";
}

/**
 * Error state component - displays error message with retry option
 */
export function ErrorState({
  error,
  onRetry,
  onBack,
  title = "Something went wrong",
  className,
}: ErrorStateProps) {
  const message = getErrorMessage(error);

  return (
    <Card className={cn("border-destructive", className)}>
      <CardContent className="p-6 text-center">
        <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-muted-foreground mb-4 max-w-md mx-auto">{message}</p>
        <div className="flex items-center justify-center gap-3">
          {onBack && (
            <Button onClick={onBack} variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Go Back
            </Button>
          )}
          {onRetry && (
            <Button onClick={onRetry}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Inline error message - smaller, less prominent
 */
export function InlineError({
  error,
  onRetry,
  className,
}: {
  error: Error | null;
  onRetry?: () => void;
  className?: string;
}) {
  const message = getErrorMessage(error);

  return (
    <div
      className={cn(
        "flex items-center gap-2 text-sm text-destructive",
        className
      )}
    >
      <AlertCircle className="h-4 w-4 flex-shrink-0" />
      <span>{message}</span>
      {onRetry && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onRetry}
          className="h-auto p-1 text-destructive hover:text-destructive"
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}

/**
 * Full page error state
 */
export function FullPageError({
  error,
  onRetry,
  onBack,
}: {
  error: Error | null;
  onRetry?: () => void;
  onBack?: () => void;
}) {
  return (
    <div className="flex min-h-[400px] items-center justify-center p-6">
      <ErrorState error={error} onRetry={onRetry} onBack={onBack} />
    </div>
  );
}

export default ErrorState;
