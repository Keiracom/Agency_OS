---
name: Fix 31 - Profile Settings Page
description: Creates user profile settings page
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 31: Profile Page Missing

## Gap Reference
- **TODO.md Item:** #31
- **Priority:** P3 Medium (Frontend Components)
- **Location:** `frontend/app/settings/profile/`
- **Issue:** Page missing

## Pre-Flight Checks

1. Check if page exists:
   ```bash
   ls frontend/app/settings/profile/page.tsx
   ```

2. Check settings layout:
   ```bash
   ls frontend/app/settings/
   cat frontend/app/settings/layout.tsx
   ```

3. Check user API:
   ```bash
   grep -n "user\|profile" frontend/lib/api/*.ts
   ```

## Implementation Steps

1. **Create directory if needed:**
   ```bash
   mkdir -p frontend/app/settings/profile
   ```

2. **Create profile page:**
   ```typescript
   // frontend/app/settings/profile/page.tsx
   "use client";

   import { useState, useEffect } from "react";
   import { useForm } from "react-hook-form";
   import { zodResolver } from "@hookform/resolvers/zod";
   import * as z from "zod";
   import {
     Card,
     CardContent,
     CardDescription,
     CardHeader,
     CardTitle,
   } from "@/components/ui/card";
   import {
     Form,
     FormControl,
     FormDescription,
     FormField,
     FormItem,
     FormLabel,
     FormMessage,
   } from "@/components/ui/form";
   import { Input } from "@/components/ui/input";
   import { Button } from "@/components/ui/button";
   import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
   import { Separator } from "@/components/ui/separator";
   import { useToast } from "@/components/ui/use-toast";
   import { Loader2, Upload, User } from "lucide-react";
   import { getCurrentUser, updateProfile } from "@/lib/api/auth";

   const profileSchema = z.object({
     first_name: z.string().min(1, "First name is required"),
     last_name: z.string().min(1, "Last name is required"),
     email: z.string().email("Invalid email address"),
     phone: z.string().optional(),
     title: z.string().optional(),
     linkedin_url: z.string().url().optional().or(z.literal("")),
     timezone: z.string().optional(),
   });

   type ProfileFormValues = z.infer<typeof profileSchema>;

   export default function ProfilePage() {
     const [isLoading, setIsLoading] = useState(true);
     const [isSaving, setIsSaving] = useState(false);
     const { toast } = useToast();

     const form = useForm<ProfileFormValues>({
       resolver: zodResolver(profileSchema),
       defaultValues: {
         first_name: "",
         last_name: "",
         email: "",
         phone: "",
         title: "",
         linkedin_url: "",
         timezone: "Australia/Sydney",
       },
     });

     useEffect(() => {
       async function loadProfile() {
         try {
           const user = await getCurrentUser();
           form.reset({
             first_name: user.first_name || "",
             last_name: user.last_name || "",
             email: user.email || "",
             phone: user.phone || "",
             title: user.title || "",
             linkedin_url: user.linkedin_url || "",
             timezone: user.timezone || "Australia/Sydney",
           });
         } catch (error) {
           toast({
             title: "Failed to load profile",
             description: "Please try again later",
             variant: "destructive",
           });
         } finally {
           setIsLoading(false);
         }
       }
       loadProfile();
     }, [form, toast]);

     const onSubmit = async (data: ProfileFormValues) => {
       setIsSaving(true);
       try {
         await updateProfile(data);
         toast({
           title: "Profile updated",
           description: "Your profile has been saved successfully",
         });
       } catch (error) {
         toast({
           title: "Failed to save profile",
           description: error instanceof Error ? error.message : "Unknown error",
           variant: "destructive",
         });
       } finally {
         setIsSaving(false);
       }
     };

     if (isLoading) {
       return (
         <div className="flex items-center justify-center py-12">
           <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
         </div>
       );
     }

     const initials = `${form.watch("first_name")?.[0] || ""}${form.watch("last_name")?.[0] || ""}`.toUpperCase();

     return (
       <div className="space-y-6">
         <div>
           <h3 className="text-lg font-medium">Profile</h3>
           <p className="text-sm text-muted-foreground">
             Manage your personal information and preferences
           </p>
         </div>
         <Separator />

         {/* Avatar Section */}
         <Card>
           <CardHeader>
             <CardTitle>Profile Picture</CardTitle>
             <CardDescription>
               Your profile picture is visible to team members
             </CardDescription>
           </CardHeader>
           <CardContent className="flex items-center gap-6">
             <Avatar className="h-24 w-24">
               <AvatarImage src="" />
               <AvatarFallback className="text-2xl">
                 {initials || <User className="h-12 w-12" />}
               </AvatarFallback>
             </Avatar>
             <Button variant="outline" size="sm">
               <Upload className="mr-2 h-4 w-4" />
               Upload Photo
             </Button>
           </CardContent>
         </Card>

         {/* Profile Form */}
         <Card>
           <CardHeader>
             <CardTitle>Personal Information</CardTitle>
             <CardDescription>
               Update your personal details
             </CardDescription>
           </CardHeader>
           <CardContent>
             <Form {...form}>
               <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                 <div className="grid gap-4 md:grid-cols-2">
                   <FormField
                     control={form.control}
                     name="first_name"
                     render={({ field }) => (
                       <FormItem>
                         <FormLabel>First Name</FormLabel>
                         <FormControl>
                           <Input {...field} />
                         </FormControl>
                         <FormMessage />
                       </FormItem>
                     )}
                   />
                   <FormField
                     control={form.control}
                     name="last_name"
                     render={({ field }) => (
                       <FormItem>
                         <FormLabel>Last Name</FormLabel>
                         <FormControl>
                           <Input {...field} />
                         </FormControl>
                         <FormMessage />
                       </FormItem>
                     )}
                   />
                 </div>

                 <FormField
                   control={form.control}
                   name="email"
                   render={({ field }) => (
                     <FormItem>
                       <FormLabel>Email</FormLabel>
                       <FormControl>
                         <Input {...field} type="email" disabled />
                       </FormControl>
                       <FormDescription>
                         Contact support to change your email address
                       </FormDescription>
                       <FormMessage />
                     </FormItem>
                   )}
                 />

                 <div className="grid gap-4 md:grid-cols-2">
                   <FormField
                     control={form.control}
                     name="title"
                     render={({ field }) => (
                       <FormItem>
                         <FormLabel>Job Title</FormLabel>
                         <FormControl>
                           <Input {...field} placeholder="e.g. Sales Manager" />
                         </FormControl>
                         <FormMessage />
                       </FormItem>
                     )}
                   />
                   <FormField
                     control={form.control}
                     name="phone"
                     render={({ field }) => (
                       <FormItem>
                         <FormLabel>Phone</FormLabel>
                         <FormControl>
                           <Input {...field} placeholder="+61 XXX XXX XXX" />
                         </FormControl>
                         <FormMessage />
                       </FormItem>
                     )}
                   />
                 </div>

                 <FormField
                   control={form.control}
                   name="linkedin_url"
                   render={({ field }) => (
                     <FormItem>
                       <FormLabel>LinkedIn Profile</FormLabel>
                       <FormControl>
                         <Input
                           {...field}
                           placeholder="https://linkedin.com/in/yourprofile"
                         />
                       </FormControl>
                       <FormDescription>
                         Used for email signatures and outreach
                       </FormDescription>
                       <FormMessage />
                     </FormItem>
                   )}
                 />

                 <div className="flex justify-end">
                   <Button type="submit" disabled={isSaving}>
                     {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                     Save Changes
                   </Button>
                 </div>
               </form>
             </Form>
           </CardContent>
         </Card>
       </div>
     );
   }
   ```

3. **Add to settings navigation** (if needed):
   ```typescript
   // In settings layout or navigation
   { name: "Profile", href: "/settings/profile", icon: User }
   ```

## Acceptance Criteria

- [ ] Page created at /settings/profile
- [ ] Loads current user data
- [ ] Form fields: first/last name, email, phone, title, LinkedIn
- [ ] Avatar display with initials fallback
- [ ] Form validation with zod
- [ ] Save functionality with toast feedback
- [ ] Loading states
- [ ] Email field disabled (contact support to change)

## Validation

```bash
# Check file exists
ls frontend/app/settings/profile/page.tsx

# Check TypeScript compiles
cd frontend && npx tsc --noEmit

# Check route accessible
# (manual test in browser)
```

## Post-Fix

1. Update TODO.md — delete gap row #31
2. Report: "Fixed #31. Profile settings page created with user info form."
