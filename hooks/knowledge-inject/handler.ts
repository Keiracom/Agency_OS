import type { HookHandler } from 'clawdbot/hooks';
import { execSync } from 'child_process';

/**
 * Smart Knowledge Injection Hook
 * 
 * Queries Supabase for relevant knowledge based on session context.
 * Only injects what's relevant - keeps token cost flat at ~100-200 tokens
 * regardless of total knowledge base size.
 */
const handler: HookHandler = async (event) => {
  if (event.type !== 'agent' || event.action !== 'bootstrap') {
    return;
  }

  console.log('[knowledge-inject] Starting smart knowledge injection...');

  // Always inject the tiny checkpoint (~30 tokens)
  const checkpoint = `## 🔄 SESSION CHECKPOINT
Autonomous operator. Decisions > options. Check tools. Spawn agents for complex work.`;

  if (event.context?.bootstrapFiles) {
    event.context.bootstrapFiles.push({
      path: 'CHECKPOINT.md',
      content: checkpoint,
      label: 'CHECKPOINT'
    });
  }

  // Try to get relevant knowledge from Supabase
  try {
    const workspaceDir = event.context?.workspaceDir || process.env.HOME + '/clawd';
    const queryScript = `${workspaceDir}/infrastructure/smart_inject.py`;
    
    // Get context hint from session if available
    let contextHint = 'general assistance';
    
    // Query Supabase for relevant tools/knowledge (use venv python)
    const result = execSync(
      `${workspaceDir}/infrastructure/.venv/bin/python3 ${workspaceDir}/infrastructure/smart_inject.py "${contextHint}"`,
      { 
        timeout: 3000, // 3 second max - don't block startup
        encoding: 'utf-8',
        env: { ...process.env }
      }
    ).trim();

    if (result && result.length > 10) {
      event.context?.bootstrapFiles?.push({
        path: 'RELEVANT_KNOWLEDGE.md',
        content: result,
        label: 'RELEVANT_KNOWLEDGE'
      });
      console.log(`[knowledge-inject] Injected ${result.length} chars of relevant knowledge`);
    }
  } catch (err) {
    // Supabase not ready yet - that's fine, just use checkpoint
    console.log('[knowledge-inject] Supabase query skipped (not configured yet)');
  }
};

export default handler;
