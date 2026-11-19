-- =============================================================
-- embossed-solution-team 数据库 DDL (PostgreSQL 14+)
-- 专家团：ORCH + 11 位成员 (IND/POL/CUS/PRO/CAS/DAT/ARC/MAT/DOC-IN/DOCX/VER)
-- 流程：raw_ingest -> normalized_data -> 分类 -> process -> 归档 -> generated_asset -> file_metadata
-- 建表顺序已调整为「被引用表在前」，raw_ingest<->normalized_data 的循环外键
-- 通过 ALTER TABLE 在两张表创建后补加，避免前向引用报错。
-- =============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================================================
-- 3. 维度表（dim_agent 先于引用它的表）
-- =========================================================
CREATE TABLE dim_agent (
    agent_code    VARCHAR(20) PRIMARY KEY,
    agent_name    VARCHAR(100) NOT NULL,
    agent_role    VARCHAR(20),                 -- lead / domain
    domain_label  VARCHAR(100),
    description   TEXT,
    model_binding VARCHAR(100),
    is_active     BOOLEAN DEFAULT true
);

CREATE TABLE dim_project (
    project_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_code    VARCHAR(32) NOT NULL UNIQUE,
    project_name    VARCHAR(200) NOT NULL,
    client_name     VARCHAR(200),
    scenario_type   VARCHAR(50),
    owner_agent     VARCHAR(20) REFERENCES dim_agent(agent_code),
    status          VARCHAR(20) DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ
);

CREATE TABLE dim_category (
    category_id         VARCHAR(20) PRIMARY KEY,
    category_name       VARCHAR(100) NOT NULL,
    parent_category_id  VARCHAR(20) REFERENCES dim_category(category_id),
    route_agent_code    VARCHAR(20) REFERENCES dim_agent(agent_code),
    description         TEXT
);

-- =========================================================
-- 4. 分类子系统
-- =========================================================
CREATE TABLE raw_ingest (
    ingest_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id          UUID REFERENCES dim_project(project_id),
    source_type         VARCHAR(20),           -- pdf/docx/pptx/text/api/form
    source_name         VARCHAR(255),
    source_path         TEXT,
    raw_size_bytes      BIGINT,
    checksum            CHAR(64),
    ingested_at         TIMESTAMPTZ DEFAULT now(),
    normalized_data_id  UUID,                 -- 循环外键，见文末 ALTER
    status              VARCHAR(20) DEFAULT 'pending'  -- pending/normalized/failed
);

CREATE TABLE normalized_data (
    data_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ingest_id         UUID REFERENCES raw_ingest(ingest_id),
    project_id        UUID REFERENCES dim_project(project_id),
    data_type         VARCHAR(50),
    normalized_payload JSONB NOT NULL,
    schema_version    VARCHAR(20),
    data_hash         CHAR(64),
    status            VARCHAR(20) DEFAULT 'classified', -- classified/processing/done
    created_at        TIMESTAMPTZ DEFAULT now(),
    created_by        VARCHAR(20)
);
CREATE INDEX ix_normalized_data_hash ON normalized_data(data_hash);

-- 补加循环外键：raw_ingest.normalized_data_id -> normalized_data.data_id
ALTER TABLE raw_ingest
    ADD CONSTRAINT fk_raw_normalized
    FOREIGN KEY (normalized_data_id) REFERENCES normalized_data(data_id);

CREATE TABLE classification_rule (
    rule_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id     VARCHAR(20) REFERENCES dim_category(category_id),
    rule_code       VARCHAR(50) UNIQUE,
    rule_name       VARCHAR(200),
    match_dimension VARCHAR(50),
    match_operator  VARCHAR(20),              -- equals/in/like/regex/range
    match_value     TEXT,
    priority        INT,
    weight          NUMERIC(5,2),
    enabled         BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ
);

CREATE TABLE data_classification (
    classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_id           UUID NOT NULL REFERENCES normalized_data(data_id),
    category_id       VARCHAR(20) NOT NULL REFERENCES dim_category(category_id),
    rule_id           UUID REFERENCES classification_rule(rule_id),
    confidence        NUMERIC(5,4),
    is_primary        BOOLEAN,
    classifier        VARCHAR(20),           -- auto / manual
    classified_at     TIMESTAMPTZ DEFAULT now(),
    UNIQUE(data_id, category_id)
);

-- =========================================================
-- 5. 过程数据与归档子系统
-- =========================================================
CREATE TABLE process_run (
    run_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID REFERENCES dim_project(project_id),
    run_code     VARCHAR(50) UNIQUE,
    orchestrator VARCHAR(20) REFERENCES dim_agent(agent_code),
    trigger_type VARCHAR(20),                -- manual/api/scheduled
    stage        VARCHAR(20),                -- stage1..stage5
    status       VARCHAR(20) DEFAULT 'running', -- running/success/failed/archived
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    total_steps  INT,
    success_steps INT
);

CREATE TABLE process_step (
    step_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       UUID REFERENCES process_run(run_id),
    step_seq     INT,
    agent_code   VARCHAR(20) REFERENCES dim_agent(agent_code),
    category_id  VARCHAR(20) REFERENCES dim_category(category_id),
    input_ref    UUID,
    status       VARCHAR(20) DEFAULT 'pending', -- pending/running/success/failed/skipped
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    duration_ms  BIGINT,
    retry_count  INT DEFAULT 0,
    UNIQUE(run_id, step_seq)
);

CREATE TABLE agent_output (
    output_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id      UUID NOT NULL REFERENCES process_step(step_id),
    agent_code   VARCHAR(20) REFERENCES dim_agent(agent_code),
    output_type  VARCHAR(30),                -- narrative/judgment/citation/teardown/metric
    content      JSONB NOT NULL,
    token_usage  INT,
    model_used   VARCHAR(100),
    quality_score NUMERIC(5,2),
    created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ix_agent_output_step_type ON agent_output(step_id, output_type);

CREATE TABLE handoff_contract (
    contract_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        UUID REFERENCES process_run(run_id),
    from_step_id  UUID REFERENCES process_step(step_id),
    to_step_id    UUID REFERENCES process_step(step_id),
    contract_type VARCHAR(20),               -- handoff/interaction/verification
    payload       JSONB NOT NULL,
    status        VARCHAR(20) DEFAULT 'pending', -- pending/accepted/rejected
    created_at    TIMESTAMPTZ,
    resolved_at   TIMESTAMPTZ
);

CREATE TABLE archive_batch (
    batch_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_code   VARCHAR(50) UNIQUE,
    trigger      VARCHAR(20),                -- on_complete/scheduled/manual
    archived_by  VARCHAR(20),
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    record_count INT,
    status       VARCHAR(20),
    note         TEXT
);

CREATE TABLE process_step_archive (
    archive_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id           UUID REFERENCES archive_batch(batch_id),
    original_step_id   UUID,
    run_id             UUID,
    step_seq           INT,
    agent_code         VARCHAR(20),
    category_id        VARCHAR(20),
    input_ref          UUID,
    status             VARCHAR(20),
    started_at         TIMESTAMPTZ,
    finished_at        TIMESTAMPTZ,
    duration_ms        BIGINT,
    retry_count        INT,
    archived_at        TIMESTAMPTZ DEFAULT now(),
    payload_snapshot   JSONB
);

CREATE TABLE agent_output_archive (
    archive_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id           UUID REFERENCES archive_batch(batch_id),
    original_output_id UUID,
    original_step_id   UUID,
    agent_code         VARCHAR(20),
    output_type        VARCHAR(30),
    content            JSONB NOT NULL,
    token_usage        INT,
    model_used         VARCHAR(100),
    quality_score      NUMERIC(5,2),
    archived_at        TIMESTAMPTZ DEFAULT now()
);

-- =========================================================
-- 6. 生成数据子系统
-- =========================================================
CREATE TABLE generated_asset (
    asset_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id     UUID REFERENCES dim_project(project_id),
    run_id         UUID REFERENCES process_run(run_id),
    asset_type     VARCHAR(30),              -- solution_doc/eval_report/teardown_bundle/knowledge_index
    title          VARCHAR(300) NOT NULL,
    version        VARCHAR(20),
    content_format VARCHAR(20),              -- md/json/pdf/docx
    content_ref    TEXT,
    content_hash   CHAR(64),
    status         VARCHAR(20) DEFAULT 'draft', -- draft/published/archived
    created_at     TIMESTAMPTZ DEFAULT now(),
    created_by     VARCHAR(20),
    published_at   TIMESTAMPTZ
);
CREATE INDEX ix_generated_asset_proj_type ON generated_asset(project_id, asset_type);

CREATE TABLE asset_version (
    version_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id     UUID REFERENCES generated_asset(asset_id),
    version_no   VARCHAR(20) NOT NULL,
    snapshot_ref TEXT,
    change_note  TEXT,
    created_at   TIMESTAMPTZ DEFAULT now(),
    created_by   VARCHAR(20),
    UNIQUE(asset_id, version_no)
);

-- =========================================================
-- 7. 文件元数据
-- =========================================================
CREATE TABLE file_metadata (
    file_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id       UUID NOT NULL REFERENCES generated_asset(asset_id),
    project_id     UUID REFERENCES dim_project(project_id),
    file_name      VARCHAR(255) NOT NULL,
    naming_pattern VARCHAR(100),
    project_code   VARCHAR(32),
    domain_code    VARCHAR(20),
    version_label  VARCHAR(20),
    seq            CHAR(2),
    file_ext       VARCHAR(10),
    storage_path   TEXT NOT NULL,
    file_hash      CHAR(64),
    file_size_bytes BIGINT,
    mime_type      VARCHAR(100),
    generated_at   TIMESTAMPTZ DEFAULT now(),
    uploaded_by    VARCHAR(20),
    UNIQUE(project_code, domain_code, version_label, seq, file_ext)
);
CREATE INDEX ix_file_metadata_proj_domain ON file_metadata(project_code, domain_code);

-- =========================================================
-- 补充索引（FK 列查询加速）
-- =========================================================
CREATE INDEX ix_raw_ingest_project ON raw_ingest(project_id);
CREATE INDEX ix_normalized_project ON normalized_data(project_id);
CREATE INDEX ix_data_classification_data ON data_classification(data_id);
CREATE INDEX ix_data_classification_cat ON data_classification(category_id);
CREATE INDEX ix_process_run_project ON process_run(project_id);
CREATE INDEX ix_process_step_run ON process_step(run_id);
CREATE INDEX ix_agent_output_agent ON agent_output(agent_code);
CREATE INDEX ix_handoff_run ON handoff_contract(run_id);
CREATE INDEX ix_generated_asset_run ON generated_asset(run_id);
CREATE INDEX ix_file_metadata_asset ON file_metadata(asset_id);
