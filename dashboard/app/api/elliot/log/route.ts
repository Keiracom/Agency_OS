import { NextRequest, NextResponse } from 'next/server';
import { createServerClient } from '@/lib/supabase';
import { verifyApiToken, unauthorizedResponse } from '@/lib/auth';

export async function POST(request: NextRequest) {
  // Verify API token
  if (!verifyApiToken(request)) {
    return unauthorizedResponse();
  }

  try {
    const supabase = createServerClient();
    const body = await request.json();
    
    const {
      action,
      action_type = 'task',
      status = 'completed',
      result,
      tokens_used = 0,
      cost_usd = 0,
      duration_ms,
      session_id,
      parent_id,
      metadata = {},
    } = body;

    if (!action) {
      return NextResponse.json(
        { error: 'Missing action' },
        { status: 400 }
      );
    }

    // Use the database function for logging
    const { data: activityId, error } = await supabase.rpc('log_elliot_activity', {
      p_action: action,
      p_action_type: action_type,
      p_status: status,
      p_result: result,
      p_tokens_used: tokens_used,
      p_cost_usd: cost_usd,
      p_duration_ms: duration_ms,
      p_session_id: session_id,
      p_metadata: metadata,
    });

    if (error) {
      // Fallback to direct insert if function doesn't exist
      const { data: activity, error: insertError } = await supabase
        .from('elliot_activity')
        .insert({
          action,
          action_type,
          status,
          result,
          tokens_used,
          cost_usd,
          duration_ms,
          session_id,
          parent_id,
          metadata,
          completed_at: ['completed', 'failed'].includes(status) ? new Date().toISOString() : null,
        })
        .select()
        .single();

      if (insertError) throw insertError;
      return NextResponse.json({ success: true, id: activity.id });
    }

    return NextResponse.json({ success: true, id: activityId });
  } catch (error) {
    console.error('Log API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}

// Support for updating existing activity (e.g., marking as complete)
export async function PATCH(request: NextRequest) {
  if (!verifyApiToken(request)) {
    return unauthorizedResponse();
  }

  try {
    const supabase = createServerClient();
    const body = await request.json();
    
    const { id, ...updates } = body;

    if (!id) {
      return NextResponse.json(
        { error: 'Missing activity id' },
        { status: 400 }
      );
    }

    // Add completed_at if status is being set to completed/failed
    if (updates.status && ['completed', 'failed'].includes(updates.status)) {
      updates.completed_at = new Date().toISOString();
    }

    const { data: activity, error } = await supabase
      .from('elliot_activity')
      .update(updates)
      .eq('id', id)
      .select()
      .single();

    if (error) throw error;

    return NextResponse.json({ success: true, activity });
  } catch (error) {
    console.error('Log PATCH error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
