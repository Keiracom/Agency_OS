/**
 * FILE: frontend/app/plasmic-host/page.tsx
 * PURPOSE: Plasmic Studio host page for live preview
 * DOCS: https://docs.plasmic.app/learn/app-hosting/
 */

import { PlasmicCanvasHost } from "@plasmicapp/loader-nextjs";
import { PLASMIC } from "@/plasmic-init";

export default function PlasmicHost() {
  return <PlasmicCanvasHost />;
}
