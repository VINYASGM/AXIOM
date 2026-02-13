"""
Database Service
Handles PostgreSQL interactions using asyncpg.
"""
import os
import json
import asyncpg
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

class DatabaseConfig:
    """Database configuration"""
    DB_URL = os.getenv("DATABASE_URL", "postgresql://axiom:axiom@axiom-postgres:5432/axiom")

class DatabaseService:
    """
    Manages database connections and persistence for SDOs.
    """
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._url = DatabaseConfig.DB_URL

    async def initialize(self) -> bool:
        """Initialize database connection pool and schema."""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(self._url)
            
            # Initialize Schema
            async with self.pool.acquire() as conn:
                await self._create_schema(conn)
                
            print(f"Connected to PostgreSQL at {self._url.split('@')[-1]}")
            return True
        except Exception as e:
            print(f"Failed to initialize DatabaseService: {e}")
            return False

    async def _create_schema(self, conn: asyncpg.Connection):
        """Create necessary tables if they don't exist."""
        # SDO Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sdos (
                id UUID PRIMARY KEY,
                raw_intent TEXT NOT NULL,
                parsed_intent JSONB,
                language TEXT DEFAULT 'python',
                status TEXT NOT NULL,
                confidence FLOAT DEFAULT 0.0,
                code TEXT,
                selected_candidate_id TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                meta JSONB DEFAULT '{}'::jsonb,
                history JSONB DEFAULT '[]'::jsonb
            );
        """)

        # Candidates Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id UUID PRIMARY KEY,
                sdo_id UUID REFERENCES sdos(id) ON DELETE CASCADE,
                code TEXT NOT NULL,
                confidence FLOAT,
                verification_passed BOOLEAN DEFAULT FALSE,
                verification_score FLOAT DEFAULT 0.0,
                verification_result JSONB,
                pruned BOOLEAN DEFAULT FALSE,
                model_id TEXT,
                reasoning TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Add column if not exists (migration)
        try:
            await conn.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS verification_result JSONB;")
            await conn.execute("ALTER TABLE sdos ADD COLUMN IF NOT EXISTS history JSONB DEFAULT '[]'::jsonb;")
        except Exception:
            pass
        
        # Verification Results Table (Legacy/Alternate)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS verification_results (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                candidate_id UUID REFERENCES candidates(id) ON DELETE CASCADE,
                passed BOOLEAN NOT NULL,
                score FLOAT,
                details JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # =====================================================================
        # RBAC Tables - Phase 7
        # =====================================================================
        
        # Organizations Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                plan TEXT DEFAULT 'free',
                settings JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Users Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT,
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                role TEXT DEFAULT 'developer',
                settings JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        
        # Teams Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                description TEXT,
                settings JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Team Members Junction Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_id, user_id)
            );
        """)
        
        # API Keys Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                key_hash TEXT UNIQUE NOT NULL,
                key_prefix TEXT NOT NULL,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                permissions JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP WITH TIME ZONE,
                expires_at TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN DEFAULT TRUE
            );
        """)
        
        try:
            # Add org_id to SDOs for multi-tenancy
            await conn.execute("ALTER TABLE sdos ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id);")
            await conn.execute("ALTER TABLE sdos ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id);")
        except Exception:
            pass

        # Learner Model Table (Phase 3)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS learner_models (
                user_id TEXT PRIMARY KEY, 
                skills JSONB DEFAULT '{}'::jsonb,
                learning_style JSONB DEFAULT '{}'::jsonb,
                history JSONB DEFAULT '[]'::jsonb,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        try:
             await conn.execute("ALTER TABLE learner_models ADD COLUMN IF NOT EXISTS history JSONB DEFAULT '[]'::jsonb;")
        except Exception:
             pass

        # =====================================================================
        # Model Configuration Table - Dynamic Model Config (Design.md 3.3)
        # =====================================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS model_configurations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL UNIQUE,
                provider TEXT NOT NULL,
                model_id TEXT NOT NULL,
                tier TEXT NOT NULL CHECK (tier IN ('local', 'balanced', 'high_accuracy', 'frontier')),
                cost_per_1k_tokens DECIMAL(10,6) NOT NULL DEFAULT 0.0,
                accuracy_score DECIMAL(3,2) CHECK (accuracy_score BETWEEN 0 AND 1),
                capabilities JSONB DEFAULT '{}'::jsonb,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS model_configurations_tier_idx 
                ON model_configurations (tier, is_active);
            CREATE INDEX IF NOT EXISTS model_configurations_provider_idx 
                ON model_configurations (provider);
        """)

        # Seed default model configurations if table is empty
        existing = await conn.fetchval("SELECT COUNT(*) FROM model_configurations")
        if existing == 0:
            await conn.execute("""
                INSERT INTO model_configurations (name, provider, model_id, tier, cost_per_1k_tokens, accuracy_score, capabilities) VALUES
                ('deepseek-v3', 'deepseek', 'deepseek-chat', 'balanced', 0.002, 0.90, '{"code_generation": true, "reasoning": true}'::jsonb),
                ('claude-sonnet-4', 'anthropic', 'claude-sonnet-4-20250514', 'high_accuracy', 0.015, 0.92, '{"code_generation": true, "reasoning": true, "long_context": true}'::jsonb),
                ('gpt-4o', 'openai', 'gpt-4o-2024-11-20', 'high_accuracy', 0.030, 0.91, '{"code_generation": true, "vision": true}'::jsonb),
                ('gpt-4-turbo', 'openai', 'gpt-4-turbo', 'high_accuracy', 0.030, 0.88, '{"code_generation": true}'::jsonb),
                ('qwen3-8b', 'local', 'qwen3-8b-instruct', 'local', 0.000, 0.75, '{"code_generation": true}'::jsonb),
                ('mock', 'mock', 'mock-fast', 'local', 0.000, 0.50, '{"code_generation": true, "testing": true}'::jsonb)
                ON CONFLICT (name) DO NOTHING;
            """)

        # =====================================================================
        # Projection Stats Table - Read Model Aggregates (Design.md 2.2)
        # =====================================================================
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS projection_stats (
                entity_id UUID NOT NULL,
                stat_type TEXT NOT NULL,
                value BIGINT DEFAULT 0,
                metadata JSONB DEFAULT '{}'::jsonb,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entity_id, stat_type)
            );

            CREATE INDEX IF NOT EXISTS projection_stats_entity_idx 
                ON projection_stats (entity_id);
        """)


    async def save_sdo(self, sdo_data: Dict[str, Any]):
        """
        Upsert SDO record.
        """
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            # Upsert SDO
            await conn.execute("""
                INSERT INTO sdos (id, raw_intent, parsed_intent, language, status, confidence, code, selected_candidate_id, meta, history)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO UPDATE SET
                    raw_intent = EXCLUDED.raw_intent,
                    parsed_intent = EXCLUDED.parsed_intent,
                    language = EXCLUDED.language,
                    status = EXCLUDED.status,
                    confidence = EXCLUDED.confidence,
                    code = EXCLUDED.code,
                    selected_candidate_id = EXCLUDED.selected_candidate_id,
                    meta = EXCLUDED.meta,
                    history = EXCLUDED.history,
                    updated_at = CURRENT_TIMESTAMP;
            """,
            sdo_data['id'],
            sdo_data.get('raw_intent'),
            json.dumps(sdo_data.get('parsed_intent')) if sdo_data.get('parsed_intent') else None,
            sdo_data.get('language'),
            sdo_data.get('status'),
            sdo_data.get('confidence'),
            sdo_data.get('code'),
            sdo_data.get('selected_candidate_id'),
            json.dumps(sdo_data.get('meta', {})),
            json.dumps(sdo_data.get('history', []))
            )
            
            # Save candidates if present
            if 'candidates' in sdo_data and sdo_data['candidates']:
                for cand in sdo_data['candidates']:
                    # Helper to get dict result if it's already a dict or Pydantic model
                    v_res = cand.get('verification_result')
                    if hasattr(v_res, 'model_dump'):
                        v_res = v_res.model_dump()
                        
                    await conn.execute("""
                        INSERT INTO candidates (id, sdo_id, code, confidence, verification_passed, verification_score, verification_result, pruned, model_id, reasoning)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        ON CONFLICT (id) DO UPDATE SET
                            code = EXCLUDED.code,
                            confidence = EXCLUDED.confidence,
                            verification_passed = EXCLUDED.verification_passed,
                            verification_score = EXCLUDED.verification_score,
                            verification_result = EXCLUDED.verification_result,
                            pruned = EXCLUDED.pruned,
                            model_id = EXCLUDED.model_id,
                            reasoning = EXCLUDED.reasoning;
                    """,
                    cand['id'],
                    sdo_data['id'],
                    cand['code'],
                    cand['confidence'],
                    cand['verification_passed'],
                    cand['verification_score'],
                    json.dumps(v_res) if v_res else None,
                    cand['pruned'],
                    cand['model_id'],
                    cand['reasoning']
                    )

    async def get_sdo(self, sdo_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve SDO and its candidates.
        """
        if not self.pool:
            return None

        async with self.pool.acquire() as conn:
            # Fetch SDO with epoch timestamps and text ID
            row = await conn.fetchrow("""
                SELECT 
                    id::text, raw_intent, parsed_intent, language, status, confidence, code, 
                    selected_candidate_id, meta, history,
                    EXTRACT(EPOCH FROM created_at) as created_at,
                    EXTRACT(EPOCH FROM updated_at) as updated_at
                FROM sdos WHERE id = $1
            """, sdo_id)
            if not row:
                return None
            
            sdo = dict(row)
            if sdo['parsed_intent']:
                sdo['parsed_intent'] = json.loads(sdo['parsed_intent'])
            if sdo['meta']:
                sdo['meta'] = json.loads(sdo['meta'])
            if sdo.get('history'):
                sdo['history'] = json.loads(sdo['history'])
            else:
                sdo['history'] = []
            
            # Fetch Candidates with epoch timestamps and text ID
            c_rows = await conn.fetch("""
                SELECT 
                    id::text, sdo_id::text, code, confidence, verification_passed, verification_score, 
                    verification_result, pruned, model_id, reasoning,
                    EXTRACT(EPOCH FROM created_at) as created_at
                FROM candidates WHERE sdo_id = $1
            """, sdo_id)
            candidates = []
            for c_row in c_rows:
                cand = dict(c_row)
                if cand['verification_result']:
                    cand['verification_result'] = json.loads(cand['verification_result'])
                candidates.append(cand)
            
            sdo['candidates'] = candidates
            return sdo

    async def get_all_sdos(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve all SDOs (lightweight list).
        """
        if not self.pool:
            return []

        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id::text, raw_intent, parsed_intent, language, status, confidence, 
                    selected_candidate_id, meta,
                    EXTRACT(EPOCH FROM updated_at) as updated_at
                FROM sdos
                ORDER BY updated_at DESC
                LIMIT $1
            """, limit)
            
            results = []
            for row in rows:
                sdo = dict(row)
                if sdo['parsed_intent']:
                    sdo['parsed_intent'] = json.loads(sdo['parsed_intent'])
                if sdo['meta']:
                    sdo['meta'] = json.loads(sdo['meta'])
                results.append(sdo)
            return results

    async def save_learner_profile(self, profile: Dict[str, Any]):
        """
        Upsert Learner Profile.
        """
        if not self.pool:
            return

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO learner_models (user_id, skills, learning_style, history, updated_at)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    skills = EXCLUDED.skills,
                    learning_style = EXCLUDED.learning_style,
                    history = EXCLUDED.history,
                    updated_at = CURRENT_TIMESTAMP;
            """,
            profile['user_id'],
            json.dumps(profile.get('skills', {})),
            json.dumps(profile.get('learning_style', {})),
            json.dumps(profile.get('history', []))
            )

    async def get_learner_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve Learner Profile.
        """
        if not self.pool:
            return None

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT user_id, skills, learning_style, history, EXTRACT(EPOCH FROM updated_at) as updated_at
                FROM learner_models WHERE user_id = $1
            """, user_id)
            
            if not row:
                return None
            
            profile = dict(row)
            if profile['skills']:
                profile['skills'] = json.loads(profile['skills'])
            if profile['learning_style']:
                profile['learning_style'] = json.loads(profile['learning_style'])
            if profile['history']:
                profile['history'] = json.loads(profile['history'])
            
            return profile

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
