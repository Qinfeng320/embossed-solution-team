-- =============================================================
-- views.sql — 售前工作台查询视图
-- 执行：psql -d <db> -f views.sql
-- =============================================================

-- 1. 已分类数据视图：规范化数据 + 命中分类 + 项目
CREATE OR REPLACE VIEW v_classified_data AS
SELECT
    nd.data_id,
    nd.project_id,
    p.project_code,
    p.project_name,
    nd.data_type,
    nd.schema_version,
    nd.status                 AS data_status,
    dc.classification_id,
    dc.category_id,
    c.category_name,
    c.route_agent_code        AS route_to_agent,
    dc.rule_id,
    dc.confidence,
    dc.is_primary,
    dc.classifier,
    dc.classified_at,
    nd.created_at
FROM normalized_data nd
JOIN data_classification dc ON dc.data_id = nd.data_id
JOIN dim_category c         ON c.category_id = dc.category_id
LEFT JOIN dim_project p     ON p.project_id = nd.project_id;

-- 2. 运行汇总视图：步骤数 / 成功数 / 耗时
CREATE OR REPLACE VIEW v_run_summary AS
SELECT
    r.run_id,
    r.run_code,
    r.project_id,
    p.project_code,
    r.orchestrator,
    r.stage,
    r.status                 AS run_status,
    r.total_steps,
    r.success_steps,
    COUNT(s.step_id)         AS step_count,
    COUNT(*) FILTER (WHERE s.status = 'success')  AS success_count,
    COUNT(*) FILTER (WHERE s.status = 'failed')   AS failed_count,
    SUM(s.duration_ms)       AS total_duration_ms,
    r.started_at,
    r.finished_at
FROM process_run r
LEFT JOIN process_step s ON s.run_id = r.run_id
LEFT JOIN dim_project p ON p.project_id = r.project_id
GROUP BY r.run_id, p.project_code;

-- 3. 每步骤最新输出视图（按创建时间取最新一条）
CREATE OR REPLACE VIEW v_agent_output_latest AS
SELECT o.*
FROM agent_output o
JOIN (
    SELECT step_id, MAX(created_at) AS max_c
    FROM agent_output
    GROUP BY step_id
) latest ON latest.step_id = o.step_id AND latest.max_c = o.created_at;

-- 4. 资产-文件视图：生成资产 + 文件元数据
CREATE OR REPLACE VIEW v_asset_files AS
SELECT
    a.asset_id,
    a.project_id,
    p.project_code,
    a.run_id,
    a.asset_type,
    a.title,
    a.version,
    a.content_format,
    a.status                AS asset_status,
    f.file_id,
    f.file_name,
    f.naming_pattern,
    f.domain_code,
    f.storage_path,
    f.file_size_bytes,
    f.file_hash,
    f.generated_at
FROM generated_asset a
LEFT JOIN file_metadata f ON f.asset_id = a.asset_id
LEFT JOIN dim_project p   ON p.project_id = a.project_id;

-- 5. 待归档运行视图：status='success' 且尚未归档（供 archive_all_completed 消费）
CREATE OR REPLACE VIEW v_runs_to_archive AS
SELECT run_id, run_code, project_id, finished_at
FROM process_run
WHERE status = 'success';
