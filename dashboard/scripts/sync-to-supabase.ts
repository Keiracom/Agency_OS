#!/usr/bin/env npx ts-node

/**
 * Elliot Memory Sync Script
 * 
 * Parses Elliot's memory files and syncs them to Supabase.
 * Run this periodically or after significant memory updates.
 * 
 * Usage:
 *   npx ts-node scripts/sync-to-supabase.ts
 *   
 * Or with env vars:
 *   SUPABASE_URL=xxx SUPABASE_SERVICE_ROLE_KEY=xxx npx ts-node scripts/sync-to-supabase.ts
 */

import { createClient } from '@supabase/supabase-js';
import * as fs from 'fs';
import * as path from 'path';

// Configuration
const ELLIOT_WORKSPACE = process.env.ELLIOT_WORKSPACE || '/home/elliotbot/clawd';
const API_URL = process.env.ELLIOT_API_URL || 'http://localhost:3000/api/elliot';
const API_TOKEN = process.env.ELLIOT_API_TOKEN || '';

// Supabase direct connection (alternative to API)
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

interface SyncResult {
  type: string;
  count: number;
  errors: string[];
}

// Parse markdown file to extract structured data
function parseMarkdownFile(content: string, type: string): any[] {
  const items: any[] = [];
  
  switch (type) {
    case 'decisions':
      // Parse DECISIONS.md format
      // Expected format: ## Decision: [title]\n**Context:** ...\n**Rationale:** ...\n**Outcome:** ...
      const decisionBlocks = content.split(/^## /m).filter(Boolean);
      for (const block of decisionBlocks) {
        const lines = block.trim().split('\n');
        const decision = lines[0].replace(/^Decision:\s*/i, '').trim();
        if (!decision) continue;
        
        const contextMatch = block.match(/\*\*Context:\*\*\s*(.+?)(?=\*\*|$)/s);
        const rationaleMatch = block.match(/\*\*Rationale:\*\*\s*(.+?)(?=\*\*|$)/s);
        const outcomeMatch = block.match(/\*\*Outcome:\*\*\s*(.+?)(?=\*\*|$)/s);
        const ratingMatch = block.match(/\*\*Rating:\*\*\s*(\d)/);
        const tagsMatch = block.match(/\*\*Tags:\*\*\s*(.+)/);
        
        items.push({
          decision,
          context: contextMatch?.[1]?.trim() || null,
          rationale: rationaleMatch?.[1]?.trim() || null,
          outcome: outcomeMatch?.[1]?.trim() || null,
          outcome_rating: ratingMatch ? parseInt(ratingMatch[1]) : null,
          tags: tagsMatch ? tagsMatch[1].split(',').map(t => t.trim()) : [],
        });
      }
      break;

    case 'learnings':
      // Parse LEARNINGS.md format
      // Expected format: - **Lesson:** ... (Source: ...)
      const learningMatches = content.matchAll(/^[-*]\s+\*\*(.+?):\*\*\s*(.+?)(?:\s*\(Source:\s*(.+?)\))?$/gm);
      for (const match of learningMatches) {
        const category = match[1].toLowerCase().trim();
        const lesson = match[2].trim();
        const source = match[3]?.trim() || null;
        
        if (lesson) {
          items.push({
            lesson,
            source,
            category: category === 'lesson' ? 'general' : category,
          });
        }
      }
      
      // Also try simpler format: - Lesson text
      const simpleLearnings = content.matchAll(/^[-*]\s+(?!\*\*)(.{20,}?)$/gm);
      for (const match of simpleLearnings) {
        items.push({
          lesson: match[1].trim(),
          category: 'general',
        });
      }
      break;

    case 'rules':
      // Parse RULES.md format
      // Expected format: ### Category\n- Rule text
      let currentCategory = 'general';
      const ruleLines = content.split('\n');
      
      for (const line of ruleLines) {
        const categoryMatch = line.match(/^###\s+(.+)/);
        if (categoryMatch) {
          currentCategory = categoryMatch[1].toLowerCase().trim();
          continue;
        }
        
        const ruleMatch = line.match(/^[-*]\s+(.{10,})$/);
        if (ruleMatch) {
          items.push({
            rule: ruleMatch[1].trim(),
            category: currentCategory,
            priority: currentCategory === 'safety' ? 10 : 5,
          });
        }
      }
      break;

    case 'patterns':
      // Parse PATTERNS.md format
      // Expected format: ## Pattern: [name]\n[description]\n**Occurrences:** N
      const patternBlocks = content.split(/^## /m).filter(Boolean);
      for (const block of patternBlocks) {
        const lines = block.trim().split('\n');
        const pattern = lines[0].replace(/^Pattern:\s*/i, '').trim();
        if (!pattern) continue;
        
        const descriptionLines = lines.slice(1).filter(l => !l.startsWith('**'));
        const description = descriptionLines.join('\n').trim();
        
        const occurrencesMatch = block.match(/\*\*Occurrences:\*\*\s*(\d+)/);
        const categoryMatch = block.match(/\*\*Category:\*\*\s*(.+)/);
        
        items.push({
          pattern,
          description: description || null,
          occurrences: occurrencesMatch ? parseInt(occurrencesMatch[1]) : 1,
          category: categoryMatch?.[1]?.trim().toLowerCase() || 'behavioral',
        });
      }
      break;

    case 'memory':
      // Parse MEMORY.md format
      // Expected format: ## [Category]\n### [Key]\n[Value]
      let memCategory = 'general';
      let memKey = '';
      let memValue: string[] = [];
      
      const memLines = content.split('\n');
      for (let i = 0; i < memLines.length; i++) {
        const line = memLines[i];
        
        // Category header
        const catMatch = line.match(/^##\s+(?!#)(.+)/);
        if (catMatch) {
          // Save previous item
          if (memKey && memValue.length) {
            items.push({
              key: memKey,
              value: memValue.join('\n').trim(),
              category: memCategory,
            });
          }
          memCategory = catMatch[1].toLowerCase().trim();
          memKey = '';
          memValue = [];
          continue;
        }
        
        // Key header
        const keyMatch = line.match(/^###\s+(.+)/);
        if (keyMatch) {
          // Save previous item
          if (memKey && memValue.length) {
            items.push({
              key: memKey,
              value: memValue.join('\n').trim(),
              category: memCategory,
            });
          }
          memKey = keyMatch[1].trim();
          memValue = [];
          continue;
        }
        
        // Value content
        if (memKey && line.trim()) {
          memValue.push(line);
        }
      }
      
      // Save last item
      if (memKey && memValue.length) {
        items.push({
          key: memKey,
          value: memValue.join('\n').trim(),
          category: memCategory,
        });
      }
      break;
  }
  
  return items;
}

// Sync via API
async function syncViaApi(type: string, data: any[]): Promise<SyncResult> {
  const result: SyncResult = { type, count: 0, errors: [] };
  
  if (!data.length) return result;
  
  try {
    const response = await fetch(`${API_URL}/sync`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_TOKEN}`,
      },
      body: JSON.stringify({ type, data }),
    });
    
    if (!response.ok) {
      const error = await response.text();
      result.errors.push(`API error: ${error}`);
      return result;
    }
    
    const json = await response.json();
    result.count = json.result?.inserted || data.length;
  } catch (err) {
    result.errors.push(`Fetch error: ${err}`);
  }
  
  return result;
}

// Sync directly to Supabase
async function syncToSupabase(type: string, data: any[]): Promise<SyncResult> {
  const result: SyncResult = { type, count: 0, errors: [] };
  
  if (!data.length) return result;
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    result.errors.push('Supabase credentials not configured');
    return result;
  }
  
  const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
  
  const tableMap: Record<string, string> = {
    decisions: 'elliot_decisions',
    learnings: 'elliot_learnings',
    patterns: 'elliot_patterns',
    rules: 'elliot_rules',
    memory: 'elliot_memory',
  };
  
  const table = tableMap[type];
  if (!table) {
    result.errors.push(`Unknown type: ${type}`);
    return result;
  }
  
  try {
    if (type === 'memory') {
      // Upsert memory by key
      const { data: inserted, error } = await supabase
        .from(table)
        .upsert(data, { onConflict: 'key' })
        .select();
      
      if (error) throw error;
      result.count = inserted?.length || 0;
    } else if (type === 'patterns') {
      // Handle patterns specially - update occurrences
      for (const pattern of data) {
        const { data: existing } = await supabase
          .from(table)
          .select()
          .eq('pattern', pattern.pattern)
          .single();
        
        if (existing) {
          await supabase
            .from(table)
            .update({
              occurrences: Math.max(existing.occurrences, pattern.occurrences || 1),
              last_seen: new Date().toISOString(),
            })
            .eq('id', existing.id);
        } else {
          await supabase.from(table).insert(pattern);
        }
        result.count++;
      }
    } else {
      // Insert new items (skip duplicates by checking existing)
      const { data: inserted, error } = await supabase
        .from(table)
        .insert(data)
        .select();
      
      if (error) throw error;
      result.count = inserted?.length || 0;
    }
  } catch (err) {
    result.errors.push(`Supabase error: ${err}`);
  }
  
  return result;
}

// Main sync function
async function syncAll(): Promise<void> {
  console.log('🔄 Starting Elliot memory sync...\n');
  
  const files: { path: string; type: string }[] = [
    { path: 'knowledge/DECISIONS.md', type: 'decisions' },
    { path: 'knowledge/LEARNINGS.md', type: 'learnings' },
    { path: 'knowledge/RULES.md', type: 'rules' },
    { path: 'memory/PATTERNS.md', type: 'patterns' },
    { path: 'MEMORY.md', type: 'memory' },
  ];
  
  const results: SyncResult[] = [];
  
  for (const file of files) {
    const filePath = path.join(ELLIOT_WORKSPACE, file.path);
    
    if (!fs.existsSync(filePath)) {
      console.log(`⏭️  Skipping ${file.path} (not found)`);
      continue;
    }
    
    console.log(`📖 Reading ${file.path}...`);
    const content = fs.readFileSync(filePath, 'utf-8');
    const items = parseMarkdownFile(content, file.type);
    
    console.log(`   Found ${items.length} ${file.type}`);
    
    if (items.length === 0) continue;
    
    // Try direct Supabase first, fall back to API
    let result: SyncResult;
    if (SUPABASE_URL && SUPABASE_KEY) {
      result = await syncToSupabase(file.type, items);
    } else {
      result = await syncViaApi(file.type, items);
    }
    
    results.push(result);
    
    if (result.errors.length) {
      console.log(`   ❌ Errors: ${result.errors.join(', ')}`);
    } else {
      console.log(`   ✅ Synced ${result.count} items`);
    }
  }
  
  // Summary
  console.log('\n📊 Sync Summary:');
  console.log('─'.repeat(40));
  for (const r of results) {
    const status = r.errors.length ? '❌' : '✅';
    console.log(`${status} ${r.type}: ${r.count} items`);
  }
  
  const totalErrors = results.reduce((sum, r) => sum + r.errors.length, 0);
  if (totalErrors === 0) {
    console.log('\n✨ Sync completed successfully!');
  } else {
    console.log(`\n⚠️  Sync completed with ${totalErrors} errors`);
    process.exit(1);
  }
}

// Run if called directly
syncAll().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});

export { syncAll, parseMarkdownFile, syncToSupabase, syncViaApi };
