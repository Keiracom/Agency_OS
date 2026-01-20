-- Migration: 040_drop_ab_testing.sql
-- Phase: SDK/Content Architecture Refactor
-- Purpose: Remove A/B testing tables and related objects (no longer needed with SDK-generated content)
-- Date: 2026-01-20
-- Reason: SDK generates unique emails per lead, making traditional A/B testing moot.
--         Future optimization will use "strategy testing" (angles, tones) if needed.

-- ============================================================================
-- 1. DROP TRIGGERS
-- ============================================================================

DROP TRIGGER IF EXISTS on_activity_ab_test_insert ON activities;
DROP TRIGGER IF EXISTS on_reply_ab_test_success ON replies;

-- ============================================================================
-- 2. DROP FUNCTIONS
-- ============================================================================

DROP FUNCTION IF EXISTS update_ab_test_variant_stats();
DROP FUNCTION IF EXISTS update_ab_test_success_on_reply();
DROP FUNCTION IF EXISTS calculate_ab_test_winner(UUID);

-- ============================================================================
-- 3. DROP INDEXES ON ACTIVITIES
-- ============================================================================

DROP INDEX IF EXISTS idx_activities_ab_test_id;
DROP INDEX IF EXISTS idx_activities_ab_variant;

-- ============================================================================
-- 4. DROP FOREIGN KEY CONSTRAINT ON ACTIVITIES
-- ============================================================================

ALTER TABLE activities DROP CONSTRAINT IF EXISTS fk_activities_ab_test;

-- ============================================================================
-- 5. KEEP COLUMNS ON ACTIVITIES FOR TRACKING
-- ============================================================================
-- NOTE: We keep ab_test_id and ab_variant on activities because:
--   1. They're used for content tracking/analytics (Phase 24B)
--   2. They could be repurposed for "strategy testing" in the future
--   3. They're just nullable fields that don't break anything
--
-- DO NOT drop: ab_test_id, ab_variant columns from activities table

-- ============================================================================
-- 6. DROP RLS POLICIES
-- ============================================================================

DROP POLICY IF EXISTS ab_tests_client_isolation ON ab_tests;
DROP POLICY IF EXISTS ab_test_variants_client_isolation ON ab_test_variants;

-- ============================================================================
-- 7. DROP INDEXES ON AB_TESTS AND AB_TEST_VARIANTS
-- ============================================================================

DROP INDEX IF EXISTS idx_ab_tests_client_id;
DROP INDEX IF EXISTS idx_ab_tests_campaign_id;
DROP INDEX IF EXISTS idx_ab_tests_status;
DROP INDEX IF EXISTS idx_ab_test_variants_test_id;

-- ============================================================================
-- 8. DROP TABLES (variants first due to FK)
-- ============================================================================

DROP TABLE IF EXISTS ab_test_variants;
DROP TABLE IF EXISTS ab_tests;

-- ============================================================================
-- COMPLETE
-- ============================================================================
