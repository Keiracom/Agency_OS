import type { HookHandler } from 'clawdbot/hooks';
import { execSync } from 'child_process';

/**
 * Mid-Session Smart Context Hook
 * 
 * 1. Extracts keywords from message (free)
 * 2. Searches Supabase knowledge (free)
 * 3. If not found → Brave web search (free)
 * 4. Stores new knowledge in Supabase (grows over time)
 * 5. Injects relevant context (~100-200 tokens)
 * 
 * Zero Claude API cost. Works with learning cron.
 */
const handler: HookHandler = async (event) => {
  if (event.type !== 'message' || event.action !== 'received') {
    return;
  }

  const workspaceDir = event.context?.workspaceDir || '/home/elliotbot/clawd';
  const venvPython = `${workspaceDir}/infrastructure/.venv/bin/python3`;
  const scriptPath = `${workspaceDir}/infrastructure/smart_context.py`;
  
  // Get message text
  const messageText = event.context?.message?.text || '';
  
  // Skip very short messages
  if (messageText.length < 10) {
    injectStaticCheckpoint(event);
    return;
  }

  console.log('[mid-session-check] Processing message for context...');

  try {
    // Call smart_context.py with message as input
    // Script handles: keyword extraction, Supabase search, Brave fallback, storage
    const escaped = messageText.replace(/'/g, "'\\''").substring(0, 500);
    const result = execSync(
      `${venvPython} ${scriptPath} '${escaped}'`,
      { 
        timeout: 10000,  // 10 second max
        encoding: 'utf-8',
        env: { ...process.env }
      }
    ).trim();

    if (result && result.length > 20) {
      // Inject static rules + dynamic context
      event.messages?.push(getStaticRules());
      event.messages?.push(result);
      console.log(`[mid-session-check] Injected ${result.length} chars of context`);
    } else {
      injectStaticCheckpoint(event);
    }
  } catch (err) {
    console.log('[mid-session-check] Context fetch failed, using static only');
    injectStaticCheckpoint(event);
  }
};

function getStaticRules(): string {
  return `## 🔄 RULES (Auto-injected every message)
- Present DECISIONS, not options
- Spawn agents for complex tasks (>5 tool calls)
- Check tools/_index.md before suggesting new tools
- Don't ask "A or B?" — pick one, present for sign-off`;
}

function injectStaticCheckpoint(event: any): void {
  event.messages?.push(getStaticRules());
}

export default handler;
