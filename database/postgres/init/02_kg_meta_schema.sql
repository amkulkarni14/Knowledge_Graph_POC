-- kg_meta: ontology repository + graph build metadata.
-- Kept separate from the source data. The prototype stores the same information
-- as files under storage/ (see src/kg/stages/s09_ontology_repository.py); this DDL
-- is the production target for that repository.

CREATE SCHEMA IF NOT EXISTS kg_meta;

CREATE TABLE IF NOT EXISTS kg_meta.ontology (
    ontology_id text PRIMARY KEY,
    namespace   text NOT NULL,
    name        text NOT NULL,
    owner       text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (namespace, name)
);

CREATE TABLE IF NOT EXISTS kg_meta.ontology_version (
    ontology_id     text    NOT NULL REFERENCES kg_meta.ontology(ontology_id),
    version         integer NOT NULL,
    parent_version  integer,
    status          text    NOT NULL CHECK (status IN ('draft','pending_review','approved','rejected','superseded')),
    definition      jsonb   NOT NULL,
    definition_hash text    NOT NULL,
    change_note     text,
    created_by      text    NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    approved_by     text,
    approved_at     timestamptz,
    PRIMARY KEY (ontology_id, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_one_approved
    ON kg_meta.ontology_version(ontology_id) WHERE status = 'approved';

CREATE TABLE IF NOT EXISTS kg_meta.ai_suggestion (
    suggestion_id      bigserial PRIMARY KEY,
    request_id         uuid    NOT NULL,
    ontology_id        text    NOT NULL,
    base_version       integer NOT NULL,
    kind               text    NOT NULL CHECK (kind IN ('class','relationship','attribute','duplicate')),
    payload            jsonb   NOT NULL,
    confidence         numeric(4,3),
    validation         text    NOT NULL CHECK (validation IN ('valid','invalid','needs_review')),
    problems           jsonb   NOT NULL DEFAULT '[]',
    decision           text    CHECK (decision IN ('approved','edited','rejected')),
    decided_by         text,
    decided_at         timestamptz,
    applied_in_version integer
);

CREATE TABLE IF NOT EXISTS kg_meta.ai_request_log (
    request_id     uuid PRIMARY KEY,
    ontology_id    text NOT NULL,
    requested_by   text NOT NULL,
    model          text NOT NULL,
    prompt_hash    text NOT NULL,
    tables_shared  text[] NOT NULL,
    samples_shared boolean NOT NULL,
    attempts       integer NOT NULL,
    outcome        text NOT NULL,
    latency_ms     integer,
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kg_meta.ontology_audit (
    audit_id    bigserial PRIMARY KEY,
    ontology_id text NOT NULL,
    version     integer,
    action      text NOT NULL,
    actor       text NOT NULL,
    detail      jsonb NOT NULL DEFAULT '{}',
    at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kg_meta.graph_build (
    build_id          text PRIMARY KEY,
    ontology_id       text    NOT NULL,
    ontology_version  integer NOT NULL,
    mode              text    NOT NULL CHECK (mode IN ('full','incremental')),
    status            text    NOT NULL,
    source_watermarks jsonb   NOT NULL DEFAULT '{}',
    node_count        integer,
    edge_count        integer,
    validation        jsonb,
    artifact_uri      text,
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz
);

CREATE TABLE IF NOT EXISTS kg_meta.quarantine (
    id           bigserial PRIMARY KEY,
    build_id     text NOT NULL REFERENCES kg_meta.graph_build,
    stage        text NOT NULL,
    class_or_rel text NOT NULL,
    source_table text NOT NULL,
    source_key   jsonb NOT NULL,
    reason       text NOT NULL,
    at           timestamptz NOT NULL DEFAULT now()
);
