/**
 * FILE: frontend/app/api/exit-preview/route.ts
 * PURPOSE: Exit Plasmic preview mode
 */

import { draftMode } from "next/headers";
import { redirect } from "next/navigation";

export async function GET() {
  const draft = await draftMode();
  draft.disable();
  redirect("/dashboard");
}
