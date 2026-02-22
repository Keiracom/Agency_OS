-- Migration: 060_discovery_tables.sql
-- CEO Directive #021 — Supabase Migration + Seed Data
-- Creates discovery tables for ABN/Maps lead generation and seeds lookup data

-- ================================
-- TABLE DEFINITIONS
-- ================================

-- 1. Industry Keywords Table
CREATE TABLE industry_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_slug TEXT NOT NULL UNIQUE,
    industry_label TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    maps_categories TEXT[],
    discovery_mode TEXT DEFAULT 'both' CHECK (discovery_mode IN ('abn_first', 'maps_first', 'both')),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_industry_keywords_slug ON industry_keywords(industry_slug);

-- 2. Location Suburbs Table
CREATE TABLE location_suburbs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    suburb TEXT NOT NULL,
    postcode TEXT,
    latitude DECIMAL,
    longitude DECIMAL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(city, state, suburb)
);

CREATE INDEX idx_location_suburbs_city_state ON location_suburbs(city, state);

-- 3. Discovery Queries Table
CREATE TABLE discovery_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    mode TEXT NOT NULL CHECK (mode IN ('abn', 'maps', 'parallel')),
    query_type TEXT NOT NULL CHECK (query_type IN ('abn_search', 'maps_serp')),
    query_params JSONB NOT NULL,
    results_count INT,
    cost_aud DECIMAL(10,4),
    executed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_discovery_queries_campaign ON discovery_queries(campaign_id);

-- 4. Discovery Results Table
CREATE TABLE discovery_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    query_id UUID REFERENCES discovery_queries(id) ON DELETE SET NULL,
    abn TEXT,
    business_name TEXT NOT NULL,
    trading_name TEXT,
    source TEXT NOT NULL CHECK (source IN ('abn_api', 'maps_serp')),
    raw_data JSONB NOT NULL,
    dedup_hash TEXT NOT NULL,
    passed_filters BOOLEAN DEFAULT true,
    filter_reason TEXT,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(campaign_id, dedup_hash)
);

CREATE INDEX idx_discovery_results_campaign ON discovery_results(campaign_id);
CREATE INDEX idx_discovery_results_abn ON discovery_results(abn) WHERE abn IS NOT NULL;
CREATE INDEX idx_discovery_results_dedup ON discovery_results(dedup_hash);

-- ================================
-- SEED DATA - INDUSTRY KEYWORDS
-- ================================

INSERT INTO industry_keywords (industry_slug, industry_label, keywords, maps_categories, discovery_mode) VALUES
('marketing_agency', 'Marketing Agency', 
 ARRAY['marketing', 'advertising', 'digital media', 'SEO', 'social media marketing', 'creative agency', 'media buying', 'PR agency', 'branding agency', 'content marketing'],
 ARRAY['marketing agency', 'advertising agency', 'digital marketing'],
 'both'),

('plumber', 'Plumber',
 ARRAY['plumbing', 'plumber', 'drainage', 'gas fitting', 'hot water', 'pipe relining', 'blocked drain'],
 ARRAY['plumber', 'plumbing service'],
 'maps_first'),

('electrician', 'Electrician',
 ARRAY['electrical', 'electrician', 'electrical contractor', 'lighting', 'rewiring', 'switchboard'],
 ARRAY['electrician', 'electrical contractor'],
 'maps_first'),

('accountant', 'Accountant',
 ARRAY['accounting', 'accountant', 'bookkeeping', 'tax agent', 'BAS agent', 'financial services', 'CPA', 'chartered accountant'],
 ARRAY['accountant', 'accounting firm', 'tax consultant'],
 'both'),

('lawyer', 'Lawyer',
 ARRAY['legal', 'lawyer', 'solicitor', 'barrister', 'law firm', 'attorney', 'legal services'],
 ARRAY['lawyer', 'law firm', 'legal services'],
 'abn_first'),

('dentist', 'Dentist',
 ARRAY['dental', 'dentist', 'dentistry', 'dental clinic', 'orthodontist', 'dental surgery'],
 ARRAY['dentist', 'dental clinic'],
 'maps_first'),

('real_estate', 'Real Estate Agent',
 ARRAY['real estate', 'property', 'real estate agent', 'property management', 'realestate'],
 ARRAY['real estate agency', 'real estate agent'],
 'both'),

('mortgage_broker', 'Mortgage Broker',
 ARRAY['mortgage', 'mortgage broker', 'home loan', 'finance broker', 'lending'],
 ARRAY['mortgage broker', 'loan service'],
 'abn_first'),

('financial_advisor', 'Financial Advisor',
 ARRAY['financial advisor', 'financial planner', 'wealth management', 'investment advisor', 'SMSF'],
 ARRAY['financial planner', 'financial consultant'],
 'abn_first'),

('it_msp', 'IT / MSP',
 ARRAY['IT services', 'managed services', 'IT support', 'computer services', 'technology services', 'MSP', 'IT consulting'],
 ARRAY['IT services', 'computer support', 'managed IT services'],
 'both'),

('recruitment', 'Recruitment Agency',
 ARRAY['recruitment', 'staffing', 'employment agency', 'job placement', 'HR services', 'talent acquisition'],
 ARRAY['employment agency', 'staffing agency'],
 'abn_first'),

('architect', 'Architect',
 ARRAY['architect', 'architecture', 'architectural', 'building design', 'architectural services'],
 ARRAY['architect', 'architecture firm'],
 'both'),

('physiotherapist', 'Physiotherapist',
 ARRAY['physiotherapy', 'physio', 'physiotherapist', 'physical therapy', 'sports physio'],
 ARRAY['physiotherapist', 'physical therapy'],
 'maps_first'),

('chiropractor', 'Chiropractor',
 ARRAY['chiropractic', 'chiropractor', 'spinal', 'back pain'],
 ARRAY['chiropractor', 'chiropractic clinic'],
 'maps_first'),

('veterinarian', 'Veterinarian',
 ARRAY['veterinary', 'vet', 'veterinarian', 'animal hospital', 'pet clinic'],
 ARRAY['veterinarian', 'animal hospital', 'pet clinic'],
 'maps_first'),

('auto_mechanic', 'Auto Mechanic',
 ARRAY['mechanic', 'auto repair', 'car service', 'automotive', 'motor mechanic'],
 ARRAY['auto repair', 'car repair', 'mechanic'],
 'maps_first'),

('landscaper', 'Landscaper',
 ARRAY['landscaping', 'landscaper', 'garden', 'lawn', 'horticulture'],
 ARRAY['landscaper', 'landscaping company'],
 'maps_first'),

('builder', 'Builder',
 ARRAY['builder', 'construction', 'building', 'home builder', 'residential construction', 'commercial builder'],
 ARRAY['general contractor', 'home builder', 'construction company'],
 'both'),

('insurance_broker', 'Insurance Broker',
 ARRAY['insurance', 'insurance broker', 'insurance agent', 'risk management'],
 ARRAY['insurance agency', 'insurance broker'],
 'abn_first'),

('freight_logistics', 'Freight & Logistics',
 ARRAY['freight', 'logistics', 'transport', 'shipping', 'courier', 'trucking', 'warehousing'],
 ARRAY['freight service', 'logistics company', 'trucking company'],
 'abn_first');

-- ================================
-- SEED DATA - LOCATION SUBURBS
-- ================================

-- Sydney, NSW (30 suburbs)
INSERT INTO location_suburbs (city, state, suburb) VALUES
('Sydney', 'NSW', 'Sydney CBD'),
('Sydney', 'NSW', 'Parramatta'),
('Sydney', 'NSW', 'Chatswood'),
('Sydney', 'NSW', 'North Sydney'),
('Sydney', 'NSW', 'Bondi'),
('Sydney', 'NSW', 'Surry Hills'),
('Sydney', 'NSW', 'Newtown'),
('Sydney', 'NSW', 'Manly'),
('Sydney', 'NSW', 'Randwick'),
('Sydney', 'NSW', 'Liverpool'),
('Sydney', 'NSW', 'Blacktown'),
('Sydney', 'NSW', 'Penrith'),
('Sydney', 'NSW', 'Cronulla'),
('Sydney', 'NSW', 'Bankstown'),
('Sydney', 'NSW', 'Hornsby'),
('Sydney', 'NSW', 'Castle Hill'),
('Sydney', 'NSW', 'Campbelltown'),
('Sydney', 'NSW', 'Hurstville'),
('Sydney', 'NSW', 'Dee Why'),
('Sydney', 'NSW', 'Brookvale'),
('Sydney', 'NSW', 'Mosman'),
('Sydney', 'NSW', 'Double Bay'),
('Sydney', 'NSW', 'Pyrmont'),
('Sydney', 'NSW', 'Alexandria'),
('Sydney', 'NSW', 'Mascot'),
('Sydney', 'NSW', 'Ryde'),
('Sydney', 'NSW', 'Epping'),
('Sydney', 'NSW', 'Miranda'),
('Sydney', 'NSW', 'Eastwood'),
('Sydney', 'NSW', 'Leichhardt');

-- Melbourne, VIC (30 suburbs)
INSERT INTO location_suburbs (city, state, suburb) VALUES
('Melbourne', 'VIC', 'Melbourne CBD'),
('Melbourne', 'VIC', 'South Yarra'),
('Melbourne', 'VIC', 'Richmond'),
('Melbourne', 'VIC', 'St Kilda'),
('Melbourne', 'VIC', 'Fitzroy'),
('Melbourne', 'VIC', 'Collingwood'),
('Melbourne', 'VIC', 'Brunswick'),
('Melbourne', 'VIC', 'Carlton'),
('Melbourne', 'VIC', 'Prahran'),
('Melbourne', 'VIC', 'Hawthorn'),
('Melbourne', 'VIC', 'Box Hill'),
('Melbourne', 'VIC', 'Dandenong'),
('Melbourne', 'VIC', 'Frankston'),
('Melbourne', 'VIC', 'Moonee Ponds'),
('Melbourne', 'VIC', 'Footscray'),
('Melbourne', 'VIC', 'Doncaster'),
('Melbourne', 'VIC', 'Glen Waverley'),
('Melbourne', 'VIC', 'Chadstone'),
('Melbourne', 'VIC', 'Brighton'),
('Melbourne', 'VIC', 'Toorak'),
('Melbourne', 'VIC', 'Malvern'),
('Melbourne', 'VIC', 'Camberwell'),
('Melbourne', 'VIC', 'Preston'),
('Melbourne', 'VIC', 'Northcote'),
('Melbourne', 'VIC', 'Coburg'),
('Melbourne', 'VIC', 'Essendon'),
('Melbourne', 'VIC', 'Williamstown'),
('Melbourne', 'VIC', 'Port Melbourne'),
('Melbourne', 'VIC', 'South Melbourne'),
('Melbourne', 'VIC', 'Abbotsford');

-- Brisbane, QLD (30 suburbs)
INSERT INTO location_suburbs (city, state, suburb) VALUES
('Brisbane', 'QLD', 'Brisbane CBD'),
('Brisbane', 'QLD', 'South Brisbane'),
('Brisbane', 'QLD', 'Fortitude Valley'),
('Brisbane', 'QLD', 'West End'),
('Brisbane', 'QLD', 'New Farm'),
('Brisbane', 'QLD', 'Paddington'),
('Brisbane', 'QLD', 'Milton'),
('Brisbane', 'QLD', 'Toowong'),
('Brisbane', 'QLD', 'Indooroopilly'),
('Brisbane', 'QLD', 'Chermside'),
('Brisbane', 'QLD', 'Carindale'),
('Brisbane', 'QLD', 'Mt Gravatt'),
('Brisbane', 'QLD', 'Sunnybank'),
('Brisbane', 'QLD', 'Garden City'),
('Brisbane', 'QLD', 'Upper Mt Gravatt'),
('Brisbane', 'QLD', 'Woolloongabba'),
('Brisbane', 'QLD', 'Kangaroo Point'),
('Brisbane', 'QLD', 'Spring Hill'),
('Brisbane', 'QLD', 'Newstead'),
('Brisbane', 'QLD', 'Teneriffe'),
('Brisbane', 'QLD', 'Bulimba'),
('Brisbane', 'QLD', 'Hawthorne'),
('Brisbane', 'QLD', 'Ashgrove'),
('Brisbane', 'QLD', 'Clayfield'),
('Brisbane', 'QLD', 'Nundah'),
('Brisbane', 'QLD', 'Stafford'),
('Brisbane', 'QLD', 'Kedron'),
('Brisbane', 'QLD', 'Windsor'),
('Brisbane', 'QLD', 'Albion'),
('Brisbane', 'QLD', 'Bowen Hills');

-- Perth, WA (30 suburbs)
INSERT INTO location_suburbs (city, state, suburb) VALUES
('Perth', 'WA', 'Perth CBD'),
('Perth', 'WA', 'Subiaco'),
('Perth', 'WA', 'Fremantle'),
('Perth', 'WA', 'Joondalup'),
('Perth', 'WA', 'Rockingham'),
('Perth', 'WA', 'Midland'),
('Perth', 'WA', 'Morley'),
('Perth', 'WA', 'Cannington'),
('Perth', 'WA', 'Victoria Park'),
('Perth', 'WA', 'Leederville'),
('Perth', 'WA', 'Mount Lawley'),
('Perth', 'WA', 'Northbridge'),
('Perth', 'WA', 'West Perth'),
('Perth', 'WA', 'East Perth'),
('Perth', 'WA', 'South Perth'),
('Perth', 'WA', 'Como'),
('Perth', 'WA', 'Claremont'),
('Perth', 'WA', 'Cottesloe'),
('Perth', 'WA', 'Scarborough'),
('Perth', 'WA', 'Innaloo'),
('Perth', 'WA', 'Osborne Park'),
('Perth', 'WA', 'Balcatta'),
('Perth', 'WA', 'Stirling'),
('Perth', 'WA', 'Belmont'),
('Perth', 'WA', 'Welshpool'),
('Perth', 'WA', 'Malaga'),
('Perth', 'WA', 'Wanneroo'),
('Perth', 'WA', 'Ellenbrook'),
('Perth', 'WA', 'Armadale'),
('Perth', 'WA', 'Mandurah');

-- Adelaide, SA (30 suburbs)
INSERT INTO location_suburbs (city, state, suburb) VALUES
('Adelaide', 'SA', 'Adelaide CBD'),
('Adelaide', 'SA', 'North Adelaide'),
('Adelaide', 'SA', 'Glenelg'),
('Adelaide', 'SA', 'Norwood'),
('Adelaide', 'SA', 'Unley'),
('Adelaide', 'SA', 'Prospect'),
('Adelaide', 'SA', 'Hindmarsh'),
('Adelaide', 'SA', 'Thebarton'),
('Adelaide', 'SA', 'Mile End'),
('Adelaide', 'SA', 'Parkside'),
('Adelaide', 'SA', 'Burnside'),
('Adelaide', 'SA', 'Magill'),
('Adelaide', 'SA', 'Marion'),
('Adelaide', 'SA', 'Morphett Vale'),
('Adelaide', 'SA', 'Modbury'),
('Adelaide', 'SA', 'Tea Tree Gully'),
('Adelaide', 'SA', 'Elizabeth'),
('Adelaide', 'SA', 'Salisbury'),
('Adelaide', 'SA', 'Port Adelaide'),
('Adelaide', 'SA', 'Semaphore'),
('Adelaide', 'SA', 'Henley Beach'),
('Adelaide', 'SA', 'West Lakes'),
('Adelaide', 'SA', 'Fulham'),
('Adelaide', 'SA', 'Grange'),
('Adelaide', 'SA', 'Woodville'),
('Adelaide', 'SA', 'Findon'),
('Adelaide', 'SA', 'Kilkenny'),
('Adelaide', 'SA', 'Kensington'),
('Adelaide', 'SA', 'Kent Town'),
('Adelaide', 'SA', 'Stepney');