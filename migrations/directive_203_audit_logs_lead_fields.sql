-- FILE: migrations/directive_203_audit_logs_lead_fields.sql
-- PURPOSE: Add lead_company and domain columns to audit_logs
-- DIRECTIVE: #203
-- DATE: 2026-03-17

ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS lead_company TEXT,
    ADD COLUMN IF NOT EXISTS domain TEXT;
