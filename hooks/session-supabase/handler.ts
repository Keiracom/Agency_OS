import type { HookHandler } from 'clawdbot/hooks';
import { spawn } from 'child_process';
import { resolve } from 'path';

/**
 * Session Supabase Hook (LAW IX Automation)
 * Fires on /new and /reset - auto-saves session summary to Supabase via MCP Bridge
 * Uses memory-mcp for consistent storage with embeddings
 */

const MCP_BRIDGE_PATH = resolve(process.env.HOME || '~', 'clawd/skills/mcp-bridge/scripts/mcp-bridge.js');

async function callMcpBridge(args: object): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn('node', [
      MCP_BRIDGE_PATH,
      'call',
      'memory', 
      'save',
      JSON.stringify(args)
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 30000
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (data) => { stdout += data; });
    child.stderr.on('data', (data) => { stderr += data; });

    child.on('close', (code) => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(stderr || stdout || `Exit code ${code}`));
      }
    });

    child.on('error', reject);
  });
}

const handler: HookHandler = async (event) => {
  if (event.type !== 'command' || !['new', 'reset'].includes(event.action)) {
    return;
  }

  const session = (event as any).session;
  const today = new Date().toISOString().split('T')[0];
  
  const content = `Session ${today}: ${event.action} triggered. Tokens: ${session?.totalTokens || 'unknown'}. Context: ${session?.contextPercent || 'unknown'}%. Auto-saved by session-supabase hook.`;

  try {
    const result = await callMcpBridge({
      type: 'daily_log',
      content,
      metadata: { 
        source: 'hook', 
        trigger: event.action,
        date: today,
        tokens: session?.totalTokens,
        contextPercent: session?.contextPercent
      }
    });
    
    if (result.includes('"status": "saved"')) {
      console.log('[session-supabase] Saved via MCP bridge');
    } else {
      console.error('[session-supabase] Unexpected response:', result.slice(0, 200));
    }
  } catch (err) {
    console.error('[session-supabase] Failed:', err instanceof Error ? err.message : err);
  }
};

export default handler;
