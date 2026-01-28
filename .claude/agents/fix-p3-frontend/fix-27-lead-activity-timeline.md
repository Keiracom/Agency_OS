---
name: Fix 27 - LeadActivityTimeline Component
description: Creates LeadActivityTimeline component for lead history
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 27: LeadActivityTimeline Component Missing

## Gap Reference
- **TODO.md Item:** #27
- **Priority:** P3 Medium (Frontend Components)
- **Location:** `frontend/components/leads/`
- **Issue:** Component planned but not created

## Pre-Flight Checks

1. Check if component exists:
   ```bash
   ls frontend/components/leads/LeadActivityTimeline.tsx
   ```

2. Review LEADS.md for spec:
   ```bash
   grep -A 20 "LeadActivityTimeline" frontend/LEADS.md
   ```

3. Check for activity types in backend:
   ```bash
   grep -rn "activity_type\|ActivityType" src/models/
   ```

## Implementation Steps

1. **Create LeadActivityTimeline.tsx:**
   ```typescript
   // frontend/components/leads/LeadActivityTimeline.tsx
   "use client";

   import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
   import { Badge } from "@/components/ui/badge";
   import { ScrollArea } from "@/components/ui/scroll-area";
   import {
     Mail,
     Phone,
     Linkedin,
     MessageSquare,
     CheckCircle,
     XCircle,
     Clock,
     Eye,
     Send,
     Reply,
   } from "lucide-react";
   import { formatDistanceToNow } from "date-fns";

   interface Activity {
     id: string;
     type: string;
     channel: string;
     status: string;
     description: string;
     created_at: string;
     metadata?: Record<string, unknown>;
   }

   interface LeadActivityTimelineProps {
     activities: Activity[];
     className?: string;
     maxHeight?: string;
   }

   const activityIcons: Record<string, React.ReactNode> = {
     email_sent: <Send className="h-4 w-4" />,
     email_opened: <Eye className="h-4 w-4" />,
     email_clicked: <CheckCircle className="h-4 w-4" />,
     email_replied: <Reply className="h-4 w-4" />,
     email_bounced: <XCircle className="h-4 w-4" />,
     sms_sent: <MessageSquare className="h-4 w-4" />,
     sms_delivered: <CheckCircle className="h-4 w-4" />,
     sms_replied: <Reply className="h-4 w-4" />,
     call_initiated: <Phone className="h-4 w-4" />,
     call_completed: <CheckCircle className="h-4 w-4" />,
     call_no_answer: <XCircle className="h-4 w-4" />,
     linkedin_viewed: <Eye className="h-4 w-4" />,
     linkedin_connected: <Linkedin className="h-4 w-4" />,
     linkedin_messaged: <Send className="h-4 w-4" />,
     status_change: <Clock className="h-4 w-4" />,
   };

   const channelColors: Record<string, string> = {
     email: "bg-blue-100 text-blue-800",
     sms: "bg-green-100 text-green-800",
     voice: "bg-purple-100 text-purple-800",
     linkedin: "bg-sky-100 text-sky-800",
     system: "bg-gray-100 text-gray-800",
   };

   export function LeadActivityTimeline({
     activities,
     className,
     maxHeight = "400px",
   }: LeadActivityTimelineProps) {
     if (!activities || activities.length === 0) {
       return (
         <Card className={className}>
           <CardHeader>
             <CardTitle className="text-base">Activity Timeline</CardTitle>
           </CardHeader>
           <CardContent>
             <p className="text-sm text-muted-foreground">No activity yet</p>
           </CardContent>
         </Card>
       );
     }

     return (
       <Card className={className}>
         <CardHeader>
           <CardTitle className="text-base">Activity Timeline</CardTitle>
         </CardHeader>
         <CardContent>
           <ScrollArea style={{ maxHeight }}>
             <div className="relative space-y-4 pl-6">
               {/* Timeline line */}
               <div className="absolute left-2 top-2 bottom-2 w-px bg-border" />

               {activities.map((activity, index) => (
                 <div key={activity.id} className="relative flex gap-3">
                   {/* Timeline dot */}
                   <div className="absolute -left-6 mt-1.5 h-3 w-3 rounded-full border-2 border-background bg-primary" />

                   {/* Activity content */}
                   <div className="flex-1 space-y-1">
                     <div className="flex items-center gap-2">
                       <span className="text-muted-foreground">
                         {activityIcons[activity.type] || <Clock className="h-4 w-4" />}
                       </span>
                       <span className="font-medium text-sm">
                         {activity.description}
                       </span>
                     </div>
                     <div className="flex items-center gap-2">
                       <Badge
                         variant="secondary"
                         className={`text-xs ${channelColors[activity.channel] || ""}`}
                       >
                         {activity.channel}
                       </Badge>
                       <span className="text-xs text-muted-foreground">
                         {formatDistanceToNow(new Date(activity.created_at), {
                           addSuffix: true,
                         })}
                       </span>
                     </div>
                   </div>
                 </div>
               ))}
             </div>
           </ScrollArea>
         </CardContent>
       </Card>
     );
   }
   ```

2. **Export from index:**
   ```typescript
   export { LeadActivityTimeline } from "./LeadActivityTimeline";
   ```

3. **Install date-fns if needed:**
   ```bash
   cd frontend && npm install date-fns
   ```

## Acceptance Criteria

- [ ] LeadActivityTimeline.tsx created
- [ ] Shows activities in chronological order
- [ ] Displays appropriate icons per activity type
- [ ] Shows channel badges with colors
- [ ] Shows relative timestamps
- [ ] Handles empty state
- [ ] Scrollable for long lists
- [ ] Exported from index.ts

## Validation

```bash
# Check file exists
ls frontend/components/leads/LeadActivityTimeline.tsx

# Check TypeScript compiles
cd frontend && npx tsc --noEmit

# Check date-fns installed
grep "date-fns" frontend/package.json
```

## Post-Fix

1. Update TODO.md — delete gap row #27
2. Report: "Fixed #27. LeadActivityTimeline component created."
