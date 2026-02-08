INSERT INTO model_configurations (name, provider, model_id, tier, cost_per_1k_tokens, accuracy_score, capabilities)
VALUES 
    ('mock', 'mock', 'mock-fast', 'local', 0.0, 0.5, '{"testing": true}'::jsonb),
    ('qwen3-8b', 'local', 'qwen3-8b', 'local', 0.0, 0.70, '{"privacy": true}'::jsonb),
    ('deepseek-v3', 'deepseek', 'deepseek-chat', 'balanced', 0.002, 0.90, '{"code_generation": true}'::jsonb),
    ('gpt-4-turbo', 'openai', 'gpt-4-turbo', 'high_accuracy', 0.03, 0.88, '{"code_generation": true}'::jsonb),
    ('claude-sonnet', 'anthropic', 'claude-3-5-sonnet-latest', 'high_accuracy', 0.015, 0.92, '{"reasoning": true}'::jsonb),
    ('claude-opus', 'anthropic', 'claude-3-opus-20240229', 'frontier', 0.075, 0.95, '{"novel_problems": true}'::jsonb)
ON CONFLICT (name) DO NOTHING;
