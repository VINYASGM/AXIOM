DROP TABLE IF EXISTS usage_logs;

ALTER TABLE projects DROP COLUMN IF EXISTS budget_limit;
ALTER TABLE projects DROP COLUMN IF EXISTS current_usage;
