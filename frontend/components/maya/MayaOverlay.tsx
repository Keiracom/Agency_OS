'use client';

/**
 * MayaOverlay - AI Assistant Overlay Component
 * Sprint 4: Maya Overlay Component
 * 
 * Bloomberg Terminal aesthetic - amber only
 * HeyGen-ready: avatarSrc prop accepts video feed URL post-launch
 * 
 * Reusable across:
 * - /onboarding — with step context
 * - /dashboard — ambient presence mode
 * - Any page — generic overlay
 */

import { cn } from '@/lib/utils';
import { useState, useEffect } from 'react';
import { Minus, Plus } from 'lucide-react';
import { MayaAvatar } from './MayaAvatar';
import { MayaTypingIndicator } from './MayaTypingIndicator';
import { MayaStatusBadge } from './MayaStatusBadge';

// Contextual messages by step (used when currentStep is provided)
const MAYA_MESSAGES: Record<string, { status: string; message: string }> = {
  'website': {
    status: 'SCANNING',
    message: 'Analysing your website for insights...'
  },
  'icp': {
    status: 'LEARNING',
    message: 'Building your Ideal Customer Profile...'
  },
  'linkedin': {
    status: 'CONNECTING',
    message: 'Preparing LinkedIn integration...'
  },
  'integrations': {
    status: 'CONNECTING',
    message: 'Setting up your integrations...'
  },
  'campaigns': {
    status: 'STRATEGISING',
    message: 'Crafting your campaign recommendations...'
  },
  'review': {
    status: 'READY',
    message: 'Your AI outreach engine is configured!'
  },
  'complete': {
    status: 'LAUNCHING',
    message: 'Preparing your dashboard...'
  },
  'default': {
    status: 'THINKING',
    message: 'Maya is processing...'
  }
};

export interface MayaOverlayProps {
  // Current step context
  currentStep?: string;
  stepProgress?: number; // 0-100
  
  // Status display (overrides step-based defaults)
  statusText?: string;
  contextMessage?: string;
  
  // State
  isMinimised?: boolean;
  onMinimise?: () => void;
  onMaximise?: () => void;
  
  // Animation
  isTyping?: boolean;
  isPulsing?: boolean;
  
  // Positioning
  position?: 'bottom-right' | 'bottom-left' | 'custom';
  className?: string;
  
  // HeyGen placeholder (future)
  avatarSrc?: string;
  avatarFallback?: 'silhouette' | 'initial' | 'icon';
  
  // Visibility
  isVisible?: boolean;
}

export function MayaOverlay({
  currentStep,
  stepProgress = 0,
  statusText,
  contextMessage,
  isMinimised: controlledMinimised,
  onMinimise,
  onMaximise,
  isTyping = false,
  isPulsing = true,
  position = 'bottom-right',
  className,
  avatarSrc,
  avatarFallback = 'initial',
  isVisible = true,
}: MayaOverlayProps) {
  // Internal minimised state (if not controlled)
  const [internalMinimised, setInternalMinimised] = useState(false);
  const isMinimised = controlledMinimised ?? internalMinimised;

  // Get contextual messages based on step
  const stepMessages = currentStep 
    ? MAYA_MESSAGES[currentStep] || MAYA_MESSAGES['default']
    : MAYA_MESSAGES['default'];

  // Use provided values or fall back to step-based defaults
  const displayStatus = statusText || stepMessages.status;
  const displayMessage = contextMessage || stepMessages.message;

  // Handle minimise toggle
  const handleToggle = () => {
    if (isMinimised) {
      onMaximise?.();
      setInternalMinimised(false);
    } else {
      onMinimise?.();
      setInternalMinimised(true);
    }
  };

  // Position classes
  const positionClasses = {
    'bottom-right': 'fixed bottom-6 right-6',
    'bottom-left': 'fixed bottom-6 left-6',
    'custom': '',
  };

  if (!isVisible) return null;

  return (
    <div 
      className={cn(
        'z-50 transition-all duration-300 ease-out',
        positionClasses[position],
        className
      )}
    >
      {/* Minimised State - Just the glowing ring */}
      {isMinimised ? (
        <button
          onClick={handleToggle}
          className="group relative cursor-pointer"
          aria-label="Expand Maya"
        >
          <MayaAvatar 
            size="sm" 
            isPulsing={isPulsing}
            avatarSrc={avatarSrc}
            avatarFallback={avatarFallback}
          />
          {/* Expand hint on hover */}
          <div 
            className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 rounded 
              text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity"
            style={{
              backgroundColor: '#141210',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#A39E96',
            }}
          >
            Click to expand
          </div>
        </button>
      ) : (
        /* Expanded State - Full overlay */
        <div 
          className="relative rounded-2xl overflow-hidden"
          style={{
            backgroundColor: 'rgba(12,10,8,0.95)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid rgba(255,255,255,0.08)',
            boxShadow: '0 8px 40px rgba(0,0,0,0.5), 0 0 60px rgba(212,149,106,0.1)',
          }}
        >
          {/* Top edge light refraction */}
          <div 
            className="absolute inset-x-0 top-0 h-px pointer-events-none"
            style={{
              background: 'linear-gradient(90deg, transparent 0%, rgba(212,149,106,0.2) 30%, rgba(212,149,106,0.2) 70%, transparent 100%)',
            }}
          />

          {/* Content */}
          <div className="px-6 py-5 flex flex-col items-center min-w-[200px]">
            {/* Avatar */}
            <MayaAvatar 
              size="lg"
              isPulsing={isPulsing}
              avatarSrc={avatarSrc}
              avatarFallback={avatarFallback}
            />

            {/* Status Badge */}
            <div className="mt-4">
              <MayaStatusBadge 
                status={displayStatus}
                progress={stepProgress}
                showProgress={stepProgress > 0}
              />
            </div>

            {/* Context Message */}
            <p 
              className="mt-2 text-sm text-center max-w-[180px]"
              style={{ color: '#A39E96' }}
            >
              "{displayMessage}"
            </p>

            {/* Typing Indicator */}
            {isTyping && (
              <div className="mt-3">
                <MayaTypingIndicator size="md" />
              </div>
            )}

            {/* Minimise Button */}
            <button
              onClick={handleToggle}
              className="mt-4 flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                text-xs font-medium transition-all duration-200
                hover:bg-white/5"
              style={{
                color: '#6B6660',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <Minus className="w-3 h-3" />
              Minimise
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
