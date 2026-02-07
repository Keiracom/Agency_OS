/**
 * Prototype Preview Page - Information Dense Dashboard
 * Phase: Operation Modular Cockpit - REFACTORED
 * 
 * This page is now ~300 lines, importing modular components
 * instead of defining everything inline.
 */

"use client";

import { useState } from "react";
import {
  Search,
  Bell,
} from "lucide-react";

// ============ MODULAR IMPORTS ============
import { CampaignProvider, useCampaignContext } from "@/contexts";
import {
  Sidebar,
  StatsGrid,
  LiveActivityFeed,
  LeadTable,
  NewCampaignModal,
  ProcessingOverlay,
  MayaCompanion,
  type PageKey,
} from "@/components/dashboard";

// Page content components (to be extracted in future refactor)
import { DashboardContent } from "./pages/DashboardContent";
import { CampaignsContent } from "./pages/CampaignsContent";
import { LeadsContent } from "./pages/LeadsContent";
import { RepliesContent } from "./pages/RepliesContent";
import { ReportsContent } from "./pages/ReportsContent";
import { SettingsContent } from "./pages/SettingsContent";

// ============ HEADER COMPONENT ============
// Small enough to keep inline
function Header({ title }: { title: string }) {
  return (
    <div className="h-14 bg-white border-b border-slate-200 shadow-md shadow-black/5 flex items-center justify-between px-6">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search..."
            className="w-64 pl-9 pr-4 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button className="relative p-2 text-slate-400 hover:text-slate-600">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>
      </div>
    </div>
  );
}

// ============ PAGE TITLES ============
const titles: Record<PageKey, string> = {
  dashboard: "Dashboard",
  campaigns: "Campaigns",
  leads: "Leads",
  replies: "Replies",
  reports: "Reports",
  settings: "Settings",
};

// ============ MAIN PAGE ============
export default function PrototypePage() {
  return (
    <CampaignProvider>
      <PrototypePageContent />
    </CampaignProvider>
  );
}

function PrototypePageContent() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [showNewCampaignModal, setShowNewCampaignModal] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState(0);
  const [isPageTransitioning, setIsPageTransitioning] = useState(false);
  const [pageAnimationKey, setPageAnimationKey] = useState(0);

  const { activeCampaignId } = useCampaignContext();

  // Handle page navigation with animation
  const handleNavigate = (page: PageKey) => {
    if (page === activePage) return;
    setIsPageTransitioning(true);

    setTimeout(() => {
      setActivePage(page);
      setPageAnimationKey(prev => prev + 1);

      setTimeout(() => {
        setIsPageTransitioning(false);
      }, 50);
    }, 200);
  };

  const handleNewCampaign = (data: { name: string; description: string; permissionMode: string }) => {
    setShowNewCampaignModal(false);
    handleConfirmActivate();
  };

  const handleConfirmActivate = () => {
    setIsProcessing(true);
    setProcessingStage(0);

    const stageTimings = [1500, 2000, 2500, 2000, 1500];
    let currentStage = 0;

    const advanceStage = () => {
      currentStage++;
      if (currentStage < stageTimings.length) {
        setProcessingStage(currentStage);
        setTimeout(advanceStage, stageTimings[currentStage]);
      } else {
        setTimeout(() => {
          setIsProcessing(false);
          setProcessingStage(0);
        }, 1000);
      }
    };

    setTimeout(advanceStage, stageTimings[0]);
  };

  const renderPage = () => {
    const commonProps = {
      campaignId: activeCampaignId,
      onNewCampaign: () => setShowNewCampaignModal(true),
    };

    switch (activePage) {
      case "dashboard":
        return (
          <DashboardContent
            {...commonProps}
            onConfirmActivate={handleConfirmActivate}
          />
        );
      case "campaigns":
        return <CampaignsContent {...commonProps} />;
      case "leads":
        return <LeadsContent campaignId={activeCampaignId} />;
      case "replies":
        return <RepliesContent campaignId={activeCampaignId} />;
      case "reports":
        return <ReportsContent campaignId={activeCampaignId} />;
      case "settings":
        return <SettingsContent />;
      default:
        return (
          <DashboardContent
            {...commonProps}
            onConfirmActivate={handleConfirmActivate}
          />
        );
    }
  };

  return (
    <div className="flex min-h-screen bg-[#8a8e96]">
      <Sidebar activePage={activePage} onNavigate={handleNavigate} />
      <div className="flex-1 ml-60">
        <Header title={titles[activePage]} />

        {/* Page Content with Animations */}
        <div
          key={pageAnimationKey}
          className={`transition-all duration-300 ease-out ${
            isPageTransitioning
              ? "opacity-0 scale-95 translate-y-4"
              : "opacity-100 scale-100 translate-y-0"
          }`}
          style={{
            animation: !isPageTransitioning ? "pageEnter 0.4s ease-out forwards" : "none",
          }}
        >
          {renderPage()}
        </div>
      </div>

      {/* New Campaign Modal */}
      <NewCampaignModal
        isOpen={showNewCampaignModal}
        onClose={() => setShowNewCampaignModal(false)}
        onSubmit={handleNewCampaign}
      />

      {/* Processing Overlay */}
      <ProcessingOverlay isVisible={isProcessing} stage={processingStage} />

      {/* Maya Companion */}
      <MayaCompanion />

      {/* Page Transition Styles */}
      <style jsx global>{`
        @keyframes pageEnter {
          0% {
            opacity: 0;
            transform: scale(0.96) translateY(20px);
          }
          50% {
            opacity: 0.8;
            transform: scale(0.99) translateY(8px);
          }
          100% {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }

        @keyframes cardStagger {
          0% {
            opacity: 0;
            transform: translateY(20px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-card-enter {
          animation: cardStagger 0.4s ease-out forwards;
        }
      `}</style>
    </div>
  );
}
