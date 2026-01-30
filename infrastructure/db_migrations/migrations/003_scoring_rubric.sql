-- ============================================
-- 003: Knowledge Relevance Scoring Rubric
-- ============================================
-- Scores incoming knowledge items 0.0-1.0 based on relevance to Agency OS
-- 
-- Scoring Tiers:
--   HIGH (0.8-1.0): Agency OS stack, SaaS/agency business, AI/LLM, outreach/automation
--   MEDIUM (0.5-0.7): General dev tools, productivity, business insights
--   LOW (0.0-0.4): Gaming, crypto, social entertainment, unrelated

-- ============================================
-- Scoring Function
-- ============================================

CREATE OR REPLACE FUNCTION score_knowledge_relevance(
    content TEXT,
    category TEXT DEFAULT NULL
)
RETURNS FLOAT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    content_lower TEXT;
    base_score FLOAT := 0.3;  -- Default: low relevance
    keyword_boost FLOAT := 0.0;
    category_boost FLOAT := 0.0;
    penalty FLOAT := 0.0;
BEGIN
    -- Normalize content for matching
    content_lower := LOWER(COALESCE(content, ''));
    
    -- ==========================================
    -- HIGH RELEVANCE KEYWORDS (0.3-0.5 boost)
    -- ==========================================
    
    -- Agency OS Stack (direct matches get highest boost)
    IF content_lower ~ '\y(fastapi|fast-api|fast api)\y' THEN
        keyword_boost := keyword_boost + 0.45;
    END IF;
    IF content_lower ~ '\y(nextjs|next\.js|next js)\y' THEN
        keyword_boost := keyword_boost + 0.45;
    END IF;
    IF content_lower ~ '\ysupabase\y' THEN
        keyword_boost := keyword_boost + 0.50;
    END IF;
    IF content_lower ~ '\yprefect\y' THEN
        keyword_boost := keyword_boost + 0.50;
    END IF;
    IF content_lower ~ '\yrailway\y' THEN
        keyword_boost := keyword_boost + 0.40;
    END IF;
    IF content_lower ~ '\yvercel\y' THEN
        keyword_boost := keyword_boost + 0.35;
    END IF;
    
    -- AI/LLM Tools (high relevance)
    IF content_lower ~ '\y(anthropic|claude|sonnet|opus|haiku)\y' THEN
        keyword_boost := keyword_boost + 0.50;
    END IF;
    IF content_lower ~ '\y(openai|gpt-4|gpt4|chatgpt|gpt-3|gpt3)\y' THEN
        keyword_boost := keyword_boost + 0.40;
    END IF;
    IF content_lower ~ '\y(llm|llms|large language model)\y' THEN
        keyword_boost := keyword_boost + 0.35;
    END IF;
    IF content_lower ~ '\y(langchain|langsmith|langgraph)\y' THEN
        keyword_boost := keyword_boost + 0.40;
    END IF;
    IF content_lower ~ '\y(rag|retrieval augmented|vector database|embedding)\y' THEN
        keyword_boost := keyword_boost + 0.35;
    END IF;
    IF content_lower ~ '\y(ai agent|ai agents|agentic|multi-agent)\y' THEN
        keyword_boost := keyword_boost + 0.45;
    END IF;
    IF content_lower ~ '\y(mcp|model context protocol)\y' THEN
        keyword_boost := keyword_boost + 0.45;
    END IF;
    
    -- Outreach/Automation (high relevance for agency)
    IF content_lower ~ '\y(cold email|email outreach|outbound|lead gen|lead generation)\y' THEN
        keyword_boost := keyword_boost + 0.45;
    END IF;
    IF content_lower ~ '\y(sales automation|crm|pipeline|prospecting)\y' THEN
        keyword_boost := keyword_boost + 0.40;
    END IF;
    IF content_lower ~ '\y(linkedin automation|linkedin outreach)\y' THEN
        keyword_boost := keyword_boost + 0.45;
    END IF;
    IF content_lower ~ '\y(workflow automation|n8n|zapier|make\.com)\y' THEN
        keyword_boost := keyword_boost + 0.35;
    END IF;
    IF content_lower ~ '\y(twilio|sendgrid|resend|email api)\y' THEN
        keyword_boost := keyword_boost + 0.35;
    END IF;
    
    -- SaaS/Agency Business
    IF content_lower ~ '\y(saas|software as a service)\y' THEN
        keyword_boost := keyword_boost + 0.35;
    END IF;
    IF content_lower ~ '\y(agency|agencies|white label|whitelabel)\y' THEN
        keyword_boost := keyword_boost + 0.40;
    END IF;
    IF content_lower ~ '\y(mrr|arr|churn|retention|pricing|monetization)\y' THEN
        keyword_boost := keyword_boost + 0.30;
    END IF;
    IF content_lower ~ '\y(b2b|enterprise sales|smb)\y' THEN
        keyword_boost := keyword_boost + 0.30;
    END IF;
    
    -- ==========================================
    -- MEDIUM RELEVANCE KEYWORDS (0.1-0.25 boost)
    -- ==========================================
    
    -- General Dev Tools
    IF content_lower ~ '\y(python|typescript|javascript|rust|go)\y' THEN
        keyword_boost := keyword_boost + 0.15;
    END IF;
    IF content_lower ~ '\y(docker|kubernetes|k8s|terraform|aws|gcp|azure)\y' THEN
        keyword_boost := keyword_boost + 0.15;
    END IF;
    IF content_lower ~ '\y(postgres|postgresql|redis|mongodb)\y' THEN
        keyword_boost := keyword_boost + 0.20;
    END IF;
    IF content_lower ~ '\y(api|rest|graphql|grpc)\y' THEN
        keyword_boost := keyword_boost + 0.15;
    END IF;
    IF content_lower ~ '\y(github|gitlab|ci/cd|devops)\y' THEN
        keyword_boost := keyword_boost + 0.15;
    END IF;
    
    -- Productivity & Business
    IF content_lower ~ '\y(productivity|efficiency|automation)\y' THEN
        keyword_boost := keyword_boost + 0.20;
    END IF;
    IF content_lower ~ '\y(startup|founder|entrepreneur|bootstrap)\y' THEN
        keyword_boost := keyword_boost + 0.20;
    END IF;
    IF content_lower ~ '\y(remote work|async|team management)\y' THEN
        keyword_boost := keyword_boost + 0.15;
    END IF;
    IF content_lower ~ '\y(analytics|metrics|dashboard|monitoring)\y' THEN
        keyword_boost := keyword_boost + 0.15;
    END IF;
    
    -- General AI/ML (medium - not as specific as LLM)
    IF content_lower ~ '\y(machine learning|ml|deep learning|neural network)\y' THEN
        keyword_boost := keyword_boost + 0.20;
    END IF;
    IF content_lower ~ '\y(nlp|natural language|computer vision|cv)\y' THEN
        keyword_boost := keyword_boost + 0.15;
    END IF;
    
    -- ==========================================
    -- LOW RELEVANCE / PENALTIES
    -- ==========================================
    
    -- Gaming (penalty)
    IF content_lower ~ '\y(gaming|game|gamer|esports|playstation|xbox|nintendo|steam|twitch)\y' THEN
        penalty := penalty + 0.30;
    END IF;
    IF content_lower ~ '\y(fortnite|minecraft|valorant|league of legends|dota)\y' THEN
        penalty := penalty + 0.40;
    END IF;
    
    -- Crypto/Web3 (penalty - unless DeFi/fintech relevant)
    IF content_lower ~ '\y(crypto|cryptocurrency|bitcoin|btc|ethereum|eth|nft|web3|defi|blockchain)\y' THEN
        penalty := penalty + 0.25;
    END IF;
    IF content_lower ~ '\y(token|ico|airdrop|memecoin|shitcoin|hodl|moon)\y' THEN
        penalty := penalty + 0.40;
    END IF;
    
    -- Social/Entertainment (penalty)
    IF content_lower ~ '\y(tiktok|instagram|snapchat|influencer|viral|meme)\y' THEN
        penalty := penalty + 0.25;
    END IF;
    IF content_lower ~ '\y(celebrity|gossip|drama|reality tv)\y' THEN
        penalty := penalty + 0.40;
    END IF;
    
    -- Consumer/Unrelated
    IF content_lower ~ '\y(recipe|cooking|fitness|workout|diet)\y' THEN
        penalty := penalty + 0.25;
    END IF;
    IF content_lower ~ '\y(dating|relationship|horoscope)\y' THEN
        penalty := penalty + 0.35;
    END IF;
    
    -- ==========================================
    -- CATEGORY BOOST
    -- ==========================================
    
    IF category IS NOT NULL THEN
        CASE LOWER(category)
            WHEN 'tech_trend' THEN category_boost := 0.10;
            WHEN 'tool_discovery' THEN category_boost := 0.15;
            WHEN 'business_insight' THEN category_boost := 0.10;
            WHEN 'competitor_intel' THEN category_boost := 0.15;
            WHEN 'pattern_recognition' THEN category_boost := 0.10;
            WHEN 'general' THEN category_boost := 0.0;
            ELSE category_boost := 0.0;
        END CASE;
    END IF;
    
    -- ==========================================
    -- CALCULATE FINAL SCORE
    -- ==========================================
    
    -- Cap keyword boost at 0.65 (so base + boost = max 0.95)
    keyword_boost := LEAST(keyword_boost, 0.65);
    
    -- Cap penalty at 0.50
    penalty := LEAST(penalty, 0.50);
    
    -- Final calculation
    RETURN GREATEST(0.0, LEAST(1.0, base_score + keyword_boost + category_boost - penalty));
END;
$$;

-- ============================================
-- Add relevance_score column to elliot_knowledge
-- ============================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'elliot_knowledge' 
        AND column_name = 'relevance_score'
    ) THEN
        ALTER TABLE elliot_knowledge 
        ADD COLUMN relevance_score FLOAT DEFAULT 0.5;
    END IF;
END $$;

-- ============================================
-- Index for filtering by relevance
-- ============================================

CREATE INDEX IF NOT EXISTS idx_elliot_knowledge_relevance 
ON elliot_knowledge(relevance_score DESC);

-- ============================================
-- Trigger to auto-score on insert/update
-- ============================================

CREATE OR REPLACE FUNCTION trigger_score_knowledge()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.relevance_score := score_knowledge_relevance(
        COALESCE(NEW.content, '') || ' ' || COALESCE(NEW.summary, ''),
        NEW.category
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_score_knowledge_insert ON elliot_knowledge;
CREATE TRIGGER trg_score_knowledge_insert
    BEFORE INSERT ON elliot_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION trigger_score_knowledge();

DROP TRIGGER IF EXISTS trg_score_knowledge_update ON elliot_knowledge;
CREATE TRIGGER trg_score_knowledge_update
    BEFORE UPDATE OF content, summary, category ON elliot_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION trigger_score_knowledge();

-- ============================================
-- Backfill existing records
-- ============================================

UPDATE elliot_knowledge
SET relevance_score = score_knowledge_relevance(
    COALESCE(content, '') || ' ' || COALESCE(summary, ''),
    category
)
WHERE relevance_score IS NULL OR relevance_score = 0.5;

-- ============================================
-- Helper view for high-relevance knowledge
-- ============================================

CREATE OR REPLACE VIEW elliot_knowledge_relevant AS
SELECT *
FROM elliot_knowledge
WHERE relevance_score >= 0.5
ORDER BY relevance_score DESC, learned_at DESC;

-- ============================================
-- Comments
-- ============================================

COMMENT ON FUNCTION score_knowledge_relevance IS 
'Scores content relevance 0.0-1.0 for Agency OS knowledge system.
HIGH (0.8-1.0): Stack match, SaaS/agency, AI/LLM, outreach
MEDIUM (0.5-0.7): Dev tools, productivity, business
LOW (0.0-0.4): Gaming, crypto, social, unrelated';

COMMENT ON COLUMN elliot_knowledge.relevance_score IS 
'Auto-scored relevance 0.0-1.0 via score_knowledge_relevance()';
