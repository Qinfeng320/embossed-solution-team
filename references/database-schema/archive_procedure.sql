-- =============================================================
-- archive_procedure.sql — 过程数据自动归档
-- 提供 archive_run()（单运行）与 archive_all_completed()（批量），
-- 并给出 pg_cron 定时调度示例。
-- 执行：psql -d <db> -f archive_procedure.sql
-- =============================================================

-- 单运行归档：热表 -> 归档表（硬迁移），并以 archive_batch 溯源
CREATE OR REPLACE FUNCTION archive_run(
    p_run_id     UUID,
    p_archived_by VARCHAR(20) DEFAULT 'system'
) RETURNS UUID AS $$
DECLARE
    v_batch  UUID;
    v_count  INT := 0;
BEGIN
    -- 仅归档 status='success' 且未归档的运行
    IF NOT EXISTS (
        SELECT 1 FROM process_run WHERE run_id = p_run_id AND status = 'success'
    ) THEN
        RAISE NOTICE 'run % 不处于可归档(success)状态，跳过', p_run_id;
        RETURN NULL;
    END IF;

    -- 1) 创建归档批次
    INSERT INTO archive_batch (batch_id, batch_code, trigger, archived_by, started_at, status)
    VALUES (
        gen_random_uuid(),
        'ARCH-' || to_char(now(), 'YYYYMMDD-HH24MISS') || '-' || substring(p_run_id::text, 1, 8),
        'manual', p_archived_by, now(), 'running'
    )
    RETURNING batch_id INTO v_batch;

    -- 2) 归档步骤（含 outputs + 外发 handoffs 的完整快照）
    INSERT INTO process_step_archive (
        batch_id, original_step_id, run_id, step_seq, agent_code, category_id,
        input_ref, status, started_at, finished_at, duration_ms, retry_count, payload_snapshot
    )
    SELECT
        v_batch, s.step_id, s.run_id, s.step_seq, s.agent_code, s.category_id,
        s.input_ref, s.status, s.started_at, s.finished_at, s.duration_ms, s.retry_count,
        jsonb_build_object(
            'step', jsonb_build_object(
                'step_id', s.step_id, 'run_id', s.run_id, 'step_seq', s.step_seq,
                'agent_code', s.agent_code, 'category_id', s.category_id,
                'input_ref', s.input_ref, 'status', s.status,
                'started_at', s.started_at, 'finished_at', s.finished_at,
                'duration_ms', s.duration_ms, 'retry_count', s.retry_count),
            'outputs', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'output_id', o.output_id, 'step_id', o.step_id, 'agent_code', o.agent_code,
                    'output_type', o.output_type, 'content', o.content, 'token_usage', o.token_usage,
                    'model_used', o.model_used, 'quality_score', o.quality_score))
                FROM agent_output o WHERE o.step_id = s.step_id), '[]'::jsonb),
            'handoffs_out', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'contract_id', h.contract_id, 'run_id', h.run_id, 'from_step_id', h.from_step_id,
                    'to_step_id', h.to_step_id, 'contract_type', h.contract_type, 'payload', h.payload,
                    'status', h.status))
                FROM handoff_contract h WHERE h.from_step_id = s.step_id), '[]'::jsonb)
        )
    FROM process_step s
    WHERE s.run_id = p_run_id;

    GET DIAGNOSTICS v_count = ROW_COUNT;

    -- 3) 归档输出（独立归档表，便于直接检索）
    INSERT INTO agent_output_archive (
        batch_id, original_output_id, original_step_id, agent_code,
        output_type, content, token_usage, model_used, quality_score
    )
    SELECT
        v_batch, o.output_id, o.step_id, o.agent_code,
        o.output_type, o.content, o.token_usage, o.model_used, o.quality_score
    FROM agent_output o
    JOIN process_step s ON s.step_id = o.step_id
    WHERE s.run_id = p_run_id;

    -- 4) 从热表删除（先 outputs 再 steps）
    --    交接契约已随各步骤快照(payload_snapshot.handoffs_out)留存，此处清理热表行以避免外键冲突
    DELETE FROM handoff_contract
    WHERE run_id = p_run_id;

    DELETE FROM agent_output
    WHERE step_id IN (SELECT step_id FROM process_step WHERE run_id = p_run_id);

    DELETE FROM process_step
    WHERE run_id = p_run_id;

    -- 5) 收尾：批次与运行状态
    UPDATE archive_batch
    SET finished_at = now(), record_count = v_count, status = 'done'
    WHERE batch_id = v_batch;

    UPDATE process_run
    SET status = 'archived', finished_at = COALESCE(finished_at, now())
    WHERE run_id = p_run_id;

    RAISE NOTICE 'run % 归档完成，批次 %，步骤数 %', p_run_id, v_batch, v_count;
    RETURN v_batch;
END;
$$ LANGUAGE plpgsql;

-- 批量归档：归档所有待归档运行
CREATE OR REPLACE FUNCTION archive_all_completed(
    p_archived_by VARCHAR(20) DEFAULT 'system'
) RETURNS INT AS $$
DECLARE
    r       RECORD;
    n       INT := 0;
    v_batch UUID;
BEGIN
    FOR r IN SELECT run_id FROM v_runs_to_archive LOOP
        v_batch := archive_run(r.run_id, p_archived_by);
        IF v_batch IS NOT NULL THEN
            n := n + 1;
        END IF;
    END LOOP;
    RAISE NOTICE '本次共归档 % 个运行', n;
    RETURN n;
END;
$$ LANGUAGE plpgsql;

-- =============================================================
-- 定时调度（需 pg_cron 扩展）
--   每 6 小时归档一次所有已完成运行
-- 若环境无 pg_cron，可用系统 crontab 调起：
--   0 */6 * * * psql -d <db> -c "SELECT archive_all_completed('scheduler');"
-- =============================================================
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule(
--     'archive_completed_runs',
--     '0 */6 * * *',
--     $$ SELECT archive_all_completed('scheduler'); $$
-- );
