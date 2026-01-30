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
    
    const { type, data } = body;
    
    if (!type || !data) {
      return NextResponse.json(
        { error: 'Missing type or data' },
        { status: 400 }
      );
    }

    let result;

    switch (type) {
      case 'memory':
        // Upsert memory items
        if (Array.isArray(data)) {
          const { data: inserted, error } = await supabase
            .from('elliot_memory')
            .upsert(
              data.map(item => ({
                key: item.key,
                value: item.value,
                category: item.category || 'general',
                importance: item.importance || 5,
                metadata: item.metadata || {},
              })),
              { onConflict: 'key' }
            )
            .select();
          if (error) throw error;
          result = { inserted: inserted?.length || 0 };
        } else {
          const { error } = await supabase
            .from('elliot_memory')
            .upsert({
              key: data.key,
              value: data.value,
              category: data.category || 'general',
              importance: data.importance || 5,
              metadata: data.metadata || {},
            }, { onConflict: 'key' });
          if (error) throw error;
          result = { success: true };
        }
        break;

      case 'decision':
        const { data: decision, error: decisionError } = await supabase
          .from('elliot_decisions')
          .insert({
            decision: data.decision,
            context: data.context,
            rationale: data.rationale,
            outcome: data.outcome,
            outcome_rating: data.outcome_rating,
            tags: data.tags || [],
            session_id: data.session_id,
          })
          .select()
          .single();
        if (decisionError) throw decisionError;
        result = { id: decision.id };
        break;

      case 'learning':
        const { data: learning, error: learningError } = await supabase
          .from('elliot_learnings')
          .insert({
            lesson: data.lesson,
            source: data.source,
            category: data.category || 'general',
            confidence: data.confidence || 0.8,
            tags: data.tags || [],
          })
          .select()
          .single();
        if (learningError) throw learningError;
        result = { id: learning.id };
        break;

      case 'pattern':
        // Upsert pattern (increment occurrences if exists)
        const { data: existingPattern } = await supabase
          .from('elliot_patterns')
          .select()
          .eq('pattern', data.pattern)
          .single();

        if (existingPattern) {
          const { error: updateError } = await supabase
            .from('elliot_patterns')
            .update({
              occurrences: existingPattern.occurrences + 1,
              last_seen: new Date().toISOString(),
              examples: [...(existingPattern.examples || []).slice(-9), data.example].filter(Boolean),
            })
            .eq('id', existingPattern.id);
          if (updateError) throw updateError;
          result = { id: existingPattern.id, occurrences: existingPattern.occurrences + 1 };
        } else {
          const { data: pattern, error: patternError } = await supabase
            .from('elliot_patterns')
            .insert({
              pattern: data.pattern,
              description: data.description,
              category: data.category || 'behavioral',
              examples: data.example ? [data.example] : [],
            })
            .select()
            .single();
          if (patternError) throw patternError;
          result = { id: pattern.id, occurrences: 1 };
        }
        break;

      case 'rule':
        const { data: rule, error: ruleError } = await supabase
          .from('elliot_rules')
          .insert({
            rule: data.rule,
            category: data.category || 'operational',
            priority: data.priority || 5,
            source: data.source,
          })
          .select()
          .single();
        if (ruleError) throw ruleError;
        result = { id: rule.id };
        break;

      case 'session':
        const { data: session, error: sessionError } = await supabase
          .from('elliot_sessions')
          .upsert({
            session_id: data.session_id,
            channel: data.channel,
            messages_count: data.messages_count || 0,
            tokens_input: data.tokens_input || 0,
            tokens_output: data.tokens_output || 0,
            context_percentage: data.context_percentage || 0,
            total_cost_usd: data.total_cost_usd || 0,
            status: data.status || 'active',
            metadata: data.metadata || {},
          }, { onConflict: 'session_id' })
          .select()
          .single();
        if (sessionError) throw sessionError;
        result = { id: session.id };
        break;

      case 'bulk':
        // Handle bulk sync of multiple types
        const results: Record<string, any> = {};
        
        if (data.memory?.length) {
          const { data: mem, error } = await supabase
            .from('elliot_memory')
            .upsert(data.memory, { onConflict: 'key' })
            .select();
          if (!error) results.memory = mem?.length || 0;
        }
        
        if (data.decisions?.length) {
          const { data: dec, error } = await supabase
            .from('elliot_decisions')
            .insert(data.decisions)
            .select();
          if (!error) results.decisions = dec?.length || 0;
        }
        
        if (data.learnings?.length) {
          const { data: learn, error } = await supabase
            .from('elliot_learnings')
            .insert(data.learnings)
            .select();
          if (!error) results.learnings = learn?.length || 0;
        }
        
        result = results;
        break;

      default:
        return NextResponse.json(
          { error: `Unknown type: ${type}` },
          { status: 400 }
        );
    }

    return NextResponse.json({ success: true, result });
  } catch (error) {
    console.error('Sync API error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
