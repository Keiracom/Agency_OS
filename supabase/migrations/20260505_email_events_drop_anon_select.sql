-- 20260505_email_events_drop_anon_select.sql
-- Task #20 follow-up — drop the wide-open anon SELECT policy added by
-- 20260505_email_events.sql. Email send/delivery logs include recipient
-- addresses + subjects + delivery state; anon read access leaks PII.
--
-- Frontend reads continue via service-role through the FastAPI route
-- (`GET /api/email/status/{message_id}`), which is the intended access
-- path. RLS remains enabled on the table, so without a policy no role
-- below `bypassrls` (service_role) can read.

DROP POLICY IF EXISTS email_events_anon_select
    ON keiracom_admin.email_events;
