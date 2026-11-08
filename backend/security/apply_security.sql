-- M1.4 PREPARATION ONLY. Requires a separate, explicit execution approval.
-- Administrator-owned transaction; no passwords, role activation or destructive recovery.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $preflight$
DECLARE
    expected_tables text[] := ARRAY[
        'alembic_version', 'audit_events', 'customers', 'orders', 'shipment_events'
    ];
    actual_tables text[];
BEGIN
    IF current_database() <> 'nexus_ai'
       OR current_setting('server_version_num')::integer / 10000 <> 16
       OR session_user <> 'postgres' OR current_user <> 'postgres'
       OR NOT (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) THEN
        RAISE EXCEPTION 'M1.4 requires the approved PostgreSQL 16 nexus_ai bootstrap administrator';
    END IF;
    IF (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database()) <> 'postgres' THEN
        RAISE EXCEPTION 'Unexpected database owner; stop without changing state';
    END IF;
    IF (SELECT datacl FROM pg_database WHERE datname = current_database()) IS NOT NULL THEN
        RAISE EXCEPTION 'Unexpected pre-existing database ACL; review before deployment';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('nexus_owner', 'nexus_app', 'nexus_tool')) THEN
        RAISE EXCEPTION 'A designated role already exists; do not reuse or alter it';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_namespace
        WHERE nspname NOT LIKE 'pg_%' AND nspname NOT IN ('public', 'information_schema')
    ) OR EXISTS (SELECT 1 FROM pg_default_acl) THEN
        RAISE EXCEPTION 'Unexpected schema/default privileges; review before deployment';
    END IF;
    SELECT array_agg(c.relname::text ORDER BY c.relname) INTO actual_tables
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p');
    IF actual_tables IS DISTINCT FROM expected_tables THEN
        RAISE EXCEPTION 'The exact frozen initial schema must be applied first';
    END IF;
    IF ARRAY(
        SELECT c.relname::text FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' ORDER BY c.relname
    ) IS DISTINCT FROM ARRAY(
        SELECT value FROM unnest(ARRAY[
            'alembic_version', 'audit_events', 'customers', 'orders', 'shipment_events',
            'audit_events_id_seq', 'pk_customers', 'pk_orders', 'pk_shipment_events',
            'pk_audit_events', 'alembic_version_pkc', 'customers_email_lower_uidx',
            'customers_name_lower_idx', 'orders_pending_idx', 'orders_overdue_idx',
            'orders_customer_created_idx', 'shipment_events_order_occurred_idx',
            'audit_events_request_idx', 'audit_events_created_idx'
        ]) AS names(value) ORDER BY value
    ) THEN
        RAISE EXCEPTION 'Unexpected public relations; refuse normalization or cleanup';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_namespace n
        WHERE n.nspname = 'public' AND
        (pg_get_userbyid(n.nspowner) NOT IN ('pg_database_owner', 'postgres')
         OR EXISTS (
             SELECT 1 FROM aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
             WHERE a.grantee NOT IN (0, n.nspowner)
                OR (a.grantee = 0 AND (a.privilege_type <> 'USAGE' OR a.is_grantable))
         ))
    ) THEN
        RAISE EXCEPTION 'Unexpected public schema owner or privileges';
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND
        (c.relkind NOT IN ('r', 'i', 'S') OR pg_get_userbyid(c.relowner) <> 'postgres'
         OR c.relacl IS NOT NULL OR c.relrowsecurity OR c.relforcerowsecurity)
    ) OR EXISTS (
        SELECT 1 FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND a.attacl IS NOT NULL
    ) OR EXISTS (SELECT 1 FROM pg_proc WHERE pronamespace = 'public'::regnamespace) THEN
        RAISE EXCEPTION 'Unexpected public object ownership, ACL, RLS or function';
    END IF;
    IF (SELECT count(*) FROM public.alembic_version) <> 1
       OR (SELECT version_num FROM public.alembic_version) <> '0001_initial_schema' THEN
        RAISE EXCEPTION 'Unexpected initial migration state';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.customers UNION ALL SELECT 1 FROM public.orders
        UNION ALL SELECT 1 FROM public.shipment_events UNION ALL SELECT 1 FROM public.audit_events
    ) THEN
        RAISE EXCEPTION 'Initial security deployment requires empty application tables';
    END IF;
END
$preflight$;

CREATE ROLE nexus_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOINHERIT NOREPLICATION NOBYPASSRLS;
CREATE ROLE nexus_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOINHERIT NOREPLICATION NOBYPASSRLS;
CREATE ROLE nexus_tool NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOINHERIT NOREPLICATION NOBYPASSRLS;

-- Scope is this database. PUBLIC privileges in other databases are unchanged.
REVOKE ALL PRIVILEGES ON DATABASE nexus_ai FROM PUBLIC, nexus_app, nexus_tool;
GRANT CONNECT ON DATABASE nexus_ai TO nexus_owner, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES ON SCHEMA public FROM PUBLIC, nexus_app, nexus_tool;
ALTER SCHEMA public OWNER TO nexus_owner;
GRANT USAGE ON SCHEMA public TO nexus_app, nexus_tool;

ALTER TABLE public.customers OWNER TO nexus_owner;
ALTER TABLE public.orders OWNER TO nexus_owner;
ALTER TABLE public.shipment_events OWNER TO nexus_owner;
-- PostgreSQL transfers the table-owned identity sequence with its table.
ALTER TABLE public.audit_events OWNER TO nexus_owner;
ALTER TABLE public.alembic_version OWNER TO nexus_owner;

-- Global means all schemas FOR THIS CREATING ROLE IN THIS DATABASE.
-- A per-schema revoke alone cannot subtract global default PUBLIC EXECUTE.
ALTER DEFAULT PRIVILEGES FOR ROLE nexus_owner
    REVOKE ALL PRIVILEGES ON TABLES FROM PUBLIC, nexus_app, nexus_tool;
ALTER DEFAULT PRIVILEGES FOR ROLE nexus_owner
    REVOKE ALL PRIVILEGES ON SEQUENCES FROM PUBLIC, nexus_app, nexus_tool;
ALTER DEFAULT PRIVILEGES FOR ROLE nexus_owner
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, nexus_app, nexus_tool;

SET LOCAL ROLE nexus_owner;
SET LOCAL search_path = pg_catalog, public;
CREATE VIEW public.v_customers WITH (security_invoker = false) AS
    SELECT id, name, email FROM public.customers;
CREATE VIEW public.v_orders WITH (security_invoker = false) AS
    SELECT id, customer_id, status, created_at, expected_delivery_at FROM public.orders;
CREATE VIEW public.v_shipment_events WITH (security_invoker = false) AS
    SELECT id, order_id, event_type, occurred_at FROM public.shipment_events;
RESET ROLE;

-- Whole-table revocation does not remove separate column ACLs, hence both.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES (id, name, email, created_at) ON TABLE public.customers
    FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES (id, customer_id, status, created_at, expected_delivery_at)
    ON TABLE public.orders FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES (id, order_id, event_type, occurred_at) ON TABLE public.shipment_events
    FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES (
    id, request_id, event_type, actor_id, tool_name, args_hash, decision,
    row_count, latency_ms, model, error_code, created_at
) ON TABLE public.audit_events FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES (version_num) ON TABLE public.alembic_version
    FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES (id, name, email) ON TABLE public.v_customers
    FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES (id, customer_id, status, created_at, expected_delivery_at)
    ON TABLE public.v_orders FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES (id, order_id, event_type, occurred_at) ON TABLE public.v_shipment_events
    FROM PUBLIC, nexus_app, nexus_tool;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC, nexus_app, nexus_tool;

GRANT SELECT ON public.v_customers, public.v_orders, public.v_shipment_events TO nexus_tool;
-- Deliberately excludes generated id; no SELECT/RETURNING or sequence ACL.
GRANT INSERT (
    request_id, event_type, actor_id, tool_name, args_hash, decision,
    row_count, latency_ms, model, error_code, created_at
) ON public.audit_events TO nexus_app;

ALTER ROLE nexus_app IN DATABASE nexus_ai SET search_path = pg_catalog, public;
ALTER ROLE nexus_tool IN DATABASE nexus_ai SET search_path = pg_catalog, public;

DO $postflight$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname IN ('nexus_owner', 'nexus_app', 'nexus_tool')
        AND (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole OR rolinherit
             OR rolreplication OR rolbypassrls)
    ) OR EXISTS (
        SELECT 1 FROM pg_auth_members m
        WHERE m.roleid IN (SELECT oid FROM pg_roles WHERE rolname IN ('nexus_owner', 'nexus_app', 'nexus_tool'))
           OR m.member IN (SELECT oid FROM pg_roles WHERE rolname IN ('nexus_owner', 'nexus_app', 'nexus_tool'))
    ) THEN
        RAISE EXCEPTION 'Roles must remain disabled/unprivileged with no memberships';
    END IF;
    IF pg_get_userbyid((SELECT relowner FROM pg_class WHERE oid = 'public.audit_events_id_seq'::regclass)) <> 'nexus_owner' THEN
        RAISE EXCEPTION 'Identity sequence ownership did not follow table ownership';
    END IF;
END
$postflight$;

-- Runtime LOGIN/passwords are a separately approved, guarded stage. No activation here.
COMMIT;
