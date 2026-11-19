-- =============================================================
-- seed.sql — embossed-solution-team 基准数据
-- 灌入：ORCH + 11 位成员（9 域专家 + DOC-IN / DOCX 文档专员）、9 分类(+CROSS/UNC)、示例项目、分类规则
-- 执行：psql -d <db> -f seed.sql
-- =============================================================

-- ---------- 1. 智能体维度：ORCH + 11 位成员（9 域专家 + DOC-IN / DOCX） ----------
INSERT INTO dim_agent (agent_code, agent_name, agent_role, domain_label, description, model_binding, is_active) VALUES
('ORCH', '团长·方案编排',        'lead',   '方案总编排', '统筹 5 阶段流程、专家协作与质量门禁',               'WorkbuddyJudgment', true),
('IND',  '产业行业专家',          'domain', '产业行业',   '产业基础 / 行业趋势 / 产能布局分析',               'ModelJudgment',     true),
('POL',  '政策合规专家',          'domain', '政策合规',   '政策解读 / 合规审查 / 补贴申报要点',               'ModelJudgment',     true),
('CUS',  '客户诉求专家',          'domain', '客户诉求',   '客户需求挖掘 / 痛点与诉求结构化',                   'ModelJudgment',     true),
('PRO',  '产品方案专家',          'domain', '产品方案',   '产品选型 / 方案组合 / 配置建议',                   'ModelJudgment',     true),
('CAS',  '案例标杆专家',          'domain', '案例标杆',   '标杆案例检索 / 对标与差异化',                       'ModelJudgment',     true),
('DAT',  '数据测算专家',          'domain', '数据测算',   '投资测算 / ROI / 容量与负荷模型',                  'ModelJudgment',     true),
('ARC',  '技术架构专家',          'domain', '技术架构',   '系统架构 / 集成设计 / 接口契约',                   'ModelJudgment',     true),
('MAT',  '物料资源专家',          'domain', '物料资源',   '设备清单 / 供应商 / 物料与排期',                   'ModelJudgment',     true),
('DOC-IN', '文档输入专员',        'specialist', '文档输入', '多源材料解析 / 七维度抽取 / 溯源与红线预检',     'ModelJudgment',     true),
('DOCX', '文档输出专员',          'specialist', '文档输出', '标准模板渲染 / 保真输出 / 编校检查',             'ModelJudgment',     true),
('VER',  '验证评审专家',          'domain', '验证评审',   '方案验证 / 评审打分 / 一致性校验',                 'WorkbuddyJudgment', true)
ON CONFLICT (agent_code) DO NOTHING;

-- ---------- 2. 分类维度：9 域 + 跨域 + 未分类 ----------
INSERT INTO dim_category (category_id, category_name, parent_category_id, route_agent_code, description) VALUES
('IND',  '产业行业',   NULL, 'IND',  '产业与行业维度数据'),
('POL',  '政策合规',   NULL, 'POL',  '政策与合规维度数据'),
('CUS',  '客户诉求',   NULL, 'CUS',  '客户需求与诉求维度数据'),
('PRO',  '产品方案',   NULL, 'PRO',  '产品与方案维度数据'),
('CAS',  '案例标杆',   NULL, 'CAS',  '标杆案例维度数据'),
('DAT',  '数据测算',   NULL, 'DAT',  '测算与数据维度数据'),
('ARC',  '技术架构',   NULL, 'ARC',  '架构与集成维度数据'),
('MAT',  '物料资源',   NULL, 'MAT',  '物料与资源维度数据'),
('VER',  '验证评审',   NULL, 'VER',  '验证与评审维度数据'),
('CROSS','跨域综合',   NULL, 'ORCH', '跨多个域的综合型数据'),
('UNC',  '未分类',     NULL, 'ORCH', '暂无法判定归属的数据')
ON CONFLICT (category_id) DO NOTHING;

-- ---------- 3. 分类规则（按 priority 降序评估） ----------
INSERT INTO classification_rule (rule_id, category_id, rule_code, rule_name, match_dimension, match_operator, match_value, priority, weight, enabled) VALUES
(gen_random_uuid(), 'IND',  'RULE_IND_01',   '产业报告识别',   'data_type', 'equals', 'industry_report', 90, 1.00, true),
(gen_random_uuid(), 'CUS',  'RULE_CUS_01',   '需求文档识别',   'data_type', 'equals', 'requirement',     85, 1.00, true),
(gen_random_uuid(), 'POL',  'RULE_POL_01',   '政策文档识别',   'data_type', 'equals', 'policy_doc',      80, 1.00, true),
(gen_random_uuid(), 'PRO',  'RULE_PRO_01',   '产品方案识别',   'tags',      'in',     '["product","solution"]', 75, 0.90, true),
(gen_random_uuid(), 'CAS',  'RULE_CAS_01',   '标杆案例识别',   'data_type', 'equals', 'case_doc',        70, 1.00, true),
(gen_random_uuid(), 'DAT',  'RULE_DAT_01',   '预算测算识别',   'data_type', 'equals', 'budget_sheet',    72, 1.00, true),
(gen_random_uuid(), 'ARC',  'RULE_ARC_01',   '架构集成识别',   'tags',      'in',     '["architecture","integration"]', 68, 0.90, true),
(gen_random_uuid(), 'MAT',  'RULE_MAT_01',   '物料清单识别',   'data_type', 'equals', 'bom_list',        66, 1.00, true),
(gen_random_uuid(), 'VER',  'RULE_VER_01',   '评审草稿识别',   'data_type', 'equals', 'draft_review',    64, 1.00, true),
(gen_random_uuid(), 'CROSS','RULE_CROSS_01', '跨域综合识别',   'tags',      'in',     '["cross","comprehensive"]', 60, 0.80, true),
(gen_random_uuid(), 'UNC',  'RULE_UNC_DEF',  '未分类兜底',     'data_type', 'equals', 'unknown',         10, 0.50, true);

-- ---------- 4. 示例项目 ----------
INSERT INTO dim_project (project_id, project_code, project_name, client_name, scenario_type, owner_agent, status)
VALUES (gen_random_uuid(), 'EISA-2026-001', '某职业院校产教融合实训基地建设项目', 'XX 职业技术学院', '产教融合', 'ORCH', 'active')
ON CONFLICT (project_code) DO NOTHING;
