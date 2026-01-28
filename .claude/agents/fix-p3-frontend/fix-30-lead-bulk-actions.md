---
name: Fix 30 - LeadBulkActions Component
description: Creates LeadBulkActions component for multi-lead operations
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 30: LeadBulkActions Component Missing

## Gap Reference
- **TODO.md Item:** #30
- **Priority:** P3 Medium (Frontend Components)
- **Location:** `frontend/components/leads/`
- **Issue:** Component planned but not created

## Pre-Flight Checks

1. Check if component exists:
   ```bash
   ls frontend/components/leads/LeadBulkActions.tsx
   ```

2. Check for bulk API endpoints:
   ```bash
   grep -rn "bulk\|batch" frontend/lib/api/leads.ts
   ```

3. Check existing selection patterns:
   ```bash
   grep -rn "selected\|checkbox\|selection" frontend/components/leads/
   ```

## Implementation Steps

1. **Create LeadBulkActions.tsx:**
   ```typescript
   // frontend/components/leads/LeadBulkActions.tsx
   "use client";

   import { useState } from "react";
   import { Button } from "@/components/ui/button";
   import {
     DropdownMenu,
     DropdownMenuContent,
     DropdownMenuItem,
     DropdownMenuSeparator,
     DropdownMenuSub,
     DropdownMenuSubContent,
     DropdownMenuSubTrigger,
     DropdownMenuTrigger,
   } from "@/components/ui/dropdown-menu";
   import {
     AlertDialog,
     AlertDialogAction,
     AlertDialogCancel,
     AlertDialogContent,
     AlertDialogDescription,
     AlertDialogFooter,
     AlertDialogHeader,
     AlertDialogTitle,
   } from "@/components/ui/alert-dialog";
   import { Progress } from "@/components/ui/progress";
   import { useToast } from "@/components/ui/use-toast";
   import {
     ChevronDown,
     Mail,
     UserX,
     Trash2,
     Tag,
     RefreshCw,
     Download,
     ArrowRight,
   } from "lucide-react";

   interface LeadBulkActionsProps {
     selectedIds: string[];
     onAction: (action: string, leadIds: string[], options?: any) => Promise<void>;
     onClearSelection: () => void;
     campaigns?: Array<{ id: string; name: string }>;
   }

   export function LeadBulkActions({
     selectedIds,
     onAction,
     onClearSelection,
     campaigns = [],
   }: LeadBulkActionsProps) {
     const [isLoading, setIsLoading] = useState(false);
     const [progress, setProgress] = useState(0);
     const [confirmDialog, setConfirmDialog] = useState<{
       open: boolean;
       action: string;
       title: string;
       description: string;
     }>({ open: false, action: "", title: "", description: "" });
     const { toast } = useToast();

     const selectedCount = selectedIds.length;

     if (selectedCount === 0) {
       return null;
     }

     const handleAction = async (action: string, options?: any) => {
       // Actions requiring confirmation
       const confirmActions = ["delete", "suppress"];
       if (confirmActions.includes(action)) {
         setConfirmDialog({
           open: true,
           action,
           title: action === "delete" ? "Delete Leads" : "Suppress Leads",
           description: `This will ${action} ${selectedCount} lead${selectedCount > 1 ? "s" : ""}. ${action === "delete" ? "This cannot be undone." : ""}`,
         });
         return;
       }

       await executeAction(action, options);
     };

     const executeAction = async (action: string, options?: any) => {
       setIsLoading(true);
       setProgress(0);

       try {
         // Simulate progress for large batches
         const progressInterval = setInterval(() => {
           setProgress((prev) => Math.min(prev + 10, 90));
         }, 200);

         await onAction(action, selectedIds, options);

         clearInterval(progressInterval);
         setProgress(100);

         toast({
           title: "Bulk action completed",
           description: `Successfully ${action} ${selectedCount} leads`,
         });

         onClearSelection();
       } catch (error) {
         toast({
           title: "Bulk action failed",
           description: error instanceof Error ? error.message : "Unknown error",
           variant: "destructive",
         });
       } finally {
         setIsLoading(false);
         setProgress(0);
         setConfirmDialog({ ...confirmDialog, open: false });
       }
     };

     return (
       <>
         <div className="flex items-center gap-2 rounded-lg border bg-muted/50 p-2">
           <span className="text-sm font-medium">
             {selectedCount} selected
           </span>

           {isLoading && (
             <Progress value={progress} className="w-24 h-2" />
           )}

           <DropdownMenu>
             <DropdownMenuTrigger asChild>
               <Button variant="outline" size="sm" disabled={isLoading}>
                 Actions
                 <ChevronDown className="ml-2 h-4 w-4" />
               </Button>
             </DropdownMenuTrigger>
             <DropdownMenuContent align="end" className="w-48">
               {/* Outreach */}
               <DropdownMenuItem onClick={() => handleAction("send_email")}>
                 <Mail className="mr-2 h-4 w-4" />
                 Send Email
               </DropdownMenuItem>

               {/* Campaign Assignment */}
               {campaigns.length > 0 && (
                 <DropdownMenuSub>
                   <DropdownMenuSubTrigger>
                     <ArrowRight className="mr-2 h-4 w-4" />
                     Assign to Campaign
                   </DropdownMenuSubTrigger>
                   <DropdownMenuSubContent>
                     {campaigns.map((campaign) => (
                       <DropdownMenuItem
                         key={campaign.id}
                         onClick={() =>
                           handleAction("assign_campaign", { campaignId: campaign.id })
                         }
                       >
                         {campaign.name}
                       </DropdownMenuItem>
                     ))}
                   </DropdownMenuSubContent>
                 </DropdownMenuSub>
               )}

               {/* Tagging */}
               <DropdownMenuItem onClick={() => handleAction("add_tag")}>
                 <Tag className="mr-2 h-4 w-4" />
                 Add Tag
               </DropdownMenuItem>

               <DropdownMenuSeparator />

               {/* Data Operations */}
               <DropdownMenuItem onClick={() => handleAction("re_enrich")}>
                 <RefreshCw className="mr-2 h-4 w-4" />
                 Re-enrich All
               </DropdownMenuItem>
               <DropdownMenuItem onClick={() => handleAction("export")}>
                 <Download className="mr-2 h-4 w-4" />
                 Export to CSV
               </DropdownMenuItem>

               <DropdownMenuSeparator />

               {/* Destructive */}
               <DropdownMenuItem
                 onClick={() => handleAction("suppress")}
                 className="text-orange-600"
               >
                 <UserX className="mr-2 h-4 w-4" />
                 Suppress All
               </DropdownMenuItem>
               <DropdownMenuItem
                 onClick={() => handleAction("delete")}
                 className="text-red-600"
               >
                 <Trash2 className="mr-2 h-4 w-4" />
                 Delete All
               </DropdownMenuItem>
             </DropdownMenuContent>
           </DropdownMenu>

           <Button
             variant="ghost"
             size="sm"
             onClick={onClearSelection}
             disabled={isLoading}
           >
             Clear
           </Button>
         </div>

         {/* Confirmation Dialog */}
         <AlertDialog
           open={confirmDialog.open}
           onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, open })}
         >
           <AlertDialogContent>
             <AlertDialogHeader>
               <AlertDialogTitle>{confirmDialog.title}</AlertDialogTitle>
               <AlertDialogDescription>
                 {confirmDialog.description}
               </AlertDialogDescription>
             </AlertDialogHeader>
             <AlertDialogFooter>
               <AlertDialogCancel>Cancel</AlertDialogCancel>
               <AlertDialogAction
                 onClick={() => executeAction(confirmDialog.action)}
                 className="bg-destructive text-destructive-foreground"
               >
                 {isLoading ? "Processing..." : "Confirm"}
               </AlertDialogAction>
             </AlertDialogFooter>
           </AlertDialogContent>
         </AlertDialog>
       </>
     );
   }
   ```

2. **Export from index:**
   ```typescript
   export { LeadBulkActions } from "./LeadBulkActions";
   ```

## Acceptance Criteria

- [ ] LeadBulkActions.tsx created
- [ ] Shows selected count
- [ ] Dropdown with bulk actions
- [ ] Supports: email, campaign assign, tag, re-enrich, export
- [ ] Supports: suppress, delete (with confirmation)
- [ ] Progress indicator for large batches
- [ ] Clear selection button
- [ ] Loading states
- [ ] Exported from index.ts

## Validation

```bash
# Check file exists
ls frontend/components/leads/LeadBulkActions.tsx

# Check TypeScript compiles
cd frontend && npx tsc --noEmit

# Check export
grep "LeadBulkActions" frontend/components/leads/index.ts
```

## Post-Fix

1. Update TODO.md — delete gap row #30
2. Report: "Fixed #30. LeadBulkActions component created with batch operations."
