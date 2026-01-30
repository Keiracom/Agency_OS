import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabase';

export async function GET(request: NextRequest) {
  try {
    const supabase = createServerClient();
    const { searchParams } = new URL(request.url);
    const include = searchParams.get('include')?.split(',') || [];
    const limit = parseInt(searchParams.get('limit') || '50');

    // Get stats from function
    const { data: stats, error: statsError } = await supabase.rpc('get_elliot_stats');
    
    if (statsError) {
      console.error('Stats error:', statsError);
      // Return fallback stats if function doesn't exist yet
      return NextResponse.json({
        stats: {
          decisions_count: 0,
          learnings_count: 0,
          patterns_count: 0,
          memory_items: 0,
          rules_count: 0,
          today_activities: 0,
          today_tokens: 0,
          today_cost: 0,
          active_sessions: 0,
          last_activity: null,
        },
        recentActivity: [],
      });
    }

    const response: Record<string, any> = { stats };

    // Get recent activity by default
    const { data: recentActivity } = await supabase
      .from('elliot_activity')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit);
    
    response.recentActivity = recentActivity || [];

    // Include additional data if requested
    if (include.includes('memory')) {
      const { data: memory } = await supabase
        .from('elliot_memory')
        .select('*')
        .order('importance', { ascending: false })
        .limit(100);
      response.memory = memory || [];
    }

    if (include.includes('learnings')) {
      const { data: learnings } = await supabase
        .from('elliot_learnings')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      response.learnings = learnings || [];
    }

    if (include.includes('patterns')) {
      const { data: patterns } = await supabase
        .from('elliot_patterns')
        .select('*')
        .eq('is_active', true)
        .order('occurrences', { ascending: false })
        .limit(50);
      response.patterns = patterns || [];
    }

    if (include.includes('rules')) {
      const { data: rules } = await supabase
        .from('elliot_rules')
        .select('*')
        .eq('is_active', true)
        .order('priority', { ascending: false });
      response.rules = rules || [];
    }

    if (include.includes('decisions')) {
      const { data: decisions } = await supabase
        .from('elliot_decisions')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);
      response.decisions = decisions || [];
    }

    if (include.includes('activity')) {
      // Already included in recentActivity
    }

    return NextResponse.json(response);
  } catch (error) {
    console.error('Stats API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
