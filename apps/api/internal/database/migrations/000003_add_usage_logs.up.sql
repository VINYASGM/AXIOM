-- Create usage_logs table
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cost DECIMAL(12, 4) NOT NULL DEFAULT 0.0,
    operation_type VARCHAR(50) NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add budget columns to projects table if not exists
ALTER TABLE projects ADD COLUMN IF NOT EXISTS budget_limit DECIMAL(12, 4) DEFAULT 100.0;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS current_usage DECIMAL(12, 4) DEFAULT 0.0;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_usage_logs_project_id ON usage_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
