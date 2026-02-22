/**
 * FILE: frontend/lib/demo-context.tsx
 * PURPOSE: Demo mode context provider for public demo access
 * CEO Directive #028 — Public Demo Dashboard
 * 
 * Provides:
 * - Demo mode detection via ?demo=true query param
 * - Mock user session for demo mode
 * - Session storage persistence across navigation
 */

'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';

// ============================================
// TYPES
// ============================================

export interface DemoUser {
  id: string;
  email: string;
  name: string;
  company: string;
  tier: 'Ignition' | 'Velocity' | 'Domination';
  initials: string;
}

export interface DemoContextValue {
  isDemo: boolean;
  demoUser: DemoUser | null;
  enterDemoMode: () => void;
  exitDemoMode: () => void;
}

// ============================================
// CONSTANTS
// ============================================

const DEMO_STORAGE_KEY = 'agency_os_demo_mode';

const DEMO_USER: DemoUser = {
  id: 'demo-user-001',
  email: 'demo@horizondigital.com.au',
  name: 'Demo User',
  company: 'Horizon Digital',
  tier: 'Ignition',
  initials: 'DU',
};

// ============================================
// CONTEXT
// ============================================

const DemoContext = createContext<DemoContextValue>({
  isDemo: false,
  demoUser: null,
  enterDemoMode: () => {},
  exitDemoMode: () => {},
});

// ============================================
// PROVIDER
// ============================================

export function DemoProvider({ children }: { children: React.ReactNode }) {
  const [isDemo, setIsDemo] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const searchParams = useSearchParams();

  // Check for demo mode on mount and when search params change
  useEffect(() => {
    // Check URL parameter first
    const demoParam = searchParams?.get('demo');
    
    if (demoParam === 'true') {
      // Enable demo mode from URL
      setIsDemo(true);
      try {
        sessionStorage.setItem(DEMO_STORAGE_KEY, 'true');
      } catch {
        // sessionStorage might not be available
      }
    } else if (demoParam === 'false') {
      // Explicitly disable demo mode
      setIsDemo(false);
      try {
        sessionStorage.removeItem(DEMO_STORAGE_KEY);
      } catch {
        // sessionStorage might not be available
      }
    } else {
      // Check session storage for persistence across navigation
      try {
        const stored = sessionStorage.getItem(DEMO_STORAGE_KEY);
        setIsDemo(stored === 'true');
      } catch {
        // sessionStorage might not be available
        setIsDemo(false);
      }
    }
    
    setIsInitialized(true);
  }, [searchParams]);

  const enterDemoMode = useCallback(() => {
    setIsDemo(true);
    try {
      sessionStorage.setItem(DEMO_STORAGE_KEY, 'true');
    } catch {
      // sessionStorage might not be available
    }
  }, []);

  const exitDemoMode = useCallback(() => {
    setIsDemo(false);
    try {
      sessionStorage.removeItem(DEMO_STORAGE_KEY);
    } catch {
      // sessionStorage might not be available
    }
  }, []);

  const contextValue: DemoContextValue = {
    isDemo,
    demoUser: isDemo ? DEMO_USER : null,
    enterDemoMode,
    exitDemoMode,
  };

  // Don't render children until we've checked the demo state
  // This prevents flash of non-demo content
  if (!isInitialized) {
    return null;
  }

  return (
    <DemoContext.Provider value={contextValue}>
      {children}
    </DemoContext.Provider>
  );
}

// ============================================
// HOOKS
// ============================================

export function useDemo() {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
}

/**
 * Hook to check if we're in demo mode
 * Returns a simpler boolean for components that just need to know
 */
export function useDemoMode() {
  const { isDemo } = useDemo();
  return isDemo;
}

/**
 * Hook to get the demo user (if in demo mode)
 */
export function useDemoUser() {
  const { demoUser } = useDemo();
  return demoUser;
}
