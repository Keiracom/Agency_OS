-- Migration 074: Create location_suburbs table with seed data
-- Bug #22 fix: LocationExpander requires this table for suburb-based GMB discovery
-- CEO Directive #110

-- =====================================================
-- CREATE TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS location_suburbs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    suburb TEXT NOT NULL,
    postcode TEXT,
    priority INTEGER DEFAULT 50,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(city, state, suburb)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_location_suburbs_city_state ON location_suburbs(city, state);
CREATE INDEX IF NOT EXISTS idx_location_suburbs_state ON location_suburbs(state);

-- =====================================================
-- SEED DATA: Australian Metropolitan Suburbs
-- Priority 1-100: Higher = more business density, query first
-- =====================================================

-- MELBOURNE, VIC (25 suburbs)
INSERT INTO location_suburbs (city, state, suburb, postcode, priority) VALUES
('Melbourne', 'VIC', 'Melbourne CBD', '3000', 100),
('Melbourne', 'VIC', 'South Melbourne', '3205', 90),
('Melbourne', 'VIC', 'Richmond', '3121', 85),
('Melbourne', 'VIC', 'Fitzroy', '3065', 85),
('Melbourne', 'VIC', 'Collingwood', '3066', 80),
('Melbourne', 'VIC', 'South Yarra', '3141', 80),
('Melbourne', 'VIC', 'Prahran', '3181', 75),
('Melbourne', 'VIC', 'St Kilda', '3182', 75),
('Melbourne', 'VIC', 'Carlton', '3053', 70),
('Melbourne', 'VIC', 'Brunswick', '3056', 70),
('Melbourne', 'VIC', 'Hawthorn', '3122', 65),
('Melbourne', 'VIC', 'Cremorne', '3121', 65),
('Melbourne', 'VIC', 'Port Melbourne', '3207', 60),
('Melbourne', 'VIC', 'Docklands', '3008', 60),
('Melbourne', 'VIC', 'Southbank', '3006', 55),
('Melbourne', 'VIC', 'Abbotsford', '3067', 55),
('Melbourne', 'VIC', 'North Melbourne', '3051', 50),
('Melbourne', 'VIC', 'West Melbourne', '3003', 50),
('Melbourne', 'VIC', 'Albert Park', '3206', 45),
('Melbourne', 'VIC', 'Toorak', '3142', 45),
('Melbourne', 'VIC', 'Malvern', '3144', 40),
('Melbourne', 'VIC', 'Camberwell', '3124', 40),
('Melbourne', 'VIC', 'Box Hill', '3128', 35),
('Melbourne', 'VIC', 'Glen Waverley', '3150', 30),
('Melbourne', 'VIC', 'Dandenong', '3175', 25)
ON CONFLICT (city, state, suburb) DO NOTHING;

-- SYDNEY, NSW (25 suburbs)
INSERT INTO location_suburbs (city, state, suburb, postcode, priority) VALUES
('Sydney', 'NSW', 'Sydney CBD', '2000', 100),
('Sydney', 'NSW', 'Surry Hills', '2010', 90),
('Sydney', 'NSW', 'Pyrmont', '2009', 85),
('Sydney', 'NSW', 'Ultimo', '2007', 80),
('Sydney', 'NSW', 'Darlinghurst', '2010', 80),
('Sydney', 'NSW', 'Newtown', '2042', 75),
('Sydney', 'NSW', 'Bondi', '2026', 75),
('Sydney', 'NSW', 'Paddington', '2021', 70),
('Sydney', 'NSW', 'Redfern', '2016', 70),
('Sydney', 'NSW', 'Alexandria', '2015', 65),
('Sydney', 'NSW', 'Chippendale', '2008', 65),
('Sydney', 'NSW', 'Glebe', '2037', 60),
('Sydney', 'NSW', 'North Sydney', '2060', 60),
('Sydney', 'NSW', 'Crows Nest', '2065', 55),
('Sydney', 'NSW', 'Manly', '2095', 55),
('Sydney', 'NSW', 'Potts Point', '2011', 50),
('Sydney', 'NSW', 'Waterloo', '2017', 50),
('Sydney', 'NSW', 'Marrickville', '2204', 45),
('Sydney', 'NSW', 'Chatswood', '2067', 45),
('Sydney', 'NSW', 'Parramatta', '2150', 40),
('Sydney', 'NSW', 'Mascot', '2020', 40),
('Sydney', 'NSW', 'Mosman', '2088', 35),
('Sydney', 'NSW', 'Double Bay', '2028', 35),
('Sydney', 'NSW', 'Neutral Bay', '2089', 30),
('Sydney', 'NSW', 'Barangaroo', '2000', 30)
ON CONFLICT (city, state, suburb) DO NOTHING;

-- BRISBANE, QLD (20 suburbs)
INSERT INTO location_suburbs (city, state, suburb, postcode, priority) VALUES
('Brisbane', 'QLD', 'Brisbane CBD', '4000', 100),
('Brisbane', 'QLD', 'Fortitude Valley', '4006', 90),
('Brisbane', 'QLD', 'South Brisbane', '4101', 85),
('Brisbane', 'QLD', 'West End', '4101', 80),
('Brisbane', 'QLD', 'Newstead', '4006', 80),
('Brisbane', 'QLD', 'Milton', '4064', 75),
('Brisbane', 'QLD', 'Spring Hill', '4000', 70),
('Brisbane', 'QLD', 'Paddington', '4064', 65),
('Brisbane', 'QLD', 'Kangaroo Point', '4169', 60),
('Brisbane', 'QLD', 'Woolloongabba', '4102', 55),
('Brisbane', 'QLD', 'New Farm', '4005', 55),
('Brisbane', 'QLD', 'Toowong', '4066', 50),
('Brisbane', 'QLD', 'Indooroopilly', '4068', 45),
('Brisbane', 'QLD', 'Albion', '4010', 45),
('Brisbane', 'QLD', 'Bowen Hills', '4006', 40),
('Brisbane', 'QLD', 'Ascot', '4007', 35),
('Brisbane', 'QLD', 'Hamilton', '4007', 35),
('Brisbane', 'QLD', 'Bulimba', '4171', 30),
('Brisbane', 'QLD', 'Chermside', '4032', 25),
('Brisbane', 'QLD', 'Carindale', '4152', 20)
ON CONFLICT (city, state, suburb) DO NOTHING;

-- PERTH, WA (18 suburbs)
INSERT INTO location_suburbs (city, state, suburb, postcode, priority) VALUES
('Perth', 'WA', 'Perth CBD', '6000', 100),
('Perth', 'WA', 'West Perth', '6005', 90),
('Perth', 'WA', 'Subiaco', '6008', 85),
('Perth', 'WA', 'Leederville', '6007', 80),
('Perth', 'WA', 'Northbridge', '6003', 75),
('Perth', 'WA', 'East Perth', '6004', 70),
('Perth', 'WA', 'South Perth', '6151', 65),
('Perth', 'WA', 'Victoria Park', '6100', 60),
('Perth', 'WA', 'Fremantle', '6160', 55),
('Perth', 'WA', 'Claremont', '6010', 50),
('Perth', 'WA', 'Mount Lawley', '6050', 50),
('Perth', 'WA', 'Nedlands', '6009', 45),
('Perth', 'WA', 'Cottesloe', '6011', 40),
('Perth', 'WA', 'Osborne Park', '6017', 40),
('Perth', 'WA', 'Joondalup', '6027', 35),
('Perth', 'WA', 'Burswood', '6100', 30),
('Perth', 'WA', 'Cannington', '6107', 25),
('Perth', 'WA', 'Morley', '6062', 20)
ON CONFLICT (city, state, suburb) DO NOTHING;

-- ADELAIDE, SA (15 suburbs)
INSERT INTO location_suburbs (city, state, suburb, postcode, priority) VALUES
('Adelaide', 'SA', 'Adelaide CBD', '5000', 100),
('Adelaide', 'SA', 'North Adelaide', '5006', 90),
('Adelaide', 'SA', 'Kent Town', '5067', 80),
('Adelaide', 'SA', 'Norwood', '5067', 75),
('Adelaide', 'SA', 'Unley', '5061', 70),
('Adelaide', 'SA', 'Glenelg', '5045', 65),
('Adelaide', 'SA', 'Prospect', '5082', 60),
('Adelaide', 'SA', 'Hindmarsh', '5007', 55),
('Adelaide', 'SA', 'Mile End', '5031', 50),
('Adelaide', 'SA', 'Parkside', '5063', 45),
('Adelaide', 'SA', 'Fullarton', '5063', 40),
('Adelaide', 'SA', 'Burnside', '5066', 35),
('Adelaide', 'SA', 'Marion', '5043', 30),
('Adelaide', 'SA', 'Port Adelaide', '5015', 25),
('Adelaide', 'SA', 'Mawson Lakes', '5095', 20)
ON CONFLICT (city, state, suburb) DO NOTHING;

-- GOLD COAST, QLD (10 suburbs)
INSERT INTO location_suburbs (city, state, suburb, postcode, priority) VALUES
('Gold Coast', 'QLD', 'Surfers Paradise', '4217', 100),
('Gold Coast', 'QLD', 'Broadbeach', '4218', 85),
('Gold Coast', 'QLD', 'Southport', '4215', 80),
('Gold Coast', 'QLD', 'Bundall', '4217', 70),
('Gold Coast', 'QLD', 'Burleigh Heads', '4220', 60),
('Gold Coast', 'QLD', 'Robina', '4226', 55),
('Gold Coast', 'QLD', 'Main Beach', '4217', 50),
('Gold Coast', 'QLD', 'Coolangatta', '4225', 40),
('Gold Coast', 'QLD', 'Nerang', '4211', 30),
('Gold Coast', 'QLD', 'Helensvale', '4212', 25)
ON CONFLICT (city, state, suburb) DO NOTHING;

-- CANBERRA, ACT (8 suburbs)
INSERT INTO location_suburbs (city, state, suburb, postcode, priority) VALUES
('Canberra', 'ACT', 'Canberra City', '2601', 100),
('Canberra', 'ACT', 'Braddon', '2612', 85),
('Canberra', 'ACT', 'Kingston', '2604', 70),
('Canberra', 'ACT', 'Manuka', '2603', 60),
('Canberra', 'ACT', 'Barton', '2600', 55),
('Canberra', 'ACT', 'Fyshwick', '2609', 45),
('Canberra', 'ACT', 'Belconnen', '2617', 35),
('Canberra', 'ACT', 'Woden', '2606', 30)
ON CONFLICT (city, state, suburb) DO NOTHING;

-- NEWCASTLE, NSW (8 suburbs)
INSERT INTO location_suburbs (city, state, suburb, postcode, priority) VALUES
('Newcastle', 'NSW', 'Newcastle CBD', '2300', 100),
('Newcastle', 'NSW', 'Newcastle West', '2302', 80),
('Newcastle', 'NSW', 'Hamilton', '2303', 65),
('Newcastle', 'NSW', 'Charlestown', '2290', 55),
('Newcastle', 'NSW', 'Mayfield', '2304', 45),
('Newcastle', 'NSW', 'Lambton', '2299', 35),
('Newcastle', 'NSW', 'Adamstown', '2289', 30),
('Newcastle', 'NSW', 'Maitland', '2320', 25)
ON CONFLICT (city, state, suburb) DO NOTHING;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE location_suburbs IS 'Lookup table for city-to-suburb expansion used by LocationExpander in discovery pipeline';
COMMENT ON COLUMN location_suburbs.city IS 'City name (e.g., Melbourne, Sydney)';
COMMENT ON COLUMN location_suburbs.state IS 'Australian state code (VIC, NSW, QLD, WA, SA, TAS, NT, ACT)';
COMMENT ON COLUMN location_suburbs.suburb IS 'Suburb name for GMB discovery queries';
COMMENT ON COLUMN location_suburbs.postcode IS 'Australian postcode (optional, for reference)';
COMMENT ON COLUMN location_suburbs.priority IS 'Discovery priority 1-100: higher = more business density, query first';

-- =====================================================
-- VERIFICATION
-- =====================================================
-- [x] Table created with correct schema for LocationExpander
-- [x] Unique constraint on (city, state, suburb)
-- [x] Indexes for fast lookups
-- [x] Melbourne: 25 suburbs seeded
-- [x] Sydney: 25 suburbs seeded
-- [x] Brisbane: 20 suburbs seeded
-- [x] Perth: 18 suburbs seeded
-- [x] Adelaide: 15 suburbs seeded
-- [x] Gold Coast: 10 suburbs seeded
-- [x] Canberra: 8 suburbs seeded
-- [x] Newcastle: 8 suburbs seeded
-- [x] Priority column for query ordering
-- [x] ON CONFLICT for idempotent re-runs
