-- Read-only assertions after an independently approved security deployment.
-- Execute in a READ ONLY transaction. Missing roles/relations are a failed precondition.
WITH
runtime_roles(role_name) AS (VALUES ('nexus_app'), ('nexus_tool')),
roles(role_name) AS (VALUES ('nexus_owner'), ('nexus_app'), ('nexus_tool')),
objects(object_name, is_view) AS (VALUES
    ('customers', false), ('orders', false), ('shipment_events', false),
    ('audit_events', false), ('alembic_version', false),
    ('v_customers', true), ('v_orders', true), ('v_shipment_events', true)
),
writer_columns(column_name) AS (VALUES
    ('request_id'), ('event_type'), ('actor_id'), ('tool_name'), ('args_hash'),
    ('decision'), ('row_count'), ('latency_ms'), ('model'), ('error_code'), ('created_at')
),
view_contract(view_name, columns, definition) AS (VALUES
    ('v_customers', ARRAY['id','name','email'],
     'SELECT customers.id, customers.name, customers.email FROM public.customers;'),
    ('v_orders', ARRAY['id','customer_id','status','created_at','expected_delivery_at'],
     'SELECT orders.id, orders.customer_id, orders.status, orders.created_at, orders.expected_delivery_at FROM public.orders;'),
    ('v_shipment_events', ARRAY['id','order_id','event_type','occurred_at'],
     'SELECT shipment_events.id, shipment_events.order_id, shipment_events.event_type, shipment_events.occurred_at FROM public.shipment_events;')
),
checks(check_name, ok) AS (
    SELECT 'target_database', current_database() = 'nexus_ai'
    UNION ALL SELECT 'server_major_16', current_setting('server_version_num')::integer / 10000 = 16
    UNION ALL SELECT 'database_owner_unchanged',
        (SELECT pg_get_userbyid(datdba) = 'postgres' FROM pg_database WHERE datname = current_database())
    UNION ALL SELECT 'three_safe_roles',
        (SELECT count(*) = 3 AND bool_and(NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolinherit OR rolreplication OR rolbypassrls))
         FROM pg_roles WHERE rolname IN (SELECT role_name FROM roles))
    UNION ALL SELECT 'owner_cannot_login', NOT (SELECT rolcanlogin FROM pg_roles WHERE rolname = 'nexus_owner')
    UNION ALL SELECT 'no_memberships_in_either_direction', NOT EXISTS (
        SELECT 1 FROM pg_auth_members m
        WHERE m.roleid IN (SELECT oid FROM pg_roles WHERE rolname IN (SELECT role_name FROM roles))
           OR m.member IN (SELECT oid FROM pg_roles WHERE rolname IN (SELECT role_name FROM roles))
    )
    UNION ALL SELECT 'designated_object_ownership', (
        SELECT count(*) = 9 AND bool_and(pg_get_userbyid(c.relowner) = 'nexus_owner')
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND
            (c.relname IN (SELECT object_name FROM objects) OR c.relname = 'audit_events_id_seq')
    )
    UNION ALL SELECT 'public_relation_count',
        (SELECT count(*) = 22 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public')
    UNION ALL SELECT 'no_public_functions',
        NOT EXISTS (SELECT 1 FROM pg_proc WHERE pronamespace = 'public'::regnamespace)
    UNION ALL SELECT 'schema_owner',
        (SELECT pg_get_userbyid(nspowner) = 'nexus_owner' FROM pg_namespace WHERE nspname = 'public')
    UNION ALL SELECT 'runtime_database_scope', bool_and(
        has_database_privilege(role_name::name, current_database(), 'CONNECT')
        AND NOT has_database_privilege(role_name::name, current_database(), 'CREATE')
        AND NOT has_database_privilege(role_name::name, current_database(), 'TEMP')
        AND NOT has_database_privilege(role_name::name, current_database(), 'CONNECT WITH GRANT OPTION')
    ) FROM runtime_roles
    UNION ALL SELECT 'runtime_schema_scope', bool_and(
        has_schema_privilege(role_name::name, 'public', 'USAGE')
        AND NOT has_schema_privilege(role_name::name, 'public', 'CREATE')
        AND NOT has_schema_privilege(role_name::name, 'public', 'USAGE WITH GRANT OPTION')
    ) FROM runtime_roles
    UNION ALL SELECT 'public_database_revoked', NOT EXISTS (
        SELECT 1 FROM pg_database d,
            LATERAL aclexplode(coalesce(d.datacl, acldefault('d', d.datdba))) a
        WHERE d.datname = current_database() AND a.grantee = 0
    )
    UNION ALL SELECT 'public_schema_revoked', NOT EXISTS (
        SELECT 1 FROM pg_namespace n,
            LATERAL aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
        WHERE n.nspname = 'public' AND a.grantee = 0
    )
    UNION ALL SELECT 'public_relation_and_column_revoked', NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace,
            LATERAL aclexplode(coalesce(c.relacl, '{}'::aclitem[])) a
        WHERE n.nspname = 'public' AND a.grantee = 0
        UNION ALL
        SELECT 1 FROM pg_attribute p JOIN pg_class c ON c.oid = p.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace,
            LATERAL aclexplode(coalesce(p.attacl, '{}'::aclitem[])) a
        WHERE n.nspname = 'public' AND a.grantee = 0
    )
    UNION ALL SELECT 'exact_effective_table_privileges', bool_and(
        has_table_privilege(r.role_name::name, 'public.' || o.object_name, p.privilege)
            = (r.role_name = 'nexus_tool' AND o.is_view AND p.privilege = 'SELECT')
        AND NOT has_table_privilege(r.role_name::name, 'public.' || o.object_name, p.privilege || ' WITH GRANT OPTION')
    ) FROM runtime_roles r CROSS JOIN objects o CROSS JOIN
        (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('DELETE'), ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')) p(privilege)
    UNION ALL SELECT 'exact_effective_column_privileges', bool_and(
        has_column_privilege(r.role_name::name, c.oid, a.attnum, p.privilege) =
          ((r.role_name = 'nexus_tool' AND o.is_view AND p.privilege = 'SELECT') OR
           (r.role_name = 'nexus_app' AND o.object_name = 'audit_events' AND p.privilege = 'INSERT'
            AND a.attname IN (SELECT column_name FROM writer_columns)))
        AND NOT has_column_privilege(r.role_name::name, c.oid, a.attnum, p.privilege || ' WITH GRANT OPTION')
    ) FROM runtime_roles r CROSS JOIN objects o
      JOIN pg_namespace n ON n.nspname = 'public'
      JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = o.object_name
      JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
      CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('REFERENCES')) p(privilege)
    UNION ALL SELECT 'no_sequence_privileges', bool_and(
        NOT has_sequence_privilege(r.role_name::name, 'public.audit_events_id_seq', p.privilege)
    ) FROM runtime_roles r CROSS JOIN (VALUES ('USAGE'), ('SELECT'), ('UPDATE')) p(privilege)
    UNION ALL SELECT 'owner_rights_exact_views', bool_and(
        c.relkind = 'v' AND pg_get_userbyid(c.relowner) = 'nexus_owner'
        AND coalesce(c.reloptions @> ARRAY['security_invoker=false'], false)
        AND ARRAY(SELECT a.attname::text FROM pg_attribute a
                  WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum) = v.columns
        AND lower(regexp_replace(replace(pg_get_viewdef(c.oid, true), 'public.', ''), '[[:space:]]', '', 'g'))
          = lower(regexp_replace(replace(v.definition, 'public.', ''), '[[:space:]]', '', 'g'))
    ) FROM view_contract v JOIN pg_namespace n ON n.nspname = 'public'
      JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = v.view_name
    UNION ALL SELECT 'no_row_isolation_claim', NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND (c.relrowsecurity OR c.relforcerowsecurity)
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_policy p JOIN pg_class c ON c.oid = p.polrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public'
    )
    UNION ALL SELECT 'global_creator_function_default_revoked', EXISTS (
        SELECT 1 FROM pg_default_acl d WHERE d.defaclrole = 'nexus_owner'::regrole
        AND d.defaclnamespace = 0 AND d.defaclobjtype = 'f'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_default_acl d, LATERAL aclexplode(d.defaclacl) a
        WHERE d.defaclrole = 'nexus_owner'::regrole AND
          (a.grantee = 0 OR a.grantee IN ('nexus_app'::regrole, 'nexus_tool'::regrole))
    )
    UNION ALL SELECT 'runtime_login_search_paths', bool_and(EXISTS (
        SELECT 1 FROM pg_db_role_setting s
        WHERE s.setrole = r.role_name::regrole
        AND s.setdatabase = (SELECT oid FROM pg_database WHERE datname = current_database())
        AND 'search_path=pg_catalog, public' = ANY(s.setconfig)
    )) FROM runtime_roles r
)
SELECT check_name, coalesce(ok, false) AS ok FROM checks ORDER BY check_name;
