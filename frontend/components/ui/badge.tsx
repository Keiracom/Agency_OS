import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Badge Component — Pure Bloomberg Design System
 * CEO Directive #027 — Warm Charcoal + Amber ONLY
 */
const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        // ALS Tier variants — Amber-based
        hot: "border-amber/30 bg-amber-glow text-amber",
        warm: "border-amber-light/25 bg-amber-glow/70 text-amber-light",
        cool: "border-border-default bg-bg-surface text-text-secondary",
        cold: "border-border-subtle bg-bg-base text-text-muted",
        dead: "border-border-subtle bg-bg-void text-text-muted opacity-60",
        // Status variants — Amber-based
        active: "border-amber/30 bg-amber-glow text-amber",
        draft: "border-border-default bg-bg-surface text-text-secondary",
        paused: "border-amber-light/20 bg-amber-glow/50 text-amber-light",
        completed: "border-border-subtle bg-bg-surface text-text-muted",
        // Error variant
        error: "border-error/30 bg-error-glow text-error",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
