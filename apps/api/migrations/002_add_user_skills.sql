CREATE TABLE IF NOT EXISTS user_skills (
    user_id UUID NOT NULL REFERENCES users(id),
    skill VARCHAR(50) NOT NULL,
    proficiency INT NOT NULL DEFAULT 1,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, skill)
);

-- Index for fast lookup
CREATE INDEX idx_user_skills_user_id ON user_skills(user_id);
