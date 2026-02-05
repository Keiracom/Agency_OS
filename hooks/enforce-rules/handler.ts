import type { HookHandler } from 'clawdbot/hooks';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Enforce Rules Hook
 * Fires on agent:bootstrap (before every response)
 * Reads ENFORCE.md from workspace and injects into system prompt
 */
const handler: HookHandler = async (event) => {
  if (event.type !== 'agent' || event.action !== 'bootstrap') {
    return;
  }

  const context = (event as any).context;
  
  if (!context?.bootstrapFiles || !Array.isArray(context.bootstrapFiles)) {
    return;
  }

  // Read ENFORCE.md from workspace
  const workspaceDir = context.workspaceDir || '/home/elliotbot/clawd';
  const enforcePath = path.join(workspaceDir, 'ENFORCE.md');
  
  let rules: string;
  try {
    rules = fs.readFileSync(enforcePath, 'utf-8');
  } catch (err) {
    // Fallback if file doesn't exist
    rules = `## ⚡ ENFORCE (Every Response)\n\nENFORCE.md not found at ${enforcePath}`;
  }

  // Inject as a bootstrap file
  context.bootstrapFiles.push({
    name: 'ENFORCE.md',
    path: enforcePath,
    content: rules,
    missing: false
  });
};

export default handler;
