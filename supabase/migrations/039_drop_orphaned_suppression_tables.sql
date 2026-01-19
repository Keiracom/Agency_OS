-- Migration: 039_drop_orphaned_suppression_tables.sql
-- Purpose: Remove deprecated suppression tables superseded by suppression_list (migration 030)
-- Date: 2026-01-20
--
-- These tables were created in migration 004 but never wired into production code.
-- The suppression_list table (migration 030) is the active suppression system.
-- Audit confirmed 0 rows in all three tables.

-- ============================================
-- DROP ORPHANED TABLES
-- ============================================

-- Drop global_suppression (platform-wide email blocks - unused)
DROP TABLE IF EXISTS global_suppression CASCADE;

-- Drop client_suppression (client-specific blocks - unused, replaced by suppression_list)
DROP TABLE IF EXISTS client_suppression CASCADE;

-- Drop domain_suppression (domain-level blocks - unused)
DROP TABLE IF EXISTS domain_suppression CASCADE;

-- ============================================
-- DROP RELATED FUNCTIONS (if any)
-- ============================================

-- Drop old is_email_suppressed function from migration 004 if it exists
-- (superseded by is_suppressed function in migration 030)
DROP FUNCTION IF EXISTS is_email_suppressed(UUID, TEXT);

-- ============================================
-- VERIFICATION
-- ============================================
-- Run after migration to confirm:
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE '%suppression%';
-- Expected result: only 'suppression_list' should remain
