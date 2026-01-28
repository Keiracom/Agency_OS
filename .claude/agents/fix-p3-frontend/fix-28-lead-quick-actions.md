---
name: Fix 28 - LeadQuickActions Component
description: Creates LeadQuickActions component for common lead actions
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 28: LeadQuickActions Component Missing

## Gap Reference
- **TODO.md Item:** #28
- **Priority:** P3 Medium (Frontend Components)
- **Location:** `frontend/components/leads/`
- **Issue:** Component planned but not created

## Pre-Flight Checks

1. Check if component exists:
   ```bash
   ls frontend/components/leads/LeadQuickActions.tsx
   ```

2. Check available lead API actions:
   ```bash
   grep -n "export.*function\|export const" frontend/lib/api/leads.ts
   ```

3. Review existing action patterns:
   ```bash
   grep -rn "onClick\|handleClick" frontend/components/leads/
   ```

## Implementation Steps

1. **Create LeadQuickActions.tsx:**
   ```typescript
   // frontend/components/leads/LeadQuickActions.tsx
   "use client";

   import { useState } from "react";
   import { Button } from "@/components/ui/button";
   import {
     DropdownMenu,
     DropdownMenuContent,
     DropdownMenuItem,
     DropdownMenuSeparator,
     DropdownMenuTrigger,
   } from "@/components/ui/dropdown-menu";
   import {
     Dialog,
     DialogContent,
     DialogDescription,
     DialogFooter,
     DialogHeader,
     DialogTitle,
   } from "@/components/ui/dialog";
   import { useToast } from "@/components/ui/use-toast";
   import {
     MoreHorizontal,
     Mail,
     Phone,
     Linkedin,
     MessageSquare,
     UserX,
     RefreshCw,
     Trash2,
     Star,
     StarOff,
   } from "lucide-react";
   import { Lead } from "@/lib/api/types";

   interface LeadQuickActionsProps {
     lead: Lead;
     onAction?: (action: string, lead: Lead) => void;
     onRefresh?: () => void;
   }

   export function LeadQuickActions({
     lead,
     onAction,
     onRefresh,
   }: LeadQuickActionsProps) {
     const [isLoading, setIsLoading] = useState(false);
     const [confirmDialog, setConfirmDialog] = useState<{
       open: boolean;
       action: string;
       title: string;
       description: string;
     }>({ open: false, action: "", title: "", description: "" });
     const { toast } = useToast();

     const handleAction = async (action: string) => {
       // Actions that need confirmation
       const confirmActions = ["suppress", "delete"];
       if (confirmActions.includes(action)) {
         setConfirmDialog({
           open: true,
           action,
           title: action === "delete" ? "Delete Lead" : "Suppress Lead",
           description:
             action === "delete"
               ? "This will permanently delete this lead. This action cannot be undone."
               : "This will suppress this lead from all outreach. You can unsuppress later.",
         });
         return;
       }

       await executeAction(action);
     };

     const executeAction = async (action: string) => {
       setIsLoading(true);
       try {
         // Call parent handler
         if (onAction) {
           await onAction(action, lead);
         }

         toast({
           title: "Action completed",
           description: `Successfully performed ${action} on lead`,
         });

         if (onRefresh) onRefresh();
       } catch (error) {
         toast({
           title: "Action failed",
           description: error instanceof Error ? error.message : "Unknown error",
           variant: "destructive",
         });
       } finally {
         setIsLoading(false);
         setConfirmDialog({ ...confirmDialog, open: false });
       }
     };

     return (
       <>
         <DropdownMenu>
           <DropdownMenuTrigger asChild>
             <Button variant="ghost" size="icon" disabled={isLoading}>
               <MoreHorizontal className="h-4 w-4" />
               <span className="sr-only">Open menu</span>
             </Button>
           </DropdownMenuTrigger>
           <DropdownMenuContent align="end">
             {/* Outreach Actions */}
             <DropdownMenuItem onClick={() => handleAction("send_email")}>
               <Mail className="mr-2 h-4 w-4" />
               Send Email
             </DropdownMenuItem>
             <DropdownMenuItem onClick={() => handleAction("send_sms")}>
               <MessageSquare className="mr-2 h-4 w-4" />
               Send SMS
             </DropdownMenuItem>
             <DropdownMenuItem onClick={() => handleAction("call")}>
               <Phone className="mr-2 h-4 w-4" />
               Initiate Call
             </DropdownMenuItem>
             <DropdownMenuItem onClick={() => handleAction("linkedin_connect")}>
               <Linkedin className="mr-2 h-4 w-4" />
               LinkedIn Connect
             </DropdownMenuItem>

             <DropdownMenuSeparator />

             {/* Status Actions */}
             <DropdownMenuItem onClick={() => handleAction("toggle_priority")}>
               {lead.is_priority ? (
                 <>
                   <StarOff className="mr-2 h-4 w-4" />
                   Remove Priority
                 </>
               ) : (
                 <>
                   <Star className="mr-2 h-4 w-4" />
                   Mark Priority
                 </>
               )}
             </DropdownMenuItem>
             <DropdownMenuItem onClick={() => handleAction("re_enrich")}>
               <RefreshCw className="mr-2 h-4 w-4" />
               Re-enrich Data
             </DropdownMenuItem>

             <DropdownMenuSeparator />

             {/* Destructive Actions */}
             <DropdownMenuItem
               onClick={() => handleAction("suppress")}
               className="text-orange-600"
             >
               <UserX className="mr-2 h-4 w-4" />
               Suppress Lead
             </DropdownMenuItem>
             <DropdownMenuItem
               onClick={() => handleAction("delete")}
               className="text-red-600"
             >
               <Trash2 className="mr-2 h-4 w-4" />
               Delete Lead
             </DropdownMenuItem>
           </DropdownMenuContent>
         </DropdownMenu>

         {/* Confirmation Dialog */}
         <Dialog
           open={confirmDialog.open}
           onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, open })}
         >
           <DialogContent>
             <DialogHeader>
               <DialogTitle>{confirmDialog.title}</DialogTitle>
               <DialogDescription>{confirmDialog.description}</DialogDescription>
             </DialogHeader>
             <DialogFooter>
               <Button
                 variant="outline"
                 onClick={() => setConfirmDialog({ ...confirmDialog, open: false })}
               >
                 Cancel
               </Button>
               <Button
                 variant="destructive"
                 onClick={() => executeAction(confirmDialog.action)}
                 disabled={isLoading}
               >
                 {isLoading ? "Processing..." : "Confirm"}
               </Button>
             </DialogFooter>
           </DialogContent>
         </Dialog>
       </>
     );
   }
   ```

2. **Export from index:**
   ```typescript
   export { LeadQuickActions } from "./LeadQuickActions";
   ```

## Acceptance Criteria

- [ ] LeadQuickActions.tsx created
- [ ] Dropdown menu with all actions
- [ ] Outreach actions: email, SMS, call, LinkedIn
- [ ] Status actions: priority, re-enrich
- [ ] Destructive actions: suppress, delete (with confirmation)
- [ ] Loading states
- [ ] Toast notifications
- [ ] Exported from index.ts

## Validation

```bash
# Check file exists
ls frontend/components/leads/LeadQuickActions.tsx

# Check TypeScript compiles
cd frontend && npx tsc --noEmit

# Check export
grep "LeadQuickActions" frontend/components/leads/index.ts
```

## Post-Fix

1. Update TODO.md — delete gap row #28
2. Report: "Fixed #28. LeadQuickActions component created with outreach and management actions."
