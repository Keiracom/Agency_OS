import type { HookHandler } from 'clawdbot/hooks';

/**
 * Session Supabase Hook (LAW IX Automation)
 * Fires on /new and /reset - auto-saves session to Supabase
 */
const handler: HookHandler = async (event) => {
  if (event.type !== 'command' || !['new', 'reset'].includes(event.action)) {
    return;
  }

  const session = (event as any).session;
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY;

  if (!SUPABASE_URL || !SUPABASE_KEY) {
    console.error('[session-supabase] Missing SUPABASE_URL or SUPABASE_SERVICE_KEY');
    return;
  }

  const content = `Session ${new Date().toISOString().split('T')[0]}: ${event.action} triggered. Tokens: ${session?.totalTokens || 'unknown'}. Auto-saved by session-supabase hook.`;

  try {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/elliot_internal.memories`, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': `Bearer ${SUPABASE_KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify({
        type: 'daily_log',
        content,
        metadata: { source: 'hook', trigger: event.action }
      })
    });

    if (!response.ok) {
      console.error('[session-supabase] Failed:', response.status);
    }
  } catch (err) {
    console.error('[session-supabase] Error:', err);
  }
};

export default handler;
