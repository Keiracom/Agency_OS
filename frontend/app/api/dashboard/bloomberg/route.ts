/**
 * FILE: app/api/dashboard/bloomberg/route.ts
 * PURPOSE: Bloomberg Terminal dashboard data - all 6 panels with live Supabase data
 * DIRECTIVE: #052 Part I - Dashboard Data Integration
 * 
 * PANELS:
 * 1. Campaign Health - ALS distribution, hot+warm ratio, batch quota, quality gate
 * 2. Personalisation Intelligence - Enrichment depth, post availability, hooks
 * 3. Outreach Performance - Sequence status, reply intents, meetings, cost per meeting
 * 4. Alert Centre - Active alerts, human review queue, complaint queue
 * 5. Deliverability - Domain warmup status, send limits, health scores
 * 6. Discovery Loop - Discarded leads breakdown, replacement loops, quota shortfall
 */

import { NextResponse } from "next/server";
import { createClient, SupabaseClient } from "@supabase/supabase-js";

// Lazy initialization - called inside handlers to avoid build-time execution
function getSupabaseClient(): SupabaseClient {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );
}

// ========================================
// TYPE DEFINITIONS
// ========================================

interface BloombergDashboardData {
  campaignHealth: CampaignHealthData | null;
  personalisation: PersonalisationData | null;
  outreach: OutreachData | null;
  alerts: AlertsData | null;
  deliverability: DeliverabilityData | null;
  discovery: DiscoveryData | null;
}

interface CampaignHealthData {
  alsDistribution: {
    hot: number;
    warm: number;
    cool: number;
    cold: number;
  };
  hotWarmRatio: number;
  leadsEnriched: number;
  targetLeads: number;
  quotaProgress: number;
  qualityGate: {
    passed: boolean;
    reason?: string;
  };
}

interface PersonalisationData {
  leads: Array<{
    name: string;
    enrichmentDepth: number; // 0-3 representing T1, T2, T-DM
    hasLinkedInPosts: boolean;
    hasXPosts: boolean;
    personalisationHook: string | null;
  }>;
}

interface OutreachData {
  activeSequences: Array<{
    leadName: string;
    step: number;
    channel: string;
  }>;
  replyIntents: Record<string, number>;
  meetingsThisMonth: number;
  meetingsTarget: number;
  costPerMeeting: number;
  responseRate: number;
}

interface AlertsData {
  activeAlerts: Array<{
    type: string;
    title: string;
    message: string;
    severity: string;
    createdAt: string;
  }>;
  reviewQueue: Array<{
    leadName: string;
    reviewType: string;
    priority: string;
  }>;
  complaintQueue: Array<{
    leadName: string;
    content: string;
  }>;
}

interface DeliverabilityData {
  domains: Array<{
    domain: string;
    warmupStage: string;
    dailySendLimit: number;
    currentSendCount: number;
    healthScore: number;
  }>;
}

interface DiscoveryData {
  discardedByGate: {
    gate1: number;
    gate2: number;
    gate3: number;
  };
  replacementLoops: number;
  quotaShortfall: {
    needed: number;
  } | null;
  topDiscardReasons: Array<{
    reason: string;
    count: number;
  }>;
}

// ========================================
// DATA FETCHING FUNCTIONS
// ========================================

async function fetchCampaignHealth(supabase: SupabaseClient, clientId: string): Promise<CampaignHealthData | null> {
  try {
    // Get ALS distribution
    const { data: alsData, error: alsError } = await supabase
      .from('lead_pool')
      .select('als_tier')
      .eq('client_id', clientId)
      .is('deleted_at', null);
    
    if (alsError) throw alsError;
    
    // Calculate distribution
    const total = alsData?.length || 0;
    const distribution = {
      hot: 0,
      warm: 0,
      cool: 0,
      cold: 0
    };
    
    if (total > 0 && alsData) {
      alsData.forEach(lead => {
        const tier = lead.als_tier as keyof typeof distribution;
        if (tier && tier in distribution) {
          distribution[tier]++;
        }
      });
      
      // Convert to percentages
      Object.keys(distribution).forEach(key => {
        const k = key as keyof typeof distribution;
        distribution[k] = Math.round((distribution[k] / total) * 100);
      });
    }
    
    const hotWarmRatio = distribution.hot + distribution.warm;
    
    // Get quota status
    const { data: quotaData } = await supabase
      .from('campaign_quota_status')
      .select('current_qualified_count, target_lead_count')
      .eq('client_id', clientId)
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
    
    const leadsEnriched = quotaData?.current_qualified_count || 0;
    const targetLeads = quotaData?.target_lead_count || 100;
    const quotaProgress = Math.round((leadsEnriched / targetLeads) * 100);
    
    // Check quality gate (simplified - passed if hot+warm ratio >= 20%)
    const qualityGate = {
      passed: hotWarmRatio >= 20,
      reason: hotWarmRatio < 20 ? `Hot+Warm ratio ${hotWarmRatio}% below 20% threshold` : undefined
    };
    
    return {
      alsDistribution: distribution,
      hotWarmRatio,
      leadsEnriched,
      targetLeads,
      quotaProgress,
      qualityGate
    };
  } catch (error) {
    console.error('fetchCampaignHealth error:', error);
    return null;
  }
}

async function fetchPersonalisation(supabase: SupabaseClient, clientId: string): Promise<PersonalisationData | null> {
  try {
    // Get leads with enrichment data
    const { data: leads, error } = await supabase
      .from('lead_pool')
      .select(`
        id,
        first_name,
        last_name,
        enrichment_lineage,
        intent_signals
      `)
      .eq('client_id', clientId)
      .is('deleted_at', null)
      .order('propensity_score', { ascending: false })
      .limit(5);
    
    if (error) throw error;
    
    const formattedLeads = (leads || []).map(lead => {
      // Calculate enrichment depth from lineage
      const lineage = lead.enrichment_lineage || [];
      const enrichmentDepth = Array.isArray(lineage) ? Math.min(lineage.length, 3) : 0;
      
      // Check for post availability in intent signals
      const signals = lead.intent_signals || {};
      const hasLinkedInPosts = !!(signals.linkedin_posts || signals.li_posts_count);
      const hasXPosts = !!(signals.x_posts || signals.twitter_posts_count);
      
      // Generate personalisation hook preview
      let personalisationHook = null;
      if (signals.recent_post_topic) {
        personalisationHook = `Noticed your post about ${signals.recent_post_topic}...`;
      } else if (signals.company_news) {
        personalisationHook = `Congrats on ${signals.company_news}...`;
      } else if (hasLinkedInPosts) {
        personalisationHook = `Your insights on LinkedIn caught our attention...`;
      }
      
      return {
        name: [lead.first_name, lead.last_name].filter(Boolean).join(' ') || 'Unknown',
        enrichmentDepth,
        hasLinkedInPosts,
        hasXPosts,
        personalisationHook
      };
    });
    
    return { leads: formattedLeads };
  } catch (error) {
    console.error('fetchPersonalisation error:', error);
    return null;
  }
}

async function fetchOutreach(supabase: SupabaseClient, clientId: string): Promise<OutreachData | null> {
  try {
    // Get active sequences (leads currently in sequence)
    const { data: activeLeads } = await supabase
      .from('leads')
      .select('first_name, last_name, current_sequence_step, status')
      .eq('client_id', clientId)
      .eq('status', 'in_sequence')
      .limit(5);
    
    const activeSequences = (activeLeads || []).map(lead => {
      // Alternate channels for demo visualization
      const channels = ['email', 'linkedin', 'sms'];
      return {
        leadName: [lead.first_name, lead.last_name].filter(Boolean).join(' ') || 'Unknown',
        step: lead.current_sequence_step || 1,
        channel: channels[(lead.current_sequence_step || 0) % channels.length]
      };
    });
    
    // Get reply intent breakdown
    const { data: replies } = await supabase
      .from('lead_replies')
      .select('intent')
      .eq('client_id', clientId)
      .eq('direction', 'inbound')
      .gte('created_at', new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString());
    
    const replyIntents: Record<string, number> = {};
    (replies || []).forEach(reply => {
      const intent = reply.intent || 'unknown';
      replyIntents[intent] = (replyIntents[intent] || 0) + 1;
    });
    
    // Get meetings this month
    const startOfMonth = new Date();
    startOfMonth.setDate(1);
    startOfMonth.setHours(0, 0, 0, 0);
    
    const { count: meetingsThisMonth } = await supabase
      .from('meetings')
      .select('*', { count: 'exact', head: true })
      .eq('client_id', clientId)
      .gte('booked_at', startOfMonth.toISOString());
    
    // Get total COGS for cost per meeting calculation
    const { data: costData } = await supabase
      .from('lead_lineage_log')
      .select('cost_aud')
      .gte('created_at', startOfMonth.toISOString());
    
    const totalCost = (costData || []).reduce((sum, row) => sum + (row.cost_aud || 0), 0);
    const costPerMeeting = (meetingsThisMonth || 0) > 0 ? totalCost / (meetingsThisMonth || 1) : 0;
    
    // Calculate response rate
    const { count: totalSent } = await supabase
      .from('activities')
      .select('*', { count: 'exact', head: true })
      .eq('client_id', clientId)
      .in('activity_type', ['email_sent', 'linkedin_message_sent'])
      .gte('created_at', startOfMonth.toISOString());
    
    const totalReplies = Object.values(replyIntents).reduce((a, b) => a + b, 0);
    const responseRate = (totalSent || 0) > 0 ? Math.round((totalReplies / (totalSent || 1)) * 100) : 0;
    
    return {
      activeSequences,
      replyIntents,
      meetingsThisMonth: meetingsThisMonth || 0,
      meetingsTarget: 20, // TODO: Make configurable per client
      costPerMeeting: Math.round(costPerMeeting * 100) / 100,
      responseRate
    };
  } catch (error) {
    console.error('fetchOutreach error:', error);
    return null;
  }
}

async function fetchAlerts(supabase: SupabaseClient, clientId: string): Promise<AlertsData | null> {
  try {
    // Get active alerts from Part F
    const { data: alerts } = await supabase
      .from('admin_notifications')
      .select('notification_type, title, message, severity, created_at')
      .eq('client_id', clientId)
      .eq('status', 'pending')
      .order('created_at', { ascending: false })
      .limit(5);
    
    const activeAlerts = (alerts || []).map(alert => ({
      type: alert.notification_type,
      title: alert.title,
      message: alert.message,
      severity: alert.severity,
      createdAt: alert.created_at
    }));
    
    // Get human review queue
    const { data: reviewItems } = await supabase
      .from('human_review_queue')
      .select(`
        id,
        review_type,
        priority,
        lead_id,
        leads:lead_id (first_name, last_name)
      `)
      .eq('client_id', clientId)
      .eq('status', 'pending')
      .order('priority', { ascending: false })
      .limit(5);
    
    const reviewQueue = (reviewItems || []).map(item => ({
      leadName: item.leads?.[0] ? 
        [item.leads[0].first_name, item.leads[0].last_name].filter(Boolean).join(' ') : 
        'Unknown',
      reviewType: item.review_type,
      priority: item.priority
    }));
    
    // Get complaint/angry reply queue
    const { data: complaints } = await supabase
      .from('lead_replies')
      .select(`
        id,
        content,
        lead_id,
        leads:lead_id (first_name, last_name)
      `)
      .eq('client_id', clientId)
      .eq('intent', 'angry_or_complaint')
      .eq('admin_review_required', true)
      .is('admin_reviewed_at', null)
      .limit(5);
    
    const complaintQueue = (complaints || []).map(complaint => ({
      leadName: complaint.leads?.[0] ?
        [complaint.leads[0].first_name, complaint.leads[0].last_name].filter(Boolean).join(' ') :
        'Unknown',
      content: complaint.content?.substring(0, 100) || ''
    }));
    
    return {
      activeAlerts,
      reviewQueue,
      complaintQueue
    };
  } catch (error) {
    console.error('fetchAlerts error:', error);
    return null;
  }
}

async function fetchDeliverability(supabase: SupabaseClient, clientId: string): Promise<DeliverabilityData | null> {
  try {
    // Get domain warmup status from Part G
    const { data: domains, error } = await supabase
      .from('domain_warmup_status')
      .select('domain, warmup_stage, daily_send_limit, current_send_count, health_score')
      .eq('client_id', clientId)
      .order('health_score', { ascending: true });
    
    if (error) throw error;
    
    const formattedDomains = (domains || []).map(domain => ({
      domain: domain.domain,
      warmupStage: domain.warmup_stage || 'unknown',
      dailySendLimit: domain.daily_send_limit || 0,
      currentSendCount: domain.current_send_count || 0,
      healthScore: Math.round(domain.health_score || 0)
    }));
    
    return { domains: formattedDomains };
  } catch (error) {
    console.error('fetchDeliverability error:', error);
    return null;
  }
}

async function fetchDiscovery(supabase: SupabaseClient, clientId: string): Promise<DiscoveryData | null> {
  try {
    // Get discarded leads by gate
    const { data: discards } = await supabase
      .from('discarded_leads')
      .select('discard_gate, discard_reason')
      .eq('client_id', clientId)
      .gte('discarded_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString());
    
    const discardedByGate = {
      gate1: 0,
      gate2: 0,
      gate3: 0
    };
    
    const reasonCounts: Record<string, number> = {};
    
    (discards || []).forEach(discard => {
      const gate = `gate${discard.discard_gate}` as keyof typeof discardedByGate;
      if (gate in discardedByGate) {
        discardedByGate[gate]++;
      }
      
      const reason = discard.discard_reason || 'unknown';
      reasonCounts[reason] = (reasonCounts[reason] || 0) + 1;
    });
    
    // Get replacement loops from quota status
    const { data: quotaData } = await supabase
      .from('campaign_quota_status')
      .select('discovery_loops_run, replacement_needed')
      .eq('client_id', clientId)
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
    
    const replacementLoops = quotaData?.discovery_loops_run || 0;
    const replacementNeeded = quotaData?.replacement_needed ?? 0;
    const quotaShortfall = replacementNeeded > 0 ? 
      { needed: replacementNeeded } : null;
    
    // Top discard reasons
    const topDiscardReasons = Object.entries(reasonCounts)
      .map(([reason, count]) => ({ reason, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
    
    return {
      discardedByGate,
      replacementLoops,
      quotaShortfall,
      topDiscardReasons
    };
  } catch (error) {
    console.error('fetchDiscovery error:', error);
    return null;
  }
}

// ========================================
// API HANDLER
// ========================================

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const clientId = searchParams.get('clientId');
    
    if (!clientId) {
      return NextResponse.json({
        success: false,
        error: 'clientId is required'
      }, { status: 400 });
    }
    
    // Initialize Supabase client at request time (not build time)
    const supabase = getSupabaseClient();
    
    // Fetch all panel data in parallel
    const [
      campaignHealth,
      personalisation,
      outreach,
      alerts,
      deliverability,
      discovery
    ] = await Promise.all([
      fetchCampaignHealth(supabase, clientId),
      fetchPersonalisation(supabase, clientId),
      fetchOutreach(supabase, clientId),
      fetchAlerts(supabase, clientId),
      fetchDeliverability(supabase, clientId),
      fetchDiscovery(supabase, clientId)
    ]);
    
    const dashboardData: BloombergDashboardData = {
      campaignHealth,
      personalisation,
      outreach,
      alerts,
      deliverability,
      discovery
    };
    
    // Return flattened structure for easier client-side access
    return NextResponse.json({
      success: true,
      ...dashboardData,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Bloomberg dashboard error:', error);
    return NextResponse.json({
      success: false,
      error: 'Failed to fetch dashboard data'
    }, { status: 500 });
  }
}
