BEGIN;

-- Create proof type enum
CREATE TYPE proof_type_enum AS ENUM ('type_safety', 'memory_safety', 'contract_compliance', 'property_based');

-- Create proof_certificates table
CREATE TABLE proof_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ivcu_id UUID NOT NULL REFERENCES ivcus(id),
    
    -- Proof metadata
    proof_type proof_type_enum NOT NULL,
    verifier_version VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Traceability
    intent_id UUID NOT NULL,
    
    -- Cryptographic data
    ast_hash VARCHAR(64) NOT NULL,
    code_hash VARCHAR(64) NOT NULL,
    
    -- Verification signatures
    verifier_signatures JSONB NOT NULL DEFAULT '[]',
    
    -- Formal assertions
    assertions JSONB NOT NULL DEFAULT '[]',
    
    -- Proof data
    proof_data BYTEA NOT NULL,
    
    -- Hash chain for tamper detection
    hash_chain VARCHAR(128) NOT NULL,
    
    -- Master signature
    signature BYTEA NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(ivcu_id, proof_type)
);

CREATE INDEX proof_certificates_intent_idx ON proof_certificates (intent_id);
CREATE INDEX proof_certificates_hash_chain_idx ON proof_certificates (hash_chain);

COMMIT;
