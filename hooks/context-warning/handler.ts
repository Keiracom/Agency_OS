import type { HookHandler } from 'clawdbot/hooks';

/**
 * Context Warning Hook
 * Fires on message:received - monitors context usage and injects warnings
 */
const handler: HookHandler = async (event) => {
  if (event.type !== 'message' || event.action !== 'received') {
    return;
  }

  const session = (event as any).session;
  if (!session?.totalTokens || !session?.contextTokens) return;

  const usage = session.totalTokens / session.contextTokens;
  const messages = (event as any).messages;

  if (!Array.isArray(messages)) return;

  let warning = '';
  if (usage >= 0.6) {
    warning = '🔴 CONTEXT 60%+: Write session summary to Supabase NOW. Recommend restart.';
  } else if (usage >= 0.5) {
    warning = '🟠 CONTEXT 50%+: Alert Dave, prepare session summary.';
  } else if (usage >= 0.4) {
    warning = '🟡 CONTEXT 40%+: Prioritize remaining work.';
  }

  if (warning) {
    messages.push({
      role: 'system',
      content: `[CONTEXT WARNING] ${warning} (${Math.round(usage * 100)}% used: ${session.totalTokens}/${session.contextTokens})`
    });
  }
};

export default handler;
