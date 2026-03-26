-- Migration 029: signal_configurations v6 schema redesign
-- Directive #271
--
-- v5 used: vertical_slug text, service_signals jsonb (flat array), no competitor_config
-- v6 uses: vertical varchar(100), services jsonb (nested with problem/budget/not_served signals),
--          competitor_config jsonb
--
-- One test row (marketing_agency) exists, no FK dependencies. Safe to DROP and recreate.

-- 1. Drop old table and trigger function
DROP TABLE IF EXISTS signal_configurations CASCADE;
DROP FUNCTION IF EXISTS update_signal_configurations_updated_at();

-- 2. Create v6 table
CREATE TABLE signal_configurations (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    vertical            varchar(100) UNIQUE NOT NULL,
    services            jsonb NOT NULL DEFAULT '[]',
    discovery_config    jsonb NOT NULL DEFAULT '{}',
    enrichment_gates    jsonb NOT NULL DEFAULT '{}',
    competitor_config   jsonb NOT NULL DEFAULT '{}',
    channel_config      jsonb NOT NULL DEFAULT '{}',
    created_at          timestamptz NOT NULL DEFAULT NOW(),
    updated_at          timestamptz NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signal_config_vertical ON signal_configurations(vertical);

-- 3. updated_at trigger
CREATE OR REPLACE FUNCTION update_signal_configurations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signal_configurations_updated_at
    BEFORE UPDATE ON signal_configurations
    FOR EACH ROW EXECUTE FUNCTION update_signal_configurations_updated_at();

-- 4. Seed marketing_agency with 6 services (v6 structure)
INSERT INTO signal_configurations (
    vertical,
    services,
    discovery_config,
    enrichment_gates,
    competitor_config,
    channel_config
) VALUES (
    'marketing_agency',

    '[
        {
            "service_key": "paid_ads",
            "display_name": "Paid Ads Management",
            "weight": 0.20,
            "scoring_weights": {"budget": 30, "pain": 30, "gap": 25, "fit": 15},
            "problem_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "has paid spend but no conversion tracking pixel",
                    "field": "dfs_paid_etv",
                    "operator": "gt",
                    "threshold": 200
                },
                {
                    "source": "on_page_summary",
                    "condition": "missing conversion tracking — ad spend going unmeasured",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["gtag-conversion", "Google Tag Manager"]
                }
            ],
            "budget_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "active paid keyword spend indicates marketing budget",
                    "field": "dfs_paid_etv",
                    "operator": "gt",
                    "threshold": 0
                },
                {
                    "source": "domain_rank_overview",
                    "condition": "significant paid keyword volume confirms ad spend",
                    "field": "dfs_paid_keywords",
                    "operator": "gt",
                    "threshold": 5
                }
            ],
            "not_served_signals": [
                {
                    "source": "domain_technologies",
                    "condition": "no PPC management or optimisation tool detected",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["Google Ads", "Facebook Pixel", "Google Tag Manager", "WordStream", "Optmyzr", "AdEspresso"]
                }
            ]
        },
        {
            "service_key": "seo",
            "display_name": "SEO Services",
            "weight": 0.20,
            "scoring_weights": {"budget": 20, "pain": 35, "gap": 30, "fit": 15},
            "problem_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "organic ETV low vs paid spend — SEO underperforming",
                    "field": "dfs_organic_etv",
                    "operator": "lt",
                    "threshold": 100
                },
                {
                    "source": "domain_rank_overview",
                    "condition": "many keywords ranking 11-30 indicate low-hanging SEO wins",
                    "field": "dfs_organic_pos_11_20",
                    "operator": "gt",
                    "threshold": 20
                },
                {
                    "source": "domain_rank_overview",
                    "condition": "organic traffic declining month-over-month",
                    "field": "dfs_organic_etv_trend",
                    "operator": "lt",
                    "threshold": -0.10
                }
            ],
            "budget_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "some organic presence indicates investment potential",
                    "field": "dfs_organic_etv",
                    "operator": "gt",
                    "threshold": 10
                }
            ],
            "not_served_signals": [
                {
                    "source": "domain_technologies",
                    "condition": "no SEO platform or analytics tool detected",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["Google Analytics", "Google Search Console", "Yoast SEO", "SEMrush", "Ahrefs", "Moz"]
                }
            ]
        },
        {
            "service_key": "social_media_marketing",
            "display_name": "Social Media Marketing",
            "weight": 0.15,
            "scoring_weights": {"budget": 20, "pain": 25, "gap": 35, "fit": 20},
            "problem_signals": [
                {
                    "source": "domain_technologies",
                    "condition": "no social proof widget or feed on site",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["EmbedSocial", "Curator.io", "Smash Balloon", "Instagram Feed"]
                },
                {
                    "source": "domain_rank_overview",
                    "condition": "low organic reach despite paid spend — social amplification missing",
                    "field": "dfs_organic_etv",
                    "operator": "lt",
                    "threshold": 50
                }
            ],
            "budget_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "paid spend shows marketing budget exists",
                    "field": "dfs_paid_etv",
                    "operator": "gt",
                    "threshold": 100
                }
            ],
            "not_served_signals": [
                {
                    "source": "domain_technologies",
                    "condition": "no social scheduling or management platform detected",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["Facebook Pixel", "LinkedIn Insight Tag", "Hootsuite", "Buffer", "Sprout Social", "Later", "Twitter Pixel"]
                }
            ]
        },
        {
            "service_key": "web_design",
            "display_name": "Web Design & Development",
            "weight": 0.20,
            "scoring_weights": {"budget": 25, "pain": 35, "gap": 25, "fit": 15},
            "problem_signals": [
                {
                    "source": "on_page_summary",
                    "condition": "slow page speed or mobile UX issues detected",
                    "field": "page_speed_score",
                    "operator": "lt",
                    "threshold": 60
                },
                {
                    "source": "domain_technologies",
                    "condition": "site uses outdated or DIY page builder",
                    "field": "tech_stack",
                    "operator": "contains",
                    "threshold": "Wix"
                }
            ],
            "budget_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "organic or paid traffic indicates active business with budget",
                    "field": "dfs_organic_etv",
                    "operator": "gt",
                    "threshold": 0
                }
            ],
            "not_served_signals": [
                {
                    "source": "domain_technologies",
                    "condition": "site uses DIY builder or legacy CMS lacking professional design",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["WordPress", "Wix", "Squarespace", "Webflow", "React", "Next.js"]
                }
            ]
        },
        {
            "service_key": "marketing_automation",
            "display_name": "Marketing Automation",
            "weight": 0.15,
            "scoring_weights": {"budget": 25, "pain": 25, "gap": 35, "fit": 15},
            "problem_signals": [
                {
                    "source": "domain_technologies",
                    "condition": "has traffic but no lead capture or scheduling tool",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["Typeform", "Calendly", "HubSpot Forms", "Gravity Forms"]
                },
                {
                    "source": "domain_rank_overview",
                    "condition": "significant organic traffic with no automation stack — leads leaking",
                    "field": "dfs_organic_etv",
                    "operator": "gt",
                    "threshold": 50
                }
            ],
            "budget_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "paid ad spend indicates budget available for automation",
                    "field": "dfs_paid_etv",
                    "operator": "gt",
                    "threshold": 200
                }
            ],
            "not_served_signals": [
                {
                    "source": "domain_technologies",
                    "condition": "no CRM or marketing automation platform detected",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["HubSpot", "Marketo", "ActiveCampaign", "Salesforce", "Mailchimp", "Klaviyo"]
                }
            ]
        },
        {
            "service_key": "content_marketing",
            "display_name": "Content Marketing",
            "weight": 0.10,
            "scoring_weights": {"budget": 15, "pain": 35, "gap": 30, "fit": 20},
            "problem_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "organic traffic declining month-over-month",
                    "field": "dfs_organic_etv_trend",
                    "operator": "lt",
                    "threshold": -0.10
                },
                {
                    "source": "domain_rank_overview",
                    "condition": "low organic keyword count indicates thin or absent content strategy",
                    "field": "dfs_organic_keywords",
                    "operator": "lt",
                    "threshold": 50
                }
            ],
            "budget_signals": [
                {
                    "source": "domain_rank_overview",
                    "condition": "some organic presence indicates content investment potential",
                    "field": "dfs_organic_etv",
                    "operator": "gt",
                    "threshold": 10
                }
            ],
            "not_served_signals": [
                {
                    "source": "domain_technologies",
                    "condition": "no content management or blogging platform detected",
                    "field": "tech_stack",
                    "operator": "missing",
                    "threshold": ["WordPress", "Ghost", "Contentful", "HubSpot CMS", "Webflow CMS"]
                }
            ]
        }
    ]'::jsonb,

    '{
        "category_codes": [13418, 13420, 13421],
        "ad_spend_threshold": 200,
        "keywords_for_ads_search": [
            "dentist Sydney",
            "plumber Melbourne",
            "accountant Brisbane",
            "lawyer Perth",
            "gym Adelaide"
        ],
        "html_gap_combos": [
            {"has": "google-ads-pixel", "missing": "gtag-conversion"},
            {"has": "wordpress", "missing": "yoast-seo"}
        ],
        "job_search_keywords": [
            "marketing manager",
            "digital marketing coordinator",
            "SEO specialist"
        ],
        "competitor_expansion": true,
        "max_competitors_per_prospect": 5
    }'::jsonb,

    '{
        "min_score_to_qualify": 30,
        "min_score_to_compete": 50,
        "min_score_to_enrich": 30,
        "min_score_to_dm": 50,
        "min_score_to_outreach": 65
    }'::jsonb,

    '{
        "max_competitors_per_prospect": 5,
        "min_competitor_organic_etv": 100,
        "store_top_n_for_messaging": 3,
        "feed_back_to_discovery": true
    }'::jsonb,

    '{
        "email": true,
        "linkedin": true,
        "voice": true,
        "sms": false
    }'::jsonb
);
