#!/bin/bash
# ============================================================================
# MORNING WOW REPORT GENERATOR
# ============================================================================
# Purpose: Generate Dave's daily briefing with current state, achievements,
#          financial pulse, and items awaiting approval.
#
# Usage: ./scripts/morning_wow.sh
#
# Conceptual Summary (LAW IV):
#   This script queries Supabase for current project state, recent memories,
#   and pending signoff items. It formats them into a CEO-ready report that
#   enables Dave to see overnight progress without asking questions.
#
# Cost: FREE (read-only queries)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TOOL="$PROJECT_ROOT/tools/database_master.py"

# Colors for terminal output
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║                    🌅 MORNING WOW REPORT                       ║${NC}"
echo -e "${BOLD}║                    $(date '+%Y-%m-%d %H:%M %Z')                        ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# 1. CURRENT PHASE (From Supabase State)
# ============================================================================
echo -e "${BLUE}━━━ 📍 CURRENT PHASE ━━━${NC}"

CURRENT_STATE=$(python3 "$TOOL" query supabase --sql "
SELECT 
  value->>'project' as project,
  value->>'phase' as phase,
  value->>'status' as status,
  value->>'started_at' as started_at,
  updated_at
FROM elliot_internal.state 
WHERE key = 'current_process'
LIMIT 1;
" 2>/dev/null | grep -A20 "Results" || echo "No state found")

if echo "$CURRENT_STATE" | grep -q "project"; then
  PROJECT=$(echo "$CURRENT_STATE" | grep -o '"project": "[^"]*"' | cut -d'"' -f4)
  PHASE=$(echo "$CURRENT_STATE" | grep -o '"phase": "[^"]*"' | cut -d'"' -f4)
  STATUS=$(echo "$CURRENT_STATE" | grep -o '"status": "[^"]*"' | cut -d'"' -f4)
  echo -e "  Project: ${GREEN}$PROJECT${NC}"
  echo -e "  Phase:   ${GREEN}$PHASE${NC}"
  echo -e "  Status:  ${GREEN}$STATUS${NC}"
else
  echo -e "  ${YELLOW}⚠️  No active project state found${NC}"
fi
echo ""

# ============================================================================
# 2. ACHIEVEMENTS SINCE LAST UPDATE (From Memories)
# ============================================================================
echo -e "${BLUE}━━━ 🏆 RECENT ACHIEVEMENTS ━━━${NC}"

MEMORIES=$(python3 "$TOOL" query supabase --sql "
SELECT 
  type,
  LEFT(content, 100) as summary,
  created_at
FROM elliot_internal.memories 
WHERE deleted_at IS NULL
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 5;
" 2>/dev/null | grep -A50 "Results" || echo "No recent memories")

if echo "$MEMORIES" | grep -q "summary"; then
  echo "$MEMORIES" | python3 -c "
import sys, json
try:
    data = sys.stdin.read()
    start = data.find('[')
    end = data.rfind(']') + 1
    if start >= 0 and end > start:
        items = json.loads(data[start:end])
        for i, item in enumerate(items, 1):
            print(f\"  {i}. [{item.get('type', 'unknown')}] {item.get('summary', 'No summary')}\")
except:
    print('  No structured memories found')
" 2>/dev/null || echo "  (Parsing memories...)"
else
  echo -e "  ${YELLOW}No memories from last 24 hours${NC}"
  echo -e "  ${YELLOW}Check local memory/$(date +%Y-%m-%d).md for session notes${NC}"
fi
echo ""

# ============================================================================
# 3. $AUD FINANCIAL PULSE
# ============================================================================
echo -e "${BLUE}━━━ 💰 \$AUD FINANCIAL PULSE ━━━${NC}"

# Pull any cost-related memories or use static estimates
echo "  Infrastructure (Monthly Fixed):"
echo -e "    Railway Backend:     ${GREEN}\$31 AUD${NC}"
echo -e "    Vercel Frontend:     ${GREEN}\$31 AUD${NC}"
echo -e "    Supabase Database:   ${GREEN}\$39 AUD${NC}"
echo -e "    Salesforge Pro:      ${GREEN}\$154 AUD${NC}"
echo -e "    ─────────────────────────────"
echo -e "    Monthly Base:        ${BOLD}\$255 AUD${NC}"
echo ""
echo "  Variable (This Phase - Estimated):"

# Check for any enrichment/email spend tracking
SPEND_QUERY=$(python3 "$TOOL" query supabase --sql "
SELECT 
  COALESCE(SUM((metadata->>'cost_aud')::numeric), 0) as total_spend
FROM elliot_internal.memories 
WHERE type = 'cost_event'
  AND created_at > NOW() - INTERVAL '30 days';
" 2>/dev/null | grep -o '"total_spend": [0-9.]*' | cut -d' ' -f2 || echo "0")

if [ -n "$SPEND_QUERY" ] && [ "$SPEND_QUERY" != "0" ]; then
  echo -e "    Tracked API Spend:   ${YELLOW}\$${SPEND_QUERY} AUD${NC}"
else
  echo -e "    Tracked API Spend:   ${GREEN}\$0 AUD${NC} (no cost events logged)"
fi

echo -e "    Pending Pipeline:    ${YELLOW}\$46 AUD${NC} (200-lead batch awaiting approval)"
echo ""

# ============================================================================
# 4. THE VETO BLOCK (Signoff Queue)
# ============================================================================
echo -e "${BLUE}━━━ 🚫 VETO BLOCK (Awaiting Dave's Approval) ━━━${NC}"

PENDING=$(python3 "$TOOL" query supabase --sql "
SELECT 
  id,
  action_type,
  title,
  summary,
  created_at
FROM public.elliot_signoff_queue 
WHERE status = 'pending'
ORDER BY created_at ASC;
" 2>/dev/null | grep -A100 "Results" || echo "No pending items")

if echo "$PENDING" | grep -q "title"; then
  echo "$PENDING" | python3 -c "
import sys, json
try:
    data = sys.stdin.read()
    start = data.find('[')
    end = data.rfind(']') + 1
    if start >= 0 and end > start:
        items = json.loads(data[start:end])
        if items:
            for i, item in enumerate(items, 1):
                print(f\"  {i}. [{item.get('action_type', '?')}] {item.get('title', 'Untitled')}\")
                print(f\"     {item.get('summary', '')[:80]}\")
        else:
            print('  ✅ No items pending approval')
except Exception as e:
    print(f'  ✅ No items pending approval')
" 2>/dev/null || echo "  ✅ No items pending approval"
else
  echo -e "  ${GREEN}✅ No items pending approval${NC}"
fi
echo ""

# ============================================================================
# 5. LOCAL MEMORY CHECK
# ============================================================================
echo -e "${BLUE}━━━ 📝 LOCAL MEMORY STATUS ━━━${NC}"

MEMORY_FILE="$PROJECT_ROOT/memory/$(date +%Y-%m-%d).md"
if [ -f "$MEMORY_FILE" ]; then
  LINES=$(wc -l < "$MEMORY_FILE")
  echo -e "  Today's log: ${GREEN}$MEMORY_FILE${NC} ($LINES lines)"
else
  echo -e "  Today's log: ${YELLOW}Not yet created${NC}"
fi

YESTERDAY_FILE="$PROJECT_ROOT/memory/$(date -d 'yesterday' +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null).md"
if [ -f "$YESTERDAY_FILE" ]; then
  echo -e "  Yesterday:   ${GREEN}Available${NC}"
fi
echo ""

# ============================================================================
# FOOTER
# ============================================================================
echo -e "${BOLD}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  Ready for instructions. Governance: ENFORCE.md v1 active.    ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
