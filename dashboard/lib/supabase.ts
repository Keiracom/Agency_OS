import { createClient } from '@supabase/supabase-js';

// Types for Elliot's data
export interface Decision {
  id: string;
  decision: string;
  context: string | null;
  rationale: string | null;
  outcome: string | null;
  outcome_rating: number | null;
  tags: string[];
  session_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Learning {
  id: string;
  lesson: string;
  source: string | null;
  category: string;
  confidence: number;
  applications: number;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: string;
  action: string;
  action_type: string;
  status: string;
  result: string | null;
  tokens_used: number;
  cost_usd: number;
  duration_ms: number | null;
  session_id: string | null;
  parent_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  completed_at: string | null;
}

export interface Pattern {
  id: string;
  pattern: string;
  description: string | null;
  occurrences: number;
  category: string;
  first_seen: string;
  last_seen: string;
  examples: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Memory {
  id: string;
  key: string;
  value: string;
  category: string;
  importance: number;
  access_count: number;
  last_accessed: string | null;
  expires_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Rule {
  id: string;
  rule: string;
  category: string;
  priority: number;
  source: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Session {
  id: string;
  session_id: string;
  channel: string | null;
  started_at: string;
  ended_at: string | null;
  messages_count: number;
  tokens_input: number;
  tokens_output: number;
  context_percentage: number;
  total_cost_usd: number;
  status: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  decisions_count: number;
  learnings_count: number;
  patterns_count: number;
  memory_items: number;
  rules_count: number;
  today_activities: number;
  today_tokens: number;
  today_cost: number;
  active_sessions: number;
  last_activity: string | null;
}

// Database type for Supabase client
export interface Database {
  public: {
    Tables: {
      elliot_decisions: {
        Row: Decision;
        Insert: Omit<Decision, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Decision, 'id'>>;
      };
      elliot_learnings: {
        Row: Learning;
        Insert: Omit<Learning, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Learning, 'id'>>;
      };
      elliot_activity: {
        Row: Activity;
        Insert: Omit<Activity, 'id' | 'created_at'>;
        Update: Partial<Omit<Activity, 'id'>>;
      };
      elliot_patterns: {
        Row: Pattern;
        Insert: Omit<Pattern, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Pattern, 'id'>>;
      };
      elliot_memory: {
        Row: Memory;
        Insert: Omit<Memory, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Memory, 'id'>>;
      };
      elliot_rules: {
        Row: Rule;
        Insert: Omit<Rule, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Rule, 'id'>>;
      };
      elliot_sessions: {
        Row: Session;
        Insert: Omit<Session, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Session, 'id'>>;
      };
    };
    Functions: {
      get_elliot_stats: {
        Args: Record<string, never>;
        Returns: DashboardStats;
      };
      log_elliot_activity: {
        Args: {
          p_action: string;
          p_action_type?: string;
          p_status?: string;
          p_result?: string;
          p_tokens_used?: number;
          p_cost_usd?: number;
          p_duration_ms?: number;
          p_session_id?: string;
          p_metadata?: Record<string, unknown>;
        };
        Returns: string;
      };
    };
  };
}

// Create Supabase client for server-side use
export const createServerClient = () => {
  const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables');
  }

  return createClient<Database>(supabaseUrl, supabaseKey);
};

// Create Supabase client for client-side use
export const createBrowserClient = () => {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables');
  }

  return createClient<Database>(supabaseUrl, supabaseKey);
};

// Singleton for browser client
let browserClient: ReturnType<typeof createBrowserClient> | null = null;

export const getSupabaseBrowserClient = () => {
  if (!browserClient) {
    browserClient = createBrowserClient();
  }
  return browserClient;
};
