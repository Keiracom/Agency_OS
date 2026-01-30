import type { HookHandler } from 'clawdbot/hooks';
import * as fs from 'fs';

/**
 * Enforce Rules Hook
 * Fires on agent:bootstrap (before every response)
 * Injects core behavioral rules into system prompt
 */
const handler: HookHandler = async (event) => {
  // Check if this is an agent:bootstrap event
  if (event.type !== 'agent' || event.action !== 'bootstrap') {
    return;
  }

  const context = (event as any).context;
  
  // Skip if no bootstrapFiles array
  if (!context?.bootstrapFiles || !Array.isArray(context.bootstrapFiles)) {
    return;
  }

  const rules = `## ⚡ ENFORCE (Every Response)

BEFORE RESPONDING:
1. Decisions, not questions. Dave signs off. Operations are mine.
2. Validate approach with co-operator before presenting to Dave.
3. "A or B?" → Pick one.
4. NO EXECUTION. Orchestrate and communicate. Spawn agents for all tasks.
5. Bottom line first. No hedge words.
6. Path clear? → Do it. Present finished work.
7. Fix issues. Research solutions. Never report "testing..." — report results. Never disable things to test — fix them.

VIOLATIONS = FAILURE.`;

  // Inject as a bootstrap file with correct structure
  context.bootstrapFiles.push({
    name: 'ENFORCE.md',
    path: '/home/elliotbot/clawd/ENFORCE.md',
    content: rules,
    missing: false
  });

  // Debug log
  fs.appendFileSync('/tmp/enforce-rules.log', `[${new Date().toISOString()}] Hook fired - injected rules\n`);
};

export default handler;
