---
name: Fix 26 - LeadEnrichmentCard Component
description: Creates LeadEnrichmentCard component for lead details
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
---

# Fix 26: LeadEnrichmentCard Component Missing

## Gap Reference
- **TODO.md Item:** #26
- **Priority:** P3 Medium (Frontend Components)
- **Location:** `frontend/components/leads/`
- **Issue:** Component planned but not created

## Pre-Flight Checks

1. Check if component exists:
   ```bash
   ls frontend/components/leads/LeadEnrichmentCard.tsx
   ```

2. Review LEADS.md for component spec:
   ```bash
   grep -A 20 "LeadEnrichmentCard" frontend/LEADS.md
   ```

3. Check existing lead components for patterns:
   ```bash
   ls frontend/components/leads/
   ```

4. Check Lead type definition:
   ```bash
   grep -A 30 "interface Lead\|type Lead" frontend/lib/api/types.ts
   ```

## Implementation Steps

1. **Create LeadEnrichmentCard.tsx:**
   ```typescript
   // frontend/components/leads/LeadEnrichmentCard.tsx
   "use client";

   import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
   import { Badge } from "@/components/ui/badge";
   import { Lead } from "@/lib/api/types";
   import {
     Building2,
     Mail,
     Phone,
     Linkedin,
     Globe,
     Users,
     DollarSign,
     Calendar,
   } from "lucide-react";

   interface LeadEnrichmentCardProps {
     lead: Lead;
     className?: string;
   }

   export function LeadEnrichmentCard({ lead, className }: LeadEnrichmentCardProps) {
     const enrichmentData = lead.enrichment_data || {};

     return (
       <Card className={className}>
         <CardHeader>
           <CardTitle className="flex items-center gap-2">
             <Building2 className="h-5 w-5" />
             Enrichment Data
           </CardTitle>
         </CardHeader>
         <CardContent className="space-y-4">
           {/* Contact Information */}
           <div className="space-y-2">
             <h4 className="text-sm font-medium text-muted-foreground">Contact</h4>
             <div className="grid grid-cols-2 gap-2 text-sm">
               {lead.email && (
                 <div className="flex items-center gap-2">
                   <Mail className="h-4 w-4 text-muted-foreground" />
                   <span className="truncate">{lead.email}</span>
                 </div>
               )}
               {lead.phone && (
                 <div className="flex items-center gap-2">
                   <Phone className="h-4 w-4 text-muted-foreground" />
                   <span>{lead.phone}</span>
                 </div>
               )}
               {lead.linkedin_url && (
                 <div className="flex items-center gap-2">
                   <Linkedin className="h-4 w-4 text-muted-foreground" />
                   <a
                     href={lead.linkedin_url}
                     target="_blank"
                     rel="noopener noreferrer"
                     className="text-primary hover:underline truncate"
                   >
                     Profile
                   </a>
                 </div>
               )}
             </div>
           </div>

           {/* Company Information */}
           <div className="space-y-2">
             <h4 className="text-sm font-medium text-muted-foreground">Company</h4>
             <div className="grid grid-cols-2 gap-2 text-sm">
               {lead.company_name && (
                 <div className="flex items-center gap-2">
                   <Building2 className="h-4 w-4 text-muted-foreground" />
                   <span>{lead.company_name}</span>
                 </div>
               )}
               {enrichmentData.company_website && (
                 <div className="flex items-center gap-2">
                   <Globe className="h-4 w-4 text-muted-foreground" />
                   <a
                     href={enrichmentData.company_website}
                     target="_blank"
                     rel="noopener noreferrer"
                     className="text-primary hover:underline truncate"
                   >
                     Website
                   </a>
                 </div>
               )}
               {enrichmentData.company_size && (
                 <div className="flex items-center gap-2">
                   <Users className="h-4 w-4 text-muted-foreground" />
                   <span>{enrichmentData.company_size} employees</span>
                 </div>
               )}
               {enrichmentData.company_revenue && (
                 <div className="flex items-center gap-2">
                   <DollarSign className="h-4 w-4 text-muted-foreground" />
                   <span>{enrichmentData.company_revenue}</span>
                 </div>
               )}
             </div>
           </div>

           {/* Enrichment Signals */}
           {lead.sdk_signals && lead.sdk_signals.length > 0 && (
             <div className="space-y-2">
               <h4 className="text-sm font-medium text-muted-foreground">Signals</h4>
               <div className="flex flex-wrap gap-1">
                 {lead.sdk_signals.map((signal, idx) => (
                   <Badge key={idx} variant="secondary" className="text-xs">
                     {signal}
                   </Badge>
                 ))}
               </div>
             </div>
           )}

           {/* Enrichment Metadata */}
           {lead.sdk_enriched_at && (
             <div className="flex items-center gap-2 text-xs text-muted-foreground">
               <Calendar className="h-3 w-3" />
               <span>
                 Enriched {new Date(lead.sdk_enriched_at).toLocaleDateString()}
               </span>
             </div>
           )}
         </CardContent>
       </Card>
     );
   }
   ```

2. **Export from index:**
   ```typescript
   // Add to frontend/components/leads/index.ts
   export { LeadEnrichmentCard } from "./LeadEnrichmentCard";
   ```

3. **Add to lead detail page** (if exists):
   ```typescript
   import { LeadEnrichmentCard } from "@/components/leads/LeadEnrichmentCard";

   // In lead detail component
   <LeadEnrichmentCard lead={lead} />
   ```

## Acceptance Criteria

- [ ] LeadEnrichmentCard.tsx created in components/leads/
- [ ] Displays contact info (email, phone, LinkedIn)
- [ ] Displays company info (name, website, size, revenue)
- [ ] Displays SDK signals as badges
- [ ] Shows enrichment timestamp
- [ ] Exported from index.ts
- [ ] TypeScript types correct

## Validation

```bash
# Check file exists
ls frontend/components/leads/LeadEnrichmentCard.tsx

# Check TypeScript compiles
cd frontend && npx tsc --noEmit

# Check export
grep "LeadEnrichmentCard" frontend/components/leads/index.ts
```

## Post-Fix

1. Update TODO.md — delete gap row #26
2. Report: "Fixed #26. LeadEnrichmentCard component created."
