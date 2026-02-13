-- Revert initial schema

DROP TABLE IF EXISTS projection_stats;
DROP TABLE IF EXISTS model_configurations;
DROP TABLE IF EXISTS memory_nodes;
DROP TABLE IF EXISTS learner_models;
DROP TABLE IF EXISTS budgets;
DROP TABLE IF EXISTS generation_logs;
DROP TABLE IF EXISTS ivcus;
DROP TABLE IF EXISTS project_members;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS organizations CASCADE; -- cascade to remove user fk
ALTER TABLE IF EXISTS users DROP CONSTRAINT IF EXISTS fk_users_org;
DROP TABLE IF EXISTS users;

DROP EXTENSION IF EXISTS "pgcrypto";
DROP EXTENSION IF EXISTS "uuid-ossp";
