-- Migration: 063_campaign_status_enum.sql
-- SSOT Key: campaign_approval_flow (ID: 9470bfb5-fedc-4f7b-a8cc-4b42d7ff96db)
-- Purpose: Add PENDING_APPROVAL and APPROVED to campaign_status enum
-- Status flow: DRAFT → PENDING_APPROVAL → APPROVED → ACTIVE

-- Add new enum values (PostgreSQL allows adding values to existing enums)
ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'pending_approval' AFTER 'draft';
ALTER TYPE campaign_status ADD VALUE IF NOT EXISTS 'approved' AFTER 'pending_approval';

-- Result: draft, pending_approval, approved, active, paused, completed
