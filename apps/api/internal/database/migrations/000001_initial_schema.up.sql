-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    org_id UUID,
    role VARCHAR(50) DEFAULT 'developer',
    trust_dial_default INTEGER DEFAULT 5 CHECK (trust_dial_default >= 1 AND trust_dial_default <= 10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    security_context VARCHAR(50) DEFAULT 'public',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    security_context VARCHAR(50) DEFAULT 'public',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Project Members for RBAC
CREATE TABLE IF NOT EXISTS project_members (
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer', -- 'viewer', 'editor', 'admin'
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (project_id, user_id)
);

-- IVCUs (Intent-Verified Code Units) - The core entity
CREATE TABLE IF NOT EXISTS ivcus (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1,
    
    -- Intent
    raw_intent TEXT NOT NULL,
    parsed_intent JSONB,
    
    -- Contracts
    contracts JSONB DEFAULT '[]',
    
    -- Verification
    verification_result JSONB,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Implementation
    code TEXT,
    language VARCHAR(50),
    
    -- Provenance
    model_id VARCHAR(255),
    model_version VARCHAR(50),
    generation_params JSONB,
    input_hash VARCHAR(64),
    output_hash VARCHAR(64),
    
    -- Metadata
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    parent_ids UUID[] DEFAULT '{}'
);

-- Generation logs for tracking costs
CREATE TABLE IF NOT EXISTS generation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ivcu_id UUID REFERENCES ivcus(id) ON DELETE CASCADE,
    model_id VARCHAR(255) NOT NULL,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Budgets for economic control
CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_type VARCHAR(50) NOT NULL, -- 'user', 'project', 'organization'
    owner_id UUID NOT NULL,
    limit_amount DECIMAL(10, 2) NOT NULL,
    used_amount DECIMAL(10, 2) DEFAULT 0,
    period VARCHAR(50) DEFAULT 'monthly', -- 'daily', 'monthly', 'total'
    reset_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Learner models for adaptive UI
CREATE TABLE IF NOT EXISTS learner_models (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    skills JSONB DEFAULT '{}',
    learning_style JSONB DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memory nodes for project context
CREATE TABLE IF NOT EXISTS memory_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL, -- 'decision', 'constraint', 'fact', 'dependency', 'convention', 'bugfix'
    content TEXT NOT NULL,
    embedding FLOAT[] DEFAULT '{}', -- Will store vector embeddings
    source_ivcu_id UUID REFERENCES ivcus(id) ON DELETE SET NULL,
    superseded_by UUID REFERENCES memory_nodes(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ivcus_project_id ON ivcus(project_id);
CREATE INDEX IF NOT EXISTS idx_ivcus_status ON ivcus(status);
CREATE INDEX IF NOT EXISTS idx_ivcus_created_by ON ivcus(created_by);
CREATE INDEX IF NOT EXISTS idx_generation_logs_ivcu_id ON generation_logs(ivcu_id);
CREATE INDEX IF NOT EXISTS idx_memory_nodes_project_id ON memory_nodes(project_id);
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id);

-- Add foreign key for org_id in users after organizations table exists
ALTER TABLE users ADD CONSTRAINT fk_users_org FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE SET NULL;

-- Insert a default dev user
INSERT INTO users (email, name, password_hash, role, trust_dial_default)
VALUES ('dev@axiom.local', 'Dev User', crypt('password', gen_salt('bf')), 'admin', 7)
ON CONFLICT (email) DO NOTHING;

-- Model configurations for DynamicModelConfig
CREATE TABLE IF NOT EXISTS model_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    provider VARCHAR(100) NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    tier VARCHAR(50) NOT NULL, -- 'local', 'balanced', 'high_accuracy', 'frontier'
    cost_per_1k_tokens DECIMAL(10, 6) DEFAULT 0,
    accuracy_score FLOAT DEFAULT 0.5 CHECK (accuracy_score >= 0 AND accuracy_score <= 1),
    capabilities JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_configs_tier ON model_configurations(tier);
CREATE INDEX IF NOT EXISTS idx_model_configs_active ON model_configurations(is_active);

-- Seed default models
INSERT INTO model_configurations (name, provider, model_id, tier, cost_per_1k_tokens, accuracy_score, capabilities)
VALUES 
    ('mock', 'mock', 'mock-fast', 'local', 0.0, 0.5, '{"testing": true}'::jsonb),
    ('qwen3-8b', 'local', 'qwen3-8b', 'local', 0.0, 0.70, '{"privacy": true, "speed": true}'::jsonb),
    ('deepseek-v3', 'deepseek', 'deepseek-chat', 'balanced', 0.002, 0.90, '{"code_generation": true, "speed": true}'::jsonb),
    ('gpt-4-turbo', 'openai', 'gpt-4-turbo', 'high_accuracy', 0.03, 0.88, '{"code_generation": true, "analysis": true}'::jsonb),
    ('claude-sonnet', 'anthropic', 'claude-3-5-sonnet-latest', 'high_accuracy', 0.015, 0.92, '{"code_generation": true, "reasoning": true}'::jsonb),
    ('claude-opus', 'anthropic', 'claude-3-opus-20240229', 'frontier', 0.075, 0.95, '{"novel_problems": true, "complex_reasoning": true}'::jsonb)
ON CONFLICT (name) DO UPDATE SET
    cost_per_1k_tokens = EXCLUDED.cost_per_1k_tokens,
    accuracy_score = EXCLUDED.accuracy_score,
    capabilities = EXCLUDED.capabilities,
    updated_at = NOW();

-- Projection stats table for event sourcing
CREATE TABLE IF NOT EXISTS projection_stats (
    entity_id UUID NOT NULL,
    stat_type VARCHAR(100) NOT NULL,
    value INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (entity_id, stat_type)
);
