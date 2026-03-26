-- Migration 022b: seed marketing_agency signal config
-- Directive #256

INSERT INTO signal_configurations (
    vertical_slug,
    display_name,
    description,
    service_signals,
    discovery_config,
    enrichment_gates,
    channel_config
) VALUES (
    'marketing_agency',
    'Marketing Agency',
    'Identifies businesses showing buying intent for marketing agency services — paid ads management, SEO, content, social, and marketing automation.',
    '[
        {
            "service_name": "paid_ads",
            "label": "Paid Ads Management",
            "dfs_technologies": ["Google Ads", "Facebook Pixel", "Google Tag Manager"],
            "gmb_categories": ["marketing_agency", "advertising_agency", "digital_marketing"],
            "scoring_weights": {"budget": 30, "pain": 30, "gap": 25, "fit": 15}
        },
        {
            "service_name": "seo",
            "label": "SEO Services",
            "dfs_technologies": ["Google Analytics", "Google Search Console"],
            "gmb_categories": ["marketing_agency", "seo_company"],
            "scoring_weights": {"budget": 20, "pain": 35, "gap": 30, "fit": 15}
        },
        {
            "service_name": "marketing_automation",
            "label": "Marketing Automation",
            "dfs_technologies": ["Google Ads", "Facebook Pixel"],
            "must_not_have_technologies": ["HubSpot", "Marketo", "ActiveCampaign", "Mailchimp"],
            "gmb_categories": ["marketing_agency", "advertising_agency"],
            "scoring_weights": {"budget": 25, "pain": 25, "gap": 35, "fit": 15}
        }
    ]'::jsonb,
    '{
        "dfs_depth": 100,
        "gmb_radius_km": 50,
        "gmb_zoom": "14z",
        "suburb_csv_source": "src/data/au_suburbs.csv",
        "min_paid_etv_usd": 500,
        "organic_trend_signal": "declining"
    }'::jsonb,
    '{
        "min_score_to_enrich": 30,
        "min_score_to_dm": 50,
        "min_score_to_outreach": 65
    }'::jsonb,
    '{
        "email": true,
        "linkedin": true,
        "voice": true,
        "sms": false
    }'::jsonb
) ON CONFLICT (vertical_slug) DO NOTHING;
